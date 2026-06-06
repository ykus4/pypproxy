package ws

import (
	"bufio"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"time"

	"github.com/ykus4/paxy/internal/store"
)

// Frame is a captured WebSocket frame.
type Frame struct {
	EntryID   int64     `json:"entry_id"`
	Timestamp time.Time `json:"timestamp"`
	Direction string    `json:"direction"` // client, server
	Opcode    byte      `json:"opcode"`
	Payload   []byte    `json:"payload"`
	Text      string    `json:"text,omitempty"`
}

// Interceptor handles WebSocket MITM.
type Interceptor struct {
	Store *store.Store
}

func New(st *store.Store) *Interceptor {
	return &Interceptor{Store: st}
}

// IsUpgrade returns true if the request is a WebSocket upgrade.
func IsUpgrade(req *http.Request) bool {
	return req.Header.Get("Upgrade") == "websocket"
}

// Intercept hijacks a WebSocket connection and records frames.
func (wi *Interceptor) Intercept(clientConn net.Conn, req *http.Request, tlsCert *tls.Certificate, scheme string) {
	host := req.Host

	var serverConn net.Conn
	var err error
	if scheme == "wss" {
		serverConn, err = tls.Dial("tcp", host, &tls.Config{InsecureSkipVerify: false})
	} else {
		serverConn, err = net.Dial("tcp", host)
	}
	if err != nil {
		log.Printf("ws: dial %s: %v", host, err)
		return
	}
	defer serverConn.Close()

	// Forward the upgrade request to the server.
	if err := req.Write(serverConn); err != nil {
		log.Printf("ws: write upgrade: %v", err)
		return
	}

	// Read server's 101 response and forward to client.
	br := bufio.NewReader(serverConn)
	resp, err := http.ReadResponse(br, req)
	if err != nil {
		log.Printf("ws: read upgrade response: %v", err)
		return
	}
	if err := resp.Write(clientConn); err != nil {
		return
	}

	entry := wi.Store.Add(&store.Entry{
		Method:   req.Method,
		Scheme:   scheme,
		Host:     host,
		Path:     req.URL.Path,
		Protocol: "ws",
		Tags:     []string{"websocket"},
	})

	done := make(chan struct{}, 2)
	go wi.relay(clientConn, serverConn, entry.ID, "client", done)
	go wi.relay(serverConn, clientConn, entry.ID, "server", done)
	<-done
}

func (wi *Interceptor) relay(src, dst net.Conn, entryID int64, dir string, done chan struct{}) {
	defer func() { done <- struct{}{} }()

	for {
		frame, err := readFrame(src)
		if err != nil {
			return
		}

		text := ""
		if frame[0]&0x0f == 1 {
			text = string(frame[2:])
		}

		f := &Frame{
			EntryID:   entryID,
			Timestamp: time.Now(),
			Direction: dir,
			Opcode:    frame[0] & 0x0f,
			Payload:   frame[2:],
			Text:      text,
		}
		data, _ := json.Marshal(f)
		log.Printf("ws frame [%s]: %s", dir, data)

		if _, err := dst.Write(frame); err != nil {
			return
		}
	}
}

func readFrame(r io.Reader) ([]byte, error) {
	header := make([]byte, 2)
	if _, err := io.ReadFull(r, header); err != nil {
		return nil, err
	}

	payloadLen := int(header[1] & 0x7f)
	masked := header[1]&0x80 != 0

	var extLen []byte
	switch payloadLen {
	case 126:
		extLen = make([]byte, 2)
		if _, err := io.ReadFull(r, extLen); err != nil {
			return nil, err
		}
		payloadLen = int(extLen[0])<<8 | int(extLen[1])
	case 127:
		extLen = make([]byte, 8)
		if _, err := io.ReadFull(r, extLen); err != nil {
			return nil, err
		}
		payloadLen = 0
		for _, b := range extLen {
			payloadLen = payloadLen<<8 | int(b)
		}
	}

	var maskKey []byte
	if masked {
		maskKey = make([]byte, 4)
		if _, err := io.ReadFull(r, maskKey); err != nil {
			return nil, err
		}
	}

	payload := make([]byte, payloadLen)
	if _, err := io.ReadFull(r, payload); err != nil {
		return nil, err
	}

	if masked {
		for i := range payload {
			payload[i] ^= maskKey[i%4]
		}
	}

	buf := make([]byte, 0, 2+len(extLen)+payloadLen)
	buf = append(buf, header...)
	buf = append(buf, extLen...)
	buf = append(buf, payload...)

	if len(buf) < 2 {
		return nil, fmt.Errorf("ws: short frame")
	}
	return buf, nil
}
