#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 input.csv"
    exit 1
fi

INPUT="$1"
OUTPUT="${INPUT%.csv}.txt.gz"

tail -n +2 "$INPUT" | gzip > "$OUTPUT"

echo "Saved to $OUTPUT"
