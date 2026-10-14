package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	assert.Equal(t, 10, cfg.Scraper.MaxWorkers)
	assert.Equal(t, 5, cfg.Scraper.ConnectTimeout)
	assert.Equal(t, 30, cfg.Scraper.ReadTimeout)
	assert.Equal(t, 1.5, cfg.Scraper.PageDelay)
	assert.Equal(t, "athletistat/options.json", cfg.Paths.OptionsFile)
	assert.Equal(t, 30, cfg.Display.ProgressBarWidth)
	assert.True(t, cfg.Display.ShowSaveLog)
}

func TestLoadConfigMissingFile(t *testing.T) {
	cfg, err := LoadConfig("nonexistent_path/config.toml")
	require.NoError(t, err)
	assert.Equal(t, 10, cfg.Scraper.MaxWorkers)
}

func TestLoadConfigCustom(t *testing.T) {
	tmpDir := t.TempDir()
	tomlContent := `
[scraper]
max_workers = 25
page_delay = 0.5
user_agent = "CustomAgent/1.0"

[paths]
options_file = "custom_opts.json"

[display]
progress_bar_width = 40
`
	configPath := filepath.Join(tmpDir, "test_config.toml")
	err := os.WriteFile(configPath, []byte(tomlContent), 0644)
	require.NoError(t, err)

	cfg, err := LoadConfig(configPath)
	require.NoError(t, err)
	assert.Equal(t, 25, cfg.Scraper.MaxWorkers)
	assert.Equal(t, 0.5, cfg.Scraper.PageDelay)
	assert.Equal(t, "CustomAgent/1.0", cfg.Scraper.UserAgent)
	assert.Equal(t, "custom_opts.json", cfg.Paths.OptionsFile)
	assert.Equal(t, 40, cfg.Display.ProgressBarWidth)
	// Defaults preserved for unspecified fields
	assert.Equal(t, 30, cfg.Scraper.ReadTimeout)
}
