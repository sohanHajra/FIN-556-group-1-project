#!/bin/bash

set -e

DOWNLOAD_DIR="./data/downloads/deepplus"
OUTPUT_DIR="./data/output/deepplus"
SYMBOLS=""
KEEP_PCAP=false
PARALLEL_JOBS=1
PYTHON_CMD="python3"
START_DATE=""
END_DATE=""

usage() {
    cat << EOF
Usage: $0 --start-date YYYY-MM-DD --end-date YYYY-MM-DD --download-dir PATH --output-dir PATH [--symbols SYMS] [--keep-pcap] [--parallel N]
EOF
    exit 1
}
while [[ $# -gt 0 ]]; do
    case $1 in
        --start-date) START_DATE="$2"; shift 2 ;;
        --end-date) END_DATE="$2"; shift 2 ;;
        --download-dir) DOWNLOAD_DIR="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --symbols) SYMBOLS="$2"; shift 2 ;;
        --keep-pcap) KEEP_PCAP=true; shift ;;
        --parallel) PARALLEL_JOBS="$2"; shift 2 ;;
        --python) PYTHON_CMD="$2"; shift 2 ;;
        *) usage ;;
    esac
done

[[ -z "$START_DATE" ]] || [[ -z "$END_DATE" ]] && usage
[[ -z "$DOWNLOAD_DIR" ]] || [[ -z "$OUTPUT_DIR" ]] && usage

mkdir -p "$DOWNLOAD_DIR" "$OUTPUT_DIR"

get_available_files() {
    curl -s "https://iextrading.com/api/1.0/hist" | \
        $PYTHON_CMD -c "
import sys, json, datetime
data = json.load(sys.stdin)
start = datetime.datetime.strptime('$START_DATE', '%Y-%m-%d')
end = datetime.datetime.strptime('$END_DATE', '%Y-%m-%d')
for date_str, feeds in data.items():
    file_date = datetime.datetime.strptime(date_str, '%Y%m%d')
    if start <= file_date <= end:
        for feed in feeds:
            if feed.get('feed') == 'DPLS':
                print(f\"{feed['date']}|{feed['link']}|{feed['size']}\")
"
}

download_file() {
    local url=$2
    local expected_size=$3
    local filename=$(basename "$url" | sed 's/?.*$//')
    local filepath="$DOWNLOAD_DIR/$filename"
    
    if [[ -f "$filepath" ]]; then
        local actual_size=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null)
        [[ "$actual_size" == "$expected_size" ]] && echo "$filepath" && return 0
        rm -f "$filepath"
    fi
    
    echo "Downloading: $filename"
    wget -q --show-progress -O "$filepath" "$url" || curl -# -L -o "$filepath" "$url"
    echo "$filepath"
}

parse_file() {
    local pcap_file=$1
    local filename=$(basename "$pcap_file" .gz | sed 's/.pcap$//')
    local output_csv="$OUTPUT_DIR/${filename}_parsed.csv"
    
    echo "Parsing: $(basename "$pcap_file")"
    
    if [[ "$pcap_file" == *.gz ]]; then
        if [[ -n "$SYMBOLS" ]]; then
            gunzip -c "$pcap_file" | $PYTHON_CMD parse_iex_deepplus.py /dev/stdin --symbols "$SYMBOLS" --output "$output_csv"
        else
            gunzip -c "$pcap_file" | $PYTHON_CMD parse_iex_deepplus.py /dev/stdin --output "$output_csv"
        fi
    else
        if [[ -n "$SYMBOLS" ]]; then
            $PYTHON_CMD parse_iex_deepplus.py "$pcap_file" --symbols "$SYMBOLS" --output "$output_csv"
        else
            $PYTHON_CMD parse_iex_deepplus.py "$pcap_file" --output "$output_csv"
        fi
    fi
    
    if [[ $? -eq 0 ]]; then
        echo "Success: $output_csv"
        [[ "$KEEP_PCAP" == false ]] && rm -f "$pcap_file"
    fi
}

echo "Fetching available files..."
FILES=$(get_available_files)

if [[ -z "$FILES" ]]; then
    echo "No DPLS files found for date range"
    exit 1
fi

echo "$FILES" | while IFS='|' read date url size; do
    pcap_file=$(download_file "$date" "$url" "$size")
    parse_file "$pcap_file"
done

echo "Complete"
