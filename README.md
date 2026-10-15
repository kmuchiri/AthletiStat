# AthletiStat

An automated, end-to-end Python ETL (Extract, Transform, Load) pipeline for scraping, cleaning, and aggregating track and field performance data.

---

## Table of Contents

- [Features](#features)
- [Pipeline Architecture](#pipeline-architecture)
- [Directory Structure](#directory-structure)
- [Configuration](#configuration)
- [Dataset Description](#dataset-description)
  - [Output Files](#output-files)
  - [Data Dictionary](#data-dictionary)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Reference](#cli-reference)
  - [Python API Reference](docs/python_api.md)
- [Notes](#notes)

---

## Features

- **Concurrent Scraping** - Concurrent goroutine worker pool with configurable worker counts and in-place static progress bars.
- **Centralized Configuration** - Easily tune workers, request timeouts, retries, rate limits, and output paths via `config.toml`.
- **Queue System** - Tracks completed and in-progress scrape jobs in JSON files, enabling safe resumption of interrupted runs.
- **Caching & Incremental Updates** - Completed historical seasons are marked in `completed_seasons.json` and skipped on future runs. Update current season datasets in-place with `--update-season`.
- **Automatic Retries** - Requests are configured with exponential backoff and automatic retries on server-side errors (429, 500, 502, 503, 504).
- **Data Transformation** - Standardizes event names, converts time strings (e.g., `1:45.30`) to numeric seconds, calculates athlete age at time of event, and resolves ISO country codes to full names.
- **Flexible Output** - Produces aggregated CSVs per year (seasons), an all-time combined dataset, and granular sub-datasets split by gender, event type, and discipline.

---

## Pipeline Architecture

The system consists of modular Go packages that can be executed end-to-end or independently:

1. **`pkg/scraper` (Extract)** - Paginates through World Athletics record tables for every configured discipline, gender, and age category. Saves raw tabular data as CSVs.
2. **`pkg/preprocessor` (Transform)** - Reads raw CSVs, normalizes discipline slugs, parses performance marks to numeric values, maps country codes, computes athlete ages, and saves cleaned files.
3. **`pkg/generator` (Load)** - Merges all cleaned, fragmented files into final ready-to-use datasets. Supports combining multi-year season data and splitting datasets by gender, event type, and discipline.
4. **`pkg/updater` (Update)** - Replaces data for a specific year in the combined dataset in-place without recompiling the entire historical archive.
5. **`pkg/info` (Inspect)** - Generates dataset statistics and automatically updates markdown documentation tables.

---

## Directory Structure

```text
AthletiStat/
├── bin/
│   └── athletistat                     # Compiled Go binary
├── cmd/
│   └── athletistat/
│       ├── main.go                     # Cobra CLI entry point
│       └── main_test.go                # CLI tests
├── pkg/
│   ├── config/                         # Configuration loading & defaults
│   ├── console/                        # Terminal styling and progress bar
│   ├── generator/                      # Dataset generation and splitting
│   ├── info/                           # Dataset inspection & summary report
│   ├── preprocessor/                   # Data cleaning & normalization logic
│   ├── scraper/                        # Scraping & queue logic
│   └── updater/                        # In-place dataset update logic
├── scripts/                            # Utility shell scripts
├── config.toml                         # User-editable configuration tunables
├── options.json                        # Discipline/country/age-category configuration
├── data/
│   ├── datasets/
│   │   ├── all-time/                   # Final all-time aggregated datasets
│   │   ├── seasons/                    # Final per-year and combined season datasets
│   │   └── dataset_info.txt            # Generated dataset size and row count statistics
│   └── processing/
│       ├── combined/                   # Merged, per-discipline cleaned files
│       └── output/                     # Raw scraped CSVs (organized by mode/year/gender)
├── docs/
│   ├── data_pipeline_file_flow.md      # End-to-end file flow through the pipeline
│   ├── options_config_reference.md     # options.json schema and field reference
│   ├── preprocessing_normalization.md  # Normalization rules and transformation logic
│   ├── scraper_queue_system.md         # Queue system design and resumption behavior
│   ├── scripts_reference.md            # Utility script usage reference
│   └── todo.md                         # Project development task tracker
├── logs/
│   ├── all-time/                       # Scrape error logs for all-time mode
│   └── seasons/                        # Scrape error logs for seasons mode
├── queues/
│   ├── all-time/                       # All-time scrape job queues
│   └── seasons/
│       └── completed_seasons.json      # Registry of fully-scraped historical seasons
├── Makefile                            # Build and test automation
├── go.mod
├── go.sum
└── README.md
```

---

## Configuration

AthletiStat provides a user-editable configuration file at [`config.toml`](config.toml) with sensible defaults:

```toml
[scraper]
max_workers = 10              # Number of concurrent threads for scraping
connect_timeout = 5           # Seconds to wait for initial connection
read_timeout = 30             # Seconds to wait for server response
retry_total = 5               # Max retry attempts on failed requests
retry_backoff_factor = 1      # Exponential backoff multiplier between retries
retry_status_codes = [429, 500, 502, 503, 504]
page_delay = 1.5              # Seconds to wait between paginated page requests
user_agent = "Mozilla/5.0"    # Custom User-Agent header
verify_ssl = true             # SSL certificate verification

[paths]
options_file = "options.json"
scraper_output = "data/processing/output"
queue_dir = "queues"
log_dir = "logs"
combined_dir = "data/processing/combined"
dataset_dir = "data/datasets"
dataset_info_file = "data/datasets/dataset_info.txt"
dataset_summary_file = "data/datasets/dataset_summary.txt"

[display]
progress_bar_width = 30       # Character width of the terminal progress bar
row_count_chunk_size = 1048576  # Stream chunk size for counting CSV rows (1 MB)
```

---

## Dataset Description

### Output Files

| File | Location | Description |
| --- | --- | ----- |
| `{year}_track_`<br>`field_`<br>`performances.csv` | `data/datasets/`<br>`seasons/` | All top performances across every discipline for a specific calendar year. |
| `combined_track_`<br>`field_`<br>`performances_`<br>`{min}_{max}.csv` | `data/datasets/`<br>`seasons/` | All season datasets merged into a single file spanning the full year range. |
| `top_track_`<br>`field_`<br>`performances_`<br>`all_time.csv` | `data/datasets/`<br>`all-time/` | The absolute historical top performances across all disciplines. |
| Split subsets | `data/datasets/{mode}/`<br>`split_by_type/`,<br>`split_by_discipline/`,<br>`split_global/` | Granular splits by gender, event type, and discipline. |

> [!NOTE]
> Detailed metrics (including exact file sizes and row counts) for all generated datasets are saved in [dataset_info.txt](data/datasets/dataset_info.txt). You can generate or update this file by running `./bin/athletistat --dataset-info` or the `scripts/get_dataset_info.sh` utility script.

<!-- START_DATASET_INFO -->
```text
+-------------------------------------------------+-----------+-----------+
|                    File Name                    | File Size | Row Count |
+-------------------------------------------------+-----------+-----------+
| combined_track_field_performances_2001_2026.csv |  2.21 GB  |  13328122 |
|    top_track_field_performances_all_time.csv    | 112.69 MB |    658208 |
+-------------------------------------------------+-----------+-----------+top_track_field_performances_all_time.csv has 676513 records and is 121 MB in size 
combined_track_field_performances_2001_2026.csv has 14327987 records and is 2557 MB in size 
```
<!-- END_DATASET_INFO -->

### Data Dictionary

| Column | Type | Description | Example |
| --- | --- | --- | --- |
| `rank` | String | Global rank of the performance in its list. | `1`, `=2` |
| `mark` | String | Raw performance mark as scraped (time, distance, or points). | `9.58`, `1:40.91`, `8952` |
| `wind` | Float | Wind reading in m/s where applicable. | `+0.9`, `-1.2` |
| `competitor` | String | Full name of the athlete. | `Usain BOLT` |
| `dob` | Date | Athlete's date of birth. | `1986-08-21` |
| `nationality` | String | 3-letter ISO code of the athlete's country. | `JAM`, `USA` |
| `position` | String | Athlete's finishing position in the specific race/event. | `1`, `1f1` |
| `venue` | String | City/stadium where the performance occurred. | `Olympiastadion, Berlin (GER)` |
| `date` | Date | Exact date the performance was recorded. | `2009-08-16` |
| `result_score` | Integer | World Athletics points score for the performance. | `1356` |
| `discipline` | String | Raw URL slug for the discipline. | `100-metres`, `decathlon-u20` |
| `type` | String | Category slug of the event group. | `sprints`, `jumps` |
| `sex` | String | Gender category of the event. | `female`, `male` |
| `age_cat` | String | Age category of the list. | `senior`, `u20`, `u18` |
| **`normalized_discipline`** | String | *[Generated]* Cleaned discipline name - age/weight suffixes removed, known aliases resolved. | `100-metres`, `decathlon` |
| **`track_field`** | String | *[Generated]* Categorization of the event. | `track`, `field`, `mixed` |
| **`mark_numeric`** | Float | *[Generated]* Performance mark converted to a float. Times (e.g., `MM:SS`) are converted to total seconds. | `9.58`, `100.91` |
| **`nat_full`** | String | *[Generated]* Full country name of the athlete. | `Jamaica` |
| **`venue_country`** | String | *[Generated]* Full country name parsed from the venue string. | `Germany` |
| **`age_at_event`** | Integer | *[Generated]* Athlete's calculated age on the day of the performance. | `22` |
| **`season`** | Integer | *[Generated]* Calendar year the event took place. | `2009` |

---

## Installation

**1. Clone the repository:**

```bash
git clone https://github.com/your-username/AthletiStat.git
cd AthletiStat
```

**2. Build the binary:**

```bash
make build
```

This compiles the CLI binary to `bin/athletistat`.

**3. Run the test suite:**

```bash
make test
```

**4. Verify configuration and options are present:**

```text
config.toml
options.json
```

The `options.json` file contains the full list of disciplines, age categories, genders, and country code mappings that the pipeline relies on. It must be present in the root directory before running the scraper.

---

## Usage

### CLI Reference

Run the CLI via the compiled binary:

```bash
./bin/athletistat [flags]
```

View all available commands:

```bash
./bin/athletistat --help
```

#### Options

| Flag | Values | Description |
| --- | --- | --- |
| `--fetch-data` | `seasons`, `all-time` | **End-to-end pipeline.** Runs `--scraper`, `--preprocessing`, and `--create-dataset` in sequence. |
| `--scraper` | `seasons`, `all-time` | Scrape raw performance data from World Athletics. |
| `--preprocessing` | `seasons`, `all-time` | Clean and normalize previously scraped raw CSVs. |
| `--create-dataset` | `seasons`, `all-time` | Merge cleaned files into a final aggregated dataset. |
| `--combine` | *(flag)* | Combine all per-year season datasets into a single multi-year CSV. |
| `--split-dataset` | `seasons`, `all-time` | Split datasets into sub-files by gender, event type, and discipline. |
| `--update-season` | *(flag)* | In-place update of the combined season dataset for a specific year (default: current year). |
| `--no-generate` | *(flag)* | Used with `--update-season` to skip the scrape/preprocess/generate pipeline and use existing on-disk CSV. |
| `--year` | `<int>` | Target year for `seasons` mode or `--update-season`. Defaults to current year if omitted. |
| `--dataset-info` | *(flag)* | Generate or update the `dataset_info.txt` file containing name, size, and row count statistics. |

#### Common Examples

```bash
# Run the full pipeline for the current season
./bin/athletistat --fetch-data seasons

# Scrape a specific historical year
./bin/athletistat --scraper seasons --year 2024

# Scrape all-time records
./bin/athletistat --scraper all-time

# Only run preprocessing on previously scraped seasons data
./bin/athletistat --preprocessing seasons

# Generate per-year datasets from preprocessed data
./bin/athletistat --create-dataset seasons

# Combine all available season datasets into one file
./bin/athletistat --combine

# Update the combined seasons dataset for 2026 (scrapes and updates in-place)
./bin/athletistat --update-season --year 2026

# Update the combined seasons dataset using existing 2026 data on disk (skips scraping)
./bin/athletistat --update-season --year 2026 --no-generate

# Split the all-time dataset by gender, type, and discipline
./bin/athletistat --split-dataset all-time

# Generate/update dataset information and README summary
./bin/athletistat --dataset-info
```

---

## Notes

- Raw scraped files land in `data/processing/output/` and are not included in the repository.
- Final datasets land in `data/datasets/` and are also not tracked by git.
- Scrape error logs are written to `logs/{mode}/{date}/scrape_errors_{timestamp}.log`.
- The `options.json` configuration file drives which disciplines and age categories are scraped. Modifying it allows targeting a subset of events.
- The code is designed to be run from the **project root directory**.
- If a new scoring table is released this changes all the scores.
