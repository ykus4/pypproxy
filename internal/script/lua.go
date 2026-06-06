package script

import (
	"fmt"
	"net/http"

	lua "github.com/yuin/gopher-lua"
)

// Engine runs Lua scripts to transform requests and responses.
type Engine struct {
	state *lua.LState
}

func NewEngine() *Engine {
	return &Engine{}
}

// LoadFile loads a Lua script from disk.
func (e *Engine) LoadFile(path string) error {
	L := lua.NewState()
	if err := L.DoFile(path); err != nil {
		L.Close()
		return fmt.Errorf("lua load %s: %w", path, err)
	}
	if e.state != nil {
		e.state.Close()
	}
	e.state = L
	return nil
}

// LoadString loads a Lua script from a string.
func (e *Engine) LoadString(src string) error {
	L := lua.NewState()
	if err := L.DoString(src); err != nil {
		L.Close()
		return fmt.Errorf("lua load: %w", err)
	}
	if e.state != nil {
		e.state.Close()
	}
	e.state = L
	return nil
}

// OnRequest calls the Lua function `on_request(method, host, path, body)` if it exists.
// Returns the (possibly modified) body.
func (e *Engine) OnRequest(req *http.Request, body []byte) []byte {
	if e.state == nil {
		return body
	}
	fn := e.state.GetGlobal("on_request")
	if fn == lua.LNil {
		return body
	}
	err := e.state.CallByParam(lua.P{
		Fn:      fn,
		NRet:    1,
		Protect: true,
	},
		lua.LString(req.Method),
		lua.LString(req.Host),
		lua.LString(req.URL.Path),
		lua.LString(body),
	)
	if err != nil {
		return body
	}
	ret := e.state.Get(-1)
	e.state.Pop(1)
	if s, ok := ret.(lua.LString); ok {
		return []byte(s)
	}
	return body
}

// OnResponse calls the Lua function `on_response(status, body)` if it exists.
func (e *Engine) OnResponse(status int, body []byte) []byte {
	if e.state == nil {
		return body
	}
	fn := e.state.GetGlobal("on_response")
	if fn == lua.LNil {
		return body
	}
	err := e.state.CallByParam(lua.P{
		Fn:      fn,
		NRet:    1,
		Protect: true,
	},
		lua.LNumber(status),
		lua.LString(body),
	)
	if err != nil {
		return body
	}
	ret := e.state.Get(-1)
	e.state.Pop(1)
	if s, ok := ret.(lua.LString); ok {
		return []byte(s)
	}
	return body
}

func (e *Engine) Close() {
	if e.state != nil {
		e.state.Close()
		e.state = nil
	}
}
