# Getting Started

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
git clone https://github.com/ykus4/pypproxy
cd paxy
uv sync
```

## Running

### GUI mode (default)

```bash
uv run python main.py
# or
make gui
```

Open `http://localhost:8081` in your browser to see the traffic viewer.

### CUI mode

```bash
uv run python main.py --mode cui
# or
make cui
```

A real-time traffic table renders directly in the terminal.

## Startup output

```
paxy MITM proxy
  proxy : 0.0.0.0:8080
  UI    : http://0.0.0.0:8081
  CA    : /Users/you/.paxy/ca-cert.pem
Install the CA cert in your browser/device to avoid TLS warnings.
```

On first run, `~/.paxy/ca-cert.pem` and `~/.paxy/ca-key.pem` are generated automatically.

## Installing the CA certificate

To intercept HTTPS traffic, install the generated CA certificate as a trusted root on every device you want to inspect.

### macOS (system-wide)

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ~/.paxy/ca-cert.pem
```

### Firefox

1. **Settings** → **Privacy & Security** → **View Certificates** → **Authorities**
2. **Import** → select `~/.paxy/ca-cert.pem`
3. Check **Trust this CA to identify websites**

### Android

1. Transfer `ca-cert.pem` to the device
2. **Settings** → **Security** → **Install from storage**

!!! note
    Android 7+ apps targeting API 24+ do not trust user-installed CAs by default.
    Add a `network_security_config.xml` to the target app, or use a rooted device.

### iOS

1. Send the certificate to the device via email or HTTP
2. Open the attachment — iOS prompts to install a profile
3. **Settings** → **General** → **VPN & Device Management** → install the profile
4. **Settings** → **General** → **About** → **Certificate Trust Settings** → enable full trust

## Configuring the proxy

### macOS (system proxy)

```bash
networksetup -setwebproxy Wi-Fi 127.0.0.1 8080
networksetup -setsecurewebproxy Wi-Fi 127.0.0.1 8080
```

To disable:

```bash
networksetup -setwebproxystate Wi-Fi off
networksetup -setsecurewebproxystate Wi-Fi off
```

### Android

**Settings** → **Wi-Fi** → long-press your network → **Modify** → **Advanced** → **Proxy: Manual**

- Host: your machine's IP (e.g. `192.168.1.10`)
- Port: `8080`

### iOS

**Settings** → **Wi-Fi** → tap the info icon → **Configure Proxy: Manual**

- Server: your machine's IP
- Port: `8080`
