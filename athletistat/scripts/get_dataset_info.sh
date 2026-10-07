#!/bin/bash

# A script to print row count and file size of generated datasets

echo 'Dataset Information' > ./data/datasets/dataset_info.txt
echo " " >> ./data/datasets/dataset_info.txt

dir_path="./data/datasets"

for csv_file in "$dir_path"/**/*.csv;
do
    echo $csv_file
    name=$(basename $csv_file)
    file_size=$(($(wc -c $csv_file | cut -d ' ' -f 1)/1000000))
    row_count=$(sed 1d $csv_file | wc -l)

    echo "$name has $row_count records and is $file_size MB in size " >> ./data/datasets/dataset_info.txt

done

