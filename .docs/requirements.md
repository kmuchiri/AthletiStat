
# Software Requirements Specification: AthletiStat

## 1. Introduction

### 1.1 Purpose

AthletiStat an automated end-to-end ETL (Extract, Transform, Load) system designed to scrape, clean, and aggregate track and field performance data from the official World Athletics database. The system outputs large datasets (records of over 100,000 per subdataset)

### 1.2 Scope

The system consists of three distinct Python modules executed sequentially:

1. **Extraction (`scraper.py`):** Fetches raw tabular data from World Athletics web endpoints.
2. **Transformation (`preprocessing.py`):** Cleans, standardizes, and enriches the raw extracted records.
3. **Loading (`generator.py`):** Merges the fragmented, cleaned data files into monolithic, comprehensive datasets based on the execution mode (Seasons or All-Time).

---

## 2. System Architecture

The system follows a strict linear data flow architecture. Data originates from the World Athletics, lands in a `processing/output/` directory as raw CSVs, moves to a `processing/combined/` directory as cleaned CSVs, and is finally aggregated into the `datasets/` directory as monolithic CSVs.

The system is strictly bifurcated into two independent namespaces to prevent data collision:

* **Seasons Data:** Historical and active yearly records (e.g., 2024, 2025).
* **All-Time Data:** Historical absolute top-performance lists.

---

## 3. Functional Requirements

### 3.1 Global System Interfaces & Controls

* **Command Line Interface (CLI):** All three modules must support an identical CLI interface utilizing Python's `argparse` library.
* **Execution Modes:** The CLI must accept a `--mode` argument supporting three states:
* `seasons`: Executes logic exclusively for specific calendar years.
* `all-time`: Executes logic exclusively for all-time historical lists.
* `both`: Executes `seasons` logic followed sequentially by `all-time` logic.


* **Configuration:** The system must read from a centralized `modules/00-options.json` file to dictate URL generation, discipline slugs, and ISO country code mappings.

### 3.2 Stage 1: Extraction (Scraper Module)

The scraper module is responsible for secure, fault-tolerant data acquisition.

* **Data Targeting:** Must extract 14 distinct data points per row from the `.records-table` HTML elements (Rank, Mark, Wind, Competitor, DOB, Nationality, Position, Venue, Date, Result Score, Discipline, Type, Sex, Age Category).

* **State Management & Queueing:**
    * Must implement a JSON-based queue (`queue_seasons_{year}.json` or `queue_all_time_{date}.json`) to track pending scraping jobs.
    * Must automatically resume incomplete queues if the script is interrupted.
    * Should skip historical years completely if logged in a `completed_seasons.json` file.
    * Must bypass the queue system entirely when targeting the *current* calendar year, ensuring the scraper always fetches up-to-date data.
    ---
    * Should extract failed jobs from logs and restart them to ensure data integrity incase the scraper fails to fetch data from even 1 page.  
    ---


* **File I/O:** Must output raw, uncleaned `.csv` files into `{mode}/processing/output/{year}/{gender}/` (Seasons) or `all-time/processing/output/{gender}/` (All-Time).

### 3.3 Stage 2: Transformation (Preprocessor Module)

The preprocessor module normalizes the raw data for analysis.

* **Data Cleaning & Enrichment:**
    * *Discipline Normalization:* Standardize URL slugs into readable names (e.g., replacing "100m-hurdles" with "100-metres-hurdles" and stripping weight/age suffixes like "7.26kg" or "u20").
    * *Categorization:* Append a `track_field` column designating the event as `track`, `field`, or `mixed` based on predefined sets.
    * *Numeric Parsing (`mark_numeric`):* Convert formatted time strings (e.g., `1:45.30`) into pure numeric seconds (e.g., `105.30`). Non-time marks (e.g., meters) must be cast directly to floats.
    * *Date & Age Math:* Parse date strings into `datetime` objects. Calculate and append `age_at_event` by subtracting `dob` from the event `date`. Append the calendar `season` based on the event date.
    * *Olympic Code Country Name Mapping:* Extract 3-letter country codes from the venue string and map them to full country names using `options.json`.


* **Sorting Logic:** Must independently sort records based on the event type (ascending values for track events; descending values for field events).
* **File I/O:** Must output cleaned `.csv` files into `{mode}/processing/combined/{year}/{gender}/` or `all-time/processing/combined/{gender}/`.

### 3.4 Stage 3: Loading (Generator Module)

The generator module is the final aggregation step.

* **Dynamic Aggregation:** Must dynamically traverse the `combined` directories, loading all preprocessed CSVs into memory using `pandas`.
* **Seasons Output:** Must generate a single, monolithic CSV per calendar year combining all genders, ages, and disciplines.
* *Naming Convention:* `{mode}/datasets/{year}_track_field_performances.csv`.


* **All-Time Output:** Must generate a single master CSV containing the top absolute performances across all categories.
* *Naming Convention:* `all-time/datasets/top_track_field_performances_all_time.csv`.


* **Empty State Handling:** Must print console warnings and exit gracefully if no combined CSVs are found, rather than crashing.

---

## 4. Non-Functional Requirements

### 4.1 Concurrency & Performance

* The scraper must utilize Python's `ThreadPoolExecutor` to process multiple HTTP requests concurrently.
* Thread counts must be configurable via a `--workers` CLI flag (defaulting to 12).

### 4.2 Reliability & Fault Tolerance

* **Network Resilience:** The HTTP client (`requests.Session`) must implement `urllib3` retry adapters, executing up to 5 retries with exponential backoff for specific server errors (HTTP 429, 500, 502, 503, 504).
* **Thread Safety:** All file write operations during the multithreaded scraping phase must be protected by `threading.Lock()` to prevent race conditions, file corruption, or skipped records.
* **Server Politeness:** Threads must enforce a minimum 2-second sleep (`time.sleep(2)`) between pagination requests to avoid overwhelming the World Athletics servers and triggering IP bans.

---


## 5. Technology Stack

* **Language:** Python 3.13.x - 3.14.x
* **Core Libraries (Standard):** `os`, `json`, `time`, `threading`, `argparse`, `datetime`, `concurrent.futures`, `collections`, `re`, `glob`
* **Third-Party Libraries:**
    * `requests` (HTTP client and session management)
    * `beautifulsoup4` (DOM traversal and HTML parsing)
    * `pandas` (Vectorized data manipulation, CSV formatting, and concatenation)
    * `urllib3` (Advanced HTTP retry logic)


---
