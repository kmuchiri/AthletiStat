# Scripts Reference

This document covers the utility scripts in `athletistat/scripts/`.

---

## `get_dataset_info.sh`

A lightweight Bash script that scans the `data/datasets/` directory and reports the **row count** and **file size** of every CSV dataset found. Results are written to `data/datasets/info.txt`.

### Usage

Run from the **project root directory**:

```bash
bash athletistat/scripts/get_dataset_info.sh
```

### Output

The script writes to `data/datasets/info.txt`, overwriting any previous contents.

**Example output:**

```text
Dataset Information
 
top_track_field_performances_all_time.csv has 652350 records and is 117 MB in size
2025_track_field_performances.csv has 1571793 records and is 294 MB in size
2026_track_field_performances.csv has 542416 records and is 101 MB in size
2002_track_field_performances.csv has 85850 records and is 14 MB in size
```

> **Note:** Row count excludes the header line (`sed 1d` strips it before `wc -l`).
> File size is reported in whole megabytes (`wc -c` byte count divided by 1,000,000, integer division).

### What It Searches

The script uses `find` to locate CSV files matching:

```text
./data/datasets/*.csv
```

This captures top-level datasets (per-year season files, the all-time file, combined files) but **not** files in subdirectories like `split_by_type/` or `split_by_discipline/`. To include splits, the glob pattern would need to be updated to `./data/datasets/**/*.csv`.

### Script Source

```bash
#!/bin/bash

# A script to print row count and file size of generated datasets

echo 'Dataset Information' > ./data/datasets/info.txt
echo " " >> ./data/datasets/info.txt

for csv_file in $(find . -wholename "./data/datasets/*.csv");
do
    echo $csv_file
    name=$(basename $csv_file)
    file_size=$(($(wc -c $csv_file | cut -d ' ' -f 1)/1000000))
    row_count=$(sed 1d $csv_file | wc -l)

    echo "$name has $row_count records and is $file_size MB in size " >> ./data/datasets/info.txt

done
```

### Known Limitations

- File size uses integer division so small files may report `0 MB`. Use `du -sh` for human-readable sizes if needed.
- Order of results is determined by `find`, which does not guarantee alphabetical order.
- Does not recurse into split subdirectories.
