package api

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/gorilla/websocket"
	"github.com/ykus4/paxy/internal/replay"
	"github.com/ykus4/paxy/internal/rule"
	"github.com/ykus4/paxy/internal/store"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

// Server exposes the REST + WebSocket API.
type Server struct {
	Store   *store.Store
	Rules   *rule.Manager
	Replayer *replay.Replayer
	mux     *http.ServeMux
}

func NewServer(st *store.Store, rules *rule.Manager, rp *replay.Replayer) *Server {
	s := &Server{Store: st, Rules: rules, Replayer: rp}
	s.mux = http.NewServeMux()
	s.routes()
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) routes() {
	s.mux.HandleFunc("/api/traffic", s.handleTrafficList)
	s.mux.HandleFunc("/api/traffic/", s.handleTrafficItem)
	s.mux.HandleFunc("/api/rules", s.handleRules)
	s.mux.HandleFunc("/api/rules/", s.handleRuleItem)
	s.mux.HandleFunc("/api/replay", s.handleReplay)
	s.mux.HandleFunc("/api/clear", s.handleClear)
	s.mux.HandleFunc("/ws", s.handleWS)
}

// --- traffic ---

func (s *Server) handleTrafficList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	q := r.URL.Query()
	offset, _ := strconv.Atoi(q.Get("offset"))
	limit, _ := strconv.Atoi(q.Get("limit"))
	if limit == 0 {
		limit = 100
	}
	f := store.Filter{
		Method:   q.Get("method"),
		Host:     q.Get("host"),
		Search:   q.Get("search"),
		Protocol: q.Get("protocol"),
	}
	entries, total := s.Store.List(f, offset, limit)
	jsonOK(w, map[string]any{"entries": entries, "total": total, "offset": offset, "limit": limit})
}

func (s *Server) handleTrafficItem(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r.URL.Path, "/api/traffic/")
	if err != nil {
		http.Error(w, "invalid id", http.StatusBadRequest)
		return
	}
	entry, ok := s.Store.Get(id)
	if !ok {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	jsonOK(w, entry)
}

// --- rules ---

func (s *Server) handleRules(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		jsonOK(w, s.Rules.List())
	case http.MethodPost:
		var ru rule.Rule
		if err := json.NewDecoder(r.Body).Decode(&ru); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		s.Rules.Add(&ru)
		jsonOK(w, &ru)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleRuleItem(w http.ResponseWriter, r *http.Request) {
	id, err := parseID(r.URL.Path, "/api/rules/")
	if err != nil {
		http.Error(w, "invalid id", http.StatusBadRequest)
		return
	}
	switch r.Method {
	case http.MethodPut:
		var ru rule.Rule
		if err := json.NewDecoder(r.Body).Decode(&ru); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		ru.ID = id
		s.Rules.Update(&ru)
		jsonOK(w, &ru)
	case http.MethodDelete:
		s.Rules.Delete(id)
		w.WriteHeader(http.StatusNoContent)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

// --- replay ---

func (s *Server) handleReplay(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		EntryID int64               `json:"entry_id"`
		Options replay.Options      `json:"options"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	entry, ok := s.Store.Get(req.EntryID)
	if !ok {
		http.Error(w, "entry not found", http.StatusNotFound)
		return
	}
	results, err := s.Replayer.ReplayMany(r.Context(), entry, req.Options)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	jsonOK(w, results)
}

// --- clear ---

func (s *Server) handleClear(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	s.Store.Clear()
	w.WriteHeader(http.StatusNoContent)
}

// --- websocket ---

func (s *Server) handleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	ch := s.Store.Subscribe()
	defer s.Store.Unsubscribe(ch)

	for entry := range ch {
		if err := conn.WriteJSON(entry); err != nil {
			return
		}
	}
}

// --- helpers ---

func jsonOK(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}

func parseID(path, prefix string) (int64, error) {
	s := strings.TrimPrefix(path, prefix)
	s = strings.TrimSuffix(s, "/")
	return strconv.ParseInt(s, 10, 64)
}
