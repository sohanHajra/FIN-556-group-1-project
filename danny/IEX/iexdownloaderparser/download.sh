#!/bin/bash
START_DATE="$1"
END_DATE="$2"

python3 src/download_iex_pcaps.py --start-date "$START_DATE" --end-date "$END_DATE" --download-dir data/iex_downloads
