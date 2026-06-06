package proxy

import (
	"bufio"
	"bytes"
	"crypto/tls"
	"io"
	"log"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/ykus4/paxy/internal/cert"
	"github.com/ykus4/paxy/internal/interceptor"
	grpcproto "github.com/ykus4/paxy/internal/proto/grpc"
	wsproto "github.com/ykus4/paxy/internal/proto/ws"
	"github.com/ykus4/paxy/internal/script"
	"github.com/ykus4/paxy/internal/store"
)

type Proxy struct {
	Addr        string
	CA          *cert.CA
	Interceptor *interceptor.Interceptor
	Script      *script.Engine
	ignore      map[string]bool

	grpc *grpcproto.Interceptor
	ws   *wsproto.Interceptor
}

type Options struct {
	Addr        string
	CA          *cert.CA
	Interceptor *interceptor.Interceptor
	Script      *script.Engine
	Store       *store.Store
	Ignore      []string
}

func New(opts Options) *Proxy {
	ignore := make(map[string]bool, len(opts.Ignore))
	for _, h := range opts.Ignore {
		ignore[h] = true
	}
	return &Proxy{
		Addr:        opts.Addr,
		CA:          opts.CA,
		Interceptor: opts.Interceptor,
		Script:      opts.Script,
		ignore:      ignore,
		grpc:        grpcproto.New(opts.Store),
		ws:          wsproto.New(opts.Store),
	}
}

func (p *Proxy) Start() error {
	server := &http.Server{
		Addr:    p.Addr,
		Handler: http.HandlerFunc(p.handle),
	}
	log.Printf("proxy listening on %s", p.Addr)
	return server.ListenAndServe()
}

func (p *Proxy) handle(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodConnect {
		p.handleMITM(w, r)
		return
	}
	p.handleHTTP(w, r, "http")
}

func (p *Proxy) handleHTTP(w http.ResponseWriter, r *http.Request, scheme string) {
	start := time.Now()

	entry, blocked := p.Interceptor.ProcessRequest(r, scheme)
	if blocked {
		http.Error(w, "blocked by rule", http.StatusForbidden)
		return
	}

	// Apply Lua script to request body.
	if p.Script != nil {
		newBody := p.Script.OnRequest(r, entry.ReqBody)
		r.Body = io.NopCloser(bytes.NewReader(newBody))
	}

	if grpcproto.IsGRPC(r.Header) {
		p.grpc.WrapRequest(r, entry)
	}

	r.RequestURI = ""
	resp, err := http.DefaultTransport.RoundTrip(r)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	if grpcproto.IsGRPC(resp.Header) {
		p.grpc.WrapResponse(resp, entry)
	}

	p.Interceptor.ProcessResponse(entry, resp, start)

	// Apply Lua script to response body.
	if p.Script != nil {
		newBody := p.Script.OnResponse(resp.StatusCode, entry.RespBody)
		entry.RespBody = newBody
	}

	for k, vs := range resp.Header {
		for _, v := range vs {
			w.Header().Add(k, v)
		}
	}
	w.WriteHeader(resp.StatusCode)
	w.Write(entry.RespBody)

	log.Printf("%s %s %s%s %d (%dms)", scheme, r.Method, r.Host, r.URL.Path, resp.StatusCode, entry.DurationMs)
}

func (p *Proxy) handleMITM(w http.ResponseWriter, r *http.Request) {
	host := r.Host
	if !strings.Contains(host, ":") {
		host = host + ":443"
	}
	hostname := strings.Split(host, ":")[0]

	// Passthrough mode for ignored hosts.
	if p.ignore[hostname] {
		p.tunnel(w, r, host)
		return
	}

	tlsCert, err := p.CA.ForHost(hostname)
	if err != nil {
		http.Error(w, "cert generation failed: "+err.Error(), http.StatusInternalServerError)
		return
	}

	hijack, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "hijacking not supported", http.StatusInternalServerError)
		return
	}
	conn, _, err := hijack.Hijack()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer conn.Close()

	conn.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n"))

	tlsConn := tls.Server(conn, &tls.Config{
		Certificates: []tls.Certificate{*tlsCert},
	})
	if err := tlsConn.Handshake(); err != nil {
		log.Printf("TLS handshake failed for %s: %v", hostname, err)
		return
	}
	defer tlsConn.Close()

	p.serveDecrypted(tlsConn, host, tlsCert)
}

func (p *Proxy) serveDecrypted(conn net.Conn, upstreamHost string, tlsCert *tls.Certificate) {
	br := bufio.NewReader(conn)
	for {
		req, err := http.ReadRequest(br)
		if err != nil {
			return
		}

		// WebSocket upgrade — hand off to WS interceptor.
		if wsproto.IsUpgrade(req) {
			p.ws.Intercept(conn, req, tlsCert, "wss")
			return
		}

		req.URL.Scheme = "https"
		req.URL.Host = upstreamHost

		rw := &bufResponseWriter{header: make(http.Header), conn: conn}
		p.handleHTTP(rw, req, "https")
		if req.Close || rw.closed {
			return
		}
	}
}

// tunnel creates a raw TCP tunnel without MITM (for ignored hosts).
func (p *Proxy) tunnel(w http.ResponseWriter, r *http.Request, host string) {
	dst, err := net.Dial("tcp", host)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer dst.Close()

	hijack, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "hijacking not supported", http.StatusInternalServerError)
		return
	}
	conn, _, err := hijack.Hijack()
	if err != nil {
		return
	}
	defer conn.Close()

	conn.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n"))
	done := make(chan struct{}, 2)
	go func() { io.Copy(dst, conn); done <- struct{}{} }()
	go func() { io.Copy(conn, dst); done <- struct{}{} }()
	<-done
}

// bufResponseWriter writes HTTP responses back to the underlying conn.
type bufResponseWriter struct {
	header http.Header
	conn   net.Conn
	status int
	closed bool
}

func (rw *bufResponseWriter) Header() http.Header { return rw.header }

func (rw *bufResponseWriter) WriteHeader(code int) {
	rw.status = code
	var sb strings.Builder
	sb.WriteString("HTTP/1.1 ")
	sb.WriteString(http.StatusText(code))
	sb.WriteString("\r\n")
	for k, vs := range rw.header {
		for _, v := range vs {
			sb.WriteString(k)
			sb.WriteString(": ")
			sb.WriteString(v)
			sb.WriteString("\r\n")
		}
	}
	sb.WriteString("\r\n")
	rw.conn.Write([]byte(sb.String()))
}

func (rw *bufResponseWriter) Write(b []byte) (int, error) {
	if rw.status == 0 {
		rw.WriteHeader(http.StatusOK)
	}
	n, err := rw.conn.Write(b)
	if err != nil {
		rw.closed = true
	}
	return n, err
}

func (rw *bufResponseWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	br := bufio.NewReadWriter(bufio.NewReader(rw.conn), bufio.NewWriter(rw.conn))
	return rw.conn, br, nil
}
