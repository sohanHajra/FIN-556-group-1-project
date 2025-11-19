#!/bin/bash
set -e

while [[ $# -gt 0 ]]; do
    case $1 in
        --start-date)
            START_DATE="$2"
            shift 2
            ;;
        --end-date)
            END_DATE="$2"
            shift 2
            ;;
        --download-dir)
            DOWNLOAD_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --symbols)
            SYMBOLS="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$START_DATE" ] || [ -z "$END_DATE" ] || [ -z "$DOWNLOAD_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage:"
    echo "  $0 --start-date YYYY-MM-DD --end-date YYYY-MM-DD \\"
    echo "     --download-dir DIR --output-dir DIR [--symbols AAPL,TSLA]"
    exit 1
fi

mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$OUTPUT_DIR"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 "$SCRIPT_DIR/download_iex_pcaps.py" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --download-dir "$DOWNLOAD_DIR"

DEEP_DIR="$DOWNLOAD_DIR/DEEP"

if [ ! -d "$DEEP_DIR" ]; then
    echo "ERROR: $DEEP_DIR not found"
    exit 1
fi
echo "Starting to parse..."
for FILE in "$DEEP_DIR"/*.pcap.gz; do
    BASENAME=$(basename "$FILE" .pcap.gz)
    OUTFILE="$OUTPUT_DIR/${BASENAME}.out"

    if [ -z "$SYMBOLS" ]; then
        python3 "$SCRIPT_DIR/parse_compressed_iex_pcap.py" "$FILE" > "$OUTFILE"
    else
        python3 "$SCRIPT_DIR/parse_compressed_iex_pcap.py" "$FILE" --symbols "$SYMBOLS" > "$OUTFILE"
    fi
done

echo "Pipeline complete."

