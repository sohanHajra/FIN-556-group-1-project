#!/usr/bin/env python
"""
Convert NASDAQ ITCH trade messages to Strategy Studio trade (T) ticks.

Processes trade messages (P, Q, C, optionally E) and outputs Strategy Studio
format trade ticks for time & sales displays.

1. NonCrossTradeMessage (P) — Regular trades
What: Trades from non-displayable (hidden) orders
When: Matches between hidden orders
Has: stock, price, shares, buy_sell_indicator, match_number
Use: Regular trades for time & sales

2. CrossTradeMessage (Q) — Auction crosses
What: Opening/closing/IPO crosses (bulk auction trades)
When: Special auction events
Has: stock, cross_price, shares, cross_type (O/C/H), match_number
Use: Include if you want opening/closing crosses

3. OrderExecutedMessage (E) — Book order executions
What: Visible order on book gets executed
When: Displayable order matches
Has: order_reference_number, executed_shares, match_number (no price in message)
Issue: Price not in message; need to look up from order book

4. OrderExecutedWithPriceMessage (C) — Book order executions with price
What: Visible order executed at different price than display price
When: Execution price ≠ display price
Has: order_reference_number, executed_shares, execution_price, printable, match_number
Use: Trades from visible orders (has price)
"""

import argparse
import csv
import time
from datetime import datetime, date, timedelta
from typing import Optional, Set

from itch.parser import MessageParser
from itch.messages import (
    NonCrossTradeMessage,           # P
    CrossTradeMessage,              # Q
    OrderExecutedWithPriceMessage,  # C
    OrderExecutedMessage,           # E (needs order book lookup)
    AddOrderNoMPIAttributionMessage,  # A (for order book tracking)
    AddOrderMPIDAttribution,          # F (for order book tracking)
    OrderCancelMessage,              # X (for order book tracking)
    OrderDeleteMessage,              # D (for order book tracking)
    OrderReplaceMessage,             # U (for order book tracking)
)

# =====================================================================
# Time helper: ns since midnight -> 'YYYY-MM-DD HH:MM:SS.ffffff'
# =====================================================================

def ns_since_midnight_to_str(trade_date: date, ts_ns: int) -> str:
    """Convert nanoseconds since midnight to Strategy Studio datetime string."""
    seconds = ts_ns // 1_000_000_000
    micros = (ts_ns % 1_000_000_000) // 1_000
    dt = datetime.combine(trade_date, datetime.min.time()) + timedelta(
        seconds=seconds,
        microseconds=micros,
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


# =====================================================================
# Emit Strategy Studio Trade (T) line
# =====================================================================

def emit_t_line(
    writer,
    trade_date: date,
    ts_ns: int,
    seq_num: int,
    market_center: str,
    price: float,
    size: int,
    feed_type: int = 1,
    side: int | str = "",
    trade_cond_type: str = "",
    trade_cond: str = "",
):
    """
    Emit a Strategy Studio Trade (T) tick line.
    
    Args:
        writer: CSV writer
        trade_date: Trading date
        ts_ns: Timestamp in nanoseconds since midnight
        seq_num: Sequence number
        market_center: Market center string (e.g., "NASDAQ")
        price: Trade price
        size: Trade size (shares)
        feed_type: 1=consolidated, 2=direct, 3=depth (default: 1)
        side: -1=SELL, 0/""=UNKNOWN, 1=BUY (default: "")
        trade_cond_type: 'S'=SIAC, 'U'=UTP, 'O'=OPRA, 'L'=LSE (default: "")
        trade_cond: Trade condition string (default: "")
    """
    ts_str = ns_since_midnight_to_str(trade_date, ts_ns)
    
    # Build row - always include all columns (Strategy Studio format)
    # Use empty strings for optional fields when not provided
    row = [
        ts_str,                 # COLLECTION_TIME
        ts_str,                 # SOURCE_TIME
        str(seq_num),           # SEQ_NUM
        "T",                    # TICK_TYPE
        market_center,          # MARKET_CENTER
        f"{price:.4f}",         # PRICE
        str(size),              # SIZE
        str(feed_type) if feed_type != 1 or side != "" or trade_cond_type != "" else "",  # FEED_TYPE
        str(side) if side != "" else "",  # SIDE
        trade_cond_type,        # TRADE_COND_TYPE
        trade_cond,             # TRADE_COND
    ]
    
    writer.writerow(row)


# =====================================================================
# Main conversion: ITCH -> Strategy Studio T ticks for one symbol
# =====================================================================

def dump_trades(
    itch_path: str,
    symbol: str,
    out_csv: str,
    trade_date: str,
    market_center: str = "NASDAQ",
    trade_types: Optional[Set[str]] = None,
    feed_type: int = 1,
    include_cross_trades: bool = True,
    progress_interval: Optional[int] = None,
    debug: Optional[Set[str]] = None,
    optimized: bool = True,
):
    """
    Convert ITCH trade messages to Strategy Studio trade (T) ticks.
    
    Args:
        itch_path: Path to raw ITCH file
        symbol: Stock symbol to filter
        out_csv: Output CSV file path
        trade_date: Trading date in YYYY-MM-DD format
        market_center: Market center string
        trade_types: Set of message types to process (default: {'P', 'C'})
                    Options: 'P' (NonCrossTrade), 'Q' (CrossTrade), 
                            'C' (OrderExecutedWithPrice), 'E' (OrderExecuted)
        feed_type: Feed type (1=consolidated, 2=direct, 3=depth)
        include_cross_trades: Whether to include cross trades (Q messages)
        progress_interval: Print progress every N messages
        debug: Set of message types to debug (None, empty set=all, or specific types)
        optimized: Enable performance optimizations
    """
    if trade_types is None:
        # Default: P (hidden orders) + E (visible orders)
        # This captures ALL trades: hidden orders (P) and visible orders (E)
        trade_types = {'P', 'E'}
        # Note: C (OrderExecutedWithPrice) is less common - only when execution price ≠ display price
        # Q (CrossTrade) is for opening/closing crosses
    
    symbol = symbol.upper()
    trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()
    
    # Helper function to check if a message type should be debugged
    _debug_cache = {}
    def should_debug(msg_type: bytes) -> bool:
        """Check if this message type should be debugged."""
        if debug is None:
            return False
        if len(debug) == 0:  # Empty set means debug all
            return True
        if msg_type not in _debug_cache:
            _debug_cache[msg_type] = msg_type.decode()
        return _debug_cache[msg_type] in debug
    
    # Build parser message type filter
    # If processing E messages, we need to track orders (A, F, X, D, U)
    parser_types_set = set(trade_types)
    if 'E' in trade_types:
        parser_types_set.update(['A', 'F', 'X', 'D', 'U'])  # Need order book messages
    
    parser_types = b"".join([t.encode() for t in parser_types_set])
    if optimized:
        parser = MessageParser(message_type=parser_types)
    else:
        parser = MessageParser()  # Parse all, filter later
    
    seq_num = 1
    msg_count = 0
    trades_written = 0
    start_time = time.time()
    
    # Order book for E messages: order_ref -> {symbol, price, side}
    # side: 1 = bid (buy), 2 = ask (sell) - Strategy Studio convention
    order_book = {} if 'E' in trade_types else None
    
    with open(itch_path, "rb") as f, open(out_csv, "w", newline="") as out_file:
        writer = csv.writer(out_file)
        
        # Header
        writer.writerow([
            "COLLECTION_TIME",
            "SOURCE_TIME",
            "SEQ_NUM",
            "TICK_TYPE",
            "MARKET_CENTER",
            "PRICE",
            "SIZE",
            "FEED_TYPE",
            "SIDE",
            "TRADE_COND_TYPE",
            "TRADE_COND",
        ])
        
        for msg in parser.parse_file(f):
            msg_count += 1
            
            # Progress logging
            if progress_interval is not None and msg_count > 0 and msg_count % progress_interval == 0:
                elapsed = time.time() - start_time
                rate = msg_count / elapsed if elapsed > 0 else 0
                ts_str = ns_since_midnight_to_str(trade_date_obj, msg.timestamp) if hasattr(msg, 'timestamp') else "N/A"
                print(
                    f"[PROGRESS] Messages: {msg_count:,} | "
                    f"Trades written: {trades_written:,} | "
                    f"Time: {elapsed:.1f}s | "
                    f"Rate: {rate:,.0f} msg/s | "
                    f"Current time: {ts_str}"
                )
            
            ts_ns = msg.timestamp
            ts_str = None  # Lazy computation
            
            def get_ts_str():
                """Lazy timestamp string computation."""
                nonlocal ts_str
                if ts_str is None:
                    ts_str = ns_since_midnight_to_str(trade_date_obj, ts_ns)
                return ts_str
            
            # --- ORDER BOOK TRACKING (for E messages) ---
            # Track AddOrder, Cancel, Delete, Replace to maintain order book
            if order_book is not None:
                if isinstance(msg, (AddOrderNoMPIAttributionMessage, AddOrderMPIDAttribution)):
                    # OPTIMIZATION: Check symbol before decode()
                    if optimized:
                        stock_raw = msg.stock
                        if isinstance(stock_raw, bytes):
                            stock_check = stock_raw.rstrip(b' \x00').decode('ascii', errors='ignore').upper()
                        else:
                            stock_check = str(stock_raw).strip().upper()
                        # Only track orders for our symbol
                        if stock_check != symbol:
                            if should_debug(msg.message_type):
                                print(f"[MSG {msg_count}] ADD_ORDER ({msg.message_type.decode()}) | "
                                      f"Time: {get_ts_str()} | Stock: {stock_check} | -> FILTERED (symbol mismatch)")
                            continue
                    
                    # Decode for full processing
                    dec = msg.decode()
                    stock = dec.stock.strip().upper()
                    
                    # Double-check symbol (if not already checked in optimized path)
                    if not optimized and stock != symbol:
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] ADD_ORDER ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | Stock: {stock} | -> FILTERED (symbol mismatch)")
                        continue
                    
                    order_ref = dec.order_reference_number
                    # side: 1 = bid (buy), 2 = ask (sell) - Strategy Studio convention
                    side = 1 if dec.buy_sell_indicator == b"B" else 2
                    order_book[order_ref] = {
                        "symbol": stock,
                        "price": dec.price,
                        "side": side,
                    }
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] ADD_ORDER ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {order_ref} | "
                              f"Stock: {stock} | Price: {dec.price:.4f} | Side: {side}")
                    continue  # Don't process as trade, just track
                
                elif isinstance(msg, OrderCancelMessage):
                    # OPTIMIZATION: Check if order is in book before decode()
                    if optimized:
                        order_ref = msg.order_reference_number
                        if order_ref not in order_book:
                            if should_debug(msg.message_type):
                                print(f"[MSG {msg_count}] CANCEL ({msg.message_type.decode()}) | "
                                      f"Time: {get_ts_str()} | OrderRef: {order_ref} | -> FILTERED (order not in book)")
                            continue
                        dec = msg.decode()
                    else:
                        dec = msg.decode()
                        order_ref = dec.order_reference_number
                    
                    # Update remaining size (but keep order in book)
                    # Note: We don't track size in our simple order book, so we just keep it
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] CANCEL ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {order_ref}")
                    continue
                
                elif isinstance(msg, OrderDeleteMessage):
                    # OPTIMIZATION: Check if order is in book before decode()
                    if optimized:
                        order_ref = msg.order_reference_number
                        if order_ref not in order_book:
                            if should_debug(msg.message_type):
                                print(f"[MSG {msg_count}] DELETE ({msg.message_type.decode()}) | "
                                      f"Time: {get_ts_str()} | OrderRef: {order_ref} | -> FILTERED (order not in book)")
                            continue
                        del order_book[order_ref]
                        dec = msg.decode()  # Decode only for debug if needed
                    else:
                        dec = msg.decode()
                        order_ref = dec.order_reference_number
                        if order_ref in order_book:
                            del order_book[order_ref]
                    
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] DELETE ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {order_ref if optimized else dec.order_reference_number}")
                    continue
                
                elif isinstance(msg, OrderReplaceMessage):
                    # OPTIMIZATION: Check if order is in book before decode()
                    if optimized:
                        order_ref = msg.order_reference_number
                        if order_ref not in order_book:
                            if should_debug(msg.message_type):
                                print(f"[MSG {msg_count}] REPLACE ({msg.message_type.decode()}) | "
                                      f"Time: {get_ts_str()} | OldOrderRef: {order_ref} | -> FILTERED (order not in book)")
                            continue
                        dec = msg.decode()
                        old_ref = order_ref
                        new_ref = dec.new_order_reference_number
                    else:
                        dec = msg.decode()
                        old_ref = dec.order_reference_number
                        new_ref = dec.new_order_reference_number
                    
                    if old_ref in order_book:
                        # Transfer order info to new reference
                        order_info = order_book.pop(old_ref)
                        order_info["price"] = dec.price  # Updated price
                        # Note: side doesn't change in replace, but we could update if needed
                        order_book[new_ref] = order_info
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] REPLACE ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | OldRef: {old_ref} | NewRef: {new_ref} | "
                                  f"NewPrice: {dec.price:.4f}")
                    continue
            
            # --- NON-CROSS TRADE (P) ---
            if isinstance(msg, NonCrossTradeMessage):
                if 'P' not in trade_types:
                    continue
                
                dec = msg.decode()
                stock = dec.stock.strip().upper()
                
                # Symbol filtering
                if optimized:
                    stock_raw = msg.stock
                    if isinstance(stock_raw, bytes):
                        stock_check = stock_raw.rstrip(b' \x00').decode('ascii', errors='ignore').upper()
                    else:
                        stock_check = str(stock_raw).strip().upper()
                    if stock_check != symbol:
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] TRADE_P ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | Stock: {stock_check} | -> FILTERED (symbol mismatch)")
                        continue
                
                if stock != symbol:
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] TRADE_P ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | Stock: {stock} | -> FILTERED (symbol mismatch)")
                    continue
                
                # Determine side from buy_sell_indicator
                # Handle both bytes and single-byte formats
                buy_sell = dec.buy_sell_indicator
                if isinstance(buy_sell, bytes):
                    buy_sell_str = buy_sell.decode('ascii', errors='ignore').strip()
                else:
                    buy_sell_str = str(buy_sell).strip()
                
                if buy_sell_str == "B":
                    side = 1
                elif buy_sell_str == "S":
                    side = -1
                else:
                    side = ""  # Unknown
                
                if should_debug(msg.message_type):
                    print(f"[MSG {msg_count}] TRADE_P ({msg.message_type.decode()}) | "
                          f"Time: {get_ts_str()} | Stock: {stock} | "
                          f"Price: {dec.price:.4f} | Size: {dec.shares} | Side: {side}")
                
                emit_t_line(
                    writer,
                    trade_date_obj,
                    ts_ns,
                    seq_num,
                    market_center,
                    dec.price,
                    dec.shares,
                    feed_type=feed_type,
                    side=side,
                )
                seq_num += 1
                trades_written += 1
            
            # --- CROSS TRADE (Q) ---
            elif isinstance(msg, CrossTradeMessage):
                if 'Q' not in trade_types or not include_cross_trades:
                    continue
                
                dec = msg.decode()
                stock = dec.stock.strip().upper()
                
                # Symbol filtering
                if optimized:
                    stock_raw = msg.stock
                    if isinstance(stock_raw, bytes):
                        stock_check = stock_raw.rstrip(b' \x00').decode('ascii', errors='ignore').upper()
                    else:
                        stock_check = str(stock_raw).strip().upper()
                    if stock_check != symbol:
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] TRADE_Q ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | Stock: {stock_check} | -> FILTERED (symbol mismatch)")
                        continue
                
                if stock != symbol:
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] TRADE_Q ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | Stock: {stock} | -> FILTERED (symbol mismatch)")
                    continue
                
                # Cross trades: side is unknown, map cross_type to trade condition
                side = ""  # Unknown for crosses
                trade_cond_type = ""
                trade_cond = ""
                
                # Map cross_type to trade condition
                cross_type = dec.cross_type.decode() if isinstance(dec.cross_type, bytes) else str(dec.cross_type)
                if cross_type == "O":
                    trade_cond = "OPEN"
                elif cross_type == "C":
                    trade_cond = "CLOSE"
                elif cross_type == "H":
                    trade_cond = "HALT"
                
                if should_debug(msg.message_type):
                    print(f"[MSG {msg_count}] TRADE_Q ({msg.message_type.decode()}) | "
                          f"Time: {get_ts_str()} | Stock: {stock} | "
                          f"Price: {dec.cross_price:.4f} | Size: {dec.shares} | CrossType: {cross_type}")
                
                emit_t_line(
                    writer,
                    trade_date_obj,
                    ts_ns,
                    seq_num,
                    market_center,
                    dec.cross_price,
                    dec.shares,
                    feed_type=feed_type,
                    side=side,
                    trade_cond_type=trade_cond_type,
                    trade_cond=trade_cond,
                )
                seq_num += 1
                trades_written += 1
            
            # --- ORDER EXECUTED WITH PRICE (C) ---
            elif isinstance(msg, OrderExecutedWithPriceMessage):
                if 'C' not in trade_types:
                    continue
                
                # OPTIMIZATION: If we have order book, check if order is in book before decode()
                if optimized and order_book is not None:
                    order_ref = msg.order_reference_number
                    if order_ref not in order_book:
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] TRADE_C ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | OrderRef: {order_ref} | -> FILTERED (order not in book)")
                        continue
                    dec = msg.decode()
                else:
                    dec = msg.decode()
                
                # Check if printable (skip non-printable to avoid double counting)
                if dec.printable == b"N":
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] TRADE_C ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {dec.order_reference_number} | "
                              f"-> FILTERED (non-printable)")
                    continue
                
                # Optional: Filter by symbol if we're tracking orders
                order_ref = dec.order_reference_number
                side = ""  # Unknown for C messages without order book
                
                if order_book is not None and order_ref in order_book:
                    # We have order book info - use it for symbol filtering and side
                    order_info = order_book[order_ref]
                    order_symbol = order_info["symbol"]
                    order_side = order_info["side"]
                    
                    # Filter by symbol
                    if order_symbol != symbol:
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] TRADE_C ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | OrderRef: {order_ref} | "
                                  f"Symbol: {order_symbol} | -> FILTERED (symbol mismatch)")
                        continue
                    
                    # Map order book side to trade side
                    side = 1 if order_side == 1 else -1
                    
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] TRADE_C ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {order_ref} | "
                              f"Symbol: {order_symbol} | Price: {dec.execution_price:.4f} | "
                              f"Size: {dec.executed_shares} | Side: {side} | Printable: {dec.printable.decode()}")
                else:
                    # No order book - process all C messages (no symbol filtering)
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] TRADE_C ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {order_ref} | "
                              f"Price: {dec.execution_price:.4f} | Size: {dec.executed_shares} | "
                              f"Printable: {dec.printable.decode()}")
                
                emit_t_line(
                    writer,
                    trade_date_obj,
                    ts_ns,
                    seq_num,
                    market_center,
                    dec.execution_price,
                    dec.executed_shares,
                    feed_type=feed_type,
                    side=side,
                )
                seq_num += 1
                trades_written += 1
            
            # --- ORDER EXECUTED (E) ---
            elif isinstance(msg, OrderExecutedMessage):
                if 'E' not in trade_types:
                    continue
                
                if order_book is None:
                    # Order book not initialized - skip
                    if should_debug(msg.message_type):
                        dec = msg.decode()
                        print(f"[MSG {msg_count}] TRADE_E ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {dec.order_reference_number} | "
                              f"-> SKIPPED (order book not initialized)")
                    continue
                
                # OPTIMIZATION: Check if order is in book before decode()
                if optimized:
                    order_ref = msg.order_reference_number
                    if order_ref not in order_book:
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] TRADE_E ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | OrderRef: {order_ref} | -> FILTERED (order not in book)")
                        continue
                    # Order is in book - decode for processing
                    dec = msg.decode()
                else:
                    dec = msg.decode()
                    order_ref = dec.order_reference_number
                    # Look up order in book
                    if order_ref not in order_book:
                        if should_debug(msg.message_type):
                            print(f"[MSG {msg_count}] TRADE_E ({msg.message_type.decode()}) | "
                                  f"Time: {get_ts_str()} | OrderRef: {order_ref} | "
                                  f"-> FILTERED (order not in book)")
                        continue
                
                order_info = order_book[order_ref]
                order_symbol = order_info["symbol"]
                order_price = order_info["price"]
                order_side = order_info["side"]
                
                # Filter by symbol
                if order_symbol != symbol:
                    if should_debug(msg.message_type):
                        print(f"[MSG {msg_count}] TRADE_E ({msg.message_type.decode()}) | "
                              f"Time: {get_ts_str()} | OrderRef: {order_ref} | "
                              f"Symbol: {order_symbol} | -> FILTERED (symbol mismatch)")
                    continue
                
                # Map order book side (1=bid, 2=ask) to trade side (1=BUY, -1=SELL)
                # For E messages: if order was a bid (buy), trade side is BUY (1)
                #                 if order was an ask (sell), trade side is SELL (-1)
                trade_side = 1 if order_side == 1 else -1
                
                if should_debug(msg.message_type):
                    print(f"[MSG {msg_count}] TRADE_E ({msg.message_type.decode()}) | "
                          f"Time: {get_ts_str()} | OrderRef: {order_ref} | "
                          f"Symbol: {order_symbol} | Price: {order_price:.4f} | "
                          f"Size: {dec.executed_shares} | Side: {trade_side}")
                
                emit_t_line(
                    writer,
                    trade_date_obj,
                    ts_ns,
                    seq_num,
                    market_center,
                    order_price,
                    dec.executed_shares,
                    feed_type=feed_type,
                    side=trade_side,
                )
                seq_num += 1
                trades_written += 1
                
                # Note: We don't remove order from book on execution
                # because it might execute multiple times (partial fills)
            
            # Other message types - skip
            else:
                if should_debug(msg.message_type if hasattr(msg, 'message_type') else b'?'):
                    msg_type_code = msg.message_type.decode() if hasattr(msg, 'message_type') else '?'
                    print(f"[MSG {msg_count}] OTHER ({msg_type_code}) | -> IGNORED")
        
        # Final summary
        elapsed = time.time() - start_time
        rate = msg_count / elapsed if elapsed > 0 else 0
        print(
            f"\n[COMPLETE] Processed {msg_count:,} total messages | "
            f"{trades_written:,} trades written | "
            f"Time: {elapsed:.1f}s | "
            f"Rate: {rate:,.0f} msg/s"
        )


def main():
    ap = argparse.ArgumentParser(
        description="Convert NASDAQ ITCH trade messages to Strategy Studio trade (T) ticks."
    )
    ap.add_argument("itch_file", help="Path to raw ITCH 5.0 binary file")
    ap.add_argument("symbol", help="Symbol to filter on, e.g. USO")
    ap.add_argument("trade_date", help="Trading date in YYYY-MM-DD (UTC)")
    ap.add_argument(
        "-o",
        "--output",
        default="trade_SYMBOL_YYYYMMDD.txt",
        help="Output trade file (default: trade_SYMBOL_YYYYMMDD.txt)",
    )
    ap.add_argument(
        "--market-center",
        default="NASDAQ",
        help="Market center string for Strategy Studio (default: NASDAQ)",
    )
    ap.add_argument(
        "--trade-types",
        nargs="+",
        choices=['P', 'Q', 'C', 'E'],
        default=['P', 'E'],
        help="Trade message types to process: P (NonCrossTrade - hidden orders), "
              "E (OrderExecuted - visible orders, requires order book), "
              "C (OrderExecutedWithPrice - visible orders at different price), "
              "Q (CrossTrade - opening/closing crosses). Default: P E (captures all trades)",
    )
    ap.add_argument(
        "--no-cross-trades",
        action="store_true",
        help="Exclude cross trades (Q messages) even if Q is in --trade-types",
    )
    ap.add_argument(
        "--feed-type",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Feed type: 1=consolidated, 2=direct, 3=depth (default: 1)",
    )
    ap.add_argument(
        "--progress-interval",
        type=int,
        default=None,
        help="Print progress every N messages (e.g., 100000) (default: disabled)",
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information for ALL message types",
    )
    ap.add_argument(
        "--debug-types",
        nargs="+",
        metavar="TYPE",
        help="Print debug information for specific message types (P, Q, C, E)",
    )
    ap.add_argument(
        "--no-optimized",
        action="store_true",
        help="Disable performance optimizations",
    )
    args = ap.parse_args()
    
    # Process debug arguments
    debug_set = None
    if args.debug:
        debug_set = set()
    elif args.debug_types:
        debug_set = set(args.debug_types)
    
    # Process trade types
    trade_types = set(args.trade_types)
    include_cross = not args.no_cross_trades
    
    dump_trades(
        args.itch_file,
        args.symbol,
        args.output,
        args.trade_date,
        market_center=args.market_center,
        trade_types=trade_types,
        feed_type=args.feed_type,
        include_cross_trades=include_cross,
        progress_interval=args.progress_interval,
        debug=debug_set,
        optimized=not args.no_optimized,
    )


if __name__ == "__main__":
    main()

