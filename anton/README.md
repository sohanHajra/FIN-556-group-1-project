# Anton's Data Processing and Visualization Tools

This directory contains tools for processing NASDAQ ITCH market data and visualizing the results.

## Quick Overview

- **Data Processing**: Convert NASDAQ PCAP files to Strategy Studio-compatible tick and trade files
- **Visualization**: Interactive web-based tools to explore market data and arbitrage opportunities

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

# Visualize processed data
python src/visualize/event_stream_visualizer.py --date 20250401
```
