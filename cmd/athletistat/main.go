package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"athletistat/pkg/console"
	"athletistat/pkg/generator"
	"athletistat/pkg/info"
	"athletistat/pkg/preprocessor"
	"athletistat/pkg/scraper"
	"athletistat/pkg/updater"

	"github.com/spf13/cobra"
)

func main() {
	if err := newRootCmd().Execute(); err != nil {
		os.Exit(1)
	}
}

func newRootCmd() *cobra.Command {
	var (
		scraperMode       string
		preprocessingMode string
		createDatasetMode string
		combine           bool
		splitDatasetMode  string
		fetchDataMode     string
		year              int
		datasetInfo       bool
		updateSeason      bool
		noGenerate        bool
	)

	cmd := &cobra.Command{
		Use:   "athletistat",
		Short: "AthletiStat - Track & Field Data Pipeline",
		RunE: func(cmd *cobra.Command, args []string) error {
			console.Header("AthletiStat  -  Track & Field Data Pipeline", "─", 52)
			currentYear := time.Now().Year()
			ctx := context.Background()

			validateChoice := func(name, val string) error {
				if val != "" && val != "seasons" && val != "all-time" {
					return fmt.Errorf("invalid value for %s: %s (must be 'seasons' or 'all-time')", name, val)
				}
				return nil
			}

			if err := validateChoice("--scraper", scraperMode); err != nil {
				return err
			}
			if err := validateChoice("--preprocessing", preprocessingMode); err != nil {
				return err
			}
			if err := validateChoice("--create-dataset", createDatasetMode); err != nil {
				return err
			}
			if err := validateChoice("--split-dataset", splitDatasetMode); err != nil {
				return err
			}
			if err := validateChoice("--fetch-data", fetchDataMode); err != nil {
				return err
			}

			if fetchDataMode != "" {
				sYear := year
				if sYear == 0 {
					sYear = currentYear
				}
				targetLabel := "all-time"
				if fetchDataMode == "seasons" {
					targetLabel = strconv.Itoa(sYear)
				}
				console.Info(fmt.Sprintf("fetch-data mode: %s  |  year: %s", strings.ToUpper(fetchDataMode), targetLabel))
				console.Divider("─", 52, console.Dim)

				console.Step("[1/3] Starting scraper...")
				sc := scraper.NewScraper(fetchDataMode, "")
				var yArg []int
				if fetchDataMode == "seasons" {
					yArg = append(yArg, sYear)
				}
				if err := sc.Run(ctx, 0, yArg...); err != nil {
					return err
				}

				console.Step("[2/3] Running preprocessing...")
				pp := preprocessor.NewPreprocessor(fetchDataMode, "")
				var yrStr []string
				if fetchDataMode == "seasons" && year > 0 {
					yrStr = append(yrStr, strconv.Itoa(year))
				}
				if err := pp.Run(yrStr...); err != nil {
					return err
				}

				console.Step("[3/3] Generating datasets...")
				gen := generator.NewDatasetGenerator(fetchDataMode)
				if err := gen.Run(false, yrStr...); err != nil {
					return err
				}

				console.Divider("─", 52, console.Dim)
				console.Success("fetch-data pipeline complete.")
			}

			if scraperMode != "" {
				sYear := year
				if sYear == 0 {
					sYear = currentYear
				}
				targetLabel := "all-time"
				if scraperMode == "seasons" {
					targetLabel = strconv.Itoa(sYear)
				}
				console.Info(fmt.Sprintf("Scraper mode: %s  |  year: %s", strings.ToUpper(scraperMode), targetLabel))
				sc := scraper.NewScraper(scraperMode, "")
				var yArg []int
				if scraperMode == "seasons" {
					yArg = append(yArg, sYear)
				}
				if err := sc.Run(ctx, 0, yArg...); err != nil {
					return err
				}
			}

			if preprocessingMode != "" {
				console.Info(fmt.Sprintf("Preprocessing mode: %s", strings.ToUpper(preprocessingMode)))
				pp := preprocessor.NewPreprocessor(preprocessingMode, "")
				var yrStr []string
				if preprocessingMode == "seasons" && year > 0 {
					yrStr = append(yrStr, strconv.Itoa(year))
				}
				if err := pp.Run(yrStr...); err != nil {
					return err
				}
			}

			if createDatasetMode != "" {
				console.Info(fmt.Sprintf("Generating dataset - mode: %s", strings.ToUpper(createDatasetMode)))
				gen := generator.NewDatasetGenerator(createDatasetMode)
				var yrStr []string
				if createDatasetMode == "seasons" && year > 0 {
					yrStr = append(yrStr, strconv.Itoa(year))
				}
				if err := gen.Run(false, yrStr...); err != nil {
					return err
				}
			}

			if combine {
				console.Info("Combining season datasets into a single aggregated file...")
				gen := generator.NewDatasetGenerator("seasons")
				if err := gen.Run(true); err != nil {
					return err
				}
			}

			if splitDatasetMode != "" {
				console.Info(fmt.Sprintf("Splitting dataset - mode: %s", strings.ToUpper(splitDatasetMode)))
				splitter := generator.NewDatasetSplitter(splitDatasetMode)
				if err := splitter.Run(); err != nil {
					return err
				}
			}

			if updateSeason {
				uYear := year
				if uYear == 0 {
					uYear = currentYear
				}
				genFlag := !noGenerate
				console.Info(fmt.Sprintf("Updating season: %d  |  generate: %t", uYear, genFlag))
				u := updater.NewSeasonsUpdate(uYear, genFlag)
				if err := u.Run(ctx); err != nil {
					return err
				}
			}

			if datasetInfo {
				console.Info("Fetching dataset information...")
				di := info.NewDatasetInfo()
				_ = di.GenerateInfo()
				_ = di.GenerateSummary()
			}

			return nil
		},
	}

	cmd.Flags().StringVar(&scraperMode, "scraper", "", "Scrape data for seasons or all-time.")
	cmd.Flags().StringVar(&preprocessingMode, "preprocessing", "", "Preprocess scraped data.")
	cmd.Flags().StringVar(&createDatasetMode, "create-dataset", "", "Generate datasets from preprocessed data.")
	cmd.Flags().BoolVar(&combine, "combine", false, "Combine datasets in season for all years scraped.")
	cmd.Flags().StringVar(&splitDatasetMode, "split-dataset", "", "Splits datasets according to gender, discipline, and event type.")
	cmd.Flags().StringVar(&fetchDataMode, "fetch-data", "", "Performs --scraper, --preprocessing and --create-dataset for given mode.")
	cmd.Flags().IntVar(&year, "year", 0, "Year to use for seasons mode. If blank, behavior depends on the command.")
	cmd.Flags().BoolVar(&datasetInfo, "dataset-info", false, "Generates a txt file of dataset information; file name, file size, and row number")
	cmd.Flags().BoolVar(&updateSeason, "update-season", false, "Update the combined seasons dataset for a given year (default: current year). Uses --year to specify which year.")
	cmd.Flags().BoolVar(&noGenerate, "no-generate", false, "Skip scrape/preprocess/generate; assume the per-year dataset already exists on disk.")

	return cmd
}
