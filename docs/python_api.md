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
