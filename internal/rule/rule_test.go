package rule_test

import (
	"testing"

	"github.com/ykus4/paxy/internal/rule"
)

func newCtx(method, host, path string) *rule.MatchContext {
	return &rule.MatchContext{
		Method:  method,
		Host:    host,
		Path:    path,
		Headers: map[string][]string{},
	}
}

// TestMatchNoRules verifies Match returns nil when the manager has no rules.
func TestMatchNoRules(t *testing.T) {
	m := rule.NewManager()
	got := m.Match(newCtx("GET", "example.com", "/"))
	if got != nil {
		t.Fatalf("expected nil, got %+v", got)
	}
}

// TestMatchByHostContains verifies Match returns a rule whose host condition
// uses the "contains" operator.
func TestMatchByHostContains(t *testing.T) {
	m := rule.NewManager()
	r := &rule.Rule{
		ID:      1,
		Name:    "host-contains",
		Enabled: true,
		Priority: 10,
		Action:  rule.ActionBlock,
		Conditions: []rule.Condition{
			{Field: rule.FieldHost, Op: "contains", Value: "example"},
		},
	}
	m.Add(r)

	got := m.Match(newCtx("GET", "www.example.com", "/"))
	if got == nil {
		t.Fatal("expected a matching rule, got nil")
	}
	if got.ID != 1 {
		t.Fatalf("expected rule ID 1, got %d", got.ID)
	}

	// Non-matching host should return nil.
	got = m.Match(newCtx("GET", "other.org", "/"))
	if got != nil {
		t.Fatalf("expected nil for non-matching host, got %+v", got)
	}
}

// TestMatchDisabledRuleSkipped verifies that a disabled rule is never returned
// by Match even when its conditions would otherwise match.
func TestMatchDisabledRuleSkipped(t *testing.T) {
	m := rule.NewManager()
	m.Add(&rule.Rule{
		ID:      2,
		Name:    "disabled",
		Enabled: false,
		Priority: 5,
		Action:  rule.ActionBlock,
		Conditions: []rule.Condition{
			{Field: rule.FieldHost, Op: "equals", Value: "example.com"},
		},
	})

	got := m.Match(newCtx("GET", "example.com", "/"))
	if got != nil {
		t.Fatalf("expected nil because rule is disabled, got %+v", got)
	}
}

// TestMatchPriorityOrdering verifies that when multiple rules match the
// context, the one with the highest Priority value is returned first.
func TestMatchPriorityOrdering(t *testing.T) {
	m := rule.NewManager()

	low := &rule.Rule{
		ID:      10,
		Name:    "low-priority",
		Enabled: true,
		Priority: 1,
		Action:  rule.ActionPassthrough,
		Conditions: []rule.Condition{
			{Field: rule.FieldPath, Op: "prefix", Value: "/"},
		},
	}
	high := &rule.Rule{
		ID:      20,
		Name:    "high-priority",
		Enabled: true,
		Priority: 100,
		Action:  rule.ActionBlock,
		Conditions: []rule.Condition{
			{Field: rule.FieldPath, Op: "prefix", Value: "/"},
		},
	}

	// Add in low-first order to ensure sorting is exercised.
	m.Add(low)
	m.Add(high)

	got := m.Match(newCtx("GET", "example.com", "/api/data"))
	if got == nil {
		t.Fatal("expected a match, got nil")
	}
	if got.ID != 20 {
		t.Fatalf("expected high-priority rule (ID 20), got ID %d", got.ID)
	}
}

// TestMatchNegateCondition verifies that a Condition with Negate=true matches
// when the underlying op does NOT match.
func TestMatchNegateCondition(t *testing.T) {
	m := rule.NewManager()
	m.Add(&rule.Rule{
		ID:      3,
		Name:    "negate-host",
		Enabled: true,
		Priority: 5,
		Action:  rule.ActionModify,
		Conditions: []rule.Condition{
			{Field: rule.FieldHost, Op: "equals", Value: "blocked.com", Negate: true},
		},
	})

	// Host is NOT "blocked.com" — negated condition is satisfied.
	got := m.Match(newCtx("GET", "allowed.com", "/"))
	if got == nil {
		t.Fatal("expected match when negated condition is satisfied, got nil")
	}

	// Host IS "blocked.com" — negated condition is NOT satisfied.
	got = m.Match(newCtx("GET", "blocked.com", "/"))
	if got != nil {
		t.Fatalf("expected nil when negated condition fails, got %+v", got)
	}
}

// TestMatchRegexOp verifies that the "regex" operator matches correctly.
func TestMatchRegexOp(t *testing.T) {
	m := rule.NewManager()
	m.Add(&rule.Rule{
		ID:      4,
		Name:    "regex-path",
		Enabled: true,
		Priority: 5,
		Action:  rule.ActionBlock,
		Conditions: []rule.Condition{
			{Field: rule.FieldPath, Op: "regex", Value: `^/api/v[0-9]+/`},
		},
	})

	cases := []struct {
		path    string
		wantHit bool
	}{
		{"/api/v1/users", true},
		{"/api/v42/items", true},
		{"/api/vX/bad", false},
		{"/static/file.js", false},
	}

	for _, tc := range cases {
		got := m.Match(newCtx("GET", "example.com", tc.path))
		if tc.wantHit && got == nil {
			t.Errorf("path %q: expected match, got nil", tc.path)
		}
		if !tc.wantHit && got != nil {
			t.Errorf("path %q: expected nil, got rule ID %d", tc.path, got.ID)
		}
	}
}

// TestDeleteRemovesRule verifies that after Delete the rule no longer appears
// in List and is no longer matched.
func TestDeleteRemovesRule(t *testing.T) {
	m := rule.NewManager()
	m.Add(&rule.Rule{
		ID:      5,
		Name:    "to-delete",
		Enabled: true,
		Priority: 5,
		Action:  rule.ActionBlock,
		Conditions: []rule.Condition{
			{Field: rule.FieldHost, Op: "equals", Value: "target.com"},
		},
	})

	// Confirm it is present before deletion.
	if got := m.Match(newCtx("GET", "target.com", "/")); got == nil {
		t.Fatal("rule should match before deletion")
	}
	if len(m.List()) != 1 {
		t.Fatalf("expected 1 rule before deletion, got %d", len(m.List()))
	}

	m.Delete(5)

	if len(m.List()) != 0 {
		t.Fatalf("expected 0 rules after deletion, got %d", len(m.List()))
	}
	if got := m.Match(newCtx("GET", "target.com", "/")); got != nil {
		t.Fatalf("expected nil after deletion, got %+v", got)
	}
}
