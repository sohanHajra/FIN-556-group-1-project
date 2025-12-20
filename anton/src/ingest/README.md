# NASDAQ ITCH Processing Pipeline

Complete guide to process NASDAQ ITCH data from PCAP files to Strategy Studio tick and trade files.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Setup and Configuration](#setup-and-configuration)
- [Usage Guide](#usage-guide)
- [Batch Processing](#batch-processing)
- [File Combining](#file-combining)
- [Timestamp Conversion](#timestamp-conversion)
- [Output Format](#output-format)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

- **Python 3.8+**
- **Operating System**: Windows, Linux, or macOS
- **Disk Space**: Sufficient space for decompressed PCAP files (typically 3-5x compressed size)

---

## Installation

### Install Dependencies

From the `anton/` directory:

```bash
# Install all required packages
pip install -r src/requirements.txt
```

Or install core dependencies individually:

```bash
pip install zstandard dpkt itchfeed pandas
```

**Key Dependencies:**
- `zstandard`: For decompressing `.zst` files
- `dpkt`: For parsing PCAP files
- `itchfeed`: For parsing NASDAQ ITCH 5.0 messages
- `pandas`: For data manipulation (used in combining/UTC conversion)

---

## Quick Start

### One-Command Pipeline

The simplest way to process NASDAQ data:

```bash
# Navigate to anton directory
cd anton

# Process a .zst file (auto-detects date from filename)
python process.py file.pcap.zst USO
```

**Example:**
```bash
python process.py ny4-xnas-tvitch-a-20250401T083000.pcap.zst USO
```

This automatically:
1. Decompresses `.zst` → `.pcap`
2. Converts `.pcap` → `.itch` (MoldUDP64 extraction)
3. Converts `.itch` → Strategy Studio ticks (L3 to L2 conversion)

**Output:** `output/tick_messages/YYYYMMDD/tick_USO_YYYYMMDDTHHMMSS.csv`

---

## Setup and Configuration

### Directory Structure

The pipeline expects data organized as:

```
anton/
├── data/
│   └── nasdaq_pcaps/
│       ├── 20250401/
│       │   ├── ny4-xnas-tvitch-a-20250401T070000.pcap.zst
│       │   ├── ny4-xnas-tvitch-a-20250401T071000.pcap.zst
│       │   └── ...
│       └── 20250402/
│           └── ...
├── output/
│   ├── pcap_decompressed/
│   ├── itch_converted_pcaps/
│   ├── tick_messages/
│   └── trade_messages/
└── src/
    └── ingest/
        └── [scripts]
```

### Configuration Options

#### Option 1: Environment Variable (Recommended)

Set the environment variable to point to your data directory:

```bash
# Linux/Mac
export NASDAQ_PCAPS_DIR=/path/to/nasdaq_pcaps

# Windows (PowerShell)
$env:NASDAQ_PCAPS_DIR="C:\path\to\nasdaq_pcaps"

# Windows (CMD)
set NASDAQ_PCAPS_DIR=C:\path\to\nasdaq_pcaps
```

#### Option 2: Edit config.py

Edit `src/ingest/config.py`:

```python
# Change from:
NASDAQ_PCAPS_DIR = PROJECT_ROOT / "data" / "nasdaq_pcaps"

# To your absolute path:
NASDAQ_PCAPS_DIR = Path("/path/to/nasdaq_pcaps")
```

**Note:** Environment variable takes priority over config file setting.

### Verify Configuration

Check that the path is configured correctly:

```bash
python -c "from src.ingest.config import NASDAQ_PCAPS_DIR; print(f'Data directory: {NASDAQ_PCAPS_DIR}')"
```

---

## Usage Guide

### Basic Usage

#### Generate Depth-by-Price Ticks (Default)

```bash
python process.py file.pcap.zst USO
```

#### Generate Trade Ticks Only

```bash
python process.py file.pcap.zst USO --trades
```

#### Generate Both Ticks and Trades

```bash
python process.py file.pcap.zst USO --both
```

### Input File Location

**Option 1: Place files in default directory**
```bash
# Put files in: anton/data/nasdaq_pcaps/
python process.py file.pcap.zst USO
```

**Option 2: Use full path**
```bash
python process.py C:/path/to/file.pcap.zst USO
```

### Output Locations

All outputs are organized by date in the `output/` directory:

- **Ticks**: `output/tick_messages/YYYYMMDD/tick_SYMBOL_YYYYMMDDTHHMMSS.csv`
- **Trades**: `output/trade_messages/YYYYMMDD/trade_SYMBOL_YYYYMMDDTHHMMSS.csv`
- **PCAPs**: `output/pcap_decompressed/YYYYMMDD/filenameTtime.pcap`
- **ITCH**: `output/itch_converted_pcaps/YYYYMMDD/filenameTtime.itch`

### Common Options

#### With Explicit Date

```bash
python process.py file.pcap SPY --date 2025-04-01
```

#### Custom Output Directory

```bash
python process.py file.pcap.zst USO --output ./custom_output
```

#### Performance Options

```bash
# Show progress every 100k messages (default)
python process.py file.pcap.zst USO --progress 100000

# Disable progress updates
python process.py file.pcap.zst USO --progress 0
```

#### Skip Steps (if intermediate files exist)

```bash
# Skip decompression (use existing .pcap)
python process.py file.pcap.zst USO --skip-decompress

# Skip both decompression and PCAP conversion
python process.py file.pcap.zst USO --skip-decompress --skip-pcap
```

### Mode Options

- **Default** (no flag): Depth-by-price ticks only
- `--trades`: Trade ticks only
- `--both`: Both depth-by-price and trade ticks

### Examples

```bash
# Most common: depth-by-price ticks
python process.py ny4-xnas-tvitch-a-20250401T083000.pcap.zst USO

# Trade ticks only
python process.py file.pcap.zst SPY --trades

# Both types with explicit date
python process.py file.pcap.zst USO --both --date 2025-04-01
```

---

## Batch Processing

Process multiple `.zst` files across a date range:

```bash
# Process all files from 2025-04-01 to 2025-04-02 for USO
python batch_process.py USO 20250401 20250402

# Process trades only for a single day
python batch_process.py SPY 20250401 20250401 --trades

# Process both ticks and trades for multiple days
python batch_process.py USO 20250401 20250405 --both

# Skip steps if intermediate files exist (faster re-runs)
python batch_process.py USO 20250401 20250402 --skip-decompress --skip-pcap
```

**Note**: Batch processing expects files organized as:
```
data/nasdaq_pcaps/
├── 20250401/
│   ├── ny4-xnas-tvitch-a-20250401T070000.pcap.zst
│   ├── ny4-xnas-tvitch-a-20250401T071000.pcap.zst
│   └── ...
└── 20250402/
    └── ...
```

---

## File Combining

After processing multiple files, combine them into single files per day:

```bash
# Combine files for a single day
python combine_csv.py 20250401

# Combine files for a date range
python combine_csv.py 20250401 20250402

# Combine only tick files
python combine_csv.py 20250401 --ticks-only

# Combine only trade files
python combine_csv.py 20250401 --trades-only

# Don't sort by timestamp (faster, but files must already be in order)
python combine_csv.py 20250401 --no-sort
```

**Output**: 
- `output/combined/combined_tick_YYYYMMDD.csv`
- `output/combined/combined_trade_YYYYMMDD.csv`

Files are automatically sorted by timestamp to maintain chronological order.

---

## Timestamp Conversion

Convert timestamps from EDT/EST to UTC:

```bash
# Process all files in output/combined/
python utc_nasdaq_timestamp_converter.py

# Process a specific file
python utc_nasdaq_timestamp_converter.py --input output/combined/combined_tick_20250401.csv

# Process all files for a specific date
python utc_nasdaq_timestamp_converter.py --date 20250401

# Custom input and output directories
python utc_nasdaq_timestamp_converter.py --input-dir ./combined --output-dir ./converted
```

**Output**: `output/converted_combined/` with UTC timestamps (adds 4 hours offset)

---

## Output Format

### Depth-by-Price (P) Ticks

The tick files contain Strategy Studio depth-by-price format:

**Columns:**
- `COLLECTION_TIME`: UTC timestamp (`YYYY-MM-DD HH:MM:SS.ffffff`)
- `SOURCE_TIME`: Same as COLLECTION_TIME
- `SEQ_NUM`: Synthetic sequence number
- `TICK_TYPE`: "P" (depth-by-price)
- `MARKET_CENTER`: "NASDAQ"
- `SIDE`: 1=bid, 2=ask
- `PRICE`: Price level (4 decimal precision)
- `SIZE`: Aggregated size at price level
- `NUM_ORDERS`: Number of orders at price level
- `IS_IMPLIED`: 0 (not implied)
- `REASON`: 1=UNATTRIBUTED, 2=ADD_ORDER, 3=PARTIAL_CANCEL, 4=FULL_CANCEL, 5=EXECUTED, 8=CANCEL_REPLACE
- `IS_PARTIAL`: 0 (not partial)

### Trade (T) Ticks

The trade files contain Strategy Studio trade format:

**Columns:**
- `COLLECTION_TIME`: UTC timestamp
- `SOURCE_TIME`: Same as COLLECTION_TIME
- `SEQ_NUM`: Synthetic sequence number
- `TICK_TYPE`: "T" (trade)
- `MARKET_CENTER`: "NASDAQ"
- `PRICE`: Trade price (4 decimal precision)
- `SIZE`: Trade size (shares)
- `FEED_TYPE`: 1=consolidated (optional)
- `SIDE`: 1=BUY, -1=SELL, ""=UNKNOWN (optional)
- `TRADE_COND_TYPE`: "" (optional)
- `TRADE_COND`: "OPEN"/"CLOSE"/"HALT" for cross trades (optional)

---

## Individual Scripts

If you need to run pipeline steps separately:

### Step 1: Decompress

```bash
python zst_to_pcap.py file.pcap.zst -o file.pcap
```

### Step 2: Convert PCAP to ITCH

```bash
python pcap_to_itch_converter.py file.pcap file.itch
```

### Step 3: Convert ITCH to Ticks

```bash
# Depth-by-price ticks
python nasdaq_ss_tick_builder.py file.itch SYMBOL YYYY-MM-DD -o tick_SYMBOL_YYYYMMDD.txt

# Trade ticks
python nasdaq_ss_trade_builder.py file.itch SYMBOL YYYY-MM-DD -o trade_SYMBOL_YYYYMMDD.txt
```

---

## Troubleshooting

### Date Not Detected

**Problem:** Script can't auto-detect date from filename

**Solution:** Use `--date` flag:
```bash
python process.py file.pcap.zst USO --date 2025-04-01
```

### File Not Found

**Problem:** Script can't find input file

**Solutions:**
1. Check that file is in `data/nasdaq_pcaps/` directory
2. Use full path: `python process.py C:/full/path/to/file.pcap.zst USO`
3. Verify `NASDAQ_PCAPS_DIR` configuration (see Setup section)

### Missing Library

**Problem:** Import errors when running scripts

**Solution:** Install dependencies:
```bash
pip install -r src/requirements.txt
```

### Disk Quota Exceeded

**Problem:** Running out of disk space during processing

**Solutions:**
1. Use `--skip-decompress` if you already have `.pcap` files
2. Use `--skip-pcap` if you already have `.itch` files
3. Clean up intermediate files after processing
4. Process files in smaller batches

### Processing Too Slow

**Problem:** Pipeline is running slowly

**Solutions:**
1. Ensure optimized mode is enabled (default)
2. Use `--skip-*` flags to skip steps that already completed
3. Process smaller date ranges
4. Check system resources (CPU, disk I/O)

---

## Related Tools

After processing data, you may want to:

- **Visualize the results**: Use `src/visualize/event_stream_visualizer.py` to interactively explore tick and trade data (see `src/visualize/README.md`)
- **Merge with IEX data**: Use scripts in `danny/merger/` to combine NASDAQ and IEX data for multi-venue strategies
- **Convert for Strategy Studio**: Use `danny/merger/merged_data/to_txtgz.sh` to convert CSV files to `.txt.gz` format

For more details on the complete pipeline, see the main project `README.md`.

---

## Help

Get help for any script:

```bash
python process.py --help
python batch_process.py --help
python combine_csv.py --help
python utc_nasdaq_timestamp_converter.py --help
python nasdaq_ss_tick_builder.py --help
python nasdaq_ss_trade_builder.py --help
```
