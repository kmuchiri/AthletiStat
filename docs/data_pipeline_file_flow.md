# Data Pipeline: File Flow Reference

This document traces exactly how data moves through the pipeline from raw scrape to final dataset, including every intermediate directory and file naming convention.

---

## Stage 1 — Extraction (`scraper.py`)

**Input:** `athletistat/options.json` (discipline/gender/age-category config)

**Output directory:** `data/processing/output/{mode}/`

### Seasons mode

```text
data/processing/output/seasons/
└── {year}/
    ├── male/
    │   └── {year}_{type_slug}_{discipline_slug}_{age_category}.csv
    └── female/
        └── {year}_{type_slug}_{discipline_slug}_{age_category}.csv
```

**Example:**

```text
data/processing/output/seasons/2025/male/2025_sprints_100-metres_senior.csv
data/processing/output/seasons/2025/female/2025_jumps_long-jump_u20.csv
```

### All-time mode

```text
data/processing/output/all-time/
├── male/
│   └── {type_slug}_{discipline_slug}_{age_category}.csv
└── female/
    └── {type_slug}_{discipline_slug}_{age_category}.csv
```

**Example:**

```text
data/processing/output/all-time/male/sprints_100-metres_senior.csv
```

### Raw file columns

| Column | Source |
| --- | --- |
| `rank` | Column 0 of scraped table row |
| `mark` | Column 1 |
| `wind` | Column 2 |
| `competitor` | Column 3 |
| `dob` | Column 4 |
| `nationality` | Column 5 |
| `position` | Column 6 |
| `venue` | Column 8 (column 7 is skipped) |
| `date` | Column 9 |
| `result_score` | Column 10 |
| `discipline` | Injected from `discipline_slug` |
| `type` | Injected from `type_slug` |
| `sex` | Injected from `gender` loop variable |
| `age_cat` | Injected from `age_category` loop variable |

> Column 7 is the athlete's country flag/image element and is skipped.

---

## Stage 2 — Transformation (`preprocessing.py`)

**Input:** `data/processing/output/{mode}/`

**Output directory:** `data/processing/combined/{mode}/`

The preprocessor **groups** raw files by `(year, gender, type_slug, normalized_discipline)` key, concatenates all files sharing the same key, applies transformations, and saves one combined file per key.

### Seasons mode

```text
data/processing/combined/seasons/
└── {year}/
    └── {year}_{gender}_{type_slug}_{normalized_discipline}.csv
```

**Example:**

```text
data/processing/combined/seasons/2025/2025_male_sprints_100-metres.csv
```

### All-time mode

```text
data/processing/combined/all-time/
└── {gender}_{type_slug}_{normalized_discipline}.csv
```

**Example:**

```text
data/processing/combined/all-time/female_jumps_long-jump.csv
```

### Transformations applied at this stage

| Column Added | Logic |
| --- | --- |
| `normalized_discipline` | Aliases resolved, age/weight suffixes stripped from `discipline` slug |
| `track_field` | Assigned from `type_slug`: `track`, `field`, or `mixed` |
| `mark_numeric` | `mark` string parsed to float (MM:SS → seconds) |
| `nat_full` | `nationality` (lowercase) looked up in country registry |
| `venue_country` | 3-letter code extracted from `venue` parentheses, then resolved |
| `dob` | Parsed from `"DD Mon YYYY"` to `datetime` |
| `date` | Parsed from `"DD Mon YYYY"` to `datetime` |
| `age_at_event` | `(date - dob).days // 365` |
| `season` | `date.year` |

The combined file is also **sorted by `mark_numeric`** — ascending for timed events (track), descending for measured events (field/combined).

---

## Stage 3 — Loading (`generator.py`)

**Input:** `data/processing/combined/{mode}/`

**Output directory:** `data/datasets/{mode}/`

### `DatasetGenerator` — per-year aggregation

Seasons: reads all combined CSVs in each year subdirectory and merges them into one file per year.

```text
data/datasets/seasons/
└── {year}_track_field_performances.csv
```

All-time: reads all combined CSVs in the flat `all-time/` directory and merges into one file, deduplicating rows.

```text
data/datasets/all-time/
└── top_track_field_performances_all_time.csv
```

### `DatasetGenerator.combine_seasons()` — multi-year merge

Reads all per-year files in `data/datasets/seasons/` and concatenates them. The year range is inferred from the subdirectory names in `data/processing/combined/seasons/`.

```text
data/datasets/seasons/
└── combined_track_field_performances_{min_year}_{max_year}.csv
```

### `DatasetSplitter` — granular splits

Operates on the final aggregated files. Splits are produced at three levels of granularity, under the same base directory:

```text
data/datasets/{mode}/
├── split_global/
│   ├── individual_events[_{year_range}].csv
│   └── relay_events[_{year_range}].csv
├── split_by_type/
│   ├── male/
│   │   ├── sprints[_{year_range}].csv
│   │   ├── jumps[_{year_range}].csv
│   │   └── ...
│   └── female/
│       └── ...
├── split_by_discipline/
│   ├── male/
│   │   ├── 100-metres[_{year_range}].csv
│   │   └── ...
│   └── female/
│       └── ...
└── {gender}/
    └── relays/
        └── {discipline}[_{year_range}].csv
```

For **seasons** datasets, filenames include a year suffix derived from the `season` column:

- Single year: `sprints_2025.csv`
- Multi-year range: `sprints_2022-2025.csv`

Relay splits drop the `dob` and `age_at_event` columns (not applicable for team events).

---

## Summary Table

| Stage | Input | Output |
| --- | --- | --- |
| 1. Scrape | World Athletics website | `data/processing/output/` |
| 2. Transform | `data/processing/output/` | `data/processing/combined/` |
| 3a. Generate | `data/processing/combined/` | `data/datasets/` (per-year or all-time) |
| 3b. Combine | `data/datasets/seasons/` | `data/datasets/seasons/combined_*.csv` |
| 3c. Split | `data/datasets/{mode}/*.csv` | `data/datasets/{mode}/split_*/` |
