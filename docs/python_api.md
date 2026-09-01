# Python API Reference

This document provides a reference for importing and using the core AthletiStat classes directly in Python.

---

## Python API

All core classes can be imported and used directly.

### Scraper

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

### Preprocessor

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

### DatasetGenerator

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

### DatasetSplitter

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

- `split_global/` - Full individual events and relay events as separate files.
- `split_by_type/{gender}/` - One CSV per event type (e.g., `sprints`, `jumps`, `hurdles`).
- `split_by_discipline/{gender}/` - One CSV per normalized discipline (e.g., `100-metres`, `long-jump`).
- `{gender}/relays/` - Relay events by discipline (excludes `dob` and `age_at_event`).

---

### SeasonsUpdate

Updates the combined seasons dataset in-place by removing and replacing data for a specific year without recompiling the entire dataset from scratch.

```python
from athletistat.core.seasons_update import SeasonsUpdate

# Full pipeline: scrapes, preprocesses, generates for 2026, and updates combined CSV
updater = SeasonsUpdate(year=2026, generate=True)
updater.run()

# In-place update assuming per-year CSV already exists on disk
updater = SeasonsUpdate(year=2026, generate=False)
updater.run()
```

---

### DatasetInfo

Generates detailed dataset statistics (file size, row count) and updates the summary table in the project README.

```python
from athletistat.scripts.fetch_info import DatasetInfo

info = DatasetInfo()
info.generate_info()     # Writes data/datasets/dataset_info.txt
info.generate_summary()  # Updates README.md between anchor tags
```

---

### Centralized Configuration (`cfg`)

AthletiStat loads tunables from `athletistat/config.toml` (with built-in defaults) into typed frozen dataclasses via `athletistat.config`:

```python
from athletistat.config import cfg

# Scraper settings
print(cfg.scraper.max_workers)          # 10
print(cfg.scraper.page_delay)           # 1.5
print(cfg.scraper.retry_total)          # 5
print(cfg.scraper.connect_timeout)      # 5
print(cfg.scraper.read_timeout)         # 30

# File paths
print(cfg.paths.dataset_dir)            # "data/datasets"
print(cfg.paths.scraper_output)         # "data/processing/output"
print(cfg.paths.queue_dir)              # "queues"

# Display settings
print(cfg.display.progress_bar_width)   # 30
```

---

### Console Utilities & ProgressBar

```python
from athletistat.console import ProgressBar, cprint, Colors, Symbols, header, divider, success, warn, error, info, step

# Thread-safe in-place progress bar
bar = ProgressBar(total=50, label="SEASONS 2026", width=30)
bar.update()       # Increments by 1 and redraws on current line
bar.update(5)      # Increments by 5
bar.finish()       # Finalizes at 100% and outputs newline

# Colored output
cprint("Operation complete", Colors.BRIGHT_GREEN, bold=True, prefix=Symbols.OK)
success("File saved successfully")
warn("Job remains in queue")
```
