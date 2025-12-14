"""
Strategy Observer - Detects and highlights trading opportunities.

Easily extendable framework for detecting arbitrage and trading opportunities
across different market centers.
"""

from typing import List, Dict, Optional
import pandas as pd
from dataclasses import dataclass


@dataclass
class TradingOpportunity:
    """Represents a detected trading opportunity."""
    event_idx: int
    timestamp: pd.Timestamp
    opportunity_type: str
    buy_market: str
    buy_price: float
    sell_market: str
    sell_price: float
    spread: float
    time_window_ns: Optional[int] = None
    description: str = ""
    buy_event_idx: Optional[int] = None
    sell_event_idx: Optional[int] = None


class StrategyObserver:
    """Base class for strategy detection."""
    
    def __init__(self, name: str):
        self.name = name
        self.opportunities: List[TradingOpportunity] = []
    
    def detect(self, events: pd.DataFrame, nearest_only: bool = False) -> List[TradingOpportunity]:
        """Detect opportunities in the event stream.
        
        Args:
            events: Event dataframe
            nearest_only: If True, only return the nearest opportunity per starting event
        """
        raise NotImplementedError("Subclasses must implement detect()")
    
    def get_highlight_data(self) -> Dict:
        """Return data for highlighting opportunities on the chart."""
        if not self.opportunities:
            return {"x": [], "y": [], "text": [], "spread": [], "colors": []}
        
        return {
            "x": [opp.event_idx for opp in self.opportunities],
            "y": [(opp.buy_price + opp.sell_price) / 2 for opp in self.opportunities],
            "text": [opp.description for opp in self.opportunities],
            "spread": [opp.spread for opp in self.opportunities],
            "colors": [
                "green" if s >= 0.01 else "orange" if s >= 0.005 else "yellow"
                for s in [opp.spread for opp in self.opportunities]
            ],
        }


class CrossMarketArbitrageObserver(StrategyObserver):
    """
    Detects cross-market arbitrage opportunities:
    - IEX ask < NASDAQ bid -> buy IEX, sell NASDAQ
    - IEX bid > NASDAQ ask -> buy NASDAQ, sell IEX
    """
    
    def __init__(self, market1: str = "IEX", market2: str = "NASDAQ", 
                 max_time_window_ns: int = 1_000_000):  # 1ms default
        super().__init__(f"Cross-Market Arbitrage ({market1}/{market2})")
        self.market1 = market1
        self.market2 = market2
        self.max_time_window_ns = max_time_window_ns
    
    def detect(self, events: pd.DataFrame, nearest_only: bool = False) -> List[TradingOpportunity]:
        """Detect arbitrage opportunities between two markets.
        
        Args:
            events: Event dataframe
            nearest_only: If True, only return the nearest opportunity per starting event
        """
        opportunities = []
        
        # Ensure we have time_ns column
        if "time_ns" not in events.columns:
            events["time_ns"] = events["COLLECTION_TIME"].astype('int64')
        
        # Get bids and asks for both markets
        market1_bids = events[
            (events["MARKET_CENTER"] == self.market1) & 
            (events["event_type"] == "order") & 
            (events["SIDE"] == 1)
        ].copy()
        
        market1_asks = events[
            (events["MARKET_CENTER"] == self.market1) & 
            (events["event_type"] == "order") & 
            (events["SIDE"] == 2)
        ].copy()
        
        market2_bids = events[
            (events["MARKET_CENTER"] == self.market2) & 
            (events["event_type"] == "order") & 
            (events["SIDE"] == 1)
        ].copy()
        
        market2_asks = events[
            (events["MARKET_CENTER"] == self.market2) & 
            (events["event_type"] == "order") & 
            (events["SIDE"] == 2)
        ].copy()
        
        # Strategy 1: market1 ask < market2 bid -> buy market1, sell market2
        for _, m1_ask in market1_asks.iterrows():
            time_ns = m1_ask["time_ns"]
            m2_bids_in_window = market2_bids[
                (market2_bids["time_ns"] >= time_ns) &
                (market2_bids["time_ns"] <= time_ns + self.max_time_window_ns) &
                (market2_bids["PRICE"] > m1_ask["PRICE"])
            ]
            
            if len(m2_bids_in_window) == 0:
                continue
            
            if nearest_only:
                # Find the nearest match (smallest time difference)
                m2_bids_in_window = m2_bids_in_window.copy()
                m2_bids_in_window["time_diff"] = m2_bids_in_window["time_ns"] - time_ns
                nearest_idx = m2_bids_in_window["time_diff"].idxmin()
                m2_bid = m2_bids_in_window.loc[nearest_idx]
                spread = m2_bid["PRICE"] - m1_ask["PRICE"]
                if spread > 0:
                    opportunities.append(TradingOpportunity(
                        event_idx=m1_ask["event_index"],
                        timestamp=m1_ask["COLLECTION_TIME"],
                        opportunity_type="buy_low_sell_high",
                        buy_market=self.market1,
                        buy_price=m1_ask["PRICE"],
                        sell_market=self.market2,
                        sell_price=m2_bid["PRICE"],
                        spread=spread,
                        time_window_ns=int(m2_bid["time_ns"] - time_ns),
                        buy_event_idx=int(m1_ask["event_index"]),
                        sell_event_idx=int(m2_bid["event_index"]),
                        description=f"Buy {self.market1} @ ${m1_ask['PRICE']:.4f}, Sell {self.market2} @ ${m2_bid['PRICE']:.4f}, Spread: ${spread:.4f}"
                    ))
            else:
                # Show all matches
                for _, m2_bid in m2_bids_in_window.iterrows():
                    spread = m2_bid["PRICE"] - m1_ask["PRICE"]
                    if spread > 0:
                        opportunities.append(TradingOpportunity(
                            event_idx=m1_ask["event_index"],
                            timestamp=m1_ask["COLLECTION_TIME"],
                            opportunity_type="buy_low_sell_high",
                            buy_market=self.market1,
                            buy_price=m1_ask["PRICE"],
                            sell_market=self.market2,
                            sell_price=m2_bid["PRICE"],
                            spread=spread,
                            time_window_ns=int(m2_bid["time_ns"] - time_ns),
                            buy_event_idx=int(m1_ask["event_index"]),
                            sell_event_idx=int(m2_bid["event_index"]),
                            description=f"Buy {self.market1} @ ${m1_ask['PRICE']:.4f}, Sell {self.market2} @ ${m2_bid['PRICE']:.4f}, Spread: ${spread:.4f}"
                        ))
        
        # Strategy 2: market1 bid > market2 ask -> buy market2, sell market1
        for _, m1_bid in market1_bids.iterrows():
            time_ns = m1_bid["time_ns"]
            m2_asks_in_window = market2_asks[
                (market2_asks["time_ns"] >= time_ns) &
                (market2_asks["time_ns"] <= time_ns + self.max_time_window_ns) &
                (market2_asks["PRICE"] < m1_bid["PRICE"])
            ]
            
            if len(m2_asks_in_window) == 0:
                continue
            
            if nearest_only:
                # Find the nearest match (smallest time difference)
                m2_asks_in_window = m2_asks_in_window.copy()
                m2_asks_in_window["time_diff"] = m2_asks_in_window["time_ns"] - time_ns
                nearest_idx = m2_asks_in_window["time_diff"].idxmin()
                m2_ask = m2_asks_in_window.loc[nearest_idx]
                spread = m1_bid["PRICE"] - m2_ask["PRICE"]
                if spread > 0:
                    opportunities.append(TradingOpportunity(
                        event_idx=m1_bid["event_index"],
                        timestamp=m1_bid["COLLECTION_TIME"],
                        opportunity_type="buy_low_sell_high",
                        buy_market=self.market2,
                        buy_price=m2_ask["PRICE"],
                        sell_market=self.market1,
                        sell_price=m1_bid["PRICE"],
                        spread=spread,
                        time_window_ns=int(m2_ask["time_ns"] - time_ns),
                        buy_event_idx=int(m2_ask["event_index"]),
                        sell_event_idx=int(m1_bid["event_index"]),
                        description=f"Buy {self.market2} @ ${m2_ask['PRICE']:.4f}, Sell {self.market1} @ ${m1_bid['PRICE']:.4f}, Spread: ${spread:.4f}"
                    ))
            else:
                # Show all matches
                for _, m2_ask in m2_asks_in_window.iterrows():
                    spread = m1_bid["PRICE"] - m2_ask["PRICE"]
                    if spread > 0:
                        opportunities.append(TradingOpportunity(
                            event_idx=m1_bid["event_index"],
                            timestamp=m1_bid["COLLECTION_TIME"],
                            opportunity_type="buy_low_sell_high",
                            buy_market=self.market2,
                            buy_price=m2_ask["PRICE"],
                            sell_market=self.market1,
                            sell_price=m1_bid["PRICE"],
                            spread=spread,
                            time_window_ns=int(m2_ask["time_ns"] - time_ns),
                            buy_event_idx=int(m2_ask["event_index"]),
                            sell_event_idx=int(m1_bid["event_index"]),
                            description=f"Buy {self.market2} @ ${m2_ask['PRICE']:.4f}, Sell {self.market1} @ ${m1_bid['PRICE']:.4f}, Spread: ${spread:.4f}"
                        ))
        
        self.opportunities = opportunities
        return opportunities


class StrategyManager:
    """Manages multiple strategy observers."""
    
    def __init__(self):
        self.observers: List[StrategyObserver] = []
    
    def add_observer(self, observer: StrategyObserver):
        """Add a strategy observer."""
        self.observers.append(observer)
    
    def detect_all(self, events: pd.DataFrame, nearest_only: bool = False) -> Dict[str, List[TradingOpportunity]]:
        """Run all observers and return results.
        
        Args:
            events: Event dataframe
            nearest_only: If True, only return the nearest opportunity per starting event
        """
        results = {}
        for observer in self.observers:
            opportunities = observer.detect(events, nearest_only=nearest_only)
            results[observer.name] = opportunities
        return results
    
    def get_all_highlights(self) -> Dict:
        """Get highlight data from all observers."""
        all_highlights = {
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
        
        for observer in self.observers:
            for opp in observer.opportunities:
                all_highlights["x"].append(opp.event_idx)
                all_highlights["y"].append((opp.buy_price + opp.sell_price) / 2)
                all_highlights["text"].append(opp.description)
                all_highlights["spread"].append(opp.spread)
                # Color by spread size
                if opp.spread >= 0.01:
                    all_highlights["colors"].append("green")
                elif opp.spread >= 0.005:
                    all_highlights["colors"].append("orange")
                else:
                    all_highlights["colors"].append("yellow")
                
                # Add buy/sell points for connecting lines
                if opp.buy_event_idx is not None and opp.sell_event_idx is not None:
                    all_highlights["buy_x"].append(opp.buy_event_idx)
                    all_highlights["buy_y"].append(opp.buy_price)
                    all_highlights["sell_x"].append(opp.sell_event_idx)
                    all_highlights["sell_y"].append(opp.sell_price)
        
        return all_highlights

