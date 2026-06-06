package grpc

import (
	"bufio"
	"bytes"
	"encoding/binary"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/ykus4/paxy/internal/store"
)

// Frame is a single gRPC length-prefixed message.
type Frame struct {
	Compressed bool
	Data       []byte
}

// IsGRPC returns true if the content-type indicates gRPC.
func IsGRPC(h http.Header) bool {
	ct := h.Get("Content-Type")
	return len(ct) >= 16 && ct[:16] == "application/grpc"
}

// Interceptor records gRPC traffic.
type Interceptor struct {
	Store *store.Store
}

func New(st *store.Store) *Interceptor {
	return &Interceptor{Store: st}
}

// WrapRequest logs a gRPC request body and returns a replacement body.
func (gi *Interceptor) WrapRequest(req *http.Request, entry *store.Entry) {
	if req.Body == nil {
		return
	}
	body, err := io.ReadAll(req.Body)
	if err != nil {
		return
	}
	req.Body = io.NopCloser(bytes.NewReader(body))

	frames := decodeFrames(body)
	for i, f := range frames {
		log.Printf("grpc req frame[%d] compressed=%v len=%d", i, f.Compressed, len(f.Data))
	}

	entry.Tags = append(entry.Tags, "grpc")
}

// WrapResponse logs gRPC response frames.
func (gi *Interceptor) WrapResponse(resp *http.Response, entry *store.Entry) {
	if resp.Body == nil {
		return
	}

	pr, pw := io.Pipe()
	go func() {
		defer pw.Close()
		br := bufio.NewReader(resp.Body)
		for {
			frame, err := readFrame(br)
			if err != nil {
				return
			}
			log.Printf("grpc resp frame compressed=%v len=%d entry=%d", frame.Compressed, len(frame.Data), entry.ID)
			buf := encodeFrame(frame)
			pw.Write(buf)
		}
	}()

	entry.DurationMs = time.Since(entry.CreatedAt).Milliseconds()
	entry.Tags = append(entry.Tags, "grpc")
	resp.Body = pr
}

func decodeFrames(data []byte) []Frame {
	var frames []Frame
	r := bytes.NewReader(data)
	for {
		f, err := readFrame(r)
		if err != nil {
			break
		}
		frames = append(frames, *f)
	}
	return frames
}

func readFrame(r io.Reader) (*Frame, error) {
	header := make([]byte, 5)
	if _, err := io.ReadFull(r, header); err != nil {
		return nil, err
	}
	compressed := header[0] == 1
	length := binary.BigEndian.Uint32(header[1:5])
	data := make([]byte, length)
	if _, err := io.ReadFull(r, data); err != nil {
		return nil, err
	}
	return &Frame{Compressed: compressed, Data: data}, nil
}

func encodeFrame(f *Frame) []byte {
	buf := make([]byte, 5+len(f.Data))
	if f.Compressed {
		buf[0] = 1
	}
	binary.BigEndian.PutUint32(buf[1:5], uint32(len(f.Data)))
	copy(buf[5:], f.Data)
	return buf
}
