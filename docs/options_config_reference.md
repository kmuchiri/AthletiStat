# options.json Configuration Reference

`options.json` is the central configuration file that drives which disciplines, age categories, genders, and country mappings the pipeline uses. It is a JSON array of option objects, each describing one configurable dimension.

---

## Top-Level Structure

```json
[
  { "name": "ageCategory", ... },
  { "name": "gender", ... },
  { "name": "region", ... },
  { "name": "disciplineCode", ... }
]
```

Each object has a `"name"` key that identifies its role. The scraper and preprocessor each consume specific named entries.

---

## Entries in options.json

### `ageCategory`

Defines valid age categories:

```json
{
  "name": "ageCategory",
  "values": [
    { "value": "senior", "label": "Senior" },
    { "value": "u20",    "label": "U20" },
    { "value": "u18",    "label": "U18" }
  ]
}
```

---

### `gender`

Defines valid genders (`male`, `female`, and `mixed` for mixed relays):

```json
{
  "name": "gender",
  "values": [
    { "value": "male",   "label": "Men" },
    { "value": "female", "label": "Women" },
    { "value": "mixed",  "label": "Mixed" }
  ]
}
```

---

### `region` (countries case)

The `region` entry contains a `cases` array with the `countries` case holding the 3-letter WA country codes and their full names.

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

**Used by:** `Preprocessor.loadCountryLookup()` for resolving `nationality` → `nat_full` and `venue_country`.

> **Note:** Country codes in this file are lowercase 3-letter WA codes (e.g., `jam`), not standard ISO 3166-1 alpha-3 (e.g., `JAM`). The preprocessor normalizes incoming nationality strings to lowercase before lookup.

---

### `disciplineCode`

This entry has a `cases` array keyed by `(gender, ageCategory)` pairs (including `mixed senior` and `mixed u20`). Each case lists all disciplines valid for that combination.

```json
{
  "name": "disciplineCode",
  "cases": [
    {
      "gender": "male",
      "ageCategory": "senior",
      "values": [
        {
          "value": "10230285",
          "disciplineNameUrlSlug": "50-metres",
          "typeNameUrlSlug": "sprints",
          "environment": "outdoor",
          "label": "50 Metres"
        },
        {
          "value": "10229552",
          "disciplineNameUrlSlug": "200-metres-short-track",
          "typeNameUrlSlug": "sprints",
          "environment": "indoor",
          "label": "200 Metres Short Track"
        },
        ...
      ]
    },
    ...
  ]
}
```

**Used by:** `Scraper.LoadMappings()` - builds mappings for `Scraper.BuildJobs()` to construct scraping jobs. Short track events carry `"environment": "indoor"` and retain their equivalent outdoor `typeNameUrlSlug`. 2026 race walk additions (`half-marathon-race-walk`, `marathon-race-walk`) and mixed relays (`gender: "mixed"`) are also included.

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
