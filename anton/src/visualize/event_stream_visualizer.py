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

# Import strategy observer
try:
    from .strategy_observer import StrategyManager, CrossMarketArbitrageObserver
except ImportError:
    # Handle case when running as script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from strategy_observer import StrategyManager, CrossMarketArbitrageObserver


class EventStreamVisualizer:
    """Load and prepare event data for visualization."""
    
    def __init__(self, tick_file: Path, trade_file: Path):
        self.tick_file = tick_file
        self.trade_file = trade_file
        self.events = None
        self.market_centers = set()
        self.strategy_manager = StrategyManager()
        
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
        
        # Add time_ns for strategy detection (nanoseconds since epoch)
        all_events["time_ns"] = all_events["COLLECTION_TIME"].astype('int64')
        
        self.events = all_events
        
        # Initialize strategy observers based on available market centers
        market_centers_sorted = sorted(list(self.market_centers))
        if len(market_centers_sorted) >= 2:
            # Add arbitrage observer for first two market centers
            self.strategy_manager.add_observer(
                CrossMarketArbitrageObserver(
                    market1=market_centers_sorted[0],
                    market2=market_centers_sorted[1] if len(market_centers_sorted) > 1 else market_centers_sorted[0],
                    max_time_window_ns=1_000_000  # 1ms
                )
            )
            # If IEX and NASDAQ are both present, add specific observer
            if "IEX" in self.market_centers and "NASDAQ" in self.market_centers:
                self.strategy_manager.add_observer(
                    CrossMarketArbitrageObserver(
                        market1="IEX",
                        market2="NASDAQ",
                        max_time_window_ns=1_000_000
                    )
                )
        
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
            "IEX": {"bid": "purple", "ask": "gold", "trade": "green"},
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
    strategy_highlights: Optional[Dict] = None,
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
                        [
                            f"{ts.strftime('%H:%M:%S')}.{str(ts.microsecond).zfill(6)[:3]} ({int(ts.microsecond * 1000)} ns)"
                            for ts in bids["COLLECTION_TIME"]
                        ],
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
                        [
                            f"{ts.strftime('%H:%M:%S')}.{str(ts.microsecond).zfill(6)[:3]} ({int(ts.microsecond * 1000)} ns)"
                            for ts in asks["COLLECTION_TIME"]
                        ],
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
                        [
                            f"{ts.strftime('%H:%M:%S')}.{str(ts.microsecond).zfill(6)[:3]} ({int(ts.microsecond * 1000)} ns)"
                            for ts in trades["COLLECTION_TIME"]
                        ],
                        trades["SEQ_NUM"].fillna("").astype(str).values
                    )),
                ))
    
    # Add strategy highlights
    if strategy_highlights and len(strategy_highlights.get("x", [])) > 0:
        # Filter highlights to current window
        highlights_in_window = {
            "x": [],
            "y": [],
            "text": [],
            "spread": [],
            "colors": [],
            "buy_x": [],
            "sell_x": [],
            "buy_y": [],
            "sell_y": [],
        }
        
        for i, x_val in enumerate(strategy_highlights["x"]):
            if start_idx <= x_val < end_idx:
                highlights_in_window["x"].append(x_val)
                highlights_in_window["y"].append(strategy_highlights["y"][i])
                highlights_in_window["text"].append(strategy_highlights["text"][i])
                highlights_in_window["spread"].append(strategy_highlights["spread"][i])
                highlights_in_window["colors"].append(strategy_highlights["colors"][i])
                if i < len(strategy_highlights.get("buy_x", [])):
                    highlights_in_window["buy_x"].append(strategy_highlights["buy_x"][i])
                    highlights_in_window["sell_x"].append(strategy_highlights["sell_x"][i])
                    highlights_in_window["buy_y"].append(strategy_highlights["buy_y"][i])
                    highlights_in_window["sell_y"].append(strategy_highlights["sell_y"][i])
        
        if highlights_in_window["x"]:
            # Add connecting lines for buy/sell pairs
            if highlights_in_window["buy_x"]:
                for i in range(len(highlights_in_window["buy_x"])):
                    fig.add_trace(go.Scatter(
                        x=[highlights_in_window["buy_x"][i], highlights_in_window["sell_x"][i]],
                        y=[highlights_in_window["buy_y"][i], highlights_in_window["sell_y"][i]],
                        mode='lines',
                        line=dict(color=highlights_in_window["colors"][i], width=2, dash='dash'),
                        showlegend=False,
                        hoverinfo='skip',
                    ))
            
            # Add opportunity markers
            fig.add_trace(go.Scatter(
                x=highlights_in_window["x"],
                y=highlights_in_window["y"],
                mode='markers+text',
                name='Arbitrage Opportunities',
                marker=dict(
                    size=15,
                    color=highlights_in_window["colors"],
                    symbol='star',
                    opacity=0.8,
                    line=dict(width=2, color='black'),
                ),
                text=[f"${s:.4f}" for s in highlights_in_window["spread"]],
                textposition="top center",
                hovertemplate=(
                    '<b>Arbitrage Opportunity</b><br>' +
                    'Spread: $%{customdata[0]:.4f}<br>' +
                    '%{customdata[1]}<br>' +
                    '<extra></extra>'
                ),
                customdata=list(zip(
                    highlights_in_window["spread"],
                    highlights_in_window["text"]
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
                html.Label("Event Range:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Input(
                    id='start-index-input',
                    type='number',
                    value=0,
                    min=0,
                    max=len(events_df),
                    step=100,
                    placeholder='Start',
                    style={'width': '100px', 'marginRight': '5px'},
                ),
                html.Span("to", style={'margin': '0 5px'}),
                dcc.Input(
                    id='end-index-input',
                    type='number',
                    value=min(1000, len(events_df)),
                    min=0,
                    max=len(events_df),
                    step=100,
                    placeholder='End',
                    style={'width': '100px', 'marginRight': '10px'},
                ),
                html.Button("Go", id='go-range-btn', n_clicks=0,
                           style={'padding': '8px 15px', 'marginRight': '10px'}),
                html.Span(f"of {len(events_df):,} total", style={'color': '#666', 'fontSize': '11px'}),
            ], style={'width': '35%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("Jump to Time:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Input(
                    id='time-input',
                    type='text',
                    placeholder='HH:MM:SS.mmm',
                    style={'width': '150px', 'marginRight': '10px'},
                ),
                html.Button("Go", id='go-time-btn', n_clicks=0,
                           style={'padding': '8px 15px', 'marginRight': '10px'}),
                html.Span("Format: HH:MM:SS.mmm", style={'color': '#666', 'fontSize': '11px'}),
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
            ], style={'width': '35%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
        ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px', 'marginBottom': '10px'}),
        
        # Controls Row 3 - Time Offsets and Strategy
        html.Div([
            html.Div([
                html.Label("⏱️ Time Offsets (nanoseconds):", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                html.Div([
                    html.Div([
                        html.Label(f"{mc}:", style={'fontWeight': 'bold', 'marginRight': '5px', 'width': '80px', 'display': 'inline-block'}),
                        dcc.Input(
                            id=f'offset-{mc}',
                            type='number',
                            value=0,
                            step=1000,
                            placeholder='ns',
                            style={'width': '120px', 'marginRight': '15px'},
                        ),
                    ], style={'display': 'inline-block', 'marginRight': '10px', 'marginBottom': '5px'})
                    for mc in market_centers_list
                ]),
                html.Small("Adjust timestamps per exchange to test for misalignment opportunities", 
                          style={'color': '#666', 'fontSize': '11px', 'display': 'block', 'marginTop': '5px'}),
            ], style={'width': '60%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("📊 Strategy Analysis:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                html.Div([
                    html.Label("Max Time Window (ns):", style={'fontWeight': 'bold', 'marginRight': '10px', 'fontSize': '12px'}),
                    dcc.Input(
                        id='max-time-window-input',
                        type='number',
                        value=1_000_000,
                        min=0,
                        step=1000,
                        placeholder='ns',
                        style={'width': '120px', 'marginRight': '10px'},
                    ),
                ], style={'marginBottom': '10px'}),
                dcc.Checklist(
                    id='show-strategies-checklist',
                    options=[{'label': ' Show Arbitrage Opportunities', 'value': 'arbitrage'}],
                    value=[],
                    inline=True,
                ),
                html.Br(),
                html.Button("🔍 Calculate Opportunities", id='calculate-opportunities-btn', n_clicks=0,
                           style={'padding': '10px 20px', 'marginTop': '10px', 'backgroundColor': '#4CAF50', 
                                  'color': 'white', 'border': 'none', 'borderRadius': '5px', 
                                  'fontSize': '14px', 'fontWeight': 'bold', 'cursor': 'pointer'}),
            ], style={'width': '40%', 'display': 'inline-block', 'padding': '10px', 'verticalAlign': 'top'}),
        ], style={'padding': '10px', 'backgroundColor': '#f0f8ff', 'borderRadius': '5px', 'marginBottom': '10px'}),
        
        # Graph
        dcc.Graph(id='event-stream-graph', style={'marginBottom': '10px'}),
        
        # Info display
        html.Div(id='info-display', style={'padding': '10px', 'backgroundColor': '#e8f4f8', 'borderRadius': '5px', 'marginBottom': '10px'}),
        
        # Calculation status (initially empty)
        html.Div(id='calculation-status', style={'padding': '10px', 'backgroundColor': '#f0f8ff', 'borderRadius': '5px'}),
    ], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})
    
    # Create offset state inputs dynamically
    offset_states = [State(f'offset-{mc}', 'value') for mc in market_centers_list]
    
    @app.callback(
        Output('event-stream-graph', 'figure'),
        Output('info-display', 'children'),
        Output('start-index-input', 'value'),
        Output('calculation-status', 'children'),
        Input('max-events-slider', 'value'),
        Input('start-index-input', 'value'),
        Input('prev-btn', 'n_clicks'),
        Input('next-btn', 'n_clicks'),
        Input('prev-1000-btn', 'n_clicks'),
        Input('next-1000-btn', 'n_clicks'),
        Input('event-type-checklist', 'value'),
        Input('market-center-checklist', 'value'),
        Input('go-time-btn', 'n_clicks'),
        Input('go-range-btn', 'n_clicks'),
        Input('show-strategies-checklist', 'value'),
        Input('calculate-opportunities-btn', 'n_clicks'),
        State('start-index-input', 'value'),
        State('end-index-input', 'value'),
        State('time-input', 'value'),
        State('max-time-window-input', 'value'),
        *offset_states,
    )
    def update_graph(max_events, start_idx, prev_clicks, next_clicks, 
                     prev_1000_clicks, next_1000_clicks,
                     event_types, market_centers, go_time_clicks, go_range_clicks,
                     show_strategies, calculate_opportunities_clicks,
                     current_start, end_index, time_input, max_time_window_ns, *offset_values):
        # Build offset dictionary from offset values
        offsets = {}
        for i, mc in enumerate(market_centers_list):
            offset_val = offset_values[i] if i < len(offset_values) and offset_values[i] is not None else 0
            offsets[mc] = int(offset_val)
        
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
            elif trigger_id == 'go-range-btn' and end_index is not None:
                # Jump to specified event range
                start_idx = max(0, min(current_start or 0, len(events_df) - 1))
                end_idx_val = min(int(end_index), len(events_df))
                # Use the start index if provided, otherwise center around the range
                if current_start is not None:
                    start_idx = max(0, min(int(current_start), len(events_df) - max_events))
                else:
                    # If no start specified, use the range start
                    start_idx = max(0, min(int(end_idx_val) - max_events, len(events_df) - max_events))
            elif trigger_id == 'go-time-btn' and time_input:
                # Handle time-based navigation
                try:
                    # Parse time input (HH:MM:SS.mmm or HH:MM:SS)
                    time_parts = time_input.strip().split('.')
                    if len(time_parts) == 2:
                        hms = time_parts[0]
                        frac = time_parts[1]
                        # Pad to microseconds if needed
                        if len(frac) < 6:
                            frac = frac.ljust(6, '0')
                        time_str = f"{hms}.{frac[:6]}"
                    else:
                        time_str = f"{time_parts[0]}.000000"
                    
                    # Get date from first event
                    first_date = events_df.iloc[0]['COLLECTION_TIME'].date()
                    target_time = pd.to_datetime(f"{first_date} {time_str}", format="%Y-%m-%d %H:%M:%S.%f")
                    
                    # Find closest event index
                    time_diffs = (events_df["COLLECTION_TIME"] - target_time).abs()
                    closest_idx = time_diffs.idxmin()
                    # Center the window
                    start_idx = max(0, closest_idx - max_events // 2)
                except Exception as e:
                    print(f"Error parsing time: {e}")
        
        # Ensure start_idx is valid
        start_idx = max(0, min(start_idx or 0, len(events_df) - 1))
        
        # Parse event type toggles
        show_bids = 'bids' in event_types
        show_asks = 'asks' in event_types
        show_trades = 'trades' in event_types
        
        # Handle strategy calculation
        strategy_highlights = None
        calculation_status = ""
        
        if ctx.triggered:
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger_id == 'calculate-opportunities-btn':
                # Get current window
                end_idx = min(start_idx + max_events, len(events_df))
                window = events_df.iloc[start_idx:end_idx].copy()
                
                # Apply time offsets to the window for strategy detection
                window_with_offsets = window.copy()
                for mc, offset_ns in offsets.items():
                    if offset_ns != 0:
                        mask = window_with_offsets["MARKET_CENTER"] == mc
                        # Apply offset as nanoseconds (convert to microseconds for pd.Timedelta)
                        # pd.Timedelta doesn't support nanoseconds directly, so use microseconds
                        offset_us = offset_ns / 1000.0
                        times = window_with_offsets.loc[mask, "COLLECTION_TIME"]
                        window_with_offsets.loc[mask, "COLLECTION_TIME"] = times + pd.Timedelta(microseconds=offset_us)  # type: ignore
                        # Update time_ns after offset
                        times_updated = window_with_offsets.loc[mask, "COLLECTION_TIME"]
                        window_with_offsets.loc[mask, "time_ns"] = pd.to_numeric(times_updated.astype('int64'), errors='coerce')  # type: ignore
                
                # Update max_time_window_ns for all observers
                max_window_ns = max_time_window_ns if max_time_window_ns is not None and max_time_window_ns > 0 else 1_000_000
                for observer in visualizer.strategy_manager.observers:
                    if isinstance(observer, CrossMarketArbitrageObserver):
                        observer.max_time_window_ns = int(max_window_ns)
                    observer.opportunities = []
                
                strategy_results = visualizer.strategy_manager.detect_all(window_with_offsets)
                total_opps = sum(len(opps) for opps in strategy_results.values())
                
                offset_summary = ", ".join([f"{mc}: {off:+d}ns" for mc, off in offsets.items() if off != 0])
                if offset_summary:
                    calculation_status = f"✓ Found {total_opps} opportunities (offsets: {offset_summary})"
                else:
                    calculation_status = f"✓ Found {total_opps} opportunities in current window"
                
                if 'arbitrage' in show_strategies:
                    strategy_highlights = visualizer.strategy_manager.get_all_highlights()
            elif 'arbitrage' in show_strategies:
                # Show existing highlights if already calculated
                strategy_highlights = visualizer.strategy_manager.get_all_highlights()
                if not strategy_highlights.get("x"):
                    calculation_status = "⚠ Click 'Calculate Opportunities' to analyze current window"
        elif 'arbitrage' in show_strategies:
            # Show existing highlights if already calculated
            strategy_highlights = visualizer.strategy_manager.get_all_highlights()
            if not strategy_highlights.get("x"):
                calculation_status = "⚠ Click 'Calculate Opportunities' to analyze current window"
        
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
            strategy_highlights=strategy_highlights,
        )
        
        # Info text
        end_idx = min(start_idx + max_events, len(events_df))
        start_time = events_df.iloc[start_idx]['COLLECTION_TIME']
        end_time = events_df.iloc[end_idx-1]['COLLECTION_TIME'] if end_idx > start_idx else start_time
        
        # Show offset info if any offsets are applied
        offset_info = ""
        if any(off != 0 for off in offsets.values()):
            offset_info = " | " + ", ".join([f"{mc}: {off:+d}ns" for mc, off in offsets.items() if off != 0])
        
        # Format timestamps with first 3 microseconds
        start_time_str = f"{start_time.strftime('%H:%M:%S')}.{str(start_time.microsecond).zfill(6)[:3]}"
        end_time_str = f"{end_time.strftime('%H:%M:%S')}.{str(end_time.microsecond).zfill(6)[:3]}"
        
        info = html.Div([
            html.Strong("Event Range: "),
            f"{start_idx:,} to {end_idx:,} of {len(events_df):,} total events | ",
            html.Strong("Time Range: "),
            f"{start_time_str} to {end_time_str} | ",
            html.Strong("Events Shown: "),
            f"{end_idx - start_idx:,}",
            html.Span(offset_info, style={'color': '#666', 'fontSize': '12px'}),
        ], style={'fontSize': '14px'})
        
        return fig, info, start_idx, calculation_status
    
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

