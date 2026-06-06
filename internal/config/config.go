package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Proxy  ProxyConfig  `yaml:"proxy"`
	CA     CAConfig     `yaml:"ca"`
	UI     UIConfig     `yaml:"ui"`
	Script ScriptConfig `yaml:"script"`
}

type ProxyConfig struct {
	Addr    string   `yaml:"addr"`
	Ignore  []string `yaml:"ignore"`  // hosts to skip MITM (passthrough)
	MaxBody int      `yaml:"max_body"` // max bytes to capture per body
}

type CAConfig struct {
	CertPath string `yaml:"cert_path"`
	KeyPath  string `yaml:"key_path"`
}

type UIConfig struct {
	Addr string `yaml:"addr"`
}

type ScriptConfig struct {
	Path string `yaml:"path"`
}

func Default() *Config {
	return &Config{
		Proxy: ProxyConfig{
			Addr:    ":8080",
			MaxBody: 1024 * 1024, // 1MB
		},
		UI: UIConfig{
			Addr: ":8081",
		},
	}
}

func Load(path string) (*Config, error) {
	cfg := Default()
	f, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return cfg, nil
		}
		return nil, err
	}
	defer f.Close()
	if err := yaml.NewDecoder(f).Decode(cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}

func Save(path string, cfg *Config) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return yaml.NewEncoder(f).Encode(cfg)
}
