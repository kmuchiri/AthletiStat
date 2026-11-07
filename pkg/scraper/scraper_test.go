package scraper

import (
	"context"
	"encoding/csv"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"athletistat/pkg/config"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func createScraperTestOptions(t *testing.T) string {
	tmpDir := t.TempDir()
	optsPath := filepath.Join(tmpDir, "options.json")
	content := `[
  {
    "name": "disciplineCode",
    "cases": [
      {
        "gender": "male",
        "ageCategory": "senior",
        "values": [
          {
            "disciplineNameUrlSlug": "100-metres",
            "typeNameUrlSlug": "sprints"
          },
          {
            "disciplineNameUrlSlug": "shot-put",
            "typeNameUrlSlug": "throws"
          }
        ]
      },
      {
        "gender": "female",
        "ageCategory": "senior",
        "values": [
          {
            "disciplineNameUrlSlug": "100-metres",
            "typeNameUrlSlug": "sprints"
          }
        ]
      }
    ]
  }
]`
	err := os.WriteFile(optsPath, []byte(content), 0644)
	require.NoError(t, err)
	return optsPath
}

func TestLoadMappings(t *testing.T) {
	opts := createScraperTestOptions(t)
	s := NewScraper("both", opts)

	maleKey := MappingKey{Gender: "male", AgeCategory: "senior"}
	femaleKey := MappingKey{Gender: "female", AgeCategory: "senior"}

	assert.Contains(t, s.Mappings, maleKey)
	assert.Contains(t, s.Mappings, femaleKey)
	assert.Len(t, s.Mappings[maleKey], 2)
	assert.Len(t, s.Mappings[femaleKey], 1)

	for _, list := range s.Mappings {
		for _, pair := range list {
			assert.NotEmpty(t, pair.DisciplineSlug)
			assert.NotEmpty(t, pair.TypeSlug)
		}
	}
}

func TestLoadRootOptionsJson(t *testing.T) {
	rootOpts := filepath.Join("..", "..", "options.json")
	if _, err := os.Stat(rootOpts); os.IsNotExist(err) {
		t.Skip("options.json not found in root")
	}

	s := NewScraper("both", rootOpts)
	require.NotEmpty(t, s.Mappings)

	mixedSeniorKey := MappingKey{Gender: "mixed", AgeCategory: "senior"}
	assert.Contains(t, s.Mappings, mixedSeniorKey)
	assert.Len(t, s.Mappings[mixedSeniorKey], 3)

	maleSeniorKey := MappingKey{Gender: "male", AgeCategory: "senior"}
	assert.Contains(t, s.Mappings, maleSeniorKey)

	// Check for short track and 2026 race walk in male senior
	var hasShortTrack, hasHalfMarathonRW, hasMarathonRW bool
	for _, pair := range s.Mappings[maleSeniorKey] {
		if pair.DisciplineSlug == "200-metres-short-track" && pair.TypeSlug == "sprints" {
			hasShortTrack = true
		}
		if pair.DisciplineSlug == "half-marathon-race-walk" && pair.TypeSlug == "race-walks" {
			hasHalfMarathonRW = true
		}
		if pair.DisciplineSlug == "marathon-race-walk" && pair.TypeSlug == "race-walks" {
			hasMarathonRW = true
		}
	}
	assert.True(t, hasShortTrack, "should contain 200m short track")
	assert.True(t, hasHalfMarathonRW, "should contain half-marathon race walk")
	assert.True(t, hasMarathonRW, "should contain marathon race walk")
}

func TestBuildJobs(t *testing.T) {
	opts := createScraperTestOptions(t)
	s := NewScraper("both", opts)

	seasonsJobs := s.BuildJobs("seasons", 2024)
	assert.NotEmpty(t, seasonsJobs)
	for _, job := range seasonsJobs {
		assert.Equal(t, "seasons", job.Mode)
		assert.Equal(t, 2024, job.Year)
	}

	allTimeJobs := s.BuildJobs("all-time")
	assert.NotEmpty(t, allTimeJobs)
	for _, job := range allTimeJobs {
		assert.Equal(t, "all-time", job.Mode)
		assert.Equal(t, 0, job.Year)
	}
}

func TestGetQueueInfo(t *testing.T) {
	opts := createScraperTestOptions(t)
	s := NewScraper("both", opts)

	seasonsPath := s.GetQueueInfo("seasons", 2020)
	assert.Contains(t, seasonsPath, "2020")
	assert.Contains(t, seasonsPath, "queue_seasons_2020.json")

	allTimePath := s.GetQueueInfo("all-time", 0)
	assert.Contains(t, allTimePath, s.Today)
}

func TestScrapeEventSuccess(t *testing.T) {
	htmlTable := `
<html><body>
<table class="records-table">
  <tbody>
    <tr>
      <td>1</td><td>9.58</td><td>0.0</td><td>Bolt U</td><td>21 Aug 1986</td>
      <td>JAM</td><td>1</td><td>extra</td><td>Berlin (GER)</td><td>16 Aug 2009</td>
      <td>1244</td>
    </tr>
  </tbody>
</table>
</body></html>`

	pageCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		pageCount++
		if pageCount == 1 {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(htmlTable))
		} else {
			// Page 2: empty
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("<html><body></body></html>"))
		}
	}))
	defer server.Close()

	opts := createScraperTestOptions(t)
	s := NewScraper("seasons", opts)
	s.Client = server.Client()

	tmpOut := t.TempDir()
	config.Cfg.Scraper.PageDelay = 0 // No delay in tests

	job := ScrapeJob{
		Gender:         "male",
		AgeCategory:    "senior",
		DisciplineSlug: "100-metres",
		TypeSlug:       "sprints",
		OutputDir:      tmpOut,
		Mode:           "seasons",
		Year:           2024,
	}

	// We temporarily hijack request by setting client transport to route to mock server
	s.Client.Transport = &rewriteTransport{target: server.URL}

	count, ok, err := s.ScrapeEvent(context.Background(), job, nil)
	assert.Equal(t, 1, count)
	assert.True(t, ok)
	assert.NoError(t, err)

	csvPath := filepath.Join(tmpOut, "2024_sprints_100-metres_senior.csv")
	assert.FileExists(t, csvPath)

	f, err := os.Open(csvPath)
	require.NoError(t, err)
	defer f.Close()

	rows, err := csv.NewReader(f).ReadAll()
	require.NoError(t, err)
	assert.Len(t, rows, 2) // Header + 1 record
	assert.Equal(t, "Bolt U", rows[1][3])
}

type rewriteTransport struct {
	target string
}

func (t *rewriteTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	req.URL.Scheme = "http"
	req.URL.Host = strings.TrimPrefix(t.target, "http://")
	return http.DefaultTransport.RoundTrip(req)
}

func TestScraperLogging(t *testing.T) {
	tmpDir := t.TempDir()
	config.Cfg.Paths.LogDir = filepath.Join(tmpDir, "logs")

	opts := createScraperTestOptions(t)
	s := NewScraper("seasons", opts)

	job := ScrapeJob{
		Gender:         "male",
		AgeCategory:    "senior",
		DisciplineSlug: "100-metres",
		TypeSlug:       "sprints",
		Mode:           "seasons",
		Year:           2024,
	}

	// Test logError
	testErr := fmt.Errorf("simulated connection failure")
	s.logError(job, "https://worldathletics.org/test", testErr)

	modeErrorLog := filepath.Join(config.Cfg.Paths.LogDir, "seasons", "scrape_errors.log")
	assert.FileExists(t, modeErrorLog)
	content, err := os.ReadFile(modeErrorLog)
	require.NoError(t, err)
	assert.Contains(t, string(content), "100-metres")
	assert.Contains(t, string(content), "simulated connection failure")

	// Test logRunSummary
	start := time.Now().Add(-2 * time.Minute)
	end := time.Now()
	duration := end.Sub(start)

	runLogPath := s.logRunSummary("seasons", 2024, start, end, duration, 1500, 10, 9, 1)
	assert.FileExists(t, runLogPath)

	runContent, err := os.ReadFile(runLogPath)
	require.NoError(t, err)
	runStr := string(runContent)
	assert.Contains(t, runStr, "SCRAPE RUN SUMMARY")
	assert.Contains(t, runStr, "Time Started:")
	assert.Contains(t, runStr, "Time Ended:")
	assert.Contains(t, runStr, "Time Taken:")
	assert.Contains(t, runStr, "Total Time:")
	assert.Contains(t, runStr, "Amount of Records: 1500")
	assert.Contains(t, runStr, "Total Jobs:        10")
	assert.Contains(t, runStr, "Successful Jobs:   9")
	assert.Contains(t, runStr, "Failed Jobs:       1")

	// Check master runs log
	masterLog := filepath.Join(config.Cfg.Paths.LogDir, "seasons", "scrape_runs.log")
	assert.FileExists(t, masterLog)
}
