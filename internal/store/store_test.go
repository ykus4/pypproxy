package store_test

import (
	"testing"
	"time"

	"github.com/ykus4/paxy/internal/store"
)

// --- helpers ---

func newEntry(method, host, path, protocol string) *store.Entry {
	return &store.Entry{
		Method:   method,
		Host:     host,
		Path:     path,
		Protocol: protocol,
	}
}

// --- 1. Add and Get round-trip ---

func TestAddGet_AssignsID(t *testing.T) {
	s := store.New()
	e := s.Add(newEntry("GET", "example.com", "/foo", "http"))
	if e.ID == 0 {
		t.Fatal("expected non-zero ID after Add")
	}
}

func TestAddGet_IDsAreUnique(t *testing.T) {
	s := store.New()
	a := s.Add(newEntry("GET", "a.com", "/", "http"))
	b := s.Add(newEntry("POST", "b.com", "/", "http"))
	if a.ID == b.ID {
		t.Fatalf("expected distinct IDs, both got %d", a.ID)
	}
}

func TestAddGet_SetsCreatedAt(t *testing.T) {
	s := store.New()
	before := time.Now()
	e := s.Add(newEntry("GET", "example.com", "/", "http"))
	after := time.Now()

	if e.CreatedAt.Before(before) || e.CreatedAt.After(after) {
		t.Errorf("CreatedAt %v not in [%v, %v]", e.CreatedAt, before, after)
	}
}

func TestAddGet_PreservesExistingCreatedAt(t *testing.T) {
	s := store.New()
	ts := time.Date(2020, 1, 1, 0, 0, 0, 0, time.UTC)
	entry := newEntry("GET", "example.com", "/", "http")
	entry.CreatedAt = ts
	s.Add(entry)
	if !entry.CreatedAt.Equal(ts) {
		t.Errorf("expected CreatedAt to remain %v, got %v", ts, entry.CreatedAt)
	}
}

func TestAddGet_RoundTrip(t *testing.T) {
	s := store.New()
	added := s.Add(newEntry("PUT", "store.test", "/item", "https"))

	got, ok := s.Get(added.ID)
	if !ok {
		t.Fatalf("Get(%d) returned ok=false", added.ID)
	}
	if got != added {
		t.Error("Get did not return the same *Entry pointer")
	}
}

func TestGet_MissingID(t *testing.T) {
	s := store.New()
	_, ok := s.Get(99999)
	if ok {
		t.Error("expected ok=false for unknown ID")
	}
}

// --- 2. List with filter ---

func TestList_NoFilter(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "alpha.com", "/", "http"))
	s.Add(newEntry("POST", "beta.com", "/", "http"))
	s.Add(newEntry("DELETE", "gamma.com", "/", "https"))

	items, total := s.List(store.Filter{}, 0, 0)
	if total != 3 {
		t.Errorf("expected total=3, got %d", total)
	}
	if len(items) != 3 {
		t.Errorf("expected 3 items, got %d", len(items))
	}
}

func TestList_FilterByHost(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "alpha.com", "/", "http"))
	s.Add(newEntry("GET", "beta.com", "/", "http"))
	s.Add(newEntry("GET", "alpha.com", "/other", "http"))

	items, total := s.List(store.Filter{Host: "alpha.com"}, 0, 0)
	if total != 2 {
		t.Errorf("expected total=2, got %d", total)
	}
	for _, e := range items {
		if e.Host != "alpha.com" {
			t.Errorf("unexpected host %q in filtered results", e.Host)
		}
	}
}

func TestList_FilterByMethod(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "x.com", "/", "http"))
	s.Add(newEntry("POST", "x.com", "/", "http"))
	s.Add(newEntry("GET", "x.com", "/foo", "http"))

	items, total := s.List(store.Filter{Method: "GET"}, 0, 0)
	if total != 2 {
		t.Errorf("expected total=2, got %d", total)
	}
	for _, e := range items {
		if e.Method != "GET" {
			t.Errorf("unexpected method %q in filtered results", e.Method)
		}
	}
}

func TestList_FilterBySearch_MatchesHost(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "api.example.com", "/v1", "http"))
	s.Add(newEntry("GET", "other.com", "/v1", "http"))

	items, total := s.List(store.Filter{Search: "api.example"}, 0, 0)
	if total != 1 {
		t.Errorf("expected total=1, got %d", total)
	}
	if len(items) == 1 && items[0].Host != "api.example.com" {
		t.Errorf("unexpected host %q", items[0].Host)
	}
}

func TestList_FilterBySearch_MatchesPath(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "x.com", "/users/profile", "http"))
	s.Add(newEntry("GET", "x.com", "/orders", "http"))

	items, total := s.List(store.Filter{Search: "profile"}, 0, 0)
	if total != 1 {
		t.Errorf("expected total=1, got %d", total)
	}
	if len(items) == 1 && items[0].Path != "/users/profile" {
		t.Errorf("unexpected path %q", items[0].Path)
	}
}

func TestList_FilterByProtocol(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "x.com", "/", "http"))
	s.Add(newEntry("GET", "x.com", "/ws", "ws"))
	s.Add(newEntry("GET", "x.com", "/grpc", "grpc"))

	items, total := s.List(store.Filter{Protocol: "ws"}, 0, 0)
	if total != 1 {
		t.Errorf("expected total=1, got %d", total)
	}
	if len(items) == 1 && items[0].Protocol != "ws" {
		t.Errorf("unexpected protocol %q", items[0].Protocol)
	}
}

func TestList_FilterNoMatch(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "x.com", "/", "http"))

	items, total := s.List(store.Filter{Host: "notfound.com"}, 0, 0)
	if total != 0 {
		t.Errorf("expected total=0, got %d", total)
	}
	if len(items) != 0 {
		t.Errorf("expected 0 items, got %d", len(items))
	}
}

func TestList_MultipleFilters(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "api.com", "/v1", "https"))
	s.Add(newEntry("POST", "api.com", "/v1", "https"))
	s.Add(newEntry("GET", "other.com", "/v1", "https"))

	items, total := s.List(store.Filter{Method: "GET", Host: "api.com"}, 0, 0)
	if total != 1 {
		t.Errorf("expected total=1, got %d", total)
	}
	if len(items) == 1 {
		if items[0].Method != "GET" || items[0].Host != "api.com" {
			t.Errorf("unexpected entry: method=%q host=%q", items[0].Method, items[0].Host)
		}
	}
}

// --- 3. List pagination (offset/limit) ---

func addN(s *store.Store, n int) {
	for i := 0; i < n; i++ {
		s.Add(newEntry("GET", "page.com", "/", "http"))
	}
}

func TestList_Pagination_FirstPage(t *testing.T) {
	s := store.New()
	addN(s, 10)

	items, total := s.List(store.Filter{}, 0, 3)
	if total != 10 {
		t.Errorf("expected total=10, got %d", total)
	}
	if len(items) != 3 {
		t.Errorf("expected 3 items on first page, got %d", len(items))
	}
}

func TestList_Pagination_SecondPage(t *testing.T) {
	s := store.New()
	addN(s, 10)

	items, total := s.List(store.Filter{}, 3, 3)
	if total != 10 {
		t.Errorf("expected total=10, got %d", total)
	}
	if len(items) != 3 {
		t.Errorf("expected 3 items on second page, got %d", len(items))
	}
}

func TestList_Pagination_LastPartialPage(t *testing.T) {
	s := store.New()
	addN(s, 10)

	items, total := s.List(store.Filter{}, 9, 5)
	if total != 10 {
		t.Errorf("expected total=10, got %d", total)
	}
	if len(items) != 1 {
		t.Errorf("expected 1 item on last partial page, got %d", len(items))
	}
}

func TestList_Pagination_OffsetBeyondTotal(t *testing.T) {
	s := store.New()
	addN(s, 5)

	items, total := s.List(store.Filter{}, 10, 5)
	if total != 5 {
		t.Errorf("expected total=5, got %d", total)
	}
	if items != nil {
		t.Errorf("expected nil items when offset >= total, got %v", items)
	}
}

func TestList_Pagination_LimitZeroReturnsAll(t *testing.T) {
	s := store.New()
	addN(s, 7)

	items, total := s.List(store.Filter{}, 0, 0)
	if total != 7 {
		t.Errorf("expected total=7, got %d", total)
	}
	if len(items) != 7 {
		t.Errorf("expected all 7 items with limit=0, got %d", len(items))
	}
}

func TestList_Pagination_PagesAreDifferent(t *testing.T) {
	s := store.New()
	addN(s, 6)

	page1, _ := s.List(store.Filter{}, 0, 3)
	page2, _ := s.List(store.Filter{}, 3, 3)

	if len(page1) != 3 || len(page2) != 3 {
		t.Fatalf("unexpected page sizes: %d, %d", len(page1), len(page2))
	}
	for _, a := range page1 {
		for _, b := range page2 {
			if a.ID == b.ID {
				t.Errorf("ID %d appears on both pages", a.ID)
			}
		}
	}
}

// --- 4. Clear ---

func TestClear_EmptiesEntries(t *testing.T) {
	s := store.New()
	s.Add(newEntry("GET", "x.com", "/", "http"))
	s.Add(newEntry("POST", "x.com", "/", "http"))

	s.Clear()

	_, total := s.List(store.Filter{}, 0, 0)
	if total != 0 {
		t.Errorf("expected 0 entries after Clear, got %d", total)
	}
}

func TestClear_GetReturnsFalseAfterClear(t *testing.T) {
	s := store.New()
	e := s.Add(newEntry("GET", "x.com", "/", "http"))
	id := e.ID

	s.Clear()

	_, ok := s.Get(id)
	if ok {
		t.Errorf("expected Get(%d) to return false after Clear", id)
	}
}

func TestClear_CanAddAfterClear(t *testing.T) {
	s := store.New()
	addN(s, 3)
	s.Clear()

	e := s.Add(newEntry("GET", "x.com", "/new", "http"))
	got, ok := s.Get(e.ID)
	if !ok {
		t.Fatalf("Get(%d) returned false after re-Add post-Clear", e.ID)
	}
	if got.Path != "/new" {
		t.Errorf("unexpected path %q", got.Path)
	}

	_, total := s.List(store.Filter{}, 0, 0)
	if total != 1 {
		t.Errorf("expected 1 entry after re-Add, got %d", total)
	}
}

// --- 5. Subscribe receives added entries ---

func TestSubscribe_ReceivesAddedEntry(t *testing.T) {
	s := store.New()
	ch := s.Subscribe()
	defer s.Unsubscribe(ch)

	want := s.Add(newEntry("GET", "sub.com", "/", "http"))

	select {
	case got := <-ch:
		if got.ID != want.ID {
			t.Errorf("expected ID %d, got %d", want.ID, got.ID)
		}
	case <-time.After(200 * time.Millisecond):
		t.Fatal("timed out waiting for subscribed entry")
	}
}

func TestSubscribe_ReceivesMultipleEntries(t *testing.T) {
	s := store.New()
	ch := s.Subscribe()
	defer s.Unsubscribe(ch)

	const n = 5
	var ids []int64
	for i := 0; i < n; i++ {
		e := s.Add(newEntry("GET", "multi.com", "/", "http"))
		ids = append(ids, e.ID)
	}

	received := make(map[int64]bool)
	timeout := time.After(500 * time.Millisecond)
	for len(received) < n {
		select {
		case e := <-ch:
			received[e.ID] = true
		case <-timeout:
			t.Fatalf("timed out: received %d/%d entries", len(received), n)
		}
	}
	for _, id := range ids {
		if !received[id] {
			t.Errorf("did not receive entry with ID %d", id)
		}
	}
}

func TestSubscribe_UpdatePublishesToSubscriber(t *testing.T) {
	s := store.New()
	e := s.Add(newEntry("GET", "upd.com", "/", "http"))

	ch := s.Subscribe()
	defer s.Unsubscribe(ch)

	e.StatusCode = 200
	e.Modified = true
	s.Update(e)

	select {
	case got := <-ch:
		if got.ID != e.ID {
			t.Errorf("expected ID %d, got %d", e.ID, got.ID)
		}
		if got.StatusCode != 200 {
			t.Errorf("expected StatusCode=200, got %d", got.StatusCode)
		}
	case <-time.After(200 * time.Millisecond):
		t.Fatal("timed out waiting for updated entry on channel")
	}
}

func TestUnsubscribe_StopsDelivery(t *testing.T) {
	s := store.New()
	ch := s.Subscribe()

	// Drain the channel from any entries added before unsubscribe.
	s.Add(newEntry("GET", "before.com", "/", "http"))
	select {
	case <-ch:
	case <-time.After(200 * time.Millisecond):
		t.Fatal("timed out waiting for pre-unsubscribe entry")
	}

	s.Unsubscribe(ch)

	// The channel should now be closed; no new entries should arrive.
	s.Add(newEntry("GET", "after.com", "/", "http"))

	// A closed channel returns its zero value immediately.
	// An open but empty channel blocks. Either way, we should not
	// receive a valid entry after unsubscribing.
	select {
	case e, ok := <-ch:
		if ok {
			t.Errorf("received unexpected entry (ID %d) after Unsubscribe", e.ID)
		}
		// ok==false means channel was closed — that is the expected state.
	case <-time.After(100 * time.Millisecond):
		t.Error("channel neither closed nor drained after Unsubscribe")
	}
}

func TestSubscribe_MultipleSubscribers(t *testing.T) {
	s := store.New()
	ch1 := s.Subscribe()
	ch2 := s.Subscribe()
	defer s.Unsubscribe(ch1)
	defer s.Unsubscribe(ch2)

	want := s.Add(newEntry("GET", "fanout.com", "/", "http"))

	for i, ch := range []chan *store.Entry{ch1, ch2} {
		select {
		case got := <-ch:
			if got.ID != want.ID {
				t.Errorf("subscriber %d: expected ID %d, got %d", i+1, want.ID, got.ID)
			}
		case <-time.After(200 * time.Millisecond):
			t.Fatalf("subscriber %d: timed out waiting for entry", i+1)
		}
	}
}
