#!/bin/bash

# A script to print row count and file size of generated datasets

echo 'Dataset Information' > ./data/datasets/dataset_info.txt
echo " " >> ./data/datasets/dataset_info.txt

for csv_file in $(find ./data/datasets -type f \( -name "top_track_field_performances_all_time.csv" -o -name "combined_track_field_performances_*.csv" \));
do
    echo $csv_file
    name=$(basename $csv_file)
    file_size=$(($(wc -c $csv_file | cut -d ' ' -f 1)/1000000))
    row_count=$(sed 1d $csv_file | wc -l)

    echo "$name has $row_count records and is $file_size MB in size " >> ./data/datasets/dataset_info.txt

done

# Update README.md with the generated info inside a markdown code block
echo "Updating README.md with dataset information..."
if [ -f "README.md" ]; then
    awk '
      /<!-- START_DATASET_INFO -->/ {
        print
        print "```text"
        system("cat ./data/datasets/dataset_info.txt")
        print "```"
        print_info=1
        next
      }
      /<!-- END_DATASET_INFO -->/ { print_info=0 }
      !print_info { print }
    ' README.md > README.tmp && mv README.tmp README.md
    echo "README.md updated!"
else
    echo "README.md not found in the current directory."
fi