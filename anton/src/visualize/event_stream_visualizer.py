#!/usr/bin/env python
"""
Interactive event stream visualizer using Plotly Dash.

Features:
- Grid-based event visualization (uniform event spacing)
- Color coding: Bids (blue), Asks (red), Trades (yellow)
- Multiple market centers with different color schemes
- Toggle market centers on/off
- Configurable max events (default 1000)
- Forward/backward navigation
- Rich hover tooltips
- Price level display

EXAMPLES:
    # Run with default files
    python event_stream_visualizer.py
    
    # Specify custom files
    python event_stream_visualizer.py --tick-file output/converted_combined/combined_tick_20250401.csv --trade-file output/converted_combined/combined_trade_20250401.csv
    
    # Custom port
    python event_stream_visualizer.py --port 8051
"""

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import argparse
import sys


class EventStreamVisualizer:
    """Load and prepare event data for visualization."""
    
    def __init__(self, tick_file: Path, trade_file: Path):
        self.tick_file = tick_file
        self.trade_file = trade_file
        self.events = None
        self.market_centers = set()
        
    def load_and_merge_events(self) -> pd.DataFrame:
        """Load and merge tick and trade events chronologically."""
        print(f"Loading tick file: {self.tick_file}")
        ticks = pd.read_csv(self.tick_file, parse_dates=["COLLECTION_TIME"])
        ticks["event_type"] = "order"
        ticks["display_type"] = ticks["SIDE"].map({1: "Bid", 2: "Ask"})
        ticks["color"] = ticks["SIDE"].map({1: "blue", 2: "red"})
        
        print(f"Loading trade file: {self.trade_file}")
        trades = pd.read_csv(self.trade_file, parse_dates=["COLLECTION_TIME"])
        trades["event_type"] = "trade"
        trades["display_type"] = "Trade"
        trades["color"] = "yellow"
        
        # Merge and sort
        print("Merging and sorting events...")
        all_events = pd.concat([ticks, trades], ignore_index=True, sort=False)
        all_events = all_events.sort_values("COLLECTION_TIME")
        
        # Extract market centers
        self.market_centers = set(all_events["MARKET_CENTER"].unique())
        print(f"Found {len(self.market_centers)} market center(s): {sorted(self.market_centers)}")
        
        # Add event index for uniform spacing
        all_events["event_index"] = range(len(all_events))
        
        # Ensure PRICE is numeric
        all_events["PRICE"] = pd.to_numeric(all_events["PRICE"], errors='coerce')
        
        self.events = all_events
        print(f"Loaded {len(all_events):,} total events")
        return all_events
    
    def get_market_center_colors(self) -> Dict[str, Dict[str, str]]:
        """Generate color scheme for different market centers."""
        # Define color schemes for known market centers
        color_schemes = {
            "NASDAQ": {"bid": "blue", "ask": "red", "trade": "yellow"},
            "NYSE": {"bid": "cyan", "ask": "orange", "trade": "gold"},
            "BATS": {"bid": "lightblue", "ask": "lightcoral", "trade": "khaki"},
            "ARCA": {"bid": "steelblue", "ask": "tomato", "trade": "goldenrod"},
            "EDGX": {"bid": "dodgerblue", "ask": "crimson", "trade": "orange"},
        }
        
        # Default colors for unknown market centers
        default = {"bid": "blue", "ask": "red", "trade": "yellow"}
        
        return {mc: color_schemes.get(mc, default) for mc in self.market_centers}


def create_event_plot(
    events: pd.DataFrame,
    start_idx: int,
    max_events: int,
    market_centers: List[str],
    market_center_colors: Dict[str, Dict[str, str]],
    show_bids: bool = True,
    show_asks: bool = True,
    show_trades: bool = True,
) -> go.Figure:
    """
    Create Plotly figure for event stream visualization.
    
    Args:
        events: Full event dataframe
        start_idx: Starting event index
        max_events: Maximum events to display
        market_centers: List of market centers to show
        market_center_colors: Color scheme per market center
        show_bids: Toggle for bid orders
        show_asks: Toggle for ask orders
        show_trades: Toggle for trades
    """
    end_idx = min(start_idx + max_events, len(events))
    window = events.iloc[start_idx:end_idx].copy()
    
    # Filter by market center
    if market_centers:
        window = window[window["MARKET_CENTER"].isin(market_centers)]
    
    fig = go.Figure()
    
    # Plot bids
    if show_bids:
        for mc in market_centers:
            bids = window[
                (window["event_type"] == "order") & 
                (window["SIDE"] == 1) & 
                (window["MARKET_CENTER"] == mc)
            ]
            if len(bids) > 0:
                fig.add_trace(go.Scatter(
                    x=bids["event_index"],
                    y=bids["PRICE"],
                    mode='markers',
                    name=f'{mc} Bids',
                    marker=dict(
                        color=market_center_colors[mc]["bid"],
                        size=8,
                        symbol='triangle-up',
                        opacity=0.7,
                        line=dict(width=0.5, color='darkblue'),
                    ),
                    hovertemplate=(
                        '<b>%{fullData.name}</b><br>' +
                        'Event Index: %{x}<br>' +
                        'Price: $%{y:.2f}<br>' +
                        'Size: %{customdata[0]:,}<br>' +
                        'Time: %{customdata[1]}<br>' +
                        'Seq: %{customdata[2]}<br>' +
                        '<extra></extra>'
                    ),
                    customdata=list(zip(
                        bids["SIZE"].fillna(0).astype(int).values,
                        bids["COLLECTION_TIME"].dt.strftime("%H:%M:%S.%f").str[:-3].values,
                        bids["SEQ_NUM"].fillna("").astype(str).values
                    )),
                ))
    
    # Plot asks
    if show_asks:
        for mc in market_centers:
            asks = window[
                (window["event_type"] == "order") & 
                (window["SIDE"] == 2) & 
                (window["MARKET_CENTER"] == mc)
            ]
            if len(asks) > 0:
                fig.add_trace(go.Scatter(
                    x=asks["event_index"],
                    y=asks["PRICE"],
                    mode='markers',
                    name=f'{mc} Asks',
                    marker=dict(
                        color=market_center_colors[mc]["ask"],
                        size=8,
                        symbol='triangle-down',
                        opacity=0.7,
                        line=dict(width=0.5, color='darkred'),
                    ),
                    hovertemplate=(
                        '<b>%{fullData.name}</b><br>' +
                        'Event Index: %{x}<br>' +
                        'Price: $%{y:.2f}<br>' +
                        'Size: %{customdata[0]:,}<br>' +
                        'Time: %{customdata[1]}<br>' +
                        'Seq: %{customdata[2]}<br>' +
                        '<extra></extra>'
                    ),
                    customdata=list(zip(
                        asks["SIZE"].fillna(0).astype(int).values,
                        asks["COLLECTION_TIME"].dt.strftime("%H:%M:%S.%f").str[:-3].values,
                        asks["SEQ_NUM"].fillna("").astype(str).values
                    )),
                ))
    
    # Plot trades
    if show_trades:
        for mc in market_centers:
            trades = window[
                (window["event_type"] == "trade") & 
                (window["MARKET_CENTER"] == mc)
            ]
            if len(trades) > 0:
                fig.add_trace(go.Scatter(
                    x=trades["event_index"],
                    y=trades["PRICE"],
                    mode='markers',
                    name=f'{mc} Trades',
                    marker=dict(
                        color=market_center_colors[mc]["trade"],
                        size=12,
                        symbol='circle',
                        opacity=0.8,
                        line=dict(width=1.5, color='black'),
                    ),
                    hovertemplate=(
                        '<b>%{fullData.name}</b><br>' +
                        'Event Index: %{x}<br>' +
                        'Price: $%{y:.2f}<br>' +
                        'Size: %{customdata[0]:,}<br>' +
                        'Time: %{customdata[1]}<br>' +
                        'Seq: %{customdata[2]}<br>' +
                        '<extra></extra>'
                    ),
                    customdata=list(zip(
                        trades["SIZE"].fillna(0).astype(int).values,
                        trades["COLLECTION_TIME"].dt.strftime("%H:%M:%S.%f").str[:-3].values,
                        trades["SEQ_NUM"].fillna("").astype(str).values
                    )),
                ))
    
    fig.update_layout(
        title=dict(
            text="Event Stream Visualization",
            x=0.5,
            xanchor='center',
        ),
        xaxis_title="Event Index (Uniform Spacing)",
        yaxis_title="Price ($)",
        hovermode='closest',
        height=700,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
        ),
        plot_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridcolor='lightgray'),
    )
    
    return fig


def create_dash_app(visualizer: EventStreamVisualizer):
    """Create Dash application for interactive visualization."""
    app = Dash(__name__)
    
    events_df = visualizer.load_and_merge_events()
    market_center_colors = visualizer.get_market_center_colors()
    market_centers_list = sorted(list(visualizer.market_centers))
    
    app.layout = html.Div([
        html.H1(
            "NASDAQ Event Stream Visualizer",
            style={'textAlign': 'center', 'marginBottom': '20px', 'color': '#2c3e50'}
        ),
        
        # Controls Row 1
        html.Div([
            html.Div([
                html.Label("Max Events:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Slider(
                    id='max-events-slider',
                    min=100,
                    max=min(5000, len(events_df)),
                    step=100,
                    value=1000,
                    marks={i: str(i) for i in range(0, min(5001, len(events_df)+1), 500)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
            ], style={'width': '40%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("Event Type:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Checklist(
                    id='event-type-checklist',
                    options=[
                        {'label': ' Bids', 'value': 'bids'},
                        {'label': ' Asks', 'value': 'asks'},
                        {'label': ' Trades', 'value': 'trades'},
                    ],
                    value=['bids', 'asks', 'trades'],
                    inline=True,
                    style={'marginTop': '5px'},
                ),
            ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("Navigation:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                html.Br(),
                html.Button("◀◀ Prev 1000", id='prev-1000-btn', n_clicks=0,
                           style={'margin': '5px', 'padding': '8px 15px'}),
                html.Button("◀ Prev", id='prev-btn', n_clicks=0,
                           style={'margin': '5px', 'padding': '8px 15px'}),
                html.Button("Next ▶", id='next-btn', n_clicks=0,
                           style={'margin': '5px', 'padding': '8px 15px'}),
                html.Button("Next 1000 ▶▶", id='next-1000-btn', n_clicks=0,
                           style={'margin': '5px', 'padding': '8px 15px'}),
            ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
        ], style={'padding': '20px', 'backgroundColor': '#f0f0f0', 'borderRadius': '5px', 'marginBottom': '10px'}),
        
        # Controls Row 2
        html.Div([
            html.Div([
                html.Label("Start Index:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Input(
                    id='start-index-input',
                    type='number',
                    value=0,
                    min=0,
                    max=len(events_df),
                    step=100,
                    style={'width': '120px', 'marginRight': '10px'},
                ),
                html.Span(f"of {len(events_df):,} total events", style={'color': '#666'}),
            ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("Market Centers:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Checklist(
                    id='market-center-checklist',
                    options=[{'label': f' {mc}', 'value': mc} for mc in market_centers_list],
                    value=market_centers_list,
                    inline=True,
                    style={'marginTop': '5px'},
                ),
            ], style={'width': '70%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
        ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px', 'marginBottom': '10px'}),
        
        # Graph
        dcc.Graph(id='event-stream-graph', style={'marginBottom': '10px'}),
        
        # Info display
        html.Div(id='info-display', style={'padding': '10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '5px'}),
    ], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})
    
    @app.callback(
        Output('event-stream-graph', 'figure'),
        Output('info-display', 'children'),
        Output('start-index-input', 'value'),
        Input('max-events-slider', 'value'),
        Input('start-index-input', 'value'),
        Input('prev-btn', 'n_clicks'),
        Input('next-btn', 'n_clicks'),
        Input('prev-1000-btn', 'n_clicks'),
        Input('next-1000-btn', 'n_clicks'),
        Input('event-type-checklist', 'value'),
        Input('market-center-checklist', 'value'),
        State('start-index-input', 'value'),
    )
    def update_graph(max_events, start_idx, prev_clicks, next_clicks, 
                     prev_1000_clicks, next_1000_clicks,
                     event_types, market_centers, current_start):
        # Handle navigation buttons
        ctx = callback_context
        if ctx.triggered:
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger_id == 'prev-btn':
                start_idx = max(0, (current_start or 0) - max_events)
            elif trigger_id == 'next-btn':
                start_idx = min(len(events_df) - max_events, (current_start or 0) + max_events)
            elif trigger_id == 'prev-1000-btn':
                start_idx = max(0, (current_start or 0) - 1000)
            elif trigger_id == 'next-1000-btn':
                start_idx = min(len(events_df) - max_events, (current_start or 0) + 1000)
        
        # Ensure start_idx is valid
        start_idx = max(0, min(start_idx or 0, len(events_df) - 1))
        
        # Parse event type toggles
        show_bids = 'bids' in event_types
        show_asks = 'asks' in event_types
        show_trades = 'trades' in event_types
        
        # Create figure
        fig = create_event_plot(
            events_df,
            start_idx,
            max_events,
            market_centers if market_centers else market_centers_list,
            market_center_colors,
            show_bids,
            show_asks,
            show_trades,
        )
        
        # Info text
        end_idx = min(start_idx + max_events, len(events_df))
        start_time = events_df.iloc[start_idx]['COLLECTION_TIME']
        end_time = events_df.iloc[end_idx-1]['COLLECTION_TIME'] if end_idx > start_idx else start_time
        
        info = html.Div([
            html.Strong("Event Range: "),
            f"{start_idx:,} to {end_idx:,} of {len(events_df):,} total events | ",
            html.Strong("Time Range: "),
            f"{start_time.strftime('%H:%M:%S.%f')[:-3]} to {end_time.strftime('%H:%M:%S.%f')[:-3]} | ",
            html.Strong("Events Shown: "),
            f"{end_idx - start_idx:,}",
        ], style={'fontSize': '14px'})
        
        return fig, info, start_idx
    
    return app


def main():
    ap = argparse.ArgumentParser(
        description="Interactive event stream visualizer for NASDAQ order book and trade data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--tick-file",
        type=Path,
        default=None,
        help="Path to tick CSV file (default: output/converted_combined/combined_tick_YYYYMMDD.csv)",
    )
    ap.add_argument(
        "--trade-file",
        type=Path,
        default=None,
        help="Path to trade CSV file (default: output/converted_combined/combined_trade_YYYYMMDD.csv)",
    )
    ap.add_argument(
        "--date",
        type=str,
        default="20250401",
        help="Date in YYYYMMDD format (default: 20250401)",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port to run Dash app (default: 8050)",
    )
    
    args = ap.parse_args()
    
    # Determine project root
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    
    # Set default file paths if not provided
    if args.tick_file is None:
        args.tick_file = PROJECT_ROOT / "output" / "converted_combined" / f"combined_tick_{args.date}.csv"
    else:
        args.tick_file = Path(args.tick_file)
        if not args.tick_file.is_absolute():
            args.tick_file = PROJECT_ROOT / args.tick_file
    
    if args.trade_file is None:
        args.trade_file = PROJECT_ROOT / "output" / "converted_combined" / f"combined_trade_{args.date}.csv"
    else:
        args.trade_file = Path(args.trade_file)
        if not args.trade_file.is_absolute():
            args.trade_file = PROJECT_ROOT / args.trade_file
    
    # Check if files exist
    if not args.tick_file.exists():
        print(f"✗ ERROR: Tick file not found: {args.tick_file}")
        sys.exit(1)
    
    if not args.trade_file.exists():
        print(f"✗ ERROR: Trade file not found: {args.trade_file}")
        sys.exit(1)
    
    print("=" * 80)
    print("Event Stream Visualizer")
    print("=" * 80)
    print(f"Tick file: {args.tick_file}")
    print(f"Trade file: {args.trade_file}")
    print("=" * 80)
    
    visualizer = EventStreamVisualizer(args.tick_file, args.trade_file)
    app = create_dash_app(visualizer)
    
    print(f"\nStarting Dash app on http://localhost:{args.port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    
    app.run(debug=True, port=args.port)


if __name__ == "__main__":
    main()

