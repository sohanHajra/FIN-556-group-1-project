# Anton's Data Processing and Visualization Tools

This directory contains tools for processing NASDAQ ITCH market data and visualizing the results.

## Quick Overview

- **Data Processing**: Convert NASDAQ PCAP files to Strategy Studio-compatible tick and trade files
- **Visualization**: Interactive web-based tools to explore market data, arbitrage opportunities, and backtest results

## Getting Started

For detailed documentation, see:

- **Data Processing**: [`src/ingest/README.md`](src/ingest/README.md) - Complete guide to processing NASDAQ ITCH data
- **Visualization**: [`src/visualize/README.md`](src/visualize/README.md) - Guide to using the interactive visualizer

## Quick Start

```bash
# Process NASDAQ data (from anton directory)
cd src/ingest
python process.py file.pcap.zst USO

# Or from anton directory:
python src/ingest/process.py file.pcap.zst USO

# Visualize processed market data
python src/visualize/event_stream_visualizer.py --date 20250401

# Visualize backtest results
python src/visualize/backtest_results_visualizer.py \
    --fill-file path/to/fill.csv \
    --order-file path/to/order.csv \
    --pnl-file path/to/pnl.csv
```
