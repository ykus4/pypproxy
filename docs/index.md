---
layout: home

hero:
  name: paxy
  text: MITM Proxy
  tagline: Intercept, inspect, and modify HTTP/HTTPS traffic from browsers and mobile apps. Written in Python.
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/ykus4/pypproxy

features:
  - icon: 🔐
    title: HTTPS Interception
    details: Dynamically generate per-host certificates signed by a local CA. Terminate TLS and read every request and response in plain text.
  - icon: 🖥️
    title: GUI Mode
    details: Browser-based UI built with NiceGUI. Traffic streams in real time. Filter, inspect, and replay without leaving the page.
  - icon: ⌨️
    title: CUI Mode
    details: Terminal UI built with rich. Works over SSH and in CI environments with no browser required.
  - icon: ⚙️
    title: Rule Engine
    details: Block, modify, or redirect traffic by matching host, path, method, header, or body. Full regex support.
  - icon: 📝
    title: Python Scripting
    details: Define on_request / on_response hooks in plain Python. No DSL to learn — the full standard library is available.
  - icon: 🔄
    title: Replay & Fuzzing
    details: Resend any captured request with one click. Increase count to fire hundreds of parallel requests for load testing or fuzzing.
---
