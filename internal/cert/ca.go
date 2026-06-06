package cert

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"net"
	"os"
	"sync"
	"time"
)

// CA holds the root CA cert and key used to sign per-host certificates.
type CA struct {
	cert    *x509.Certificate
	key     *rsa.PrivateKey
	tlsCert tls.Certificate

	mu    sync.Mutex
	cache map[string]*tls.Certificate
}

// LoadOrCreate loads a CA from disk, or generates a new one if not found.
func LoadOrCreate(certPath, keyPath string) (*CA, error) {
	if _, err := os.Stat(certPath); err == nil {
		return load(certPath, keyPath)
	}
	return generate(certPath, keyPath)
}

func load(certPath, keyPath string) (*CA, error) {
	tlsCert, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return nil, err
	}
	x509Cert, err := x509.ParseCertificate(tlsCert.Certificate[0])
	if err != nil {
		return nil, err
	}
	key := tlsCert.PrivateKey.(*rsa.PrivateKey)
	return &CA{cert: x509Cert, key: key, tlsCert: tlsCert, cache: map[string]*tls.Certificate{}}, nil
}

func generate(certPath, keyPath string) (*CA, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}

	tmpl := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject: pkix.Name{
			CommonName:   "paxy CA",
			Organization: []string{"paxy"},
		},
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              time.Now().Add(10 * 365 * 24 * time.Hour),
		IsCA:                  true,
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid: true,
	}

	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, &key.PublicKey, key)
	if err != nil {
		return nil, err
	}

	if err := writePEM(certPath, "CERTIFICATE", der); err != nil {
		return nil, err
	}
	keyDER := x509.MarshalPKCS1PrivateKey(key)
	if err := writePEM(keyPath, "RSA PRIVATE KEY", keyDER); err != nil {
		return nil, err
	}

	x509Cert, _ := x509.ParseCertificate(der)
	tlsCert := tls.Certificate{Certificate: [][]byte{der}, PrivateKey: key, Leaf: x509Cert}
	return &CA{cert: x509Cert, key: key, tlsCert: tlsCert, cache: map[string]*tls.Certificate{}}, nil
}

// ForHost returns a TLS certificate for the given hostname, signed by the CA.
// Results are cached so we don't regenerate on every connection.
func (ca *CA) ForHost(host string) (*tls.Certificate, error) {
	ca.mu.Lock()
	defer ca.mu.Unlock()

	if c, ok := ca.cache[host]; ok {
		return c, nil
	}

	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}

	tmpl := &x509.Certificate{
		SerialNumber: big.NewInt(time.Now().UnixNano()),
		Subject:      pkix.Name{CommonName: host},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     time.Now().Add(24 * time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	}

	if ip := net.ParseIP(host); ip != nil {
		tmpl.IPAddresses = []net.IP{ip}
	} else {
		tmpl.DNSNames = []string{host}
	}

	der, err := x509.CreateCertificate(rand.Reader, tmpl, ca.cert, &key.PublicKey, ca.key)
	if err != nil {
		return nil, err
	}

	leaf, _ := x509.ParseCertificate(der)
	c := &tls.Certificate{Certificate: [][]byte{der}, PrivateKey: key, Leaf: leaf}
	ca.cache[host] = c
	return c, nil
}

// CertPEM returns the CA certificate in PEM format (for user to install).
func (ca *CA) CertPEM() []byte {
	return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: ca.cert.Raw})
}

func writePEM(path, typ string, der []byte) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return pem.Encode(f, &pem.Block{Type: typ, Bytes: der})
}
