#!/bin/bash

# A script to print row count and file size of generated datasets

dir_path="./data/datasets"
output_file="./data/datasets/dataset_info.txt"

shopt -s globstar nullglob

table=$(
    for csv_file in "$dir_path"/**/*.csv; do
        [ -f "$csv_file" ] || continue
        name=$(basename "$csv_file")
        bytes=$(wc -c < "$csv_file")
        file_size=$((bytes / 1000000))
        lines=$(wc -l < "$csv_file")
        row_count=$((lines > 0 ? lines - 1 : 0))
        printf "%d\t%s\t%s\t%s MB\n" "$bytes" "$name" "$row_count" "$file_size"
    done | sort -n | cut -f2- | (printf "Filename\tRowCount\tSize\n"; cat) | column -t -s $'\t'
)

echo 'Dataset Information' > "$output_file"
echo "" >> "$output_file"
echo "$table" >> "$output_file"

echo "$table"
