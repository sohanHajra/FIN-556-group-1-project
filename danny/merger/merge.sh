#!/bin/bash
set -e

if [ $# -ne 3 ]; then
    echo "Usage: $0 nasdaq.csv iex.csv output.csv"
    exit 1
fi

NASDAQ_FILE="$1"
IEX_FILE="$2"
OUT_FILE="$3"

HEADER="COLLECTION_TIME,SOURCE_TIME,SEQ_NUM,TICK_TYPE,MARKET_CENTER,SIDE,PRICE,SIZE,NUM_ORDERS,IS_IMPLIED,REASON,IS_PARTIAL"

TMP="${OUT_FILE}.tmp"
> "$TMP"

tail -n +2 "$NASDAQ_FILE" >> "$TMP"

tail -n +2 "$IEX_FILE" >> "$TMP"

{
    echo "$HEADER"
    sort -t',' -k2,2 "$TMP"
} > "$OUT_FILE"

rm "$TMP"

echo "Merged + sorted output saved to $OUT_FILE"
