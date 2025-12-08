# NASDAQ ITCH Processing Pipeline

Quick guide to process NASDAQ ITCH data from PCAP files to Strategy Studio tick files.

## Quick Start

### One-Command Pipeline

```bash
python process_nasdaq.py input_file.pcap.zst SYMBOL
```

**Example:**
```bash
python process_nasdaq.py ny4-xnas-tvitch-a-20250401T083000.pcap.zst USO
```

This automatically:
1. Decompresses `.zst` → `.pcap`
2. Converts `.pcap` → `.itch`
3. Converts `.itch` → Strategy Studio ticks

**Output:** `tick_USO_20250401.txt` in `data/nasdaq_pcaps/`

---

## Installation

```bash
pip install zstandard dpkt
```

---

## Usage

### Basic Examples

```bash
# Process .zst file (auto-detects date from filename)
python process_nasdaq.py file.pcap.zst SPY

# Process .pcap file with explicit date
python process_nasdaq.py file.pcap USO --trade-date 2025-04-01

# Custom output directory
python process_nasdaq.py file.pcap.zst SPY --output-dir ./output
```

### Input File Location

Put your input files (`.zst` or `.pcap`) in:
```
data/nasdaq_pcaps/
```

Or use full path:
```bash
python process_nasdaq.py C:/path/to/file.pcap.zst SYMBOL
```

### Output Files

All outputs go to `data/nasdaq_pcaps/` by default:
- `file.pcap` (intermediate)
- `file.itch` (intermediate)
- `tick_SYMBOL_YYYYMMDD.txt` (final output)

---

## Advanced Options

```bash
python process_nasdaq.py file.pcap.zst USO \
    --trade-date 2025-04-01 \
    --udp-port 50000 \
    --progress-interval 50000 \
    --output-dir ./custom_output
```

### Skip Steps (if files already exist)

```bash
# Skip decompression (use existing .pcap)
python process_nasdaq.py file.pcap.zst USO --skip-decompress

# Skip both decompression and PCAP conversion
python process_nasdaq.py file.pcap.zst USO --skip-decompress --skip-pcap-to-itch
```

---

## Individual Scripts

If you need to run steps separately:

```bash
# Step 1: Decompress
python zst_to_pcap.py file.pcap.zst -o file.pcap

# Step 2: Convert PCAP to ITCH
python pcap_to_itch_converter.py file.pcap file.itch

# Step 3: Convert ITCH to ticks
python nasdaq_ss_tick_builder.py file.itch SYMBOL YYYY-MM-DD -o tick_SYMBOL_YYYYMMDD.txt
```

---

## Configuration

Edit `config.py` to change default paths:

```python
# Input directory (where .zst/.pcap files are)
NASDAQ_PCAPS_DIR = PROJECT_ROOT / "data" / "nasdaq_pcaps"

# Output directory (where results go)
OUTPUT_DIR = PROJECT_ROOT / "data" / "nasdaq_pcaps"
```

---

## Troubleshooting

**Date not detected?** Use `--trade-date YYYY-MM-DD`

**File not found?** Check that input file is in `data/nasdaq_pcaps/` or use full path

**Missing library?** Run `pip install zstandard dpkt`

---

## Output Format

The final `.txt` file contains Strategy Studio depth-by-price (P) ticks:
- CSV format with header
- One row per order book level change
- Columns: COLLECTION_TIME, SOURCE_TIME, SEQ_NUM, TICK_TYPE, MARKET_CENTER, SIDE, PRICE, SIZE, NUM_ORDERS, etc.

