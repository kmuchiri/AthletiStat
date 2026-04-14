# Preprocessing: Discipline Normalization

The `Preprocessor` class applies normalization to raw `discipline` slugs scraped from World Athletics. This is necessary because the same underlying event can appear under multiple slug variants depending on age category or equipment weight.

---

## Why Normalization is Needed

World Athletics uses URL slugs like `decathlon-u20` or `shot-put-6kg` to distinguish age-restricted or equipment-specific versions of an event. For analysis purposes, it's useful to group all variants of `decathlon` together under a single canonical name.

The `normalized_discipline` column is computed during preprocessing and used as the grouping key for combined files and dataset splits.

---

## Normalization Logic (`normalize_discipline`)

Applied in order:

### 1. Manual alias lookup

A hardcoded dict maps known non-standard slugs to their canonical form:

```python
manual_aliases = {
    "100m-hurdles":   "100-metres-hurdles",
    "110m-hurdles":   "110-metres-hurdles",
    "400m-hurdles":   "400-metres-hurdles",
    "decathlon-u20":  "decathlon",
    "decathlon-boys": "decathlon",
    "heptathlon-girls": "heptathlon",
}
```

If the full slug matches a key exactly, it is replaced immediately.

### 2. Partial alias substitution

If the full slug doesn't match but *contains* a known alias as a substring, the alias substring is replaced within the slug. This handles composite slugs not covered by exact matches.

### 3. Regex suffix stripping

After alias resolution, a regex strips common age- and equipment-related suffixes from the end of the slug:

```python
re.sub(r"[-_](\d+(kg|g|cm)|u18|u20|senior|girls|boys)$", "", slug)
```

**Examples of suffixes stripped:**

| Raw Slug | Normalized |
| --- | --- |
| `shot-put-6kg` | `shot-put` |
| `discus-throw-1kg` | `discus-throw` |
| `javelin-throw-700g` | `javelin-throw` |
| `triple-jump-u18` | `triple-jump` |
| `high-jump-boys` | `high-jump` |
| `100-metres-senior` | `100-metres` |

---

## Event Type Classification (`track_field`)

Each combined file is also tagged with a `track_field` column based on its `type_slug`:

| `type_slug` | `track_field` value |
| --- | --- |
| `sprints` | `track` |
| `middlelong` | `track` |
| `hurdles` | `track` |
| `relays` | `track` |
| `road-running` | `track` |
| `race-walks` | `track` |
| `throws` | `field` |
| `jumps` | `field` |
| `combined-events` | `mixed` |
| *(any other)* | `unknown` |

---

## Mark Parsing (`parse_mark_to_number`)

Performance marks are stored as strings in varying formats. The preprocessor converts them to a uniform float in the `mark_numeric` column.

| Input Format | Conversion | Example Input | Example Output |
| --- | --- | --- | --- |
| Plain float/int | Direct cast | `9.58` | `9.58` |
| `M:SS.ss` | `min * 60 + sec` | `1:45.30` | `105.3` |
| `H:MM:SS.ss` | `h * 3600 + min * 60 + sec` | `2:01:39` | `7299.0` |
| Unparseable | Returns `inf` | `DNF`, `NM` | `inf` |

The `h` suffix (used in some hour-formatted marks) is stripped before parsing. Records with `mark_numeric = inf` sort to the bottom in ascending-sorted events and the top in descending-sorted, effectively isolating them without deletion.

---

## Sorting

After parsing, each combined file is sorted by `mark_numeric`:

| Event Category | Sort Direction | Rationale |
| --- | --- | --- |
| `sprints`, `middlelong`, `hurdles`, `relays`, `road-running`, `race-walks` | **Ascending** | Lower time = better |
| `throws`, `jumps`, `combined-events` | **Descending** | Higher distance/score = better |

---

## Adding a New Alias

If a new discipline slug appears that doesn't normalize correctly, add it to `manual_aliases` in `preprocessing.py`:

```python
self.manual_aliases = {
    ...
    "new-discipline-u20": "new-discipline",
}
```

Or, if it follows the standard suffix pattern (`-u20`, `-6kg`, etc.), the regex will handle it automatically.
