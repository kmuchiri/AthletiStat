# Scraper Queue & Resume System

The `Scraper` class implements a persistent job queue system that allows scrape runs to be safely interrupted and resumed without duplicating or losing work.

---

## How It Works

Each scrape run is broken into a list of **jobs**. A job is a tuple representing one unique combination of parameters to scrape:

```python
(gender, age_category, discipline_slug, type_slug, output_dir, mode, year)
```

Before any threads are launched, the scraper writes the full job list to a **queue file** (JSON) on disk. As each job completes successfully, it is removed from the in-memory list and the file is updated atomically. If the process is killed mid-run, the queue file on disk reflects exactly which jobs are still pending.

On the next run for the same target, the scraper detects the existing queue file and resumes from it instead of rebuilding from scratch.

---

## Queue File Locations

| Mode | Queue File Path |
| --- | --- |
| Seasons | `queues/seasons/queue_seasons_{year}.json` |
| All-time | `queues/all-time/queue_all_time_{YYYY-MM-DD}.json` |

### All-time queue rotation

Because all-time lists are updated continuously, the all-time queue is keyed by **today's date**. On each new day, any queue files from previous dates are automatically deleted and a fresh queue is created. This ensures all-time scrapes always reflect the most current data when started fresh.

---

## Completed Seasons Registry

Historical seasons (any year that is not the current calendar year) are tracked in a separate registry:

```text
queues/seasons/completed_seasons.json
```

This file is a JSON array of year integers. When a full scrape of a historical year completes without errors, the year is appended to this list. On future runs, the scheduler checks this file first and **skips the year entirely** if it is already present.

```json
[2022, 2023, 2024]
```

> **Note:** The current year is never cached in `completed_seasons.json` because its data is still being updated live. It is always re-scraped from scratch.

---

## Job Failure Handling

A job returns `False` if an HTTP request fails after all configured retries are exhausted. In that case:

- The job is **not** removed from the in-memory list.
- The queue file on disk is **not** updated for that job.
- An error entry is written to the log file.

This means failed jobs automatically carry over to the next run without any manual intervention.

---

## Thread Safety

All file writes (queue updates, CSV saves, log writes) are protected by a `threading.Lock` to prevent race conditions when multiple threads complete jobs simultaneously.

---

## Request Retry Configuration

The `requests.Session` is pre-configured with `urllib3.util.retry.Retry`:

| Setting | Value |
| --- | --- |
| Total retries | 5 |
| Backoff factor | 1 (exponential: 1s, 2s, 4s, 8s, 16s) |
| Retry on status codes | 429, 500, 502, 503, 504 |
| Retry methods | GET, HEAD, OPTIONS |

Additionally, a `1.5s` sleep is enforced between paginated page requests within a single job to avoid overwhelming the server.

---

## Manually Resetting a Queue

To force a full re-scrape of a year that has already been completed:

1. Remove the year from `queues/seasons/completed_seasons.json`.
2. Delete the corresponding queue file if one exists: `queues/seasons/queue_seasons_{year}.json`.
3. Delete the raw output CSVs in `data/processing/output/seasons/{year}/` if you want clean output.
4. Re-run the scraper.

To reset an all-time scrape, simply delete the queue file for today:

```bash
rm queues/all-time/queue_all_time_$(date +%Y-%m-%d).json
```
