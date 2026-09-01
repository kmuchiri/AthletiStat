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

- **Multithreaded Scraping** - Concurrent scraping via `ThreadPoolExecutor` with configurable worker counts and in-place static progress bars.
- **Centralized Configuration** - Easily tune workers, request timeouts, retries, rate limits, and output paths via `athletistat/config.toml`.
- **Queue System** - Tracks completed and in-progress scrape jobs in JSON files, enabling safe resumption of interrupted runs.
- **Caching & Incremental Updates** - Completed historical seasons are marked in `completed_seasons.json` and skipped on future runs. Update current season datasets in-place with `--update-season`.
- **Automatic Retries** - Requests are configured with exponential backoff and automatic retries on server-side errors (429, 500, 502, 503, 504).
- **Data Transformation** - Standardizes event names, converts time strings (e.g., `1:45.30`) to numeric seconds, calculates athlete age at time of event, and resolves ISO country codes to full names.
- **Flexible Output** - Produces aggregated CSVs per year (seasons), an all-time combined dataset, and granular sub-datasets split by gender, event type, and discipline.

---

## Pipeline Architecture

The system consists of modular components that can be executed end-to-end or independently:

1. **`scraper.py` (Extract)** - Paginates through World Athletics record tables for every configured discipline, gender, and age category. Saves raw tabular data as CSVs.
2. **`preprocessing.py` (Transform)** - Reads raw CSVs, normalizes discipline slugs, parses performance marks to numeric values, maps country codes, computes athlete ages, and saves cleaned files.
3. **`generator.py` (Load)** - Merges all cleaned, fragmented files into final ready-to-use datasets. Supports combining multi-year season data and splitting datasets by gender, event type, and discipline.
4. **`seasons_update.py` (Update)** - Replaces data for a specific year in the combined dataset in-place without recompiling the entire historical archive.
5. **`fetch_info.py` (Inspect)** - Generates dataset statistics and automatically updates markdown documentation tables.

---

## Directory Structure

```text
AthletiStat/
├── athletistat/
│   ├── cli/
│   │   └── cli.py                      # Click-based CLI entry point
│   ├── core/
│   │   ├── generator.py                # Dataset generation and splitting (DatasetGenerator, DatasetSplitter)
│   │   ├── preprocessing.py            # Data cleaning logic (Preprocessor class)
│   │   ├── scraper.py                  # Scraping logic (Scraper class)
│   │   └── seasons_update.py           # In-place dataset update logic (SeasonsUpdate class)
│   ├── scripts/
│   │   ├── fetch_info.py               # Dataset size/row count inspection (DatasetInfo class)
│   │   └── get_dataset_info.sh         # Shell utility script for dataset inspection
│   ├── config.py                       # Centralized configuration loader (cfg)
│   ├── config.toml                     # User-editable configuration tunables
│   ├── console.py                      # Terminal styling and static ProgressBar
│   └── options.json                    # Discipline/country/age-category configuration
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
│   ├── python_api.md                   # Python API class and usage reference
│   ├── scraper_queue_system.md         # Queue system design and resumption behavior
│   ├── scripts_reference.md            # Utility script usage reference
│   ├── todo.md                         # Project development task tracker
│   └── tree.txt                        # Reference directory tree
├── logs/
│   ├── all-time/                       # Scrape error logs for all-time mode
│   └── seasons/                        # Scrape error logs for seasons mode
├── queues/
│   ├── all-time/                       # All-time scrape job queues
│   └── seasons/
│       └── completed_seasons.json      # Registry of fully-scraped historical seasons
├── tests/                              # Pytest test suite
├── AthletiStat                         # Executable CLI entry point script
├── requirements.txt
└── README.md
```

---

## Configuration

AthletiStat provides a user-editable configuration file at [`athletistat/config.toml`](athletistat/config.toml) with sensible defaults:

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
options_file = "athletistat/options.json"
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
> Detailed metrics (including exact file sizes and row counts) for all generated datasets are saved in [dataset_info.txt](data/datasets/dataset_info.txt). You can generate or update this file by running `./AthletiStat --dataset-info` or the `get_dataset_info.sh` utility script.

<!-- START_DATASET_INFO -->
```text
+-------------------------------------------------+-----------+-----------+
|                    File Name                    | File Size | Row Count |
+-------------------------------------------------+-----------+-----------+
| combined_track_field_performances_2001_2026.csv |  2.21 GB  |  13328122 |
|    top_track_field_performances_all_time.csv    | 112.69 MB |    658208 |
+-------------------------------------------------+-----------+-----------+
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

**2. Create and activate a virtual environment (recommended):**

```bash
python -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Make the CLI script executable:**

```bash
chmod +x AthletiStat
```

**5. Verify the configuration file is present:**

```text
athletistat/options.json
```

This file contains the full list of disciplines, age categories, genders, and country code mappings that the pipeline relies on. It must be present before running the scraper.

> **Note:** For true free-threaded multi-core parallelism (GIL removed), run Python ≥ 3.13t.

---

## Usage

### CLI Reference

Run the CLI via the executable entry point:

```bash
./AthletiStat [OPTIONS]
```

View all available commands:

```bash
./AthletiStat --help
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
./AthletiStat --fetch-data seasons

# Scrape a specific historical year
./AthletiStat --scraper seasons --year 2024

# Scrape all-time records
./AthletiStat --scraper all-time

# Only run preprocessing on previously scraped seasons data
./AthletiStat --preprocessing seasons

# Generate per-year datasets from preprocessed data
./AthletiStat --create-dataset seasons

# Combine all available season datasets into one file
./AthletiStat --combine

# Update the combined seasons dataset for 2026 (scrapes and updates in-place)
./AthletiStat --update-season --year 2026

# Update the combined seasons dataset using existing 2026 data on disk (skips scraping)
./AthletiStat --update-season --year 2026 --no-generate

# Split the all-time dataset by gender, type, and discipline
./AthletiStat --split-dataset all-time

# Generate/update dataset information and README summary
./AthletiStat --dataset-info
```

---

### Python API

For details on importing and using the core Python classes (such as `Scraper`, `Preprocessor`, `DatasetGenerator`, `DatasetSplitter`, `SeasonsUpdate`, and `DatasetInfo`) directly in your own scripts, see the [Python API Reference](docs/python_api.md).

---

## Notes

- Raw scraped files land in `data/processing/output/` and are not included in the repository.
- Final datasets land in `data/datasets/` and are also not tracked by git.
- Scrape error logs are written to `logs/{mode}/{date}/scrape_errors_{timestamp}.log`.
- The `options.json` configuration file drives which disciplines and age categories are scraped. Modifying it allows targeting a subset of events.
- The code is designed to be run from the **project root directory**.
