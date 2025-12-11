#!/bin/bash
set -e

if [ $# -ne 3 ]; then
    echo "Usage: $0 nasdaq.csv iex.csv output.csv"
    exit 1
fi

NASDAQ_FILE="$1"
IEX_FILE="$2"
OUT_FILE="$3"

TMP_OUT="${OUT_FILE}.tmp"

> "$TMP_OUT"

tail -n +2 "$IEX_FILE" | \
awk -F',' '{
    pkt=$1
    msg=$2
    seq=$3
    source="IEX"
    side=$5
    price=$6
    size=$7

    # Convert IEX: 2 → -1 to unify convention
    if (side == 2) side = -1

    print pkt "," msg "," seq "," source "," side "," price "," size
}' >> "$TMP_OUT"

tail -n +2 "$NASDAQ_FILE" | \
awk -F',' '{
    collection_time = $1
    source_time     = $2
    seq             = $3
    price           = $6
    size            = $7
    side            = $9    # Nasdaq already uses 1 and -1
    source          = "NASDAQ"

    print collection_time "," source_time "," seq "," source "," side "," price "," size
}' >> "$TMP_OUT"

echo "packet_timestamp,message_timestamp,seq_num,source,side,price,size" > "$OUT_FILE"

sort -t',' -k2,2 "$TMP_OUT" >> "$OUT_FILE"

rm "$TMP_OUT"
