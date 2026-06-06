package store

import (
	"sync"
	"sync/atomic"
	"time"
)

type Direction string

const (
	DirectionRequest  Direction = "request"
	DirectionResponse Direction = "response"
)

// Entry is a captured HTTP traffic record.
type Entry struct {
	ID        int64     `json:"id"`
	CreatedAt time.Time `json:"created_at"`

	// Request fields
	Method  string            `json:"method"`
	Scheme  string            `json:"scheme"`
	Host    string            `json:"host"`
	Path    string            `json:"path"`
	Query   string            `json:"query,omitempty"`
	ReqHeader map[string][]string `json:"req_header,omitempty"`
	ReqBody []byte            `json:"req_body,omitempty"`

	// Response fields
	StatusCode  int                 `json:"status_code,omitempty"`
	RespHeader  map[string][]string `json:"resp_header,omitempty"`
	RespBody    []byte              `json:"resp_body,omitempty"`
	DurationMs  int64               `json:"duration_ms,omitempty"`

	// Metadata
	Protocol string `json:"protocol"` // http, https, ws, grpc
	Tags     []string `json:"tags,omitempty"`
	Modified bool   `json:"modified,omitempty"`
}

type Filter struct {
	Method  string
	Host    string
	Search  string
	Protocol string
}

// Store holds all captured entries in memory.
type Store struct {
	mu       sync.RWMutex
	entries  []*Entry
	byID     map[int64]*Entry
	counter  atomic.Int64
	subs     []chan *Entry
	subsMu   sync.Mutex
}

func New() *Store {
	return &Store{byID: map[int64]*Entry{}}
}

func (s *Store) Add(e *Entry) *Entry {
	e.ID = s.counter.Add(1)
	if e.CreatedAt.IsZero() {
		e.CreatedAt = time.Now()
	}
	s.mu.Lock()
	s.entries = append(s.entries, e)
	s.byID[e.ID] = e
	s.mu.Unlock()
	s.publish(e)
	return e
}

func (s *Store) Update(e *Entry) {
	s.mu.Lock()
	s.byID[e.ID] = e
	s.mu.Unlock()
	s.publish(e)
}

func (s *Store) Get(id int64) (*Entry, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	e, ok := s.byID[id]
	return e, ok
}

func (s *Store) List(f Filter, offset, limit int) ([]*Entry, int) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var out []*Entry
	for _, e := range s.entries {
		if !matchFilter(e, f) {
			continue
		}
		out = append(out, e)
	}

	total := len(out)
	if offset >= total {
		return nil, total
	}
	end := offset + limit
	if end > total || limit == 0 {
		end = total
	}
	return out[offset:end], total
}

func (s *Store) Clear() {
	s.mu.Lock()
	s.entries = nil
	s.byID = map[int64]*Entry{}
	s.mu.Unlock()
}

// Subscribe returns a channel that receives every new or updated entry.
func (s *Store) Subscribe() chan *Entry {
	ch := make(chan *Entry, 256)
	s.subsMu.Lock()
	s.subs = append(s.subs, ch)
	s.subsMu.Unlock()
	return ch
}

func (s *Store) Unsubscribe(ch chan *Entry) {
	s.subsMu.Lock()
	defer s.subsMu.Unlock()
	for i, c := range s.subs {
		if c == ch {
			s.subs = append(s.subs[:i], s.subs[i+1:]...)
			close(ch)
			return
		}
	}
}

func (s *Store) publish(e *Entry) {
	s.subsMu.Lock()
	defer s.subsMu.Unlock()
	for _, ch := range s.subs {
		select {
		case ch <- e:
		default:
		}
	}
}

func matchFilter(e *Entry, f Filter) bool {
	if f.Method != "" && e.Method != f.Method {
		return false
	}
	if f.Host != "" && e.Host != f.Host {
		return false
	}
	if f.Protocol != "" && e.Protocol != f.Protocol {
		return false
	}
	if f.Search != "" {
		if !contains(e.Host+e.Path, f.Search) {
			return false
		}
	}
	return true
}

func contains(s, sub string) bool {
	return len(sub) == 0 || len(s) >= len(sub) && (s == sub || len(s) > 0 && containsRune(s, sub))
}

func containsRune(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
