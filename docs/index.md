---
layout: home

hero:
  name: paxy
  text: MITM Proxy
  tagline: Inspect and modify HTTP/HTTPS traffic from browsers and mobile apps.
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/ykus4/paxy

features:
  - icon: 🔐
    title: HTTPS Interception
    details: Terminate TLS with dynamically generated certificates signed by a local CA. Install once, inspect everything.
  - icon: 🖥️
    title: Web UI
    details: Real-time traffic viewer in the browser. Filter, search, and inspect request/response headers and bodies.
  - icon: ⚙️
    title: Rule Engine
    details: Block, modify, or redirect traffic by matching host, path, method, header, or body with regex support.
  - icon: 📝
    title: Lua Scripting
    details: Write on_request / on_response hooks in Lua for custom transformations without recompiling.
  - icon: 🔄
    title: Replay & Fuzzing
    details: Resend any captured request with one click. Run hundreds of parallel replays for load testing or fuzzing.
  - icon: 🔌
    title: Protocol Support
    details: HTTP, HTTPS, WebSocket, and gRPC — all intercepted and displayed in the same UI.
---
