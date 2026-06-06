package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/ykus4/paxy/internal/api"
	"github.com/ykus4/paxy/internal/cert"
	"github.com/ykus4/paxy/internal/config"
	"github.com/ykus4/paxy/internal/interceptor"
	"github.com/ykus4/paxy/internal/proxy"
	"github.com/ykus4/paxy/internal/replay"
	"github.com/ykus4/paxy/internal/rule"
	"github.com/ykus4/paxy/internal/script"
	"github.com/ykus4/paxy/internal/store"
)

func main() {
	addr := flag.String("addr", ":8080", "proxy listen address")
	uiAddr := flag.String("ui-addr", ":8081", "web UI listen address")
	configPath := flag.String("config", "", "path to YAML config file")
	scriptPath := flag.String("script", "", "path to Lua script file")
	caDir := flag.String("ca-dir", mustConfigDir(), "directory to store CA cert/key")
	flag.Parse()

	cfg := config.Default()
	if *configPath != "" {
		var err error
		cfg, err = config.Load(*configPath)
		if err != nil {
			log.Fatalf("failed to load config: %v", err)
		}
	}

	// CLI flags override config file values.
	if isFlagSet("addr") {
		cfg.Proxy.Addr = *addr
	} else if cfg.Proxy.Addr != "" {
		*addr = cfg.Proxy.Addr
	}

	if isFlagSet("ui-addr") {
		cfg.UI.Addr = *uiAddr
	} else if cfg.UI.Addr != "" {
		*uiAddr = cfg.UI.Addr
	}

	if isFlagSet("ca-dir") {
		// use CLI value; no override needed
	} else if cfg.CA.CertPath != "" {
		*caDir = filepath.Dir(cfg.CA.CertPath)
	}

	if isFlagSet("script") {
		cfg.Script.Path = *scriptPath
	} else if cfg.Script.Path != "" {
		*scriptPath = cfg.Script.Path
	}

	if err := os.MkdirAll(*caDir, 0700); err != nil {
		log.Fatalf("failed to create ca-dir: %v", err)
	}

	caCertPath := filepath.Join(*caDir, "ca-cert.pem")
	caKeyPath := filepath.Join(*caDir, "ca-key.pem")
	if cfg.CA.CertPath != "" {
		caCertPath = cfg.CA.CertPath
	}
	if cfg.CA.KeyPath != "" {
		caKeyPath = cfg.CA.KeyPath
	}

	ca, err := cert.LoadOrCreate(caCertPath, caKeyPath)
	if err != nil {
		log.Fatalf("CA init failed: %v", err)
	}

	st := store.New()
	rules := rule.NewManager()
	rp := replay.New()
	ic := interceptor.New(rules, st)

	var eng *script.Engine
	if *scriptPath != "" {
		eng = script.NewEngine()
		if err := eng.LoadFile(*scriptPath); err != nil {
			log.Fatalf("failed to load script: %v", err)
		}
	}

	apiServer := api.NewServer(st, rules, rp)
	go func() {
		log.Printf("UI listening on %s", *uiAddr)
		if err := http.ListenAndServe(*uiAddr, apiServer); err != nil {
			log.Printf("UI server error: %v", err)
		}
	}()

	fmt.Printf("paxy MITM proxy\n")
	fmt.Printf("  proxy addr : %s\n", *addr)
	fmt.Printf("  UI addr    : %s\n", *uiAddr)
	fmt.Printf("  CA cert    : %s\n", caCertPath)
	fmt.Println("Install the CA cert in your browser/device to avoid TLS warnings.")

	p := proxy.New(proxy.Options{
		Addr:        *addr,
		CA:          ca,
		Interceptor: ic,
		Script:      eng,
		Store:       st,
		Ignore:      cfg.Proxy.Ignore,
	})

	if err := p.Start(); err != nil {
		log.Fatal(err)
	}
}

func mustConfigDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ".paxy"
	}
	return filepath.Join(home, ".paxy")
}

// isFlagSet reports whether a flag was explicitly set on the command line.
func isFlagSet(name string) bool {
	found := false
	flag.Visit(func(f *flag.Flag) {
		if f.Name == name {
			found = true
		}
	})
	return found
}
