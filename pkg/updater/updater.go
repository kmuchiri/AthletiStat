package updater

import (
	"context"
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"athletistat/pkg/config"
	"athletistat/pkg/console"
	"athletistat/pkg/generator"
	"athletistat/pkg/preprocessor"
	"athletistat/pkg/scraper"
)

// SeasonsUpdate updates the combined seasons dataset by removing and replacing data for a given year.
type SeasonsUpdate struct {
	Year         int
	Generate     bool
	DatasetDir   string
	CombinedFile string
	YearFile     string
}

// NewSeasonsUpdate creates a new SeasonsUpdate instance.
func NewSeasonsUpdate(year int, generate bool) *SeasonsUpdate {
	if year <= 0 {
		year = time.Now().Year()
	}
	datasetDir := filepath.Join(config.Cfg.Paths.DatasetDir, "seasons")
	u := &SeasonsUpdate{
		Year:       year,
		Generate:   generate,
		DatasetDir: datasetDir,
		YearFile:   filepath.Join(datasetDir, fmt.Sprintf("%d_track_field_performances.csv", year)),
	}
	u.CombinedFile = u.FindCombinedFile()
	return u
}

// FindCombinedFile locates the combined seasons CSV file.
func (u *SeasonsUpdate) FindCombinedFile() string {
	pattern := filepath.Join(u.DatasetDir, "combined_track_field_performances_*.csv")
	matches, _ := filepath.Glob(pattern)
	if len(matches) > 0 {
		return matches[0]
	}
	return ""
}

// RunPipeline runs scraper -> preprocessor -> generator for the target year.
func (u *SeasonsUpdate) RunPipeline(ctx context.Context) error {
	console.Step(fmt.Sprintf("[1/3] Scraping data for %d...", u.Year))
	sc := scraper.NewScraper("seasons", "")
	if err := sc.Run(ctx, 0, u.Year); err != nil {
		return err
	}

	console.Step(fmt.Sprintf("[2/3] Preprocessing data for %d...", u.Year))
	pp := preprocessor.NewPreprocessor("seasons", "")
	if err := pp.Run(strconv.Itoa(u.Year)); err != nil {
		return err
	}

	console.Step(fmt.Sprintf("[3/3] Generating per-year dataset for %d...", u.Year))
	gen := generator.NewDatasetGenerator("seasons")
	if err := gen.Run(false, strconv.Itoa(u.Year)); err != nil {
		return err
	}

	return nil
}

// Run executes the full seasons-update workflow.
func (u *SeasonsUpdate) Run(ctx context.Context) error {
	console.Header(fmt.Sprintf("Seasons Update  —  %d", u.Year), "─", 52)

	// Step 1: Optionally run pipeline
	if u.Generate {
		console.Info(fmt.Sprintf("Generating fresh data for %d (full pipeline)...", u.Year))
		console.Divider("─", 52, console.Dim)
		if err := u.RunPipeline(ctx); err != nil {
			console.Error(fmt.Sprintf("Pipeline failed: %v", err))
			return err
		}
		console.Divider("─", 52, console.Dim)
	} else {
		console.Info(fmt.Sprintf("Skipping generation — expecting existing dataset for %d.", u.Year))
	}

	// Step 2: Load combined dataset
	u.CombinedFile = u.FindCombinedFile()
	if u.CombinedFile == "" {
		console.Error("No combined seasons dataset found. Run the full pipeline first with: --create-dataset seasons --combine")
		return nil
	}

	console.Info(fmt.Sprintf("Loading combined dataset: %s", u.CombinedFile))
	fComb, err := os.Open(u.CombinedFile)
	if err != nil {
		console.Error(fmt.Sprintf("Error opening %s: %v", u.CombinedFile, err))
		return err
	}
	defer fComb.Close()

	rComb := csv.NewReader(fComb)
	header, err := rComb.Read()
	if err != nil {
		console.Error(fmt.Sprintf("Error reading header: %v", err))
		return err
	}

	seasonColIdx := -1
	for i, h := range header {
		if h == "season" {
			seasonColIdx = i
			break
		}
	}

	// Step 3: Remove records matching target year
	var filteredRows [][]string
	rowsBefore := 0
	targetYearStr := strconv.Itoa(u.Year)

	for {
		row, err := rComb.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		rowsBefore++
		if seasonColIdx >= 0 && seasonColIdx < len(row) && row[seasonColIdx] == targetYearStr {
			continue // skip target year
		}
		filteredRows = append(filteredRows, row)
	}

	removed := rowsBefore - len(filteredRows)
	console.Info(fmt.Sprintf("Removed %d rows for season %d (was %d, now %d).", removed, u.Year, rowsBefore, len(filteredRows)))

	// Step 4: Load per-year dataset and append
	if _, err := os.Stat(u.YearFile); os.IsNotExist(err) {
		console.Error(fmt.Sprintf("Per-year dataset not found: %s", u.YearFile))
		return nil
	}

	console.Info(fmt.Sprintf("Loading year dataset: %s", u.YearFile))
	fYr, err := os.Open(u.YearFile)
	if err != nil {
		console.Error(fmt.Sprintf("Error opening %s: %v", u.YearFile, err))
		return err
	}
	defer fYr.Close()

	rYr := csv.NewReader(fYr)
	_, _ = rYr.Read() // skip header

	yearRowsCount := 0
	for {
		row, err := rYr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		filteredRows = append(filteredRows, row)
		yearRowsCount++
	}

	rowsAfter := len(filteredRows)
	console.Info(fmt.Sprintf("Appended %d rows for %d → combined total: %d.", yearRowsCount, u.Year, rowsAfter))

	// Step 5: Save updated combined CSV
	minYr := u.Year
	maxYr := u.Year
	if seasonColIdx >= 0 {
		minYr = 9999
		maxYr = 0
		for _, row := range filteredRows {
			if seasonColIdx < len(row) && row[seasonColIdx] != "" {
				if yr, err := strconv.Atoi(row[seasonColIdx]); err == nil {
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

	outputFilename := filepath.Join(u.DatasetDir, fmt.Sprintf("combined_track_field_performances_%d_%d.csv", minYr, maxYr))
	if u.CombinedFile != outputFilename && u.CombinedFile != "" {
		if _, err := os.Stat(u.CombinedFile); err == nil {
			_ = os.Remove(u.CombinedFile)
			console.Info(fmt.Sprintf("Removed old combined file: %s", u.CombinedFile))
		}
	}

	outF, err := os.Create(outputFilename)
	if err != nil {
		return err
	}
	defer outF.Close()

	w := csv.NewWriter(outF)
	_ = w.Write(header)
	_ = w.WriteAll(filteredRows)
	w.Flush()

	delta := rowsAfter - rowsBefore
	deltaStr := fmt.Sprintf("+%d", delta)
	if delta < 0 {
		deltaStr = fmt.Sprintf("%d", delta)
	}

	console.Success(fmt.Sprintf("Saved updated combined dataset → %s", outputFilename))
	console.Divider("─", 52, console.Dim)
	console.Info(fmt.Sprintf("Rows before: %d  |  Rows after: %d  |  Δ %s", rowsBefore, rowsAfter, deltaStr))
	console.Success(fmt.Sprintf("Seasons update for %d complete!", u.Year))
	return nil
}
