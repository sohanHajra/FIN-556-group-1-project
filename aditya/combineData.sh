#!/bin/bash

# Define the output file
output_file="tick.txt"

# Clear the output file if it already exists
> "$output_file"

# Flag to track if it's the first file
first_file=true

# Loop through each txt file in the current directory
for file in $(ls *.txt | sort); do
    if [ "$first_file" = true ]; then
        # For the first file, just append it without modification
        cat "$file" >> "$output_file"
        first_file=false
    else
        # For subsequent files, remove the first line and append
        tail -n +2 "$file" >> "$output_file"
    fi
done

echo "Files have been combined into $output_file"
