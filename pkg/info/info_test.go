package info

import (
	"os"
	"path/filepath"
	"testing"

	"athletistat/pkg/config"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestCountRows(t *testing.T) {
	tmpDir := t.TempDir()
	csvPath := filepath.Join(tmpDir, "test.csv")
	content := "header1,header2\nrow1_col1,row1_col2\nrow2_col1,row2_col2\nrow3_col1,row3_col2\n"
	err := os.WriteFile(csvPath, []byte(content), 0644)
	require.NoError(t, err)

	d := NewDatasetInfo()
	count, err := d.CountRows(csvPath)
	require.NoError(t, err)
	assert.Equal(t, int64(3), count)
}

func TestGetFileSize(t *testing.T) {
	tmpDir := t.TempDir()
	filePath := filepath.Join(tmpDir, "small.txt")
	err := os.WriteFile(filePath, make([]byte, 1024*1024*2), 0644) // 2 MB
	require.NoError(t, err)

	d := NewDatasetInfo()
	sizeStr := d.GetFileSize(filePath)
	assert.Equal(t, "2.00 MB", sizeStr)
}

func TestGenerateInfo(t *testing.T) {
	tmpDir := t.TempDir()
	config.Cfg.Paths.DatasetDir = tmpDir
	config.Cfg.Paths.DatasetInfoFile = filepath.Join(tmpDir, "dataset_info.txt")

	allTimeDir := filepath.Join(tmpDir, "all-time")
	err := os.MkdirAll(allTimeDir, 0755)
	require.NoError(t, err)

	testCSV := filepath.Join(allTimeDir, "test_file.csv")
	err = os.WriteFile(testCSV, []byte("h1,h2\nv1,v2\n"), 0644)
	require.NoError(t, err)

	d := NewDatasetInfo()
	err = d.GenerateInfo()
	require.NoError(t, err)

	assert.FileExists(t, config.Cfg.Paths.DatasetInfoFile)
	content, err := os.ReadFile(config.Cfg.Paths.DatasetInfoFile)
	require.NoError(t, err)
	assert.Contains(t, string(content), "test_file.csv")
}
