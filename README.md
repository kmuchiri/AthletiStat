# AthletiStat

An automated, end-to-end Python ETL (Extract, Transform, Load) pipeline designed to scrape, clean, and aggregate track and field performance data from World Athletics.

## Table of Contents
* [Features](#features)
* [Pipeline Architecture](#pipeline-architecture)
* [Directory Structure](#directory-structure)
* [Dataset Description](#dataset-description)
  * [Output Files](#output-files)
  * [Data Dictionary](#data-dictionary)
* [Installation and Setup](#installation-and-setup)
* [Usage](#usage)
  * [Extract Data](#extract-data)
  * [Transform Data](#transform-data)
  * [Generate and Split Datasets](#generate-and-split-datasets)



## Features

* **Automated Extraction:** Multithreaded scraper with automatic pagination, exponential backoff, and robust state management (resumes interrupted queues safely).
* **Data Transformation:** Standardizes event names, converts complex time strings (e.g., `1:45.30`) into numeric seconds, calculates athlete ages at the time of the event, and maps ISO country codes.
* **Aggregated Output:** Generates CSV datasets separated by historical all-time lists and specific calendar years.




## Pipeline Architecture

The system consists of three distinct modules executed sequentially:

1. **Extraction (`scraper.py`):** Connects to World Athletics website, paginates through records, and saves raw tabular data.
2. **Transformation (`preprocessing.py`):** Reads raw data, normalizes strings, calculates metrics (e.g., age, numeric marks), maps country codes, and saves cleaned individual files.
3. **Loading (`generator.py`):** Merges all cleaned, fragmented files into ready datasets.


## Directory Structure


```bash
AthletiStat
.
├── all-time
│   ├── datasets
│   ├── processing
│   ├── queues
│   └── split_by_discipline
├── logs
│   ├── all-time
│   └── seasons
├── seasons
│   ├── completed_seasons.json
│   ├── datasets
│   ├── processing
│   ├── queues
│   └── split_by_discipline
├── utils
│   ├── athletistat-options.json
│   ├── generator.py
│   ├── preprocessing.py
│   └── scraper.py
├── athletistat.py
├── README.md
└── requirements.txt
```

## Dataset Description

The pipeline outputs final aggregated datasets into the `seasons/datasets/` and `all-time/datasets/` directories.

### Output Files

* **Seasons Data:** `{year}_track_field_performances.csv` (Contains all top performances across all disciplines for a specific calendar year).
* **All-Time Data:** `top_track_field_performances_all_time.csv` (Contains the absolute historical top performances across all disciplines).

### Data Dictionary

| Column Name | Data Type | Description | Example |
| --- | --- | --- | --- |
| `rank` | Integer/String | The global rank of the performance in the specific list. | `1`, `=2` |
| `mark` | String | The raw performance mark as scraped (Time, Distance, or Points). | `9.58`, `1:40.91`, `8952` |
| `wind` | Float | The wind reading in m/s (if applicable to the event). | `+0.9`, `-1.2` |
| `competitor` | String | The full name of the athlete. | `Usain BOLT` |
| `dob` | Date | The athlete's Date of Birth. | `1986-08-21` |
| `nationality` | String | The 3-letter ISO country code of the athlete. | `JAM`, `USA` |
| `position` | String | The athlete's finishing position in the specific race/event. | `1`, `1f1` |
| `venue` | String | The city/stadium where the performance occurred. | `Olympiastadion, Berlin (GER)` |
| `date` | Date | The exact date the performance was recorded. | `2009-08-16` |
| `result_score` | Integer | The World Athletics points score awarded for the performance. | `1356` |
| `discipline` | String | The raw URL slug for the discipline. | `100-metres`, `decathlon-u20` |
| `type` | String | The category slug of the event. | `sprints`, `jumps` |
| `sex` | String | The gender category of the event. | `female`, `male` |
| `age_cat` | String | The age category of the list. | `senior`, `u20`, `u18` |
| **`normalized_discipline`** | String | *[Generated]* Cleaned discipline name with youth/weight suffixes removed. | `100-metres`, `decathlon` |
| **`track_field`** | String | *[Generated]* Categorization of the event (`track`, `field`, or `mixed`). | `track` |
| **`mark_numeric`** | Float | *[Generated]* The `mark` converted to a pure float. Formatted times (MM:SS) are converted into total seconds (track) or metres(field). | `9.58`, `100.91` |
| **`nat_full`** | String | *[Generated]* The full name of the athlete's country. | `Jamaica` |
| **`venue_country`** | String | *[Generated]* The full name of the country where the venue is located. | `Germany` |
| **`age_at_event`** | Integer | *[Generated]* The calculated age of the athlete on the day of the performance. | `22` |
| **`season`** | Integer | *[Generated]* The calendar year the event took place. | `2009` |



## Installation and Setup

1. **Fork / Clone Repository**

2. **Install dependencies:**

It is recommended to use a virtual environment.

```bash
pip install -r requirements

```

3. **Verify Configuration:**
Ensure `utils/athletistat-options.json` is present in your root directory. This file dictates the disciplines, age categories, and country mappings the scraper relies upon.

**Note:**
To use with actual multithreading (GIL removed), run any version of python >= 3.13.xt

## Usage

The pipeline consists of three utility modules that should be executed sequentially. Since the CLI parameters have been refactored into classes, you can instantiate them directly in your own Python scripts or run the modules directly.

### Extract Data

Scrape raw data from World Athletics using the `Scraper` class.

```python
from utils.scraper import Scraper

# Scrape the current season
scraper = Scraper(mode="seasons")
scraper.run(max_workers=12)

# Scrape the all-time lists
scraper_all_time = Scraper(mode="all-time")
scraper_all_time.run(max_workers=12)
```

### Transform Data

Clean and normalize the raw CSV files using the `Preprocessor` class.

```python
from utils.preprocessing import Preprocessor

# Process both seasons and all-time scraped data
preprocessor = Preprocessor(mode="both")
preprocessor.run()
```

### Generate and Split Datasets

Concatenate the cleaned fragments into the final machine-learning-ready datasets, and split them logically.

```python
from utils.generator import DatasetGenerator, DatasetSplitter

# Generate the combined datasets
generator = DatasetGenerator(mode="both")
generator.run(combine=True)

# Split datasets by type, discipline, and gender
splitter = DatasetSplitter(mode="both")
splitter.run()
```

