#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./preview.sh <csv_file>"
    exit 1
fi

head -20 "$1" | column -s, -t | less -S

