#!/bin/bash

# Usage:
#   ./combine_nasdaq.sh /path/to/csv_dir
#
# This script will merge all trade_*.csv files by date prefix (YYYYMMDD)
# Assumes filenames look like:
#   trade_USO_20250401T090000.csv
#   trade_USO_20250401T091000.csv
# etc.

DIR=$1

if [[ -z "$DIR" ]]; then
    echo "Error: Provide directory containing CSV files."
    exit 1
fi

cd "$DIR" || exit 1

# Extract unique date prefixes from filenames
dates=$(ls trade_*_*.csv | sed -E 's/.*_([0-9]{8})T[0-9]{6}\.csv/\1/' | sort -u)

for d in $dates; do
    echo "Merging files for date $d ..."

    # Output file
    outfile="merged_${d}.csv"

    # Remove old output if exists
    rm -f "$outfile"

    # Append all matching files in sorted order
    for f in $(ls trade_*_${d}T*.csv | sort); do
        cat "$f" >> "$outfile"
    done

    echo "Created: $outfile"
done

echo "Done."
