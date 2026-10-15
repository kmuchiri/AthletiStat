package info

import (
	"bytes"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"athletistat/pkg/config"
	"athletistat/pkg/console"

	"github.com/olekukonko/tablewriter"
)

// FileStat holds metadata for a dataset file.
type FileStat struct {
	Name     string
	SizeStr  string
	RowCount int64
}

// DatasetInfo inspects datasets, generates summary reports, and updates documentation.
type DatasetInfo struct {
	Stats []FileStat
}

// NewDatasetInfo creates a DatasetInfo instance.
func NewDatasetInfo() *DatasetInfo {
	return &DatasetInfo{}
}

// CountRows counts total lines in a CSV file and subtracts 1 for header.
func (d *DatasetInfo) CountRows(filename string) (int64, error) {
	file, err := os.Open(filename)
	if err != nil {
		return 0, err
	}
	defer file.Close()

	chunkSize := config.Cfg.Display.RowCountChunkSize
	if chunkSize <= 0 {
		chunkSize = 1048576
	}

	buf := make([]byte, chunkSize)
	var count int64

	for {
		n, err := file.Read(buf)
		if n > 0 {
			count += int64(bytes.Count(buf[:n], []byte{'\n'}))
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			return 0, err
		}
	}

	if count > 0 {
		return count - 1, nil
	}
	return 0, nil
}

// GetFileSize formats file size into MB or GB string.
func (d *DatasetInfo) GetFileSize(filepath string) string {
	fi, err := os.Stat(filepath)
	if err != nil {
		return "0.00 MB"
	}

	sizeInBytes := float64(fi.Size())
	sizeInMB := sizeInBytes / (1024 * 1024)

	if sizeInMB > 1024 {
		sizeInGB := sizeInMB / 1024
		return fmt.Sprintf("%.2f GB", sizeInGB)
	}
	return fmt.Sprintf("%.2f MB", sizeInMB)
}

// GenerateInfo generates a text report of all datasets.
func (d *DatasetInfo) GenerateInfo() error {
	var stats []FileStat
	allTimeDir := filepath.Join(config.Cfg.Paths.DatasetDir, "all-time")
	seasonsDir := filepath.Join(config.Cfg.Paths.DatasetDir, "seasons")

	// Process all-time
	if _, err := os.Stat(allTimeDir); err == nil {
		matches, _ := filepath.Glob(filepath.Join(allTimeDir, "*.csv"))
		for _, m := range matches {
			rc, _ := d.CountRows(m)
			stats = append(stats, FileStat{
				Name:     filepath.Base(m),
				SizeStr:  d.GetFileSize(m),
				RowCount: rc,
			})
		}
	}

	// Process seasons
	if _, err := os.Stat(seasonsDir); err == nil {
		_ = filepath.Walk(seasonsDir, func(path string, info os.FileInfo, err error) error {
			if err == nil && !info.IsDir() && strings.HasSuffix(info.Name(), ".csv") {
				rc, _ := d.CountRows(path)
				stats = append(stats, FileStat{
					Name:     info.Name(),
					SizeStr:  d.GetFileSize(path),
					RowCount: rc,
				})
			}
			return nil
		})
	}

	// Sort by RowCount descending
	sort.Slice(stats, func(i, j int) bool {
		return stats[i].RowCount > stats[j].RowCount
	})

	tableStr := d.renderTable(stats)

	infoFile := config.Cfg.Paths.DatasetInfoFile
	_ = os.MkdirAll(filepath.Dir(infoFile), 0755)
	if err := os.WriteFile(infoFile, []byte(tableStr), 0644); err != nil {
		return err
	}

	console.Success(fmt.Sprintf("Dataset information saved to %s", infoFile))
	return nil
}

// GenerateSummary updates the summary table in README.md.
func (d *DatasetInfo) GenerateSummary() error {
	var stats []FileStat
	allTimeDir := filepath.Join(config.Cfg.Paths.DatasetDir, "all-time")
	seasonsDir := filepath.Join(config.Cfg.Paths.DatasetDir, "seasons")

	topAllTime := filepath.Join(allTimeDir, "top_track_field_performances_all_time.csv")
	if _, err := os.Stat(topAllTime); err == nil {
		rc, _ := d.CountRows(topAllTime)
		stats = append(stats, FileStat{
			Name:     filepath.Base(topAllTime),
			SizeStr:  d.GetFileSize(topAllTime),
			RowCount: rc,
		})
	}

	if _, err := os.Stat(seasonsDir); err == nil {
		matches, _ := filepath.Glob(filepath.Join(seasonsDir, "combined_track_field_performances_*.csv"))
		for _, m := range matches {
			rc, _ := d.CountRows(m)
			stats = append(stats, FileStat{
				Name:     filepath.Base(m),
				SizeStr:  d.GetFileSize(m),
				RowCount: rc,
			})
		}
	}

	sort.Slice(stats, func(i, j int) bool {
		return stats[i].RowCount > stats[j].RowCount
	})

	tableStr := d.renderTable(stats)

	readmePath := "README.md"
	content, err := os.ReadFile(readmePath)
	if err != nil {
		return nil
	}

	startAnchor := "<!-- START_DATASET_INFO -->"
	endAnchor := "<!-- END_DATASET_INFO -->"

	pattern := regexp.MustCompile(fmt.Sprintf(`(?s)%s.*?%s`, regexp.QuoteMeta(startAnchor), regexp.QuoteMeta(endAnchor)))
	replacement := fmt.Sprintf("%s\n```text\n%s```\n%s", startAnchor, tableStr, endAnchor)
	newContent := pattern.ReplaceAllString(string(content), replacement)

	if err := os.WriteFile(readmePath, []byte(newContent), 0644); err == nil {
		console.Success("README.md dataset info updated successfully!")
	}

	return nil
}

func (d *DatasetInfo) renderTable(stats []FileStat) string {
	buf := new(strings.Builder)
	table := tablewriter.NewTable(buf, tablewriter.WithHeader([]string{"File Name", "File Size", "Row Count"}))

	for _, s := range stats {
		_ = table.Append([]string{
			s.Name,
			s.SizeStr,
			fmt.Sprintf("%d", s.RowCount),
		})
	}

	_ = table.Render()
	return buf.String()
}
