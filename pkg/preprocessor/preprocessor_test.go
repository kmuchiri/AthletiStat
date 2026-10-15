package preprocessor

import (
	"math"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func createTestOptions(t *testing.T) string {
	tmpDir := t.TempDir()
	optionsPath := filepath.Join(tmpDir, "options.json")
	content := `[
  {
    "name": "region",
    "cases": [
      {
        "regionType": "countries",
        "values": [
          {"value": "ken", "label": "Kenya"},
          {"value": "usa", "label": "United States"},
          {"value": "eth", "label": "Ethiopia"},
          {"value": "jam", "label": "Jamaica"}
        ]
      }
    ]
  }
]`
	err := os.WriteFile(optionsPath, []byte(content), 0644)
	require.NoError(t, err)
	return optionsPath
}

func TestNormalizeDiscipline(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	assert.Equal(t, "100-metres-hurdles", p.NormalizeDiscipline("100m-hurdles"))
	assert.Equal(t, "110-metres-hurdles", p.NormalizeDiscipline("110m-hurdles"))
	assert.Equal(t, "400-metres-hurdles", p.NormalizeDiscipline("400m-hurdles"))
	assert.Equal(t, "decathlon", p.NormalizeDiscipline("decathlon-u20"))
	assert.Equal(t, "decathlon", p.NormalizeDiscipline("decathlon-boys"))
	assert.Equal(t, "heptathlon", p.NormalizeDiscipline("heptathlon-girls"))
	assert.Equal(t, "shot-put", p.NormalizeDiscipline("shot-put-u18"))
	assert.Equal(t, "shot-put", p.NormalizeDiscipline("shot-put-u20"))
	assert.Equal(t, "hammer", p.NormalizeDiscipline("hammer-7260g"))
	assert.Equal(t, "100-metres", p.NormalizeDiscipline("100-metres"))
	assert.Equal(t, "marathon", p.NormalizeDiscipline("marathon-senior"))
	assert.Contains(t, p.NormalizeDiscipline("indoor-400m-hurdles-senior"), "400-metres-hurdles")
}

func TestParseMarkToNumber(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	assert.InDelta(t, 9.58, p.ParseMarkToNumber("9.58"), 1e-4)
	assert.InDelta(t, 100.0, p.ParseMarkToNumber("100"), 1e-4)
	assert.InDelta(t, 90.0, p.ParseMarkToNumber("1:30"), 1e-4)
	assert.InDelta(t, 7393.0, p.ParseMarkToNumber("2:03:13"), 1e-4)
	assert.InDelta(t, 10.5, p.ParseMarkToNumber("10.5h"), 1e-4)
	assert.True(t, math.IsInf(p.ParseMarkToNumber("DNF"), 1))
	assert.True(t, math.IsInf(p.ParseMarkToNumber(""), 1))
	assert.InDelta(t, 9.58, p.ParseMarkToNumber("  9.58  "), 1e-4)
	assert.True(t, math.IsInf(p.ParseMarkToNumber("1:2:3:4"), 1))
}

func TestExtractCountryCodeFromVenue(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	assert.Equal(t, "KEN", p.ExtractCountryCodeFromVenue("Nairobi (KEN)"))
	assert.Equal(t, "USA", p.ExtractCountryCodeFromVenue("Eugene (USA)"))
	assert.Equal(t, "", p.ExtractCountryCodeFromVenue("Berlin"))
	assert.Equal(t, "", p.ExtractCountryCodeFromVenue(""))
	assert.Equal(t, "", p.ExtractCountryCodeFromVenue("City (US)"))
	assert.Equal(t, "AAA", p.ExtractCountryCodeFromVenue("X (AAA) Y (BBB)"))
	assert.Equal(t, "100", p.ExtractCountryCodeFromVenue("Arena (100)"))
}

func TestCountryLookup(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	assert.Equal(t, "Kenya", p.CountryLookup["ken"])
	assert.Equal(t, "United States", p.CountryLookup["usa"])
	_, exists := p.CountryLookup["xyz"]
	assert.False(t, exists)
}

func TestTypeSets(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	assert.True(t, p.AscendingTypes["sprints"])
	assert.True(t, p.DescendingTypes["throws"])
	assert.True(t, p.FieldTypes["jumps"])
	assert.True(t, p.MixedTypes["combined-events"])
	assert.True(t, p.TrackTypes["relays"])
}

func TestGetFilesByKeyMissingDir(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	res := p.GetFilesByKey("seasons")
	assert.Nil(t, res)
}
