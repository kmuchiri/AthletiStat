package scraper

import (
	"context"
	"crypto/tls"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/hashicorp/go-retryablehttp"

	"athletistat/pkg/config"
	"athletistat/pkg/console"
)

const (
	BaseURLAllTime = "https://worldathletics.org/records/all-time-toplists/%s/%s/all/%s/%s?regionType=world&page=%d&bestResultsOnly=false&firstDay=1900-01-01&lastDay=%s&maxResultsByCountry=all&ageCategory=%s"
	BaseURLSeasons = "https://worldathletics.org/records/toplists/%s/%s/all/%s/%s/%d?regionType=world&timing=all&windReading=all&page=%d&bestResultsOnly=false&maxResultsByCountry=all&ageCategory=%s"
)

// MappingKey represents a gender + ageCategory tuple.
type MappingKey struct {
	Gender      string `json:"gender"`
	AgeCategory string `json:"age_category"`
}

// DisciplinePair represents a discipline slug and its parent type slug.
type DisciplinePair struct {
	DisciplineSlug string `json:"discipline_slug"`
	TypeSlug       string `json:"type_slug"`
}

// ScrapeJob defines a single targeted scraping task.
type ScrapeJob struct {
	Gender         string `json:"gender"`
	AgeCategory    string `json:"age_category"`
	DisciplineSlug string `json:"discipline_slug"`
	TypeSlug       string `json:"type_slug"`
	OutputDir      string `json:"output_dir"`
	Mode           string `json:"mode"`
	Year           int    `json:"year,omitempty"`
}

// RawRecord holds one row scraped from the WA records table.
type RawRecord struct {
	Rank        string
	Mark        string
	Wind        string
	Competitor  string
	DOB         string
	Nationality string
	Position    string
	Venue       string
	Date        string
	ResultScore string
	Discipline  string
	Type        string
	Sex         string
	AgeCat      string
}

// Scraper handles downloading and parsing track & field records.
type Scraper struct {
	Mode        string
	OptionsFile string
	Mappings    map[MappingKey][]DisciplinePair
	Today       string
	CurrentTime string
	CurrentYear int
	Client      *http.Client

	lock sync.Mutex
}

// NewScraper instantiates a new Scraper.
func NewScraper(mode string, optionsFile string) *Scraper {
	if mode == "" {
		mode = "both"
	}
	if optionsFile == "" {
		optionsFile = config.Cfg.Paths.OptionsFile
	}

	now := time.Now()
	s := &Scraper{
		Mode:        mode,
		OptionsFile: optionsFile,
		Today:       now.Format("2006-01-02"),
		CurrentTime: now.Format("2006-01-02_150405"),
		CurrentYear: now.Year(),
		Mappings:    make(map[MappingKey][]DisciplinePair),
	}

	s.Mappings = s.LoadMappings(s.OptionsFile)
	s.Client = s.createHTTPClient()
	return s
}

func (s *Scraper) createHTTPClient() *http.Client {
	retryClient := retryablehttp.NewClient()
	retryClient.RetryMax = config.Cfg.Scraper.RetryTotal
	retryClient.RetryWaitMin = time.Duration(config.Cfg.Scraper.RetryBackoffFactor) * time.Second
	retryClient.RetryWaitMax = 10 * time.Second
	retryClient.Logger = nil // suppress verbose logs

	tr := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: !config.Cfg.Scraper.VerifySSL,
		},
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 20,
		IdleConnTimeout:     90 * time.Second,
	}

	retryClient.HTTPClient = &http.Client{
		Transport: tr,
		Timeout:   time.Duration(config.Cfg.Scraper.ReadTimeout) * time.Second,
	}

	return retryClient.StandardClient()
}

// LoadMappings parses discipline mappings from options.json.
func (s *Scraper) LoadMappings(configFile string) map[MappingKey][]DisciplinePair {
	mappings := make(map[MappingKey][]DisciplinePair)
	data, err := os.ReadFile(configFile)
	if err != nil {
		return mappings
	}

	var optionsData []map[string]interface{}
	if err := json.Unmarshal(data, &optionsData); err != nil {
		return mappings
	}

	for _, entry := range optionsData {
		name, _ := entry["name"].(string)
		if name != "disciplineCode" {
			continue
		}

		cases, _ := entry["cases"].([]interface{})
		for _, c := range cases {
			cMap, _ := c.(map[string]interface{})
			gender, _ := cMap["gender"].(string)
			ageCat, _ := cMap["ageCategory"].(string)
			key := MappingKey{Gender: gender, AgeCategory: ageCat}

			values, _ := cMap["values"].([]interface{})
			for _, v := range values {
				vMap, _ := v.(map[string]interface{})
				discSlug, ok1 := vMap["disciplineNameUrlSlug"].(string)
				typeSlug, ok2 := vMap["typeNameUrlSlug"].(string)
				if ok1 && ok2 && discSlug != "" && typeSlug != "" {
					mappings[key] = append(mappings[key], DisciplinePair{
						DisciplineSlug: discSlug,
						TypeSlug:       typeSlug,
					})
				}
			}
		}
	}

	return mappings
}

// BuildJobs compiles the list of scraping jobs for targeted disciplines.
func (s *Scraper) BuildJobs(mode string, year ...int) []ScrapeJob {
	var jobs []ScrapeJob
	y := s.CurrentYear
	if len(year) > 0 && year[0] > 0 {
		y = year[0]
	}

	for key, disciplines := range s.Mappings {
		var outputDir string
		if mode == "seasons" {
			outputDir = filepath.Join(config.Cfg.Paths.ScraperOutput, mode, fmt.Sprintf("%d", y), key.Gender)
		} else {
			outputDir = filepath.Join(config.Cfg.Paths.ScraperOutput, mode, key.Gender)
		}

		_ = os.MkdirAll(outputDir, 0755)

		for _, disc := range disciplines {
			job := ScrapeJob{
				Gender:         key.Gender,
				AgeCategory:    key.AgeCategory,
				DisciplineSlug: disc.DisciplineSlug,
				TypeSlug:       disc.TypeSlug,
				OutputDir:      outputDir,
				Mode:           mode,
			}
			if mode == "seasons" {
				job.Year = y
			}
			jobs = append(jobs, job)
		}
	}

	return jobs
}

// ScrapeEvent scrapes a single event table, paginates results, and saves to CSV.
func (s *Scraper) ScrapeEvent(ctx context.Context, job ScrapeJob, bar *console.ProgressBar) (int, bool, error) {
	page := 1
	var records []RawRecord

	for {
		var url string
		if job.Mode == "seasons" {
			url = fmt.Sprintf(BaseURLSeasons, job.TypeSlug, job.DisciplineSlug, job.Gender, job.AgeCategory, job.Year, page, job.AgeCategory)
		} else {
			url = fmt.Sprintf(BaseURLAllTime, job.TypeSlug, job.DisciplineSlug, job.Gender, job.AgeCategory, page, s.Today, job.AgeCategory)
		}

		req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
		if err != nil {
			s.logError(job, url, err)
			return 0, false, err
		}
		req.Header.Set("User-Agent", config.Cfg.Scraper.UserAgent)

		resp, err := s.Client.Do(req)
		if err != nil {
			s.logError(job, url, err)
			return 0, false, err
		}

		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			resp.Body.Close()
			statusErr := fmt.Errorf("unexpected status code: %d", resp.StatusCode)
			s.logError(job, url, statusErr)
			return 0, false, statusErr
		}

		doc, err := goquery.NewDocumentFromReader(resp.Body)
		resp.Body.Close()
		if err != nil {
			s.logError(job, url, err)
			return 0, false, err
		}

		table := doc.Find("table.records-table")
		if table.Length() == 0 {
			break
		}

		rows := table.Find("tbody tr")
		if rows.Length() == 0 {
			rows = table.Find("tr")
		}
		if rows.Length() == 0 {
			break
		}

		rowCount := 0
		rows.Each(func(i int, s *goquery.Selection) {
			cols := s.Find("td")
			if cols.Length() < 11 {
				return
			}
			rowCount++
			records = append(records, RawRecord{
				Rank:        strings.TrimSpace(cols.Eq(0).Text()),
				Mark:        strings.TrimSpace(cols.Eq(1).Text()),
				Wind:        strings.TrimSpace(cols.Eq(2).Text()),
				Competitor:  strings.TrimSpace(cols.Eq(3).Text()),
				DOB:         strings.TrimSpace(cols.Eq(4).Text()),
				Nationality: strings.TrimSpace(cols.Eq(5).Text()),
				Position:    strings.TrimSpace(cols.Eq(6).Text()),
				Venue:       strings.TrimSpace(cols.Eq(8).Text()),
				Date:        strings.TrimSpace(cols.Eq(9).Text()),
				ResultScore: strings.TrimSpace(cols.Eq(10).Text()),
				Discipline:  job.DisciplineSlug,
				Type:        job.TypeSlug,
				Sex:         job.Gender,
				AgeCat:      job.AgeCategory,
			})
		})

		if rowCount == 0 {
			break
		}

		page++
		if config.Cfg.Scraper.PageDelay > 0 {
			time.Sleep(time.Duration(config.Cfg.Scraper.PageDelay * float64(time.Second)))
		}
	}

	// Save to CSV if data collected
	if len(records) > 0 {
		_ = os.MkdirAll(job.OutputDir, 0755)
		prefix := ""
		if job.Mode == "seasons" {
			prefix = fmt.Sprintf("%d_", job.Year)
		}
		filename := fmt.Sprintf("%s%s_%s_%s.csv", prefix, job.TypeSlug, job.DisciplineSlug, job.AgeCategory)
		filename = strings.ReplaceAll(filename, " ", "_")
		filename = strings.ReplaceAll(filename, "/", "-")
		filepathTarget := filepath.Join(job.OutputDir, filename)

		s.lock.Lock()
		outFile, err := os.Create(filepathTarget)
		if err == nil {
			writer := csv.NewWriter(outFile)
			_ = writer.Write([]string{
				"rank", "mark", "wind", "competitor", "dob", "nationality",
				"position", "venue", "date", "result_score", "discipline",
				"type", "sex", "age_cat",
			})
			for _, r := range records {
				_ = writer.Write([]string{
					r.Rank, r.Mark, r.Wind, r.Competitor, r.DOB, r.Nationality,
					r.Position, r.Venue, r.Date, r.ResultScore, r.Discipline,
					r.Type, r.Sex, r.AgeCat,
				})
			}
			writer.Flush()
			outFile.Close()

			if config.Cfg.Display.ShowSaveLog {
				msg := fmt.Sprintf("%s%s%s %sSaved%s %s", console.BrightGreen, console.SymSave, console.Reset, console.Dim, console.Reset, filepathTarget)
				if bar != nil {
					bar.Write(msg)
				} else {
					console.Success(fmt.Sprintf("Saved %s", filepathTarget))
				}
			}
		}
		s.lock.Unlock()
	}

	return len(records), true, nil
}

// GetQueueInfo determines the queue file path.
func (s *Scraper) GetQueueInfo(mode string, year int) string {
	queueDir := filepath.Join(config.Cfg.Paths.QueueDir, mode)
	_ = os.MkdirAll(queueDir, 0755)
	if mode == "seasons" {
		return filepath.Join(queueDir, fmt.Sprintf("queue_seasons_%d.json", year))
	}
	return filepath.Join(queueDir, fmt.Sprintf("queue_all_time_%s.json", s.Today))
}

// ManageQueuesAndJobs handles loading existing queues or compiling new jobs.
func (s *Scraper) ManageQueuesAndJobs(mode string, year int) ([]ScrapeJob, string, []int, error) {
	queueDir := filepath.Join(config.Cfg.Paths.QueueDir, mode)
	_ = os.MkdirAll(queueDir, 0755)
	queueFile := s.GetQueueInfo(mode, year)
	var jobs []ScrapeJob

	if mode == "seasons" {
		completedFile := filepath.Join(queueDir, "completed_seasons.json")
		var completedYears []int

		if year != s.CurrentYear {
			if data, err := os.ReadFile(completedFile); err == nil {
				_ = json.Unmarshal(data, &completedYears)
			}

			for _, cy := range completedYears {
				if cy == year {
					console.Warn(fmt.Sprintf("Data for %d is already completely retrieved - skipping scrape.", year))
					return nil, queueFile, completedYears, nil
				}
			}

			if fi, err := os.Stat(queueFile); err == nil && fi.Size() > 0 {
				if data, err := os.ReadFile(queueFile); err == nil {
					_ = json.Unmarshal(data, &jobs)
					console.Info(fmt.Sprintf("Resuming %d incomplete jobs from %s...", len(jobs), queueFile))
				}
			} else {
				jobs = s.BuildJobs(mode, year)
				if bytes, err := json.Marshal(jobs); err == nil {
					_ = os.WriteFile(queueFile, bytes, 0644)
				}
				console.Info(fmt.Sprintf("Created new queue with %d jobs for historical year %d.", len(jobs), year))
			}
		} else {
			jobs = s.BuildJobs(mode, year)
			console.Info(fmt.Sprintf("Current year (%d) detected - running %d jobs from scratch (no queue).", year, len(jobs)))
		}

		return jobs, queueFile, completedYears, nil
	} else if mode == "all-time" {
		// Clean up old all-time queues
		matches, _ := filepath.Glob(filepath.Join(queueDir, "queue_all_time_*.json"))
		for _, oldQueue := range matches {
			if oldQueue != queueFile {
				_ = os.Remove(oldQueue)
				console.Warn(fmt.Sprintf("Removed outdated queue: %s", oldQueue))
			}
		}

		if fi, err := os.Stat(queueFile); err == nil && fi.Size() > 0 {
			if data, err := os.ReadFile(queueFile); err == nil {
				_ = json.Unmarshal(data, &jobs)
				console.Info(fmt.Sprintf("Resuming %d incomplete jobs from %s...", len(jobs), queueFile))
			}
		} else {
			jobs = s.BuildJobs(mode)
			if bytes, err := json.Marshal(jobs); err == nil {
				_ = os.WriteFile(queueFile, bytes, 0644)
			}
			console.Info(fmt.Sprintf("Created new queue with %d jobs for all-time (%s).", len(jobs), s.Today))
		}

		return jobs, queueFile, nil, nil
	}

	return nil, queueFile, nil, nil
}

// RunScraper runs concurrent worker goroutines over compiled jobs.
func (s *Scraper) RunScraper(ctx context.Context, mode string, maxWorkers int, year int) error {
	if maxWorkers <= 0 {
		maxWorkers = config.Cfg.Scraper.MaxWorkers
	}

	console.Cprint(fmt.Sprintf("%s Starting %s scrape - %d workers", console.SymRocket, strings.ToUpper(mode), maxWorkers), console.BrightCyan, true, "", false)
	startTime := time.Now()

	jobs, queueFile, completedYears, err := s.ManageQueuesAndJobs(mode, year)
	if err != nil || jobs == nil {
		return err
	}

	total := len(jobs)
	modeLabel := strings.ToUpper(mode)
	if mode == "seasons" && year > 0 {
		modeLabel = fmt.Sprintf("SEASONS %d", year)
	}

	progressBar := console.NewProgressBar(total, modeLabel, config.Cfg.Display.ProgressBarWidth)

	type jobResult struct {
		job          ScrapeJob
		recordsCount int
		ok           bool
		err          error
	}

	jobsChan := make(chan ScrapeJob, len(jobs))
	for _, job := range jobs {
		jobsChan <- job
	}
	close(jobsChan)

	resultsChan := make(chan jobResult, len(jobs))
	var wg sync.WaitGroup

	for i := 0; i < maxWorkers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for job := range jobsChan {
				count, ok, err := s.ScrapeEvent(ctx, job, progressBar)
				resultsChan <- jobResult{job: job, recordsCount: count, ok: ok, err: err}
			}
		}()
	}

	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	var remainingJobs []ScrapeJob
	totalRecords := 0
	succeededJobs := 0

	activeRemaining := make(map[string]ScrapeJob)
	for _, j := range jobs {
		key := fmt.Sprintf("%s|%s|%s|%s|%d", j.Gender, j.AgeCategory, j.TypeSlug, j.DisciplineSlug, j.Year)
		activeRemaining[key] = j
	}

	for res := range resultsChan {
		jobKey := fmt.Sprintf("%s|%s|%s|%s|%d", res.job.Gender, res.job.AgeCategory, res.job.TypeSlug, res.job.DisciplineSlug, res.job.Year)
		if res.ok {
			progressBar.Update(1)
			totalRecords += res.recordsCount
			succeededJobs++
			delete(activeRemaining, jobKey)
		} else {
			remainingJobs = append(remainingJobs, res.job)
			s.logError(res.job, "", res.err)
		}

		// Update persistent queue for historical years or all-time
		if (mode == "seasons" && year != s.CurrentYear) || mode == "all-time" {
			s.lock.Lock()
			var currentQueue []ScrapeJob
			for _, j := range activeRemaining {
				currentQueue = append(currentQueue, j)
			}
			if bytes, err := json.Marshal(currentQueue); err == nil {
				_ = os.WriteFile(queueFile, bytes, 0644)
			}
			s.lock.Unlock()
		}
	}

	progressBar.Finish()

	// Final cleanup
	if (mode == "seasons" && year != s.CurrentYear) || mode == "all-time" {
		if len(remainingJobs) == 0 {
			console.Success(fmt.Sprintf("All %s jobs completed successfully!", strings.ToUpper(mode)))
			_ = os.Remove(queueFile)

			if mode == "seasons" {
				alreadyMarked := false
				for _, cy := range completedYears {
					if cy == year {
						alreadyMarked = true
						break
					}
				}
				if !alreadyMarked {
					completedYears = append(completedYears, year)
					completedFile := filepath.Join(config.Cfg.Paths.QueueDir, "seasons", "completed_seasons.json")
					if bytes, err := json.Marshal(completedYears); err == nil {
						_ = os.WriteFile(completedFile, bytes, 0644)
					}
				}
			}
		} else {
			console.Warn(fmt.Sprintf("Scrape paused or encountered errors - %d jobs remaining in queue.", len(remainingJobs)))
		}
	}

	endTime := time.Now()
	duration := endTime.Sub(startTime)
	runLogPath := s.logRunSummary(mode, year, startTime, endTime, duration, totalRecords, total, succeededJobs, len(remainingJobs))

	console.Divider("─", 52, console.Dim)
	console.Cprint(fmt.Sprintf("%s  %s scraping complete", console.SymClock, strings.Title(mode)), console.BrightMagenta, true, "", false)
	console.Info(fmt.Sprintf("Started:       %s", startTime.Format("2006-01-02 15:04:05")))
	console.Info(fmt.Sprintf("Ended:         %s", endTime.Format("2006-01-02 15:04:05")))
	console.Info(fmt.Sprintf("Time Taken:    %s (%.2fs)", formatDuration(duration), duration.Seconds()))
	console.Info(fmt.Sprintf("Total Records: %d", totalRecords))
	console.Info(fmt.Sprintf("Jobs:          %d total | %d succeeded | %d failed", total, succeededJobs, len(remainingJobs)))
	console.Info(fmt.Sprintf("Run log saved: %s", runLogPath))
	if len(remainingJobs) > 0 {
		errorLogPath := filepath.Join(config.Cfg.Paths.LogDir, mode, s.Today, fmt.Sprintf("scrape_errors_%s.log", s.CurrentTime))
		console.Warn(fmt.Sprintf("Errors saved:  %s (%d failed jobs in queue)", errorLogPath, len(remainingJobs)))
	}
	console.Divider("─", 52, console.Dim)
	return nil
}

func (s *Scraper) logError(job ScrapeJob, url string, err error) {
	if err == nil {
		return
	}
	s.lock.Lock()
	defer s.lock.Unlock()

	nowStr := time.Now().Format("2006-01-02 15:04:05")
	logDir := filepath.Join(config.Cfg.Paths.LogDir, job.Mode, s.Today)
	_ = os.MkdirAll(logDir, 0755)

	msg := fmt.Sprintf("[%s] Mode: %s | Year: %d | Gender: %s | Age: %s | Type: %s | Discipline: %s | URL: %s | Error: %v\n",
		nowStr, job.Mode, job.Year, job.Gender, job.AgeCategory, job.TypeSlug, job.DisciplineSlug, url, err)

	datedPath := filepath.Join(logDir, fmt.Sprintf("scrape_errors_%s.log", s.CurrentTime))
	if f, oErr := os.OpenFile(datedPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644); oErr == nil {
		_, _ = f.WriteString(msg)
		f.Close()
	}

	modePath := filepath.Join(config.Cfg.Paths.LogDir, job.Mode, "scrape_errors.log")
	if f, oErr := os.OpenFile(modePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644); oErr == nil {
		_, _ = f.WriteString(msg)
		f.Close()
	}
}

func (s *Scraper) logRunSummary(mode string, year int, start, end time.Time, duration time.Duration, totalRecords, totalJobs, succeededJobs, failedJobs int) string {
	s.lock.Lock()
	defer s.lock.Unlock()

	logDir := filepath.Join(config.Cfg.Paths.LogDir, mode, s.Today)
	_ = os.MkdirAll(logDir, 0755)

	durStr := formatDuration(duration)
	totalSecStr := fmt.Sprintf("%.2fs", duration.Seconds())

	yearStr := "N/A (all-time)"
	if mode == "seasons" && year > 0 {
		yearStr = strconv.Itoa(year)
	}

	summary := fmt.Sprintf(
`================================================================================
SCRAPE RUN SUMMARY - %s
================================================================================
Mode:              %s
Year:              %s
Time Started:      %s
Time Ended:        %s
Time Taken:        %s
Total Time:        %s
Amount of Records: %d
Total Jobs:        %d
Successful Jobs:   %d
Failed Jobs:       %d
Remaining Queue:   %d
================================================================================
`,
		strings.ToUpper(mode),
		mode,
		yearStr,
		start.Format("2006-01-02 15:04:05"),
		end.Format("2006-01-02 15:04:05"),
		durStr,
		totalSecStr,
		totalRecords,
		totalJobs,
		succeededJobs,
		failedJobs,
		failedJobs,
	)

	runLogPath := filepath.Join(logDir, fmt.Sprintf("scrape_run_%s.log", start.Format("2006-01-02_150405")))
	_ = os.WriteFile(runLogPath, []byte(summary), 0644)

	masterLogPath := filepath.Join(config.Cfg.Paths.LogDir, mode, "scrape_runs.log")
	if f, err := os.OpenFile(masterLogPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644); err == nil {
		_, _ = f.WriteString(summary + "\n")
		f.Close()
	}

	return runLogPath
}

func formatDuration(d time.Duration) string {
	d = d.Round(time.Millisecond)
	h := d / time.Hour
	d -= h * time.Hour
	m := d / time.Minute
	d -= m * time.Minute
	s := float64(d) / float64(time.Second)

	if h > 0 {
		return fmt.Sprintf("%dh %dm %.1fs", h, m, s)
	}
	if m > 0 {
		return fmt.Sprintf("%dm %.1fs", m, s)
	}
	return fmt.Sprintf("%.2fs", s)
}

// Run dispatches scraping across modes.
func (s *Scraper) Run(ctx context.Context, maxWorkers int, year ...int) error {
	y := s.CurrentYear
	if len(year) > 0 && year[0] > 0 {
		y = year[0]
	}

	if s.Mode == "seasons" || s.Mode == "both" {
		if err := s.RunScraper(ctx, "seasons", maxWorkers, y); err != nil {
			return err
		}
	}
	if s.Mode == "all-time" || s.Mode == "both" {
		if err := s.RunScraper(ctx, "all-time", maxWorkers, 0); err != nil {
			return err
		}
	}
	return nil
}
