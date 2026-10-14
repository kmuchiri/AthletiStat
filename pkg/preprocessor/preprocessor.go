package preprocessor

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"athletistat/pkg/config"
	"athletistat/pkg/console"
)

// Record represents a single row in raw or preprocessed datasets.
type Record struct {
	Rank                 string
	Mark                 string
	Wind                 string
	Competitor           string
	DOB                  string
	Nationality          string
	Position             string
	Venue                string
	Date                 string
	ResultScore          string
	Discipline           string
	Type                 string
	Sex                  string
	AgeCat               string
	NormalizedDiscipline string
	TrackField           string
	MarkNumeric          float64
	NatFull              string
	VenueCountry         string
	AgeAtEvent           string
	Season               string
}

// GroupKey represents the grouping key for preprocessor raw files.
type GroupKey struct {
	Year           string
	Gender         string
	TypeSlug       string
	BaseDiscipline string
}

// Preprocessor handles data cleaning and normalization.
type Preprocessor struct {
	Mode            string
	OptionsFile     string
	CountryLookup   map[string]string
	ManualAliases   map[string]string
	AscendingTypes  map[string]bool
	DescendingTypes map[string]bool
	TrackTypes      map[string]bool
	FieldTypes      map[string]bool
	MixedTypes      map[string]bool

	suffixRegex *regexp.Regexp
	venueRegex  *regexp.Regexp
}

// NewPreprocessor creates and configures a Preprocessor.
func NewPreprocessor(mode string, optionsFile string) *Preprocessor {
	if mode == "" {
		mode = "both"
	}
	if optionsFile == "" {
		optionsFile = config.Cfg.Paths.OptionsFile
	}

	p := &Preprocessor{
		Mode:          mode,
		OptionsFile:   optionsFile,
		CountryLookup: make(map[string]string),
		ManualAliases: map[string]string{
			"100m-hurdles":    "100-metres-hurdles",
			"110m-hurdles":    "110-metres-hurdles",
			"400m-hurdles":    "400-metres-hurdles",
			"decathlon-u20":   "decathlon",
			"decathlon-boys":  "decathlon",
			"heptathlon-girls": "heptathlon",
		},
		AscendingTypes: map[string]bool{
			"sprints":      true,
			"middlelong":   true,
			"hurdles":      true,
			"relays":       true,
			"road-running": true,
			"race-walks":   true,
		},
		DescendingTypes: map[string]bool{
			"throws":          true,
			"jumps":           true,
			"combined-events": true,
		},
		TrackTypes: map[string]bool{
			"sprints":      true,
			"middlelong":   true,
			"hurdles":      true,
			"relays":       true,
			"road-running": true,
			"race-walks":   true,
		},
		FieldTypes: map[string]bool{
			"throws": true,
			"jumps":  true,
		},
		MixedTypes: map[string]bool{
			"combined-events": true,
		},
		suffixRegex: regexp.MustCompile(`[-_](\d+(kg|g|cm)|u18|u20|senior|girls|boys)$`),
		venueRegex:  regexp.MustCompile(`\((\w{3})\)`),
	}

	p.loadCountryLookup()
	return p
}

func (p *Preprocessor) loadCountryLookup() {
	data, err := os.ReadFile(p.OptionsFile)
	if err != nil {
		console.Error(fmt.Sprintf("Config file '%s' not found. Ensure it is in the root directory.", p.OptionsFile))
		return
	}

	var optionsData []map[string]interface{}
	if err := json.Unmarshal(data, &optionsData); err != nil {
		return
	}

	for _, item := range optionsData {
		name, _ := item["name"].(string)
		if name != "region" {
			continue
		}
		cases, _ := item["cases"].([]interface{})
		for _, c := range cases {
			caseMap, _ := c.(map[string]interface{})
			if caseMap["regionType"] != "countries" {
				continue
			}
			values, _ := caseMap["values"].([]interface{})
			for _, v := range values {
				valMap, _ := v.(map[string]interface{})
				code, _ := valMap["value"].(string)
				label, _ := valMap["label"].(string)
				if code != "" && label != "" {
					p.CountryLookup[strings.ToLower(code)] = label
				}
			}
		}
	}
}

// NormalizeDiscipline normalizes discipline slugs by mapping aliases and stripping suffixes.
func (p *Preprocessor) NormalizeDiscipline(disciplineSlug string) string {
	if standard, exists := p.ManualAliases[disciplineSlug]; exists {
		return standard
	}

	for alias, standard := range p.ManualAliases {
		if strings.Contains(disciplineSlug, alias) {
			disciplineSlug = strings.ReplaceAll(disciplineSlug, alias, standard)
		}
	}

	disciplineSlug = p.suffixRegex.ReplaceAllString(disciplineSlug, "")
	return disciplineSlug
}

// ParseMarkToNumber converts a mark string (e.g. "9.58", "1:45.30", "2:01:39") to numeric float seconds.
func (p *Preprocessor) ParseMarkToNumber(mark string) float64 {
	cleaned := strings.TrimSpace(strings.ToLower(strings.ReplaceAll(mark, "h", "")))
	if cleaned == "" {
		return math.Inf(1)
	}

	if strings.Contains(cleaned, ":") {
		parts := strings.Split(cleaned, ":")
		if len(parts) == 3 {
			h, err1 := strconv.ParseFloat(parts[0], 64)
			m, err2 := strconv.ParseFloat(parts[1], 64)
			s, err3 := strconv.ParseFloat(parts[2], 64)
			if err1 != nil || err2 != nil || err3 != nil {
				return math.Inf(1)
			}
			return h*3600 + m*60 + s
		} else if len(parts) == 2 {
			m, err1 := strconv.ParseFloat(parts[0], 64)
			s, err2 := strconv.ParseFloat(parts[1], 64)
			if err1 != nil || err2 != nil {
				return math.Inf(1)
			}
			return m*60 + s
		}
		return math.Inf(1)
	}

	val, err := strconv.ParseFloat(cleaned, 64)
	if err != nil {
		return math.Inf(1)
	}
	return val
}

// ExtractCountryCodeFromVenue extracts a three-letter country code from venue parentheses.
func (p *Preprocessor) ExtractCountryCodeFromVenue(venue string) string {
	match := p.venueRegex.FindStringSubmatch(venue)
	if len(match) > 1 {
		return match[1]
	}
	return ""
}

// GetFilesByKey scans the output directory and groups CSV files by key.
func (p *Preprocessor) GetFilesByKey(currentMode string, year ...string) map[GroupKey][]string {
	filesByKey := make(map[GroupKey][]string)
	inputRoot := filepath.Join(config.Cfg.Paths.ScraperOutput, currentMode)

	if _, err := os.Stat(inputRoot); os.IsNotExist(err) {
		console.Error(fmt.Sprintf("[%s] Input directory not found: %s", strings.ToUpper(currentMode), inputRoot))
		return nil
	}

	console.Info(fmt.Sprintf("[%s] Scanning files in: %s", strings.ToUpper(currentMode), inputRoot))

	if currentMode == "seasons" {
		entries, err := os.ReadDir(inputRoot)
		if err != nil {
			return filesByKey
		}

		var targetYears []string
		filterYear := ""
		if len(year) > 0 && year[0] != "" {
			filterYear = year[0]
		}

		for _, entry := range entries {
			if entry.IsDir() {
				name := entry.Name()
				if _, err := strconv.Atoi(name); err == nil {
					if filterYear == "" || filterYear == name {
						targetYears = append(targetYears, name)
					}
				}
			}
		}

		for _, yr := range targetYears {
			for _, gender := range []string{"male", "female"} {
				genderPath := filepath.Join(inputRoot, yr, gender)
				files, err := os.ReadDir(genderPath)
				if err != nil {
					continue
				}

				for _, file := range files {
					if !file.IsDir() && strings.HasSuffix(file.Name(), ".csv") {
						base := strings.TrimSuffix(file.Name(), ".csv")
						parts := strings.Split(base, "_")
						if len(parts) >= 4 {
							typeSlug := parts[1]
							disciplineSlug := strings.Join(parts[2:len(parts)-1], "_")
							baseDiscipline := p.NormalizeDiscipline(disciplineSlug)

							key := GroupKey{
								Year:           yr,
								Gender:         gender,
								TypeSlug:       typeSlug,
								BaseDiscipline: baseDiscipline,
							}
							filesByKey[key] = append(filesByKey[key], filepath.Join(genderPath, file.Name()))
						}
					}
				}
			}
		}
	} else if currentMode == "all-time" {
		entries, err := os.ReadDir(inputRoot)
		if err != nil {
			return filesByKey
		}

		for _, genderEntry := range entries {
			if !genderEntry.IsDir() {
				continue
			}
			gender := genderEntry.Name()
			genderPath := filepath.Join(inputRoot, gender)
			files, err := os.ReadDir(genderPath)
			if err != nil {
				continue
			}

			for _, file := range files {
				if !file.IsDir() && strings.HasSuffix(file.Name(), ".csv") {
					base := strings.TrimSuffix(file.Name(), ".csv")
					parts := strings.Split(base, "_")
					if len(parts) >= 3 {
						typeSlug := parts[0]
						disciplineSlug := strings.Join(parts[1:len(parts)-1], "_")
						baseDiscipline := p.NormalizeDiscipline(disciplineSlug)

						key := GroupKey{
							Year:           "",
							Gender:         gender,
							TypeSlug:       typeSlug,
							BaseDiscipline: baseDiscipline,
						}
						filesByKey[key] = append(filesByKey[key], filepath.Join(genderPath, file.Name()))
					}
				}
			}
		}
	}

	return filesByKey
}

// ProcessData processes and normalizes scraped CSV files and saves combined results.
func (p *Preprocessor) ProcessData(currentMode string, year ...string) error {
	filesByKey := p.GetFilesByKey(currentMode, year...)
	if filesByKey == nil {
		return nil
	}

	outputRoot := filepath.Join(config.Cfg.Paths.CombinedDir, currentMode)

	for key, fileList := range filesByKey {
		var records []Record

		for _, filePath := range fileList {
			file, err := os.Open(filePath)
			if err != nil {
				continue
			}

			reader := csv.NewReader(file)
			header, err := reader.Read()
			if err != nil {
				file.Close()
				continue
			}

			headerMap := make(map[string]int)
			for i, col := range header {
				headerMap[col] = i
			}

			getCol := func(row []string, colName string) string {
				if idx, ok := headerMap[colName]; ok && idx < len(row) {
					return row[idx]
				}
				return ""
			}

			for {
				row, err := reader.Read()
				if err == io.EOF {
					break
				}
				if err != nil {
					continue
				}

				rec := Record{
					Rank:        getCol(row, "rank"),
					Mark:        getCol(row, "mark"),
					Wind:        getCol(row, "wind"),
					Competitor:  getCol(row, "competitor"),
					DOB:         getCol(row, "dob"),
					Nationality: getCol(row, "nationality"),
					Position:    getCol(row, "position"),
					Venue:       getCol(row, "venue"),
					Date:        getCol(row, "date"),
					ResultScore: getCol(row, "result_score"),
					Discipline:  getCol(row, "discipline"),
					Type:        getCol(row, "type"),
					Sex:         getCol(row, "sex"),
					AgeCat:      getCol(row, "age_cat"),
				}
				records = append(records, rec)
			}
			file.Close()
		}

		if len(records) == 0 {
			continue
		}

		// Transform records
		for i := range records {
			r := &records[i]
			r.NormalizedDiscipline = key.BaseDiscipline

			if p.FieldTypes[key.TypeSlug] {
				r.TrackField = "field"
			} else if p.TrackTypes[key.TypeSlug] {
				r.TrackField = "track"
			} else if p.MixedTypes[key.TypeSlug] {
				r.TrackField = "mixed"
			} else {
				r.TrackField = "unknown"
			}

			r.MarkNumeric = p.ParseMarkToNumber(r.Mark)

			natFull, exists := p.CountryLookup[strings.ToLower(r.Nationality)]
			if !exists || natFull == "" {
				natFull = "Unknown"
			}
			r.NatFull = natFull

			venueCode := p.ExtractCountryCodeFromVenue(r.Venue)
			if venueCode != "" {
				venueCountry, exists := p.CountryLookup[strings.ToLower(venueCode)]
				if !exists || venueCountry == "" {
					venueCountry = "Unknown"
				}
				r.VenueCountry = venueCountry
			} else {
				r.VenueCountry = "Unknown"
			}

			// Parse dates matching Python %d %b %Y format
			parsedDate, errDate := time.Parse("02 Jan 2006", r.Date)
			parsedDOB, errDOB := time.Parse("02 Jan 2006", r.DOB)

			if errDate == nil {
				r.Date = parsedDate.Format("2006-01-02")
				r.Season = strconv.Itoa(parsedDate.Year())
			}
			if errDOB == nil {
				r.DOB = parsedDOB.Format("2006-01-02")
			}

			if errDate == nil && errDOB == nil {
				// (date - dob).days // 365
				days := int(parsedDate.Sub(parsedDOB).Hours() / 24)
				r.AgeAtEvent = strconv.Itoa(days / 365)
			}
		}

		// Sort records by MarkNumeric
		sortAscending := p.AscendingTypes[key.TypeSlug]
		sort.SliceStable(records, func(i, j int) bool {
			mi := records[i].MarkNumeric
			mj := records[j].MarkNumeric
			if math.IsInf(mi, 1) && math.IsInf(mj, 1) {
				return false
			}
			if math.IsInf(mi, 1) {
				return false
			}
			if math.IsInf(mj, 1) {
				return true
			}
			if sortAscending {
				return mi < mj
			}
			return mi > mj
		})

		// Determine target output directory
		var targetDir string
		var prefix string
		if currentMode == "seasons" {
			targetDir = filepath.Join(outputRoot, key.Year)
			prefix = fmt.Sprintf("%s_", key.Year)
		} else {
			targetDir = outputRoot
			prefix = ""
		}

		if err := os.MkdirAll(targetDir, 0755); err != nil {
			return err
		}

		outputFilename := fmt.Sprintf("%s%s_%s_%s.csv", prefix, key.Gender, key.TypeSlug, key.BaseDiscipline)
		outputPath := filepath.Join(targetDir, outputFilename)

		outFile, err := os.Create(outputPath)
		if err != nil {
			return err
		}

		writer := csv.NewWriter(outFile)
		header := []string{
			"rank", "mark", "wind", "competitor", "dob", "nationality", "position",
			"venue", "date", "result_score", "discipline", "type", "sex", "age_cat",
			"normalized_discipline", "track_field", "mark_numeric", "nat_full",
			"venue_country", "age_at_event", "season",
		}
		if err := writer.Write(header); err != nil {
			outFile.Close()
			return err
		}

		for _, r := range records {
			markNumStr := ""
			if !math.IsInf(r.MarkNumeric, 1) {
				markNumStr = strconv.FormatFloat(r.MarkNumeric, 'f', -1, 64)
			} else {
				markNumStr = "inf"
			}

			row := []string{
				r.Rank, r.Mark, r.Wind, r.Competitor, r.DOB, r.Nationality, r.Position,
				r.Venue, r.Date, r.ResultScore, r.Discipline, r.Type, r.Sex, r.AgeCat,
				r.NormalizedDiscipline, r.TrackField, markNumStr, r.NatFull,
				r.VenueCountry, r.AgeAtEvent, r.Season,
			}
			_ = writer.Write(row)
		}

		writer.Flush()
		outFile.Close()
		console.Cprint(fmt.Sprintf("[%s] Saved: %s", strings.ToUpper(currentMode), outputPath), console.BrightGreen, false, console.SymSave, false)
	}

	return nil
}

// Run executes the preprocessor for seasons, all-time, or both.
func (p *Preprocessor) Run(year ...string) error {
	if p.Mode == "seasons" || p.Mode == "both" {
		if err := p.ProcessData("seasons", year...); err != nil {
			return err
		}
	}
	if p.Mode == "all-time" || p.Mode == "both" {
		if err := p.ProcessData("all-time"); err != nil {
			return err
		}
	}
	return nil
}
