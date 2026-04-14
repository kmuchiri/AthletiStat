# AthletiStat

An automated, end-to-end Python ETL (Extract, Transform, Load) pipeline for scraping, cleaning, and aggregating track and field performance data.

---

## Table of Contents

- [Features](#features)
- [Pipeline Architecture](#pipeline-architecture)
- [Directory Structure](#directory-structure)
- [Dataset Description](#dataset-description)
  - [Output Files](#output-files)
  - [Data Dictionary](#data-dictionary)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Reference](#cli-reference)
  - [Python API](#python-api)
    - [Scraper](#scraper)
    - [Preprocessor](#preprocessor)
    - [DatasetGenerator](#datasetgenerator)
    - [DatasetSplitter](#datasetsplitter)
- [Notes](#notes)

---

## Features

- **Multithreaded Scraping** — Concurrent scraping via `ThreadPoolExecutor` with configurable worker counts.
- **Resilient Queue System** — Tracks completed and in-progress scrape jobs in persistent JSON queue files, enabling safe resumption of interrupted runs.
- **Smart Caching** — Completed historical seasons are marked in `completed_seasons.json` and skipped on future runs.
- **Automatic Retries** — Requests are configured with exponential backoff and automatic retries on server-side errors (429, 500, 502, 503, 504).
- **Rich Data Transformation** — Standardizes event names, converts time strings (e.g., `1:45.30`) to numeric seconds, calculates athlete age at time of event, and resolves ISO country codes to full names.
- **Flexible Output** — Produces aggregated CSVs per year (seasons), an all-time combined dataset, and granular sub-datasets split by gender, event type, and discipline.

---

## Pipeline Architecture

The system consists of three core modules that are executed sequentially:

```text
World Athletics
      │
      ▼
┌─────────────┐      Raw CSVs       ┌───────────────────┐     Cleaned CSVs    ┌──────────────────┐
│  scraper.py │ ─────────────────►  │ preprocessing.py  │ ──────────────────► │  generator.py    │
│  (Extract)  │                     │    (Transform)    │                     │    (Load)        │
└─────────────┘                     └───────────────────┘                     └──────────────────┘
      │                                     │                                         │
  data/processing/output/             data/processing/combined/                data/datasets/
```

1. **`scraper.py` (Extract)** — Paginates through World Athletics record tables for every configured discipline, gender, and age category. Saves raw tabular data as CSVs.
2. **`preprocessing.py` (Transform)** — Reads raw CSVs, normalizes discipline slugs, parses performance marks to numeric values, maps country codes, computes athlete ages, and saves cleaned files.
3. **`generator.py` (Load)** — Merges all cleaned, fragmented files into final ready-to-use datasets. Supports combining multi-year season data and splitting datasets by gender, event type, and discipline.

---

## Directory Structure

```text
AthletiStat/
├── athletistat/
│   ├── cli/
│   │   └── cli.py                      # Click-based CLI entry point
│   ├── core/
│   │   ├── scraper.py                  # Scraping logic (Scraper class)
│   │   ├── preprocessing.py            # Data cleaning logic (Preprocessor class)
│   │   └── generator.py                # Dataset generation and splitting (DatasetGenerator, DatasetSplitter)
│   ├── scripts/
│   │   └── get_dataset_info.sh         # Utility script for dataset inspection
│   └── options.json                    # Discipline/country/age-category configuration
├── data/
│   ├── datasets/
│   │   ├── all-time/                   # Final all-time aggregated datasets
│   │   ├── seasons/                    # Final per-year and combined season datasets
│   │   └── info.txt                    # Notes on dataset contents and structure
│   └── processing/
│       ├── combined/                   # Merged, per-discipline cleaned files
│       └── output/                     # Raw scraped CSVs (organized by mode/year/gender)
├── docs/
│   ├── data_pipeline_file_flow.md      # End-to-end file flow through the pipeline
│   ├── options_config_reference.md     # options.json schema and field reference
│   ├── preprocessing_normalization.md  # Normalization rules and transformation logic
│   ├── scraper_queue_system.md         # Queue system design and resumption behavior
│   ├── scripts_reference.md            # Shell utility script usage reference
│   └── tree.txt                        # Reference directory tree
├── logs/
│   ├── all-time/                       # Scrape error logs for all-time mode
│   └── seasons/                        # Scrape error logs for seasons mode
├── queues/
│   ├── all-time/                       # All-time scrape job queues
│   └── seasons/
│       └── completed_seasons.json  # Registry of fully-scraped historical seasons
├── AthletiStat                     # Executable CLI entry point script
├── requirements.txt
└── README.md
```

---

## Dataset Description

### Output Files

| File | Location | Description |
| --- | --- | ----- |
| `{year}_track_field_performances.csv` | `data/datasets/seasons/` | All top performances across every discipline for a specific calendar year. |
| `combined_track_field_performances _{min}_{max}.csv` | `data/datasets/seasons/` | All season datasets merged into a single file spanning the full year range. |
| `top_track_field_performances _all_time.csv` | `data/datasets/all-time/` | The absolute historical top performances across all disciplines. |
| Split subsets | `data/datasets/{mode}/split_by_type/`, `split_by_discipline/`, `split_global/` | Granular splits by gender, event type, and discipline. |

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
| **`normalized_discipline`** | String | *[Generated]* Cleaned discipline name — age/weight suffixes removed, known aliases resolved. | `100-metres`, `decathlon` |
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
| `--year` | `<int>` | Target year for `seasons` mode. Defaults to the current year if omitted. |

#### Common Examples

```bash
# Run the full pipeline for the current season
./AthletiStat --fetch-data seasons

# Scrape a specific historical year
./AthletiStat --scraper seasons --year 2022

# Scrape all-time records
./AthletiStat --scraper all-time

# Only run preprocessing on previously scraped seasons data
./AthletiStat --preprocessing seasons

# Generate per-year datasets from preprocessed data
./AthletiStat --create-dataset seasons

# Combine all available season datasets into one file
./AthletiStat --combine

# Split the all-time dataset by gender, type, and discipline
./AthletiStat --split-dataset all-time
```

---

### Python API

All core classes can be imported and used directly.

#### Scraper

```python
from athletistat.core.scraper import Scraper

# Scrape performance data for the current season
scraper = Scraper(mode="seasons")
scraper.run(max_workers=10)

# Scrape a specific historical year
scraper = Scraper(mode="seasons")
scraper.run(year=2022, max_workers=12)

# Scrape all-time records
scraper = Scraper(mode="all-time")
scraper.run(max_workers=10)
```

**Key behaviors:**

- Uses `ThreadPoolExecutor` to scrape multiple events concurrently.
- Automatically paginates through all available result pages per event.
- Persists job queues to disk; failed or interrupted jobs remain in the queue and are resumed on the next run.
- Historical years (not the current year) are cached in `completed_seasons.json` and skipped if already fully scraped.
- A `1.5s` delay is enforced between paginated requests to avoid overwhelming the server.

#### Preprocessor

```python
from athletistat.core.preprocessing import Preprocessor

# Preprocess seasons data
preprocessor = Preprocessor(mode="seasons")
preprocessor.run()

# Preprocess all-time data
preprocessor = Preprocessor(mode="all-time")
preprocessor.run()

# Preprocess both
preprocessor = Preprocessor(mode="both")
preprocessor.run()
```

**Key transformations applied:**

- Discipline slug normalization (e.g., `decathlon-u20` → `decathlon`).
- Performance mark parsing: `MM:SS.ss` / `H:MM:SS.ss` → total seconds as a float.
- Event classification: `track_field` column set to `track`, `field`, or `mixed`.
- Country code resolution to full country names (`nat_full`, `venue_country`).
- Date parsing and `age_at_event` calculation from `dob` and `date`.
- `season` column extracted from the performance date year.

#### DatasetGenerator

```python
from athletistat.core.generator import DatasetGenerator

# Generate per-year season datasets
generator = DatasetGenerator(mode="seasons")
generator.run()

# Generate all-time dataset
generator = DatasetGenerator(mode="all-time")
generator.run()

# Generate season datasets and combine into a single multi-year file
generator = DatasetGenerator(mode="seasons")
generator.run(combine=True)
```

#### DatasetSplitter

```python
from athletistat.core.generator import DatasetSplitter

# Split seasons dataset
splitter = DatasetSplitter(mode="seasons")
splitter.run()

# Split all-time dataset
splitter = DatasetSplitter(mode="all-time")
splitter.run()
```

**Split outputs produced:**

- `split_global/` — Full individual events and relay events as separate files.
- `split_by_type/{gender}/` — One CSV per event type (e.g., `sprints`, `jumps`, `hurdles`).
- `split_by_discipline/{gender}/` — One CSV per normalized discipline (e.g., `100-metres`, `long-jump`).
- `{gender}/relays/` — Relay events by discipline (excludes `dob` and `age_at_event`).

---

## Notes

- Raw scraped files land in `data/processing/output/` and are not included in the repository.
- Final datasets land in `data/datasets/` and are also not tracked by git.
- Scrape error logs are written to `logs/{mode}/{date}/scrape_errors_{timestamp}.log`.
- The `options.json` configuration file drives which disciplines and age categories are scraped. Modifying it allows targeting a subset of events.
- The pipeline is designed to be run from the **project root directory**.
