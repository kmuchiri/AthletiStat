package updater

import (
	"context"
	"encoding/csv"
	"os"
	"path/filepath"
	"testing"

	"athletistat/pkg/config"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func writeTestCSV(path string, header []string, rows [][]string) error {
	_ = os.MkdirAll(filepath.Dir(path), 0755)
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	w := csv.NewWriter(f)
	_ = w.Write(header)
	_ = w.WriteAll(rows)
	w.Flush()
	return nil
}

func TestSeasonsUpdate(t *testing.T) {
	tmpDir := t.TempDir()
	config.Cfg.Paths.DatasetDir = tmpDir
	seasonsDir := filepath.Join(tmpDir, "seasons")

	header := []string{"competitor", "mark", "season"}
	initialRows := [][]string{
		{"Athlete 2022", "10.0", "2022"},
		{"Athlete 2023 Old", "10.1", "2023"},
		{"Athlete 2024", "9.9", "2024"},
	}

	initialCombined := filepath.Join(seasonsDir, "combined_track_field_performances_2022_2024.csv")
	require.NoError(t, writeTestCSV(initialCombined, header, initialRows))

	year2023Rows := [][]string{
		{"Athlete 2023 Fresh 1", "9.95", "2023"},
		{"Athlete 2023 Fresh 2", "9.98", "2023"},
	}
	year2023File := filepath.Join(seasonsDir, "2023_track_field_performances.csv")
	require.NoError(t, writeTestCSV(year2023File, header, year2023Rows))

	u := NewSeasonsUpdate(2023, false)
	assert.Equal(t, initialCombined, u.CombinedFile)

	err := u.Run(context.Background())
	require.NoError(t, err)

	// Updated file should exist
	updatedCombined := filepath.Join(seasonsDir, "combined_track_field_performances_2022_2024.csv")
	assert.FileExists(t, updatedCombined)

	f, err := os.Open(updatedCombined)
	require.NoError(t, err)
	defer f.Close()

	r := csv.NewReader(f)
	readRows, err := r.ReadAll()
	require.NoError(t, err)

	assert.Len(t, readRows, 5) // Header + 4 records (Athlete 2022, 2024, and 2 fresh 2023 records)
	// Verify old 2023 record is gone
	for _, row := range readRows {
		assert.NotEqual(t, "Athlete 2023 Old", row[0])
	}
}
