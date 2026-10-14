package generator

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"athletistat/pkg/config"
	"athletistat/pkg/console"
)

// DatasetGenerator handles concatenating and combining preprocessed CSVs.
type DatasetGenerator struct {
	Mode string
}

// NewDatasetGenerator creates a DatasetGenerator.
func NewDatasetGenerator(mode string) *DatasetGenerator {
	if mode == "" {
		mode = "both"
	}
	return &DatasetGenerator{Mode: mode}
}

// GenerateDatasets concatenates preprocessed CSV files for the given mode.
func (g *DatasetGenerator) GenerateDatasets(mode string, year ...string) error {
	combinedDir := filepath.Join(config.Cfg.Paths.CombinedDir, mode)
	outputDatasetDir := filepath.Join(config.Cfg.Paths.DatasetDir, mode)
	_ = os.MkdirAll(outputDatasetDir, 0755)

	if mode == "seasons" {
		if _, err := os.Stat(combinedDir); os.IsNotExist(err) {
			console.Error(fmt.Sprintf("Directory not found: %s", combinedDir))
			return nil
		}

		entries, err := os.ReadDir(combinedDir)
		if err != nil {
			return err
		}

		var targetYearDirs []string
		filterYear := ""
		if len(year) > 0 && year[0] != "" {
			filterYear = year[0]
		}

		for _, entry := range entries {
			if entry.IsDir() {
				if filterYear == "" || filterYear == entry.Name() {
					targetYearDirs = append(targetYearDirs, entry.Name())
				}
			}
		}

		for _, yr := range targetYearDirs {
			yearPath := filepath.Join(combinedDir, yr)
			files, err := os.ReadDir(yearPath)
			if err != nil {
				continue
			}

			var allRows [][]string
			var commonHeader []string

			for _, f := range files {
				if !f.IsDir() && strings.HasSuffix(f.Name(), ".csv") {
					filePath := filepath.Join(yearPath, f.Name())
					header, rows, err := readCSVFile(filePath)
					if err != nil {
						console.Error(fmt.Sprintf("Error reading %s: %v", f.Name(), err))
						continue
					}
					if commonHeader == nil {
						commonHeader = header
					}
					allRows = append(allRows, rows...)
				}
			}

			if len(allRows) > 0 {
				outputFilename := filepath.Join(outputDatasetDir, fmt.Sprintf("%s_track_field_performances.csv", yr))
				if err := writeCSVFile(outputFilename, commonHeader, allRows); err != nil {
					return err
				}
				console.Success(fmt.Sprintf("Saved %s data to %s", yr, outputFilename))
			} else {
				console.Warn(fmt.Sprintf("No CSV files found in %s", yearPath))
			}
		}
	} else if mode == "all-time" {
		if _, err := os.Stat(combinedDir); os.IsNotExist(err) {
			console.Error(fmt.Sprintf("Directory not found: %s", combinedDir))
			return nil
		}

		files, err := os.ReadDir(combinedDir)
		if err != nil {
			return err
		}

		var allRows [][]string
		var commonHeader []string
		seen := make(map[string]bool)

		for _, f := range files {
			if !f.IsDir() && strings.HasSuffix(f.Name(), ".csv") {
				filePath := filepath.Join(combinedDir, f.Name())
				header, rows, err := readCSVFile(filePath)
				if err != nil {
					console.Error(fmt.Sprintf("Error reading %s: %v", f.Name(), err))
					continue
				}
				if commonHeader == nil {
					commonHeader = header
				}
				for _, row := range rows {
					key := strings.Join(row, "|||")
					if !seen[key] {
						seen[key] = true
						allRows = append(allRows, row)
					}
				}
			}
		}

		if len(allRows) > 0 {
			outputFilename := filepath.Join(outputDatasetDir, "top_track_field_performances_all_time.csv")
			if err := writeCSVFile(outputFilename, commonHeader, allRows); err != nil {
				return err
			}
			console.Success(fmt.Sprintf("All-time CSV saved: %s", outputFilename))
		} else {
			console.Warn(fmt.Sprintf("No CSV files found in %s", combinedDir))
		}
	}

	return nil
}

// CombineSeasons merges all available per-year season datasets into a single file.
func (g *DatasetGenerator) CombineSeasons() error {
	datasetDir := filepath.Join(config.Cfg.Paths.DatasetDir, "seasons")
	if _, err := os.Stat(datasetDir); os.IsNotExist(err) {
		console.Error(fmt.Sprintf("Directory not found: %s", datasetDir))
		return nil
	}

	files, err := os.ReadDir(datasetDir)
	if err != nil {
		return err
	}

	minYear := 9999
	maxYear := 0
	var seasonFiles []string

	for _, f := range files {
		if !f.IsDir() && strings.HasSuffix(f.Name(), "_track_field_performances.csv") && !strings.HasPrefix(f.Name(), "combined_") {
			parts := strings.Split(f.Name(), "_")
			if yr, err := strconv.Atoi(parts[0]); err == nil {
				if yr < minYear {
					minYear = yr
				}
				if yr > maxYear {
					maxYear = yr
				}
				seasonFiles = append(seasonFiles, filepath.Join(datasetDir, f.Name()))
			}
		}
	}

	if len(seasonFiles) == 0 {
		console.Warn(fmt.Sprintf("No season CSV files found in %s", datasetDir))
		return nil
	}

	var allRows [][]string
	var commonHeader []string

	for _, sf := range seasonFiles {
		header, rows, err := readCSVFile(sf)
		if err != nil {
			console.Error(fmt.Sprintf("Error reading %s: %v", filepath.Base(sf), err))
			continue
		}
		if commonHeader == nil {
			commonHeader = header
		}
		allRows = append(allRows, rows...)
	}

	outputFilename := filepath.Join(datasetDir, fmt.Sprintf("combined_track_field_performances_%d_%d.csv", minYear, maxYear))
	if err := writeCSVFile(outputFilename, commonHeader, allRows); err != nil {
		return err
	}

	console.Success(fmt.Sprintf("Combined seasons (%d–%d) saved to %s", minYear, maxYear, outputFilename))
	return nil
}

// Run executes generation for the configured mode.
func (g *DatasetGenerator) Run(combine bool, year ...string) error {
	if g.Mode == "seasons" || g.Mode == "both" {
		if err := g.GenerateDatasets("seasons", year...); err != nil {
			return err
		}
	}
	if g.Mode == "all-time" || g.Mode == "both" {
		if err := g.GenerateDatasets("all-time"); err != nil {
			return err
		}
	}
	if combine && (g.Mode == "seasons" || g.Mode == "both") {
		if err := g.CombineSeasons(); err != nil {
			return err
		}
	}
	return nil
}

// DatasetSplitter splits datasets into granular sub-files.
type DatasetSplitter struct {
	Mode string
}

// NewDatasetSplitter creates a DatasetSplitter.
func NewDatasetSplitter(mode string) *DatasetSplitter {
	if mode == "" {
		mode = "both"
	}
	return &DatasetSplitter{Mode: mode}
}

// GetFilenameWithYears generates dynamic filenames with year ranges.
func (s *DatasetSplitter) GetFilenameWithYears(baseName string, minYr, maxYr int, hasSeasons bool, isSeasons bool) string {
	if isSeasons && hasSeasons {
		if minYr == maxYr {
			return fmt.Sprintf("%s_%d.csv", baseName, minYr)
		}
		return fmt.Sprintf("%s_%d-%d.csv", baseName, minYr, maxYr)
	}
	return fmt.Sprintf("%s.csv", baseName)
}

// SplitDataset splits loaded rows by event type, discipline, and gender.
func (s *DatasetSplitter) SplitDataset(header []string, rows [][]string, modeDir string, isSeasons bool) error {
	colIdx := make(map[string]int)
	for i, h := range header {
		colIdx[h] = i
	}

	getVal := func(row []string, col string) string {
		if idx, ok := colIdx[col]; ok && idx < len(row) {
			return row[idx]
		}
		return ""
	}

	// Calculate season year range across rows
	minYr := 9999
	maxYr := 0
	hasSeasons := false
	if _, ok := colIdx["season"]; ok {
		for _, row := range rows {
			if sVal := getVal(row, "season"); sVal != "" {
				if yr, err := strconv.Atoi(sVal); err == nil {
					hasSeasons = true
					if yr < minYr {
						minYr = yr
					}
					if yr > maxYr {
						maxYr = yr
					}
				}
			}
		}
	}

	var individualRows [][]string
	var relayRows [][]string

	// Filter relay columns (drop dob and age_at_event for relays)
	var relayHeader []string
	var relayColIndices []int
	for i, h := range header {
		if h != "dob" && h != "age_at_event" {
			relayHeader = append(relayHeader, h)
			relayColIndices = append(relayColIndices, i)
		}
	}

	for _, row := range rows {
		if getVal(row, "type") == "relays" {
			var rRow []string
			for _, idx := range relayColIndices {
				if idx < len(row) {
					rRow = append(rRow, row[idx])
				} else {
					rRow = append(rRow, "")
				}
			}
			relayRows = append(relayRows, rRow)
		} else {
			individualRows = append(individualRows, row)
		}
	}

	// 1. Save global-level splits
	globalOut := filepath.Join(modeDir, "split_global")
	_ = os.MkdirAll(globalOut, 0755)

	indFilename := s.GetFilenameWithYears("individual_events", minYr, maxYr, hasSeasons, isSeasons)
	if err := writeCSVFile(filepath.Join(globalOut, indFilename), header, individualRows); err != nil {
		return err
	}

	if len(relayRows) > 0 {
		relayFilename := s.GetFilenameWithYears("relay_events", minYr, maxYr, hasSeasons, isSeasons)
		if err := writeCSVFile(filepath.Join(globalOut, relayFilename), relayHeader, relayRows); err != nil {
			return err
		}
	}

	// 2. Split by gender, type, and discipline
	// Find all unique genders
	genderSet := make(map[string]bool)
	for _, row := range rows {
		if g := getVal(row, "sex"); g != "" {
			genderSet[g] = true
		}
	}

	var genders []string
	for g := range genderSet {
		genders = append(genders, g)
	}
	sort.Strings(genders)

	for _, gender := range genders {
		typeOutputDir := filepath.Join(modeDir, "split_by_type", gender)
		disciplineOutputDir := filepath.Join(modeDir, "split_by_discipline", gender)
		relayOutputDir := filepath.Join(modeDir, "relays", gender)

		// Filter individual rows for gender
		var genderIndRows [][]string
		for _, row := range individualRows {
			if getVal(row, "sex") == gender {
				genderIndRows = append(genderIndRows, row)
			}
		}

		if len(genderIndRows) > 0 {
			_ = os.MkdirAll(typeOutputDir, 0755)
			byType := make(map[string][][]string)
			for _, row := range genderIndRows {
				tVal := getVal(row, "type")
				byType[tVal] = append(byType[tVal], row)
			}
			for tVal, groupRows := range byType {
				fn := s.GetFilenameWithYears(tVal, minYr, maxYr, hasSeasons, isSeasons)
				_ = writeCSVFile(filepath.Join(typeOutputDir, fn), header, groupRows)
			}

			_ = os.MkdirAll(disciplineOutputDir, 0755)
			byDisc := make(map[string][][]string)
			for _, row := range genderIndRows {
				dVal := getVal(row, "normalized_discipline")
				byDisc[dVal] = append(byDisc[dVal], row)
			}
			for dVal, groupRows := range byDisc {
				fn := s.GetFilenameWithYears(dVal, minYr, maxYr, hasSeasons, isSeasons)
				_ = writeCSVFile(filepath.Join(disciplineOutputDir, fn), header, groupRows)
			}
		}

		// Filter relay rows for gender
		var genderRelayRows [][]string
		relaySexIdx := -1
		for i, h := range relayHeader {
			if h == "sex" {
				relaySexIdx = i
				break
			}
		}
		relayDiscIdx := -1
		for i, h := range relayHeader {
			if h == "normalized_discipline" {
				relayDiscIdx = i
				break
			}
		}

		if relaySexIdx >= 0 {
			for _, row := range relayRows {
				if relaySexIdx < len(row) && row[relaySexIdx] == gender {
					genderRelayRows = append(genderRelayRows, row)
				}
			}
		}

		if len(genderRelayRows) > 0 && relayDiscIdx >= 0 {
			_ = os.MkdirAll(relayOutputDir, 0755)
			byDisc := make(map[string][][]string)
			for _, row := range genderRelayRows {
				if relayDiscIdx < len(row) {
					dVal := row[relayDiscIdx]
					byDisc[dVal] = append(byDisc[dVal], row)
				}
			}
			for dVal, groupRows := range byDisc {
				fn := s.GetFilenameWithYears(dVal, minYr, maxYr, hasSeasons, isSeasons)
				_ = writeCSVFile(filepath.Join(relayOutputDir, fn), relayHeader, groupRows)
			}
		}
	}

	console.Cprint(fmt.Sprintf("  └─ Splits generated for: %s", strings.ToUpper(modeDir)), console.BrightGreen, true, console.SymOK, false)
	return nil
}

// ExecuteSplits locates combined datasets and generates split subsets.
func (s *DatasetSplitter) ExecuteSplits() error {
	if s.Mode == "seasons" || s.Mode == "both" {
		datasetsDir := filepath.Join(config.Cfg.Paths.DatasetDir, "seasons")
		_ = os.MkdirAll(datasetsDir, 0755)

		pattern := filepath.Join(datasetsDir, "combined_track_field_performances_*.csv")
		matches, _ := filepath.Glob(pattern)

		if len(matches) == 0 {
			console.Warn(fmt.Sprintf("[SEASONS] Combined dataset not found at %s - running generator...", pattern))
			gen := NewDatasetGenerator("seasons")
			_ = gen.Run(true)
			matches, _ = filepath.Glob(pattern)
		}

		if len(matches) > 0 {
			filePath := matches[0]
			console.Info(fmt.Sprintf("[SEASONS] Loading %s for splitting...", filePath))
			header, rows, err := readCSVFile(filePath)
			if err != nil {
				console.Error(fmt.Sprintf("Error reading %s: %v", filePath, err))
			} else {
				_ = s.SplitDataset(header, rows, datasetsDir, true)
			}
		} else {
			console.Warn("[SEASONS] Still no dataset found after running generator. Is there raw data to combine?")
		}
	}

	if s.Mode == "all-time" || s.Mode == "both" {
		datasetsDir := filepath.Join(config.Cfg.Paths.DatasetDir, "all-time")
		_ = os.MkdirAll(datasetsDir, 0755)

		filePath := filepath.Join(datasetsDir, "top_track_field_performances_all_time.csv")
		if _, err := os.Stat(filePath); os.IsNotExist(err) {
			console.Warn(fmt.Sprintf("[ALL-TIME] Combined dataset not found at %s - running generator...", filePath))
			gen := NewDatasetGenerator("all-time")
			_ = gen.Run(false)
		}

		if _, err := os.Stat(filePath); err == nil {
			console.Info(fmt.Sprintf("[ALL-TIME] Loading %s for splitting...", filePath))
			header, rows, err := readCSVFile(filePath)
			if err != nil {
				console.Error(fmt.Sprintf("Error reading %s: %v", filePath, err))
			} else {
				_ = s.SplitDataset(header, rows, datasetsDir, false)
			}
		} else {
			console.Warn("[ALL-TIME] Still no dataset found after running generator. Is there raw data to combine?")
		}
	}

	return nil
}

// Run executes the splitting process.
func (s *DatasetSplitter) Run() error {
	return s.ExecuteSplits()
}

// Helpers
func readCSVFile(path string) ([]string, [][]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	header, err := reader.Read()
	if err != nil {
		return nil, nil, err
	}

	var rows [][]string
	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		rows = append(rows, row)
	}
	return header, rows, nil
}

func writeCSVFile(path string, header []string, rows [][]string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	if err := writer.Write(header); err != nil {
		return err
	}
	if err := writer.WriteAll(rows); err != nil {
		return err
	}
	writer.Flush()
	return nil
}
