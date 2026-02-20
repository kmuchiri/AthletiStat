# AthletiStat

An automated, end-to-end Python ETL (Extract, Transform, Load) pipeline designed to scrape, clean, and aggregate track and field performance data from World Athletics. The system outputs machine-learning-ready datasets for statistical analysis, modeling, and historical tracking.

## Table of Contents
* [1.0 Features](#10-features)
* [2.0 Pipeline Architecture](#20-pipeline-architecture)
* [3.0 Directory Structure](#30-directory-structure)
* [4.0 Dataset Description](#40-dataset-description)
  * [4.1 Output Files](#41-output-files)
  * [4.2 Data Dictionary](#42-data-dictionary)
* [5.0 Installation and Setup](#50-installation-and-setup)
* [6.0 Usage](#60-usage)
  * [6.1 Step 1: Extract Data](#61-step-1-extract-data)
  * [6.2 Step 2: Transform Data](#62-step-2-transform-data)
  * [6.3 Step 3: Generate Datasets](#63-step-3-generate-datasets)



## 1.0 Features

* **Automated Extraction:** Multithreaded scraper with automatic pagination, exponential backoff, and robust state management (resumes interrupted queues safely).
* **Data Transformation:** Standardizes event names, converts complex time strings (e.g., `1:45.30`) into numeric seconds, calculates athlete ages at the time of the event, and maps ISO country codes.
* **Aggregated Output:** Generates CSV datasets separated by historical all-time lists and specific calendar years.




## 2.0 Pipeline Architecture

The system consists of three distinct modules executed sequentially:

1. **Extraction (`scraper.py`):** Connects to World Athletics website, paginates through records, and saves raw tabular data.
2. **Transformation (`preprocessing.py`):** Reads raw data, normalizes strings, calculates metrics (e.g., age, numeric marks), maps country codes, and saves cleaned individual files.
3. **Loading (`generator.py`):** Merges all cleaned, fragmented files into ready datasets.


## 3.0 Directory Structure


```bash
AthletiStat
├── seasons
│   ├── queues
│   ├── processing
│   ├── datasets
│   └── completed.json
├── all-time
│   ├── queues
│   ├── processing
│   └── datasets
├── logs
│   ├── seasons
│   └── all-time
├── modules
│   ├── split_by_type.py
│   ├── 00-options.json
│   ├── scraper.py
│   ├── preprocessing.py
│   └── generator.py
├── run.py
├── requirements.txt
└── README.md
```



## 4.0 Dataset Description

The pipeline outputs final aggregated datasets into the `seasons/datasets/` and `all-time/datasets/` directories.

### 4.1 Output Files

* **Seasons Data:** `{year}_track_field_performances.csv` (Contains all top performances across all disciplines for a specific calendar year).
* **All-Time Data:** `top_track_field_performances_all_time.csv` (Contains the absolute historical top performances across all disciplines).

### 4.2 Data Dictionary

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



## 5.0 Installation and Setup

1. **Fork / Clone Repository**

2. **Install dependencies:**
It is recommended to use a virtual environment.
```bash
pip install -r requirements

```

3. **Verify Configuration:**
Ensure `modules/00-options.json` is present in your root directory. This file dictates the disciplines, age categories, and country mappings the scraper relies upon.

**Note:**
To use with actual multithreading (GIL removed), run any version of python >= 3.13.xt






## 6.0 Usage

The pipeline consists of three scripts that must be run sequentially. All scripts support the exact same CLI arguments:

* `--mode`: Target data to process (`seasons`, `all-time`, or `both`). Defaults to `both` (or `seasons` for the scraper).
* `--year`: Target year for seasons mode (Defaults to the current system year).
* `--workers`: *(Scraper only)* Maximum number of concurrent threads (Defaults to 12).

### 6.1 Step 1: Extract Data

Scrape raw data from World Athletics.

```bash
# Scrape the 2024 season
python modules/scraper.py --mode seasons --year 2024 --workers 15

# Scrape the all-time lists
python modules/scraper.py --mode all-time

```

### 6.2 Step 2: Transform Data

Clean and normalize the raw CSV files.

```bash
# Process the previously scraped 2024 data
python modules/reprocessing.py --mode seasons

# Process all-time data
python modules/preprocessing.py --mode all-time

```

### 6.3 Step 3: Generate Datasets

Concatenate the cleaned fragments into the final machine-learning-ready datasets.

```bash
# Generate the monolithic 2024 dataset
python modules/generator.py --mode seasons

# Generate the monolithic all-time dataset
python modules/generator.py --mode all-time

```

