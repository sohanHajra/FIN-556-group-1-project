#!/usr/bin/env python
"""
Interactive backtest results visualizer using Plotly Dash.

Visualizes Strategy Studio backtest results:
- Fill timeline (scatter plot: time vs price, size as marker size)
- Order timeline (showing order states over time)
- Cumulative P&L over time (line chart)

EXAMPLES:
    # Specify all three files
    python backtest_results_visualizer.py \
        --fill-file path/to/fill.csv \
        --order-file path/to/order.csv \
        --pnl-file path/to/pnl.csv
    
    # Auto-detect files from base name (relative or absolute path)
    python backtest_results_visualizer.py \
        --base-name BACK_Acharov2VenueArbInstance100000_2025-12-22_025433_start_04-01-2025_end_04-03-2025
    
    # Or with absolute path
    python backtest_results_visualizer.py \
        --base-name /home/user/ss/bt/backtesting-results/BACK_Acharov2VenueArbInstance100000_2025-12-22_025433_start_04-01-2025_end_04-03-2025
    
    # Custom port
    python backtest_results_visualizer.py --fill-file fill.csv --order-file order.csv --pnl-file pnl.csv --port 8052
"""

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html
from pathlib import Path
import argparse
import sys


class BacktestResultsVisualizer:
    """Load and prepare backtest results for visualization."""
    
    def __init__(self, fill_file: Path, order_file: Path, pnl_file: Path):
        self.fill_file = fill_file
        self.order_file = order_file
        self.pnl_file = pnl_file
        self.fills = None
        self.orders = None
        self.pnl = None
        
    def load_data(self):
        """Load all three CSV files."""
        print(f"Loading fill file: {self.fill_file}")
        self.fills = pd.read_csv(self.fill_file, parse_dates=["TradeTime"])
        print(f"  Loaded {len(self.fills)} fills")
        
        print(f"Loading order file: {self.order_file}")
        self.orders = pd.read_csv(self.order_file, parse_dates=["EntryTime", "LastModTime"])
        print(f"  Loaded {len(self.orders)} orders")
        
        print(f"Loading PnL file: {self.pnl_file}")
        self.pnl = pd.read_csv(self.pnl_file, parse_dates=["Time"])
        print(f"  Loaded {len(self.pnl)} PnL records")
        
        # Ensure numeric columns
        self.fills["Price"] = pd.to_numeric(self.fills["Price"], errors='coerce')
        self.fills["Quantity"] = pd.to_numeric(self.fills["Quantity"], errors='coerce')
        self.orders["Price"] = pd.to_numeric(self.orders["Price"], errors='coerce')
        self.orders["Quantity"] = pd.to_numeric(self.orders["Quantity"], errors='coerce')
        self.pnl["Cumulative PnL"] = pd.to_numeric(self.pnl["Cumulative PnL"], errors='coerce')
        
        print("✓ All data loaded successfully")


def create_fill_chart(fills: pd.DataFrame) -> go.Figure:
    """Create scatter plot of fills over time."""
    fig = go.Figure()
    
    # Separate buys and sells
    buys = fills[fills["Quantity"] > 0]
    sells = fills[fills["Quantity"] < 0]
    
    if len(buys) > 0:
        fig.add_trace(go.Scatter(
            x=buys["TradeTime"],
            y=buys["Price"],
            mode='markers',
            name='Buy Fills',
            marker=dict(
                size=abs(buys["Quantity"]) / 50,  # Smaller bubbles (was /10, now /50)
                color='green',
                opacity=0.6,
                line=dict(width=1, color='darkgreen')
            ),
            hovertemplate='<b>Buy Fill</b><br>' +
                         'Time: %{x}<br>' +
                         'Price: $%{y:.2f}<br>' +
                         'Quantity: %{customdata}<br>' +
                         '<extra></extra>',
            customdata=abs(buys["Quantity"]),
        ))
    
    if len(sells) > 0:
        fig.add_trace(go.Scatter(
            x=sells["TradeTime"],
            y=sells["Price"],
            mode='markers',
            name='Sell Fills',
            marker=dict(
                size=abs(sells["Quantity"]) / 100,  # Smaller bubbles (was /10, now /50)
                color='red',
                opacity=0.6,
                line=dict(width=1, color='darkred')
            ),
            hovertemplate='<b>Sell Fill</b><br>' +
                         'Time: %{x}<br>' +
                         'Price: $%{y:.2f}<br>' +
                         'Quantity: %{customdata}<br>' +
                         '<extra></extra>',
            customdata=abs(sells["Quantity"]),
        ))
    
    fig.update_layout(
        title="Fill Timeline",
        xaxis_title="Time",
        yaxis_title="Price ($)",
        hovermode='closest',
        height=400,
    )
    
    return fig


def create_order_chart(orders: pd.DataFrame) -> go.Figure:
    """Create timeline showing order states."""
    fig = go.Figure()
    
    # Group by state
    states = orders["State"].unique()
    colors = {
        'FILLED': 'green',
        'PARTIAL': 'orange',
        'CANCELLED': 'red',
        'REJECTED': 'darkred',
        'NEW': 'blue',
        'WORKING': 'cyan',
    }
    
    for state in states:
        state_orders = orders[orders["State"] == state]
        color = colors.get(state, 'gray')
        
        fig.add_trace(go.Scatter(
            x=state_orders["EntryTime"],
            y=state_orders["Price"],
            mode='markers',
            name=state,
            marker=dict(
                size=8,
                color=color,
                opacity=0.7,
            ),
            hovertemplate=f'<b>{state}</b><br>' +
                         'Entry: %{x}<br>' +
                         'Price: $%{y:.2f}<br>' +
                         'Quantity: %{customdata}<br>' +
                         '<extra></extra>',
            customdata=state_orders["Quantity"],
        ))
    
    fig.update_layout(
        title="Order Timeline (by State)",
        xaxis_title="Time",
        yaxis_title="Price ($)",
        hovermode='closest',
        height=400,
    )
    
    return fig


def create_pnl_chart(pnl: pd.DataFrame) -> go.Figure:
    """Create cumulative P&L line chart."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=pnl["Time"],
        y=pnl["Cumulative PnL"],
        mode='lines+markers',
        name='Cumulative P&L',
        line=dict(color='blue', width=2),
        marker=dict(size=4),
        hovertemplate='<b>P&L</b><br>' +
                     'Time: %{x}<br>' +
                     'Cumulative P&L: $%{y:.2f}<br>' +
                     '<extra></extra>',
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title="Cumulative P&L Over Time",
        xaxis_title="Time",
        yaxis_title="Cumulative P&L ($)",
        hovermode='x unified',
        height=800,
    )
    
    return fig


def create_dash_app(visualizer: BacktestResultsVisualizer):
    """Create Dash app with all charts."""
    app = Dash(__name__)
    
    # Load data
    visualizer.load_data()
    
    # Ensure data is loaded
    assert visualizer.fills is not None, "Fills data not loaded"
    assert visualizer.orders is not None, "Orders data not loaded"
    assert visualizer.pnl is not None, "PnL data not loaded"
    
    fills = visualizer.fills
    orders = visualizer.orders
    pnl = visualizer.pnl
    
    # Create charts
    fill_fig = create_fill_chart(fills)
    order_fig = create_order_chart(orders)
    pnl_fig = create_pnl_chart(pnl)
    
    # Calculate summary stats
    total_fills = len(fills)
    total_orders = len(orders)
    final_pnl = pnl["Cumulative PnL"].iloc[-1] if len(pnl) > 0 else 0
    max_pnl = pnl["Cumulative PnL"].max() if len(pnl) > 0 else 0
    min_pnl = pnl["Cumulative PnL"].min() if len(pnl) > 0 else 0
    
    # Calculate total volume
    total_volume = abs(fills["Quantity"]).sum() if len(fills) > 0 else 0
    
    app.layout = html.Div([
        html.H1("Strategy Studio Backtest Results", style={'textAlign': 'center'}),
        
        html.Div([
            html.Div([
                html.H3("Summary Statistics"),
                html.P(f"Total Fills: {total_fills:,}"),
                html.P(f"Total Orders: {total_orders:,}"),
                html.P(f"Total Volume: {total_volume:,.0f} shares"),
                html.P(f"Final P&L: ${final_pnl:,.2f}"),
                html.P(f"Max P&L: ${max_pnl:,.2f}"),
                html.P(f"Min P&L: ${min_pnl:,.2f}"),
            ], style={'padding': '20px', 'backgroundColor': '#f0f0f0', 'borderRadius': '5px', 'margin': '10px'}),
        ], style={'display': 'flex', 'justifyContent': 'center'}),
        
        html.Div([
            dcc.Graph(id='fill-chart', figure=fill_fig),
        ], style={'margin': '20px'}),
        
        html.Div([
            dcc.Graph(id='order-chart', figure=order_fig),
        ], style={'margin': '20px'}),
        
        html.Div([
            dcc.Graph(id='pnl-chart', figure=pnl_fig),
        ], style={'margin': '20px'}),
    ])
    
    return app


def main():
    ap = argparse.ArgumentParser(
        description="Interactive backtest results visualizer for Strategy Studio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--fill-file",
        type=Path,
        default=None,
        help="Path to fill CSV file",
    )
    ap.add_argument(
        "--order-file",
        type=Path,
        default=None,
        help="Path to order CSV file",
    )
    ap.add_argument(
        "--pnl-file",
        type=Path,
        default=None,
        help="Path to PnL CSV file",
    )
    ap.add_argument(
        "--base-name",
        type=str,
        default=None,
        help="Base filename (without _fill.csv suffix). Can be absolute or relative path. Auto-detects _fill.csv, _order.csv, _pnl.csv",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=8051,  # Different default port to avoid conflicts
        help="Port to run Dash app (default: 8051)",
    )
    
    args = ap.parse_args()
    
    # Auto-detect files from base name
    if args.base_name:
        base_path = Path(args.base_name)
        if base_path.is_absolute():
            # Absolute path provided - use it directly
            base_path = base_path
        else:
            # Relative path - try to find in common locations
            possible_dirs = [
                Path.home() / "ss" / "bt" / "backtesting-results",
                Path.cwd(),
            ]
            found = False
            for dir_path in possible_dirs:
                fill_path = dir_path / f"{args.base_name}_fill.csv"
                if fill_path.exists():
                    base_path = dir_path / args.base_name
                    found = True
                    break
            
            if not found:
                # If not found in common locations, try current directory
                base_path = Path.cwd() / args.base_name
        
        args.fill_file = Path(f"{base_path}_fill.csv")
        args.order_file = Path(f"{base_path}_order.csv")
        args.pnl_file = Path(f"{base_path}_pnl.csv")
    
    # Check that all files are provided
    if not args.fill_file or not args.order_file or not args.pnl_file:
        print("✗ ERROR: Must provide either --base-name or all three file paths")
        print("  Use --fill-file, --order-file, --pnl-file")
        print("  Or use --base-name to auto-detect")
        sys.exit(1)
    
    # Convert to Path objects and resolve
    fill_file = Path(args.fill_file)
    order_file = Path(args.order_file)
    pnl_file = Path(args.pnl_file)
    
    if not fill_file.is_absolute():
        fill_file = Path.cwd() / fill_file
    if not order_file.is_absolute():
        order_file = Path.cwd() / order_file
    if not pnl_file.is_absolute():
        pnl_file = Path.cwd() / pnl_file
    
    # Check if files exist
    if not fill_file.exists():
        print(f"✗ ERROR: Fill file not found: {fill_file}")
        sys.exit(1)
    
    if not order_file.exists():
        print(f"✗ ERROR: Order file not found: {order_file}")
        sys.exit(1)
    
    if not pnl_file.exists():
        print(f"✗ ERROR: PnL file not found: {pnl_file}")
        sys.exit(1)
    
    print("=" * 80)
    print("Backtest Results Visualizer")
    print("=" * 80)
    print(f"Fill file:  {fill_file}")
    print(f"Order file: {order_file}")
    print(f"PnL file:   {pnl_file}")
    print("=" * 80)
    
    visualizer = BacktestResultsVisualizer(fill_file, order_file, pnl_file)
    app = create_dash_app(visualizer)
    
    print(f"\nStarting Dash app on http://localhost:{args.port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    
    app.run(debug=True, port=args.port)


if __name__ == "__main__":
    main()

