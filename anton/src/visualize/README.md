# Event Stream Visualizer

Interactive web-based visualization tool for exploring NASDAQ and IEX order book updates, trades, and cross-venue arbitrage opportunities.

## Table of Contents

- [Purpose](#purpose)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Interface Guide](#interface-guide)
- [Data Format Requirements](#data-format-requirements)
- [Integration with Processing Pipeline](#integration-with-processing-pipeline)
- [Troubleshooting](#troubleshooting)

---

## Purpose

The Event Stream Visualizer was developed to provide interactive analysis of processed market data, enabling:

- **Strategy Development**: Visualize how arbitrage opportunities appear in the data stream
- **Data Validation**: Verify that merged multi-exchange data maintains proper ordering and timestamps
- **Market Microstructure Research**: Explore order book dynamics, quote updates, and trade flow patterns
- **Performance Analysis**: Identify periods of high arbitrage activity and cross-venue price divergence
- **Strategy Validation**: See how venue arbitrage strategies would have reacted to historical market conditions

The tool works directly with output files from the NASDAQ ITCH processing pipeline, creating a seamless workflow from raw PCAP files to interactive visualization.

---

## Features

- **Grid-based visualization**: Uniform event spacing for easy comparison across time
- **Color coding**:
  - 🔵 Blue: Bid orders (SIDE=1)
  - 🔴 Red: Ask/Offer orders (SIDE=2)
  - 🟡 Yellow: Trades (TICK_TYPE="T")
- **Multiple market centers**: View NASDAQ and IEX simultaneously with distinct color schemes
- **Arbitrage highlighting**: Automatically detects and highlights cross-venue arbitrage opportunities
- **Interactive controls**:
  - Toggle event types (bids, asks, trades)
  - Toggle market centers on/off
  - Adjustable max events (100-5000)
  - Forward/backward navigation through event stream
- **Rich hover tooltips**: Price, size, time, sequence number, market center
- **Price level display**: Y-axis shows price levels for easy price comparison

---

## System Requirements

- **Python 3.8+**
- **Web browser** (Chrome, Firefox, Safari, or Edge)
- **Processed data files** from the NASDAQ ITCH processing pipeline

---

## Installation

### Install Dependencies

From the `anton/` directory:

```bash
# Install all required packages
pip install -r src/requirements.txt
```

Or install visualization-specific dependencies individually:

```bash
pip install pandas plotly dash numpy
```

**Key Dependencies:**
- `pandas`: For data loading and manipulation
- `plotly`: For interactive charts
- `dash`: For web interface
- `numpy`: For numerical operations

---

## Quick Start

### Basic Usage

Navigate to the `anton/` directory and run:

```bash
# Run with default files (assumes output/converted_combined/combined_tick_20250401.csv)
python src/visualize/event_stream_visualizer.py --date 20250401
```

Then open your browser to `http://localhost:8050` to view the visualization.

---

## Usage Guide

### Specify Date (Auto-finds Files)

The easiest way to run the visualizer:

```bash
# Automatically finds files for the specified date
python src/visualize/event_stream_visualizer.py --date 20250401
```

This looks for:
- `output/converted_combined/combined_tick_20250401.csv`
- `output/converted_combined/combined_trade_20250401.csv`

### Specify Custom Files

```bash
python src/visualize/event_stream_visualizer.py \
    --tick-file output/converted_combined/combined_tick_20250401.csv \
    --trade-file output/converted_combined/combined_trade_20250401.csv
```

### Custom Port

If port 8050 is already in use:

```bash
python src/visualize/event_stream_visualizer.py --date 20250401 --port 8051
```

Then access at `http://localhost:8051`

### Command-Line Options

```bash
python src/visualize/event_stream_visualizer.py --help
```

**Available options:**
- `--tick-file PATH`: Path to tick CSV file
- `--trade-file PATH`: Path to trade CSV file
- `--date YYYYMMDD`: Date string to auto-find files (e.g., 20250401)
- `--port PORT`: Port number for web server (default: 8050)

---

## Interface Guide

Once the app starts, open your browser to `http://localhost:8050` (or your specified port).

### Controls

1. **Max Events Slider**: Adjust how many events to display (100-5000)
   - Lower values = faster rendering, smaller time window
   - Higher values = more context, slower rendering
   - Recommended: Start with 1000 events

2. **Event Type Checkboxes**: Toggle visibility of:
   - **Bids**: Blue points showing bid order updates
   - **Asks**: Red points showing ask/offer order updates
   - **Trades**: Yellow points showing executed trades

3. **Navigation Buttons**: 
   - `◀◀ Prev 1000`: Jump back 1000 events
   - `◀ Prev`: Move back by current max events
   - `Next ▶`: Move forward by current max events
   - `Next 1000 ▶▶`: Jump forward 1000 events

4. **Start Index Input**: Manually enter starting event index (0-based)

5. **Market Center Checkboxes**: Toggle which market centers to display
   - Check/uncheck to focus on specific exchanges
   - Useful for comparing NASDAQ vs IEX behavior

### Hover Tooltips

Hover over any point to see detailed information:
- **Event type**: Bid, Ask, or Trade
- **Market center**: NASDAQ, IEX, etc.
- **Event index**: Position in the event stream
- **Price**: Execution or quote price
- **Size**: Order size or trade size (shares)
- **Timestamp**: Exact time of the event
- **Sequence number**: Event sequence number

### Arbitrage Highlighting

When multiple market centers are present, the visualizer automatically detects and highlights arbitrage opportunities:
- Opportunities are marked with special annotations
- Shows buy/sell prices on different venues
- Displays spread information
- Helps identify when cross-venue price discrepancies occurred

---

## Data Format Requirements

The visualizer expects CSV files with the following columns:

### Tick Files (`combined_tick_*.csv`)

Required columns:
- `COLLECTION_TIME`: Timestamp in format `YYYY-MM-DD HH:MM:SS.ffffff`
- `MARKET_CENTER`: Market center identifier (e.g., "NASDAQ", "IEX")
- `SIDE`: 1 for bids, 2 for asks
- `PRICE`: Price level (numeric)
- `SIZE`: Order size (numeric)
- `SEQ_NUM`: Sequence number (numeric)

Optional but recommended:
- `NUM_ORDERS`: Number of orders at price level
- `TICK_TYPE`: Should be "P" for depth-by-price

### Trade Files (`combined_trade_*.csv`)

Required columns:
- `COLLECTION_TIME`: Timestamp in format `YYYY-MM-DD HH:MM:SS.ffffff`
- `MARKET_CENTER`: Market center identifier (e.g., "NASDAQ", "IEX")
- `TICK_TYPE`: Should be "T" for trades
- `PRICE`: Trade price (numeric)
- `SIZE`: Trade size (numeric)
- `SEQ_NUM`: Sequence number (numeric)

### File Location

By default, the visualizer looks for files in:
```
anton/output/converted_combined/
```

Files should be named:
- `combined_tick_YYYYMMDD.csv`
- `combined_trade_YYYYMMDD.csv`

---

## Integration with Processing Pipeline

The visualizer is designed to work seamlessly with files produced by the NASDAQ ITCH processing pipeline:

### Data Flow

1. **Raw PCAP files** → Processed via `anton/src/ingest/` pipeline
2. **Processed files** → Combined via `combine_csv.py`
3. **Combined files** → UTC converted via `utc_nasdaq_timestamp_converter.py`
4. **Converted files** → Visualized via `event_stream_visualizer.py`

### Pipeline Integration

The visualizer uses the same Strategy Studio-compatible format as the processing pipeline:
- Same column names and formats
- Same timestamp format (UTC)
- Same market center identifiers
- Compatible with merged multi-exchange data

### Workflow Example

```bash
# Step 1: Process NASDAQ data
cd anton
python process.py file.pcap.zst USO --both

# Step 2: Combine files by day
python combine_csv.py 20250401

# Step 3: Convert timestamps to UTC
python utc_nasdaq_timestamp_converter.py --date 20250401

# Step 4: Visualize
python src/visualize/event_stream_visualizer.py --date 20250401
```

This creates an end-to-end workflow:
- Raw PCAP files → Processed tick/trade files → Interactive visualization → Strategy development insights

For details on the processing pipeline, see `src/ingest/README.md` and the main project `README.md`.

---

## Examples

### View First 1000 Events

1. Start the app: `python src/visualize/event_stream_visualizer.py --date 20250401`
2. Open browser to `http://localhost:8050`
3. Set "Max Events" slider to 1000
4. Ensure "Start Index" is 0
5. All event types should be checked

### Focus on Trades Only

1. Uncheck "Bids" and "Asks" in Event Type checkboxes
2. Keep "Trades" checked
3. This shows only executed trades, useful for analyzing trade flow

### Compare Different Market Centers

1. Check multiple market centers (e.g., both NASDAQ and IEX)
2. Each will display with distinct colors
3. Use hover tooltips to identify which market center each event belongs to
4. Look for price divergences between venues (arbitrage opportunities)

### Analyze Specific Time Period

1. Use navigation buttons to jump to a specific event range
2. Or enter a start index directly
3. Adjust "Max Events" to control the time window
4. Toggle market centers to focus on specific exchanges

### Identify Arbitrage Opportunities

1. Ensure both NASDAQ and IEX are checked
2. Look for highlighted arbitrage annotations
3. Hover over highlighted points to see spread information
4. Use navigation to explore different time periods

---

## Tips

- **Performance**: Start with 1000 events for smooth interaction. Increase for more context, decrease for faster rendering.
- **Navigation**: Use the "Prev 1000" and "Next 1000" buttons to quickly jump through large datasets
- **Focus**: Toggle market centers and event types to focus on specific aspects of the data
- **Tooltips**: Hover over points to see detailed information without cluttering the view
- **Arbitrage Detection**: The visualizer automatically highlights opportunities when multiple market centers are present

---

## Troubleshooting

### Files Not Found

**Problem:** Visualizer can't find input files

**Solutions:**
1. Check that files exist in `output/converted_combined/`
2. Verify file naming: `combined_tick_YYYYMMDD.csv` and `combined_trade_YYYYMMDD.csv`
3. Use `--tick-file` and `--trade-file` to specify full paths
4. Ensure files have been processed through the full pipeline (see Integration section)

### Port Already in Use

**Problem:** Error about port 8050 being in use

**Solution:** Use a different port:
```bash
python src/visualize/event_stream_visualizer.py --date 20250401 --port 8051
```

### Missing Columns

**Problem:** Error about missing required columns

**Solutions:**
1. Ensure files were processed through the complete pipeline
2. Check that files are from `output/converted_combined/` (UTC converted)
3. Verify file format matches requirements (see Data Format Requirements section)

### Slow Performance

**Problem:** Visualization is slow or unresponsive

**Solutions:**
1. Reduce "Max Events" slider (try 500-1000)
2. Toggle off unnecessary event types
3. Toggle off market centers you're not analyzing
4. Close other browser tabs/applications

### No Data Displayed

**Problem:** Chart is empty

**Solutions:**
1. Check that at least one event type is checked
2. Check that at least one market center is checked
3. Verify files contain data for the specified date
4. Try adjusting the "Start Index" to a different value

### Import Errors

**Problem:** Python import errors when running

**Solution:** Install dependencies:
```bash
pip install -r src/requirements.txt
```

---

## Related Documentation

- **Processing Pipeline**: See `src/ingest/README.md` for complete NASDAQ ITCH processing documentation
- **Main Project**: See main project `README.md` for overall project structure and workflow
- **Strategy Development**: See main project `README.md` Phase 2 and Phase 3 for strategy implementation details
