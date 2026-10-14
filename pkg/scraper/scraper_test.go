package scraper

import (
	"context"
	"encoding/csv"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

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

	ok, err := s.ScrapeEvent(context.Background(), job, nil)
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
