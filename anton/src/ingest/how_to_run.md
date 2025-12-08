# How to Run - NASDAQ ITCH Processing Pipeline

Quick guide to process NASDAQ ITCH data files.

## Quick Start

### Basic Usage

```bash
# Generate depth-by-price ticks (default)
python process.py file.pcap.zst USO

# Generate trade ticks only
python process.py file.pcap.zst USO --trades

# Generate both ticks and trades
python process.py file.pcap.zst USO --both
```

## Output Locations

- **Ticks**: `output/tick_messages/YYYYMMDD/tick_SYMBOL_YYYYMMDDTHHMMSS.csv`
- **Trades**: `output/trade_messages/YYYYMMDD/trade_SYMBOL_YYYYMMDDTHHMMSS.csv`
- **PCAPs**: `output/pcap_decompressed/YYYYMMDD/filenameTtime.pcap`
- **ITCH**: `output/itch_converted_pcaps/YYYYMMDD/filenameTtime.itch`

## Common Commands

### With Explicit Date

```bash
python process.py file.pcap SPY --date 2025-04-01
```

### Skip Steps (if intermediate files exist)

```bash
# Skip decompression
python process.py file.pcap.zst USO --skip-decompress

# Skip both decompression and PCAP conversion
python process.py file.pcap.zst USO --skip-decompress --skip-pcap
```

### Custom Output Directory

```bash
python process.py file.pcap.zst USO --output ./custom_output
```

### Performance Options

```bash
# Show progress every 100k messages (default)
python process.py file.pcap.zst USO --progress 100000

# Disable progress updates
python process.py file.pcap.zst USO --progress 0
```

## Input File Location

Put your input files (`.zst` or `.pcap`) in:
```
data/nasdaq_pcaps/
```

Or use full path:
```bash
python process.py C:/path/to/file.pcap.zst USO
```

## Pipeline Steps

The script automatically runs:
1. **Decompress** `.zst` → `.pcap` (if needed)
2. **Convert** `.pcap` → `.itch`
3. **Generate** ticks and/or trades based on mode

Intermediate files (`.pcap`, `.itch`) are saved in the output directory.

## Mode Options

- **Default** (no flag): Depth-by-price ticks only
- `--trades`: Trade ticks only
- `--both`: Both depth-by-price and trade ticks

## Examples

```bash
# Most common: depth-by-price ticks
python process.py ny4-xnas-tvitch-a-20250401T083000.pcap.zst USO

# Trade ticks only
python process.py file.pcap.zst SPY --trades

# Both types
python process.py file.pcap.zst USO --both --date 2025-04-01
```

## Batch Processing (Multiple Files)

Process all .zst files across a date range:

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

## Help

```bash
python process.py --help
python batch_process.py --help
```

