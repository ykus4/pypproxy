package replay

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/ykus4/paxy/internal/store"
)

// Result is the outcome of one replay.
type Result struct {
	EntryID    int64         `json:"entry_id"`
	StatusCode int           `json:"status_code"`
	Body       []byte        `json:"body,omitempty"`
	DurationMs int64         `json:"duration_ms"`
	Error      string        `json:"error,omitempty"`
}

// Options controls replay behavior.
type Options struct {
	OverrideHost   string
	ExtraHeaders   map[string]string
	TimeoutSeconds int
	Count          int // number of times to replay (for fuzzing)
}

// Replayer replays captured entries.
type Replayer struct {
	client *http.Client
}

func New() *Replayer {
	return &Replayer{
		client: &http.Client{Timeout: 30 * time.Second},
	}
}

// Replay sends the request from a captured entry once and returns the result.
func (rp *Replayer) Replay(ctx context.Context, entry *store.Entry, opts Options) (*Result, error) {
	if opts.TimeoutSeconds > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, time.Duration(opts.TimeoutSeconds)*time.Second)
		defer cancel()
	}

	url := fmt.Sprintf("%s://%s%s", entry.Scheme, entry.Host, entry.Path)
	if entry.Query != "" {
		url += "?" + entry.Query
	}
	if opts.OverrideHost != "" {
		url = fmt.Sprintf("%s://%s%s", entry.Scheme, opts.OverrideHost, entry.Path)
	}

	req, err := http.NewRequestWithContext(ctx, entry.Method, url, bytes.NewReader(entry.ReqBody))
	if err != nil {
		return nil, err
	}

	for k, vs := range entry.ReqHeader {
		for _, v := range vs {
			req.Header.Add(k, v)
		}
	}
	for k, v := range opts.ExtraHeaders {
		req.Header.Set(k, v)
	}

	start := time.Now()
	resp, err := rp.client.Do(req)
	dur := time.Since(start).Milliseconds()
	if err != nil {
		return &Result{EntryID: entry.ID, DurationMs: dur, Error: err.Error()}, nil
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	return &Result{
		EntryID:    entry.ID,
		StatusCode: resp.StatusCode,
		Body:       body,
		DurationMs: dur,
	}, nil
}

// ReplayMany replays an entry multiple times concurrently (for load testing / fuzzing).
func (rp *Replayer) ReplayMany(ctx context.Context, entry *store.Entry, opts Options) ([]*Result, error) {
	count := opts.Count
	if count <= 0 {
		count = 1
	}

	results := make([]*Result, count)
	errs := make(chan error, count)
	type indexed struct {
		i int
		r *Result
	}
	ch := make(chan indexed, count)

	for i := 0; i < count; i++ {
		go func(i int) {
			r, err := rp.Replay(ctx, entry, opts)
			if err != nil {
				errs <- err
				return
			}
			ch <- indexed{i, r}
		}(i)
	}

	for i := 0; i < count; i++ {
		select {
		case idx := <-ch:
			results[idx.i] = idx.r
		case err := <-errs:
			return results, err
		}
	}
	return results, nil
}
