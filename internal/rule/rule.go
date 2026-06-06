package rule

import (
	"regexp"
	"strings"
)

type Action string

const (
	ActionPassthrough Action = "passthrough"
	ActionModify      Action = "modify"
	ActionBlock       Action = "block"
	ActionRedirect    Action = "redirect"
)

type MatchField string

const (
	FieldHost   MatchField = "host"
	FieldPath   MatchField = "path"
	FieldMethod MatchField = "method"
	FieldHeader MatchField = "header"
	FieldBody   MatchField = "body"
)

// Condition is a single match condition.
type Condition struct {
	Field   MatchField `json:"field"`
	Op      string     `json:"op"`    // contains, equals, regex, prefix
	Value   string     `json:"value"`
	Negate  bool       `json:"negate,omitempty"`
	compiled *regexp.Regexp
}

// Modification describes a header/body change to apply.
type Modification struct {
	Target    string `json:"target"`    // req_header, resp_header, req_body, resp_body
	Key       string `json:"key,omitempty"`
	Value     string `json:"value,omitempty"`
	Operation string `json:"operation"` // set, delete, replace, append
	Find      string `json:"find,omitempty"`
	Replace   string `json:"replace,omitempty"`
}

// Rule is an intercept rule with conditions and actions.
type Rule struct {
	ID           int64          `json:"id"`
	Name         string         `json:"name"`
	Enabled      bool           `json:"enabled"`
	Priority     int            `json:"priority"`
	Conditions   []Condition    `json:"conditions"`
	Action       Action         `json:"action"`
	Modifications []Modification `json:"modifications,omitempty"`
	RedirectURL  string         `json:"redirect_url,omitempty"`
}

// Manager holds all rules and applies them.
type Manager struct {
	rules []*Rule
}

func NewManager() *Manager {
	return &Manager{}
}

func (m *Manager) Add(r *Rule) {
	m.rules = append(m.rules, r)
	m.sort()
}

func (m *Manager) Update(r *Rule) {
	for i, existing := range m.rules {
		if existing.ID == r.ID {
			m.rules[i] = r
			m.sort()
			return
		}
	}
}

func (m *Manager) Delete(id int64) {
	for i, r := range m.rules {
		if r.ID == id {
			m.rules = append(m.rules[:i], m.rules[i+1:]...)
			return
		}
	}
}

func (m *Manager) List() []*Rule {
	out := make([]*Rule, len(m.rules))
	copy(out, m.rules)
	return out
}

// Match returns the first matching enabled rule, or nil.
func (m *Manager) Match(ctx *MatchContext) *Rule {
	for _, r := range m.rules {
		if !r.Enabled {
			continue
		}
		if matchAll(r.Conditions, ctx) {
			return r
		}
	}
	return nil
}

func (m *Manager) sort() {
	for i := 1; i < len(m.rules); i++ {
		for j := i; j > 0 && m.rules[j].Priority > m.rules[j-1].Priority; j-- {
			m.rules[j], m.rules[j-1] = m.rules[j-1], m.rules[j]
		}
	}
}

// MatchContext carries the data used to evaluate conditions.
type MatchContext struct {
	Method  string
	Host    string
	Path    string
	Headers map[string][]string
	Body    []byte
}

func matchAll(conds []Condition, ctx *MatchContext) bool {
	for _, c := range conds {
		if !matchOne(c, ctx) {
			return false
		}
	}
	return true
}

func matchOne(c Condition, ctx *MatchContext) bool {
	var val string
	switch c.Field {
	case FieldHost:
		val = ctx.Host
	case FieldPath:
		val = ctx.Path
	case FieldMethod:
		val = ctx.Method
	case FieldHeader:
		for k, vs := range ctx.Headers {
			if strings.EqualFold(k, c.Key()) {
				val = strings.Join(vs, ", ")
				break
			}
		}
	case FieldBody:
		val = string(ctx.Body)
	}

	var matched bool
	switch c.Op {
	case "equals":
		matched = val == c.Value
	case "contains":
		matched = strings.Contains(val, c.Value)
	case "prefix":
		matched = strings.HasPrefix(val, c.Value)
	case "regex":
		if c.compiled == nil {
			c.compiled, _ = regexp.Compile(c.Value)
		}
		if c.compiled != nil {
			matched = c.compiled.MatchString(val)
		}
	default:
		matched = strings.Contains(val, c.Value)
	}

	if c.Negate {
		return !matched
	}
	return matched
}

func (c *Condition) Key() string {
	// For header field, Value may be "Header-Name: pattern" format
	if idx := strings.Index(c.Value, ":"); idx > 0 {
		return strings.TrimSpace(c.Value[:idx])
	}
	return c.Value
}
