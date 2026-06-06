package interceptor

import (
	"bytes"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/ykus4/paxy/internal/rule"
	"github.com/ykus4/paxy/internal/store"
)

// Interceptor wires the rule engine into the HTTP flow and records traffic.
type Interceptor struct {
	Rules *rule.Manager
	Store *store.Store
}

func New(rules *rule.Manager, st *store.Store) *Interceptor {
	return &Interceptor{Rules: rules, Store: st}
}

// ProcessRequest applies rules to an outgoing request and records it.
// Returns (entry, block) where block=true means the request should be dropped.
func (ic *Interceptor) ProcessRequest(req *http.Request, scheme string) (*store.Entry, bool) {
	body, _ := io.ReadAll(req.Body)
	req.Body = io.NopCloser(bytes.NewReader(body))

	entry := &store.Entry{
		Method:    req.Method,
		Scheme:    scheme,
		Host:      req.Host,
		Path:      req.URL.Path,
		Query:     req.URL.RawQuery,
		ReqHeader: cloneHeader(req.Header),
		ReqBody:   body,
		Protocol:  scheme,
	}

	ctx := &rule.MatchContext{
		Method:  req.Method,
		Host:    req.Host,
		Path:    req.URL.Path,
		Headers: req.Header,
		Body:    body,
	}

	if r := ic.Rules.Match(ctx); r != nil {
		switch r.Action {
		case rule.ActionBlock:
			entry.Tags = append(entry.Tags, "blocked")
			ic.Store.Add(entry)
			return entry, true
		case rule.ActionModify:
			applyRequestMods(req, r.Modifications)
			entry.Modified = true
			newBody, _ := io.ReadAll(req.Body)
			req.Body = io.NopCloser(bytes.NewReader(newBody))
			entry.ReqBody = newBody
			entry.ReqHeader = cloneHeader(req.Header)
		case rule.ActionRedirect:
			entry.Tags = append(entry.Tags, "redirected")
		}
	}

	ic.Store.Add(entry)
	return entry, false
}

// ProcessResponse records the response and applies modifications.
func (ic *Interceptor) ProcessResponse(entry *store.Entry, resp *http.Response, start time.Time) {
	body, _ := io.ReadAll(resp.Body)
	resp.Body = io.NopCloser(bytes.NewReader(body))

	entry.StatusCode = resp.StatusCode
	entry.RespHeader = cloneHeader(resp.Header)
	entry.RespBody = body
	entry.DurationMs = time.Since(start).Milliseconds()

	ctx := &rule.MatchContext{
		Method:  entry.Method,
		Host:    entry.Host,
		Path:    entry.Path,
		Headers: resp.Header,
		Body:    body,
	}

	if r := ic.Rules.Match(ctx); r != nil && r.Action == rule.ActionModify {
		applyResponseMods(resp, r.Modifications)
		newBody, _ := io.ReadAll(resp.Body)
		resp.Body = io.NopCloser(bytes.NewReader(newBody))
		entry.RespBody = newBody
		entry.RespHeader = cloneHeader(resp.Header)
		entry.Modified = true
	}

	ic.Store.Update(entry)
}

func applyRequestMods(req *http.Request, mods []rule.Modification) {
	for _, m := range mods {
		if m.Target != "req_header" && m.Target != "req_body" {
			continue
		}
		switch m.Target {
		case "req_header":
			applyHeaderMod(req.Header, m)
		case "req_body":
			if m.Operation == "replace" {
				req.Body = io.NopCloser(strings.NewReader(m.Value))
			}
		}
	}
}

func applyResponseMods(resp *http.Response, mods []rule.Modification) {
	for _, m := range mods {
		switch m.Target {
		case "resp_header":
			applyHeaderMod(resp.Header, m)
		case "resp_body":
			if m.Operation == "replace" {
				resp.Body = io.NopCloser(strings.NewReader(m.Value))
			} else if m.Operation == "find_replace" {
				body, _ := io.ReadAll(resp.Body)
				newBody := strings.ReplaceAll(string(body), m.Find, m.Replace)
				resp.Body = io.NopCloser(strings.NewReader(newBody))
			}
		}
	}
}

func applyHeaderMod(h http.Header, m rule.Modification) {
	switch m.Operation {
	case "set":
		h.Set(m.Key, m.Value)
	case "delete":
		h.Del(m.Key)
	case "append":
		h.Add(m.Key, m.Value)
	}
}

func cloneHeader(h http.Header) map[string][]string {
	out := make(map[string][]string, len(h))
	for k, vs := range h {
		cp := make([]string, len(vs))
		copy(cp, vs)
		out[k] = cp
	}
	return out
}
