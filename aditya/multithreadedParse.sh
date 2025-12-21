#!/bin/bash

# Directory containing .zst files
INPUT_DIR="./data"

# Number of parallel processes (adjust to your CPU cores)
PARALLEL_JOBS=2

# Time range
START_TIME="000000"
END_TIME="120000"

ulimit -v $((32 * 1024 * 1024))  # 32 GB in KB
# Function to process a single file
process_file() {
    local zst_file="$1"

    # Skip if file does not exist
    [ -e "$zst_file" ] || { echo "File not found: $zst_file"; return; }

    # Extract base filename without extension
    local base_filename=$(basename "$zst_file" .zst)

    # Extract date (YYYYMMDD) from the filename
    local date=$(echo "$base_filename" | grep -oP '\d{8}')
    if [ -z "$date" ]; then
        echo "Could not extract date from filename $base_filename. Skipping..."
        return
    fi

    # Extract time (HHMMSS) from the filename
    local time=$(echo "$base_filename" | grep -oP 'T\d{6}' | tr -d 'T')

    # Skip files outside the time range
    if [[ "$time" < "$START_TIME" || "$time" > "$END_TIME" ]]; then
        echo "Skipping $base_filename (time $time not in range $START_TIME-$END_TIME)"
        return
    fi

    # Generate unique output filename based on input file
    local output_filename="tick_${date}_${time}.txt"

    echo "Processing $base_filename -> $output_filename"

    # Call your C++ parser
    ./a.out "$zst_file" "$output_filename"

    if [ $? -eq 0 ]; then
        echo "Processed $base_filename successfully."
    else
        echo "Error processing $base_filename"
    fi
}

export -f process_file
export START_TIME END_TIME

# Find all .zst files and run 4 in parallel
find "$INPUT_DIR" -maxdepth 1 -name '*.zst' | xargs -n 1 -P "$PARALLEL_JOBS" -I {} bash -c 'process_file "$@"' _ {}