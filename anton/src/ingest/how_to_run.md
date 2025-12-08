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

- **Ticks**: `output/tick_messages/tick_SYMBOL_YYYYMMDD.txt`
- **Trades**: `output/trade_messages/trade_SYMBOL_YYYYMMDD.txt`

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

## Help

```bash
python process.py --help
```

