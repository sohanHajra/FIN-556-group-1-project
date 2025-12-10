#!/usr/bin/env bash
#
# Usage:
#   ./merge.sh iex.txt.gz nasdaq.txt.gz output.txt.gz
#
# Assumes each file has rows formatted as:
# packet_ts message_ts seq source side price size
#
# Example separator: space or tab (stable)
#
# Output is sorted by message_ts (column 2), keeping format identical.


# future consideration - add priority or consideration for exchange latency?
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <iex_file.gz> <nasdaq_file.gz> <output_file.gz>"
    exit 1
fi

IEX_FILE="$1"
NASDAQ_FILE="$2"
OUT_FILE="$3"

TMP_IEX=$(mktemp)
TMP_NASDAQ=$(mktemp)
TMP_MERGED=$(mktemp)

gzip -cd "$IEX_FILE" > "$TMP_IEX"
gzip -cd "$NASDAQ_FILE" > "$TMP_NASDAQ"

cat "$TMP_IEX" "$TMP_NASDAQ" \
  | sort -k2,2n \
  > "$TMP_MERGED"

gzip -c "$TMP_MERGED" > "$OUT_FILE"

# Cleanup
rm -f "$TMP_IEX" "$TMP_NASDAQ" "$TMP_MERGED"

echo "Merged order log written to: $OUT_FILE"
