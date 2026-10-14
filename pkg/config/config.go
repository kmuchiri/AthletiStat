package config

import (
	"os"

	"github.com/pelletier/go-toml/v2"
)

// ScraperConfig holds settings for web scraping.
type ScraperConfig struct {
	MaxWorkers         int     `toml:"max_workers"`
	ConnectTimeout     int     `toml:"connect_timeout"`
	ReadTimeout        int     `toml:"read_timeout"`
	RetryTotal         int     `toml:"retry_total"`
	RetryBackoffFactor float64 `toml:"retry_backoff_factor"`
	RetryStatusCodes   []int   `toml:"retry_status_codes"`
	PageDelay          float64 `toml:"page_delay"`
	UserAgent          string  `toml:"user_agent"`
	VerifySSL          bool    `toml:"verify_ssl"`
}

// PathsConfig holds file system paths for the pipeline.
type PathsConfig struct {
	OptionsFile        string `toml:"options_file"`
	ScraperOutput      string `toml:"scraper_output"`
	QueueDir           string `toml:"queue_dir"`
	LogDir             string `toml:"log_dir"`
	CombinedDir        string `toml:"combined_dir"`
	DatasetDir         string `toml:"dataset_dir"`
	DatasetInfoFile    string `toml:"dataset_info_file"`
	DatasetSummaryFile string `toml:"dataset_summary_file"`
}

// DisplayConfig holds terminal display and chunk tuning.
type DisplayConfig struct {
	ProgressBarWidth  int  `toml:"progress_bar_width"`
	RowCountChunkSize int  `toml:"row_count_chunk_size"`
	ShowSaveLog       bool `toml:"show_save_log"`
}

// Config is the top-level configuration container.
type Config struct {
	Scraper ScraperConfig `toml:"scraper"`
	Paths   PathsConfig   `toml:"paths"`
	Display DisplayConfig `toml:"display"`
}

// DefaultConfig returns the built-in configuration defaults.
func DefaultConfig() *Config {
	return &Config{
		Scraper: ScraperConfig{
			MaxWorkers:         4,
			ConnectTimeout:     5,
			ReadTimeout:        30,
			RetryTotal:         5,
			RetryBackoffFactor: 1.0,
			RetryStatusCodes:   []int{429, 500, 502, 503, 504},
			PageDelay:          1.5,
			UserAgent:          "Mozilla/5.0",
			VerifySSL:          true,
		},
		Paths: PathsConfig{
			OptionsFile:        "athletistat/options.json",
			ScraperOutput:      "data/processing/output",
			QueueDir:           "queues",
			LogDir:             "logs",
			CombinedDir:        "data/processing/combined",
			DatasetDir:         "data/datasets",
			DatasetInfoFile:    "data/datasets/dataset_info.txt",
			DatasetSummaryFile: "data/datasets/dataset_summary.txt",
		},
		Display: DisplayConfig{
			ProgressBarWidth:  30,
			RowCountChunkSize: 1048576, // 1 MB
			ShowSaveLog:       true,
		},
	}
}

// LoadConfig loads TOML config from the given file, falling back to defaults if not found.
func LoadConfig(configPath string) (*Config, error) {
	cfg := DefaultConfig()

	if configPath == "" {
		// Try standard locations
		for _, candidate := range []string{"athletistat/config.toml", "config.toml"} {
			if _, err := os.Stat(candidate); err == nil {
				configPath = candidate
				break
			}
		}
	}

	if configPath == "" {
		return cfg, nil
	}

	data, err := os.ReadFile(configPath)
	if err != nil {
		if os.IsNotExist(err) {
			return cfg, nil
		}
		return nil, err
	}

	if err := toml.Unmarshal(data, cfg); err != nil {
		return nil, err
	}

	return cfg, nil
}

// Cfg is the global configuration singleton.
var Cfg *Config

func init() {
	var err error
	Cfg, err = LoadConfig("")
	if err != nil {
		Cfg = DefaultConfig()
	}
}
