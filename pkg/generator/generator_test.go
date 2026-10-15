package generator

import (
	"encoding/csv"
	"os"
	"path/filepath"
	"testing"

	"athletistat/pkg/config"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

var sampleHeader = []string{
	"rank", "mark", "wind", "competitor", "dob", "nationality", "position",
	"venue", "date", "result_score", "discipline", "type", "sex", "age_cat",
	"normalized_discipline", "track_field", "mark_numeric", "nat_full",
	"venue_country", "age_at_event", "season",
}

func sampleRow(name, mark, sex, typ, disc, season string) []string {
	return []string{
		"1", mark, "0.0", name, "21 Aug 1986", "JAM", "1",
		"Berlin (GER)", "16 Aug 2009", "1244", disc, typ, sex, "senior",
		disc, "track", mark, "Jamaica", "Germany", "22", season,
	}
}

func TestDatasetGeneratorSeasons(t *testing.T) {
	tmpDir := t.TempDir()
	config.Cfg.Paths.CombinedDir = filepath.Join(tmpDir, "combined")
	config.Cfg.Paths.DatasetDir = filepath.Join(tmpDir, "datasets")

	yearDir := filepath.Join(config.Cfg.Paths.CombinedDir, "seasons", "2024")
	err := os.MkdirAll(yearDir, 0755)
	require.NoError(t, err)

	f1 := filepath.Join(yearDir, "male_sprints_100-metres.csv")
	rows1 := [][]string{sampleRow("Bolt U", "9.58", "male", "sprints", "100-metres", "2024")}
	require.NoError(t, writeCSVFile(f1, sampleHeader, rows1))

	f2 := filepath.Join(yearDir, "female_sprints_100-metres.csv")
	rows2 := [][]string{sampleRow("Thompson E", "10.54", "female", "sprints", "100-metres", "2024")}
	require.NoError(t, writeCSVFile(f2, sampleHeader, rows2))

	gen := NewDatasetGenerator("seasons")
	err = gen.GenerateDatasets("seasons")
	require.NoError(t, err)

	outPath := filepath.Join(config.Cfg.Paths.DatasetDir, "seasons", "2024_track_field_performances.csv")
	assert.FileExists(t, outPath)

	_, rows, err := readCSVFile(outPath)
	require.NoError(t, err)
	assert.Len(t, rows, 2)
}

func TestDatasetGeneratorAllTimeDeduplication(t *testing.T) {
	tmpDir := t.TempDir()
	config.Cfg.Paths.CombinedDir = filepath.Join(tmpDir, "combined")
	config.Cfg.Paths.DatasetDir = filepath.Join(tmpDir, "datasets")

	allTimeDir := filepath.Join(config.Cfg.Paths.CombinedDir, "all-time")
	err := os.MkdirAll(allTimeDir, 0755)
	require.NoError(t, err)

	row := sampleRow("Bolt U", "9.58", "male", "sprints", "100-metres", "2009")
	require.NoError(t, writeCSVFile(filepath.Join(allTimeDir, "file_a.csv"), sampleHeader, [][]string{row}))
	require.NoError(t, writeCSVFile(filepath.Join(allTimeDir, "file_b.csv"), sampleHeader, [][]string{row}))

	gen := NewDatasetGenerator("all-time")
	err = gen.GenerateDatasets("all-time")
	require.NoError(t, err)

	outPath := filepath.Join(config.Cfg.Paths.DatasetDir, "all-time", "top_track_field_performances_all_time.csv")
	assert.FileExists(t, outPath)

	_, rows, err := readCSVFile(outPath)
	require.NoError(t, err)
	assert.Len(t, rows, 1) // Deduplicated
}

func TestCombineSeasons(t *testing.T) {
	tmpDir := t.TempDir()
	config.Cfg.Paths.DatasetDir = filepath.Join(tmpDir, "datasets")
	seasonsDir := filepath.Join(config.Cfg.Paths.DatasetDir, "seasons")
	err := os.MkdirAll(seasonsDir, 0755)
	require.NoError(t, err)

	r2020 := sampleRow("Athlete A", "10.0", "male", "sprints", "100-metres", "2020")
	r2024 := sampleRow("Athlete B", "9.9", "male", "sprints", "100-metres", "2024")

	require.NoError(t, writeCSVFile(filepath.Join(seasonsDir, "2020_track_field_performances.csv"), sampleHeader, [][]string{r2020}))
	require.NoError(t, writeCSVFile(filepath.Join(seasonsDir, "2024_track_field_performances.csv"), sampleHeader, [][]string{r2024}))

	gen := NewDatasetGenerator("seasons")
	err = gen.CombineSeasons()
	require.NoError(t, err)

	combinedFile := filepath.Join(seasonsDir, "combined_track_field_performances_2020_2024.csv")
	assert.FileExists(t, combinedFile)

	_, rows, err := readCSVFile(combinedFile)
	require.NoError(t, err)
	assert.Len(t, rows, 2)
}

func TestDatasetSplitterFilenames(t *testing.T) {
	s := NewDatasetSplitter("both")

	assert.Equal(t, "sprints_2022.csv", s.GetFilenameWithYears("sprints", 2022, 2022, true, true))
	assert.Equal(t, "sprints_2018-2022.csv", s.GetFilenameWithYears("sprints", 2018, 2022, true, true))
	assert.Equal(t, "sprints.csv", s.GetFilenameWithYears("sprints", 2018, 2022, true, false))
	assert.Equal(t, "sprints.csv", s.GetFilenameWithYears("sprints", 0, 0, false, true))
}

func TestSplitDataset(t *testing.T) {
	tmpDir := t.TempDir()
	outModeDir := filepath.Join(tmpDir, "seasons")

	indRow := sampleRow("Bolt U", "9.58", "male", "sprints", "100-metres", "2008")
	relayRow := []string{
		"1", "37.10", "0.0", "Team JAM", "21 Aug 1986", "JAM", "1",
		"Beijing (CHN)", "22 Aug 2008", "1000", "4x100-metres-relay", "relays", "male", "senior",
		"4x100-metres-relay", "track", "37.10", "Jamaica", "China", "21", "2008",
	}

	splitter := NewDatasetSplitter("seasons")
	err := splitter.SplitDataset(sampleHeader, [][]string{indRow, relayRow}, outModeDir, true)
	require.NoError(t, err)

	// Global individual exists
	globalIndPath := filepath.Join(outModeDir, "split_global", "individual_events_2008.csv")
	assert.FileExists(t, globalIndPath)

	// Global relay exists and drops dob & age_at_event
	globalRelayPath := filepath.Join(outModeDir, "split_global", "relay_events_2008.csv")
	assert.FileExists(t, globalRelayPath)

	f, err := os.Open(globalRelayPath)
	require.NoError(t, err)
	defer f.Close()
	relayHeader, err := csv.NewReader(f).Read()
	require.NoError(t, err)
	assert.NotContains(t, relayHeader, "dob")
	assert.NotContains(t, relayHeader, "age_at_event")

	// Type splits exist
	typePath := filepath.Join(outModeDir, "split_by_type", "male", "sprints_2008.csv")
	assert.FileExists(t, typePath)

	// Discipline splits exist
	discPath := filepath.Join(outModeDir, "split_by_discipline", "male", "100-metres_2008.csv")
	assert.FileExists(t, discPath)

	// Relays splits exist
	relayDiscPath := filepath.Join(outModeDir, "relays", "male", "4x100-metres-relay_2008.csv")
	assert.FileExists(t, relayDiscPath)
}
