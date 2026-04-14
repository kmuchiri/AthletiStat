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


    
    