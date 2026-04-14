# options.json Configuration Reference

`athletistat/options.json` is the central configuration file that drives which disciplines, age categories, genders, and country mappings the pipeline uses. It is a JSON array of option objects, each describing one configurable dimension.

---

## Top-Level Structure

```json
[
  { "name": "ageCategory", ... },
  { "name": "regionType", ... },
  { "name": "region", ... },
  { "name": "disciplineCode", ... },
  ...
]
```

Each object has a `"name"` key that identifies its role. The scraper and preprocessor each consume specific named entries.

---

## Entries Used by the Pipeline

### `ageCategory`

Defines the valid age categories. The scraper iterates over these when building jobs.

```json
{
  "name": "ageCategory",
  "values": [
    { "value": "senior", "label": "Senior" },
    { "value": "u20",    "label": "U20" },
    { "value": "u18",    "label": "U18" }
  ],
  "defaultValue": "senior"
}
```

**Used by:** `Scraper._load_mappings()` — age categories are embedded in the discipline mapping keys.

---

### `region` (countries case)

The `region` entry contains a `cases` array. The case where `"regionType": "countries"` holds the full world country list used to resolve ISO codes to full country names.

```json
{
  "name": "region",
  "cases": [
    {
      "regionType": "countries",
      "values": [
        { "value": "jam", "label": "Jamaica" },
        { "value": "usa", "label": "United States" },
        ...
      ]
    }
  ]
}
```

**Used by:** `Preprocessor.__init__()` — builds `self.country_lookup` (a `{code: label}` dict) for resolving `nationality` → `nat_full` and `venue_country`.

> **Note:** Country codes in this file are lowercase 3-letter WA codes (e.g., `jam`), not standard ISO 3166-1 alpha-3 (e.g., `JAM`). The preprocessor normalizes incoming nationality strings to lowercase before lookup.

---

### `disciplineCode`

This is the most critical entry. It has a `cases` array keyed by `(gender, ageCategory)` pairs. Each case lists all disciplines valid for that combination.

```json
{
  "name": "disciplineCode",
  "cases": [
    {
      "gender": "male",
      "ageCategory": "senior",
      "values": [
        {
          "disciplineNameUrlSlug": "100-metres",
          "typeNameUrlSlug": "sprints"
        },
        {
          "disciplineNameUrlSlug": "long-jump",
          "typeNameUrlSlug": "jumps"
        },
        ...
      ]
    },
    {
      "gender": "female",
      "ageCategory": "u20",
      "values": [ ... ]
    }
  ]
}
```

**Used by:** `Scraper._load_mappings()` — produces `self.mappings`, a dict of the form:

```python
{
    ("male", "senior"):   [("100-metres", "sprints"), ("long-jump", "jumps"), ...],
    ("female", "u20"):    [...],
    ...
}
```

This dict is what `Scraper.build_jobs()` iterates over to construct the full job list.

---

## Entries Not Used by the Pipeline

The following entries exist in `options.json` because the file is sourced directly from the World Athletics filter API response. They are not consumed by any pipeline code:

| Name | Description |
| --- | --- |
| `regionType` | Area/Countries/Groups selector |
| `environment` | Indoor/outdoor filter |
| `windReading` | Wind reading filter |
| `timing` | Timing method filter |
| `bestResultsOnly` | One-per-athlete vs. all results |
| `fiftyPercentRule` | Road race regularity filter |
| `oversizedTrack` | Oversized indoor track filter |
| `page` | Pagination range (handled dynamically by scraper) |
| `limit` | Results-per-page limit |

---

## Modifying the Configuration

### Targeting a subset of disciplines

To scrape only specific disciplines, edit the `values` arrays inside the relevant `disciplineCode` cases. Remove any `{ "disciplineNameUrlSlug": ..., "typeNameUrlSlug": ... }` entry you don't need.

### Adding a new discipline

If World Athletics adds a new discipline, find the appropriate `disciplineCode` case (by gender and age category) and add a new object:

```json
{ "disciplineNameUrlSlug": "new-discipline", "typeNameUrlSlug": "jumps" }
```

The `typeNameUrlSlug` must be one of the currently recognized event type slugs:

| Slug | Category | Sort Order |
| --- | --- | --- |
| `sprints` | Track | Ascending (lower = better) |
| `middlelong` | Track | Ascending |
| `hurdles` | Track | Ascending |
| `relays` | Track | Ascending |
| `road-running` | Track | Ascending |
| `race-walks` | Track | Ascending |
| `throws` | Field | Descending (higher = better) |
| `jumps` | Field | Descending |
| `combined-events` | Mixed | Descending |

The `Preprocessor` uses this slug to assign `track_field` classification and determine sort direction for `mark_numeric`.

### Adding a country code

If a country code appears in scraped data but resolves to `"Unknown"`, add it to the `countries` case under `region`:

```json
{ "value": "xyz", "label": "New Country" }
```
