# Event Stream Visualizer

Interactive web-based visualization tool for exploring NASDAQ order book updates and trades.

## Features

- **Grid-based visualization**: Uniform event spacing for easy comparison
- **Color coding**:
  - 🔵 Blue: Bid orders (SIDE=1)
  - 🔴 Red: Ask/Offer orders (SIDE=2)
  - 🟡 Yellow: Trades (TICK_TYPE="T")
- **Multiple market centers**: View different market centers with distinct color schemes
- **Interactive controls**:
  - Toggle event types (bids, asks, trades)
  - Toggle market centers on/off
  - Adjustable max events (100-5000)
  - Forward/backward navigation
- **Rich hover tooltips**: Price, size, time, sequence number
- **Price level display**: Y-axis shows price levels

## Installation

Install required dependencies:

```bash
pip install -r src/requirements.txt
```

Or install individually:

```bash
pip install pandas plotly dash numpy
```

## Usage

### Basic Usage

Run with default files (assumes `output/converted_combined/combined_tick_20250401.csv` and `combined_trade_20250401.csv`):

```bash
python src/visualize/event_stream_visualizer.py
```

### Specify Custom Files

```bash
python src/visualize/event_stream_visualizer.py \
    --tick-file output/converted_combined/combined_tick_20250401.csv \
    --trade-file output/converted_combined/combined_trade_20250401.csv
```

### Specify Date

```bash
python src/visualize/event_stream_visualizer.py --date 20250401
```

### Custom Port

```bash
python src/visualize/event_stream_visualizer.py --port 8051
```

## Interface

Once the app starts, open your browser to `http://localhost:8050` (or your specified port).

### Controls

1. **Max Events Slider**: Adjust how many events to display (100-5000)
2. **Event Type Checkboxes**: Toggle visibility of bids, asks, and trades
3. **Navigation Buttons**: 
   - `◀◀ Prev 1000`: Jump back 1000 events
   - `◀ Prev`: Move back by current max events
   - `Next ▶`: Move forward by current max events
   - `Next 1000 ▶▶`: Jump forward 1000 events
4. **Start Index Input**: Manually enter starting event index
5. **Market Center Checkboxes**: Toggle which market centers to display

### Hover Tooltips

Hover over any point to see:
- Event type and market center
- Event index
- Price
- Size (shares)
- Timestamp
- Sequence number

## Data Format

The visualizer expects CSV files with the following columns:

**Tick files** (`combined_tick_*.csv`):
- `COLLECTION_TIME`: Timestamp
- `MARKET_CENTER`: Market center identifier
- `SIDE`: 1 for bids, 2 for asks
- `PRICE`: Price level
- `SIZE`: Order size
- `SEQ_NUM`: Sequence number

**Trade files** (`combined_trade_*.csv`):
- `COLLECTION_TIME`: Timestamp
- `MARKET_CENTER`: Market center identifier
- `TICK_TYPE`: "T" for trades
- `PRICE`: Trade price
- `SIZE`: Trade size
- `SEQ_NUM`: Sequence number

## Examples

### View first 1000 events

1. Start the app
2. Set "Max Events" to 1000
3. Ensure "Start Index" is 0

### Focus on trades only

1. Uncheck "Bids" and "Asks" in Event Type
2. Keep "Trades" checked

### Compare different market centers

1. Check multiple market centers
2. Each will display with distinct colors
3. Use hover tooltips to identify which market center each event belongs to

## Tips

- Use the slider to adjust the event window size for better performance
- Start with 1000 events for smooth interaction
- Use navigation buttons to explore different time periods
- Hover over points to see detailed information
- Toggle market centers to focus on specific exchanges

