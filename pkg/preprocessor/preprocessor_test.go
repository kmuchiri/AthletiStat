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
  },
  {
    "name": "disciplineCode",
    "cases": [
      {
        "gender": "male",
        "ageCategory": "senior",
        "values": [
          {"disciplineNameUrlSlug": "100-metres", "environment": "outdoor"},
          {"disciplineNameUrlSlug": "200-metres-short-track", "environment": "indoor"}
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

func TestRootOptionsJsonCountryLookup(t *testing.T) {
	rootOpts := filepath.Join("..", "..", "options.json")
	if _, err := os.Stat(rootOpts); os.IsNotExist(err) {
		t.Skip("options.json not found in root")
	}

	p := NewPreprocessor("both", rootOpts)
	assert.Equal(t, "Kenya", p.CountryLookup["ken"])
	assert.Equal(t, "United States", p.CountryLookup["usa"])
	assert.Equal(t, "Jamaica", p.CountryLookup["jam"])
	assert.GreaterOrEqual(t, len(p.CountryLookup), 200)
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

func TestFormatCompetitor(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	// Standard athlete names
	assert.Equal(t, "Usain Bolt", p.FormatCompetitor("Usain BOLT", false))
	assert.Equal(t, "Jackie Joyner-Kersee", p.FormatCompetitor("Jackie JOYNER-KERSEE", false))
	assert.Equal(t, "Shelly-Ann Fraser-Pryce", p.FormatCompetitor("Shelly-Ann FRASER-PRYCE", false))
	assert.Equal(t, "Ferdinand Omanyala Omurwa", p.FormatCompetitor("Ferdinand OMANYALA OMURWA", false))
	assert.Equal(t, "Wayde Van Niekerk", p.FormatCompetitor("Wayde VAN NIEKERK", false))

	// Mc exceptions
	assert.Equal(t, "Eamonn McAlister", p.FormatCompetitor("Eamonn MCALISTER", false))
	assert.Equal(t, "Chantae McMillan", p.FormatCompetitor("Chantae MCMILLAN", false))
	assert.Equal(t, "Sydney McLaughlin-Levrone", p.FormatCompetitor("Sydney MCLAUGHLIN-LEVRONE", false))
	assert.Equal(t, "Miesha McKelvy-Jones", p.FormatCompetitor("Miesha MCKELVY-JONES", false))
	assert.Equal(t, "Aaliyah McCormick", p.FormatCompetitor("Aaliyah MCCORMICK", false))

	// O' exceptions
	assert.Equal(t, "Kate O'Connor", p.FormatCompetitor("Kate O'CONNOR", false))

	// Initials
	assert.Equal(t, "G. Sindhushree", p.FormatCompetitor("G. SINDHUSHREE", false))

	// Relays should NOT be modified
	assert.Equal(t, "United States", p.FormatCompetitor("United States", true))
	assert.Equal(t, "USA Red", p.FormatCompetitor("USA Red", true))
	assert.Equal(t, "Jamaica", p.FormatCompetitor("Jamaica", true))

	// Empty
	assert.Equal(t, "", p.FormatCompetitor("", false))
}

func TestGetEnvironment(t *testing.T) {
	opts := createTestOptions(t)
	p := NewPreprocessor("both", opts)

	assert.Equal(t, "outdoor", p.GetEnvironment("100-metres"))
	assert.Equal(t, "indoor", p.GetEnvironment("200-metres-short-track"))
	assert.Equal(t, "indoor", p.GetEnvironment("heptathlon-short-track"))
	assert.Equal(t, "outdoor", p.GetEnvironment("marathon"))
}
