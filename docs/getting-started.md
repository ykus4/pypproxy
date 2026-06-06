# Getting Started

## Requirements

- Go 1.21+
- Node.js 18+ (for Web UI development)

## Installation

### From source

```bash
git clone https://github.com/ykus4/paxy
cd paxy
make build
```

The binary is placed at `bin/paxy`.

### Run without building

```bash
make run
```

## First launch

```bash
./bin/paxy
```

Output:

```
paxy MITM proxy
  proxy addr : :8080
  UI addr    : :8081
  CA cert    : /Users/you/.paxy/ca-cert.pem
Install the CA cert in your browser/device to avoid TLS warnings.
```

On first run paxy generates a CA certificate at `~/.paxy/ca-cert.pem`. You need to install this certificate as a trusted CA on every device whose traffic you want to inspect.

## Install the CA certificate

### macOS (system-wide)

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ~/.paxy/ca-cert.pem
```

### macOS (Chrome / Safari — via Keychain Access)

1. Open **Keychain Access**
2. Drag `~/.paxy/ca-cert.pem` into the **System** keychain
3. Double-click the imported certificate → **Trust** → **Always Trust**

### Firefox

1. Open **Settings** → **Privacy & Security** → **Certificates** → **View Certificates**
2. **Authorities** tab → **Import** → select `~/.paxy/ca-cert.pem`
3. Check **Trust this CA to identify websites**

### Android

1. Copy `ca-cert.pem` to the device (email, ADB, etc.)
2. **Settings** → **Security** → **Install from storage**
3. Select the file and name it `paxy`

For Android 7+, apps targeting API 24+ do not trust user-installed CAs by default.
Add a `network_security_config.xml` to the target app, or use a rooted device.

### iOS

1. Email the certificate to the device or serve it over HTTP
2. Open the attachment — iOS prompts to install a profile
3. **Settings** → **General** → **VPN & Device Management** → install the profile
4. **Settings** → **General** → **About** → **Certificate Trust Settings** → enable full trust

## Configure the proxy

### Browser (macOS system proxy)

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

**Settings** → **Wi-Fi** → long-press your network → **Modify network** → **Advanced** → **Proxy: Manual**

- Host: your machine's IP (e.g. `192.168.1.10`)
- Port: `8080`

### iOS

**Settings** → **Wi-Fi** → tap the info icon → **Configure Proxy: Manual**

- Server: your machine's IP
- Port: `8080`

## Open the Web UI

Navigate to [http://localhost:8081](http://localhost:8081) in your browser.

Traffic appears in real time as requests pass through the proxy.
