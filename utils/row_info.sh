#!/bin/bash

# A script to print row count and file size of generated datasets

echo '# Dataset Information' > info.txt
echo "Filename, Row Count, File Size" >> info.txt

for csv_file in find . -name "*.csv";
do
    name = $(basename $csv_file)
    file_size = $(wc -c $csv_file)
    row_count = $(sed 1d $csv_file | wc -l )

    echo "$name, $row_count, $file_size" >> info.txt

done
    
    