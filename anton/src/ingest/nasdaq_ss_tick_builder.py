#!/usr/bin/env python

import argparse
import csv
import time
from datetime import datetime, date, timedelta
from typing import Optional

from itch.parser import MessageParser
from itch.messages import (
    AddOrderNoMPIAttributionMessage,   # A
    AddOrderMPIDAttribution,           # F
    OrderExecutedMessage,              # E
    OrderExecutedWithPriceMessage,     # C
    OrderCancelMessage,                # X
    OrderDeleteMessage,                # D
    OrderReplaceMessage,               # U,
)

# =====================================================================
# Time helper: ns since midnight -> 'YYYY-MM-DD HH:MM:SS.ffffff'
# =====================================================================

# ITCH gives timestamps which are nanoseconds since midnight
# SS needs full UTC datetime
def ns_since_midnight_to_str(trade_date: date, ts_ns: int) -> str:
    seconds = ts_ns // 1_000_000_000
    micros = (ts_ns % 1_000_000_000) // 1_000
    dt = datetime.combine(trade_date, datetime.min.time()) + timedelta(
        seconds=seconds,
        microseconds=micros,
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


# =====================================================================
# Simple price-level order book
# =====================================================================

# Maintaining my own in-memory order book
# orders = one entry pet ITCH order reference number
# side where 1=bid, and 2=ask
# levels aggregated by price level
class PriceLevelBook:
    """
    Maintains:
      - per-order state (id -> side, price, size)
      - aggregated price levels: side -> price -> {size, num_orders}

    SIDE: 1 = bid, 2 = ask (Strategy Studio convention)
    """

    def __init__(self):
        self.orders = {}             # order_id -> {"side": int, "price": float, "size": int}
        self.levels = {1: {}, 2: {}} # side -> price -> {"size": int, "num_orders": int}

    def _bump_level(self, side: int, price: float, d_size: int, d_orders: int):
        """
        Use to update or delete this price level
        
        Take a delta in d_size like (+100 or -50), and d_orders (+1, -1)
        
        Update level ->
            -> If level goes empty -> delete and emit (side,price,0,0)
            -> Otherwise -> emit (side,price,new_agg_size,new_num_orders) if something changed
            
        Triggers P writes for SS
            
        Return None if nothing changes
        """
        lvl = self.levels[side].get(price, {"size": 0, "num_orders": 0})
        old_size = lvl["size"]
        old_n = lvl["num_orders"]

        new_size = old_size + d_size
        new_n = old_n + d_orders

        # If level becomes empty, remove it and emit a "cleared" event
        if new_size <= 0 or new_n <= 0:
            if price in self.levels[side]:
                del self.levels[side][price]
                return side, price, 0, 0
            else:
                return None

        lvl["size"] = new_size
        lvl["num_orders"] = new_n
        self.levels[side][price] = lvl

        if new_size != old_size or new_n != old_n:
            return side, price, new_size, new_n
        return None

    # ---- ITCH ops ----

    # (A / F), create new order and bump that price
    def on_add(self, side: int, order_id: int, price: float, size: int):
        self.orders[order_id] = {"side": side, "price": price, "size": size}
        return self._bump_level(side, price, +size, +1)

    def on_exec(self, order_id: int, executed: int):
        o = self.orders.get(order_id)
        if not o:
            return None
        side, price = o["side"], o["price"]
        o["size"] -= executed
        d_size = -executed
        d_orders = 0
        if o["size"] <= 0:
            d_orders = -1
            del self.orders[order_id]
        return self._bump_level(side, price, d_size, d_orders)

    def on_cancel(self, order_id: int, canceled: int):
        o = self.orders.get(order_id)
        if not o:
            return None
        side, price = o["side"], o["price"]
        o["size"] -= canceled
        d_size = -canceled
        d_orders = 0
        if o["size"] <= 0:
            d_orders = -1
            del self.orders[order_id]
        return self._bump_level(side, price, d_size, d_orders)

    def on_delete(self, order_id: int):
        o = self.orders.get(order_id)
        if not o:
            return None
        side, price, size = o["side"], o["price"], o["size"]
        del self.orders[order_id]
        return self._bump_level(side, price, -size, -1)

    def on_replace(self, old_id: int, new_id: int, new_price: float, new_size: int):
        """
        CANCEL_REPLACE: remove old order, add new one.
        We may touch two levels (old price, new price), so return a list of events.
        """
        o = self.orders.get(old_id)
        if not o:
            return None

        side, old_price, old_size = o["side"], o["price"], o["size"]
        del self.orders[old_id]

        events = []

        evt1 = self._bump_level(side, old_price, -old_size, -1)
        if evt1 is not None:
            events.append(evt1)

        self.orders[new_id] = {"side": side, "price": new_price, "size": new_size}
        evt2 = self._bump_level(side, new_price, +new_size, +1)
        if evt2 is not None:
            events.append(evt2)

        if not events:
            return None
        return events

    def get_status(self, max_levels: int = 10) -> str:
        """
        Returns a formatted string showing the current order book state.
        
        Args:
            max_levels: Maximum number of price levels to show per side (default: 10)
        
        Returns:
            Formatted string with bid/ask levels and order count
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"ORDER BOOK STATUS")
        lines.append(f"  Total orders tracked: {len(self.orders)}")
        lines.append("-" * 80)
        
        # Get bid levels (side=1) sorted descending by price
        bid_levels = sorted(self.levels[1].items(), key=lambda x: x[0], reverse=True)
        # Get ask levels (side=2) sorted ascending by price
        ask_levels = sorted(self.levels[2].items(), key=lambda x: x[0])
        
        # Show ASKS first (on top), then BIDS (on bottom)
        # ASKS: display with highest at top, lowest at bottom (reverse of ascending sort)
        lines.append(f"\nASKS (side=2): {len(ask_levels)} levels")
        if ask_levels:
            lines.append(f"{'Price':>12} {'Size':>12} {'Orders':>8}")
            lines.append("-" * 32)
            # Reverse to show highest asks at top, lowest at bottom
            for price, level_info in reversed(ask_levels[:max_levels]):
                lines.append(
                    f"{price:>12.4f} {level_info['size']:>12} {level_info['num_orders']:>8}"
                )
            if len(ask_levels) > max_levels:
                lines.append(f"... ({len(ask_levels) - max_levels} more levels)")
        else:
            lines.append("  (no ask levels)")
        
        lines.append(f"\nBIDS (side=1): {len(bid_levels)} levels")
        if bid_levels:
            lines.append(f"{'Price':>12} {'Size':>12} {'Orders':>8}")
            lines.append("-" * 32)
            for price, level_info in bid_levels[:max_levels]:
                lines.append(
                    f"{price:>12.4f} {level_info['size']:>12} {level_info['num_orders']:>8}"
                )
            if len(bid_levels) > max_levels:
                lines.append(f"... ({len(bid_levels) - max_levels} more levels)")
        else:
            lines.append("  (no bid levels)")
        
        # Show best bid/ask if available
        if bid_levels and ask_levels:
            best_bid = bid_levels[0]
            best_ask = ask_levels[0]
            spread = best_ask[0] - best_bid[0]
            lines.append(f"\nBest Ask: {best_ask[0]:.4f} (size: {best_ask[1]['size']})")
            lines.append(f"Best Bid: {best_bid[0]:.4f} (size: {best_bid[1]['size']})")
            lines.append(f"Spread: {spread:.4f}")
        
        lines.append("=" * 80)
        return "\n".join(lines)

    def print_status(self, max_levels: int = 10):
        """Print the current order book status to stdout."""
        print(self.get_status(max_levels))


# =====================================================================
# Emit Strategy Studio Depth-by-Price (P) line
# =====================================================================

def emit_p_line(
    writer,
    trade_date: date,
    ts_ns: int,
    seq_num: int,
    market_center: str,
    side: int,
    price: float,
    size: int,
    num_orders: int,
    reason: int = 1,
    is_implied: int = 0,
    is_partial: int = 0,
):
    ts_str = ns_since_midnight_to_str(trade_date, ts_ns)
    row = [
        ts_str,                 # COLLECTION_TIME
        ts_str,                 # SOURCE_TIME
        str(seq_num),           # SEQ_NUM
        "P",                    # TICK_TYPE
        market_center,          # MARKET_CENTER
        str(side),              # SIDE (1=bid,2=ask)
        f"{price:.4f}",         # PRICE (tweak precision as needed)
        str(size),              # SIZE (agg)
        str(num_orders),        # NUM_ORDERS
        str(is_implied),        # IS_IMPLIED
        str(reason),            # REASON
        str(is_partial),        # IS_PARTIAL
    ]
    writer.writerow(row)


# =====================================================================
# Main conversion: ITCH -> Strategy Studio P ticks for one symbol
# =====================================================================

def dump_depth_by_price(
    itch_path: str,
    symbol: str,
    out_csv: str,
    trade_date: str,
    market_center: str = "NASDAQ",
    print_interval: Optional[int] = None,
    print_after_messages: Optional[int] = None,
    print_at_end: bool = False,
    max_levels: int = 10,
    progress_interval: Optional[int] = None,
    debug: bool = False,
):
    symbol = symbol.upper()
    trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()

    parser = MessageParser()  # parse all ITCH messages
    book = PriceLevelBook()
    seq_num = 1  # synthetic sequence number
    msg_count = 0  # count of messages processed for this symbol
    relevant_msg_count = 0  # count of messages that affected the book
    printed_after = False  # track if we've already printed after N messages
    start_time = time.time()  # track processing time

    with open(itch_path, "rb") as f, open(out_csv, "w", newline="") as out_file:
        writer = csv.writer(out_file)

        # Header (optional for Strategy Studio, useful for debug)
        writer.writerow(
            [
                "COLLECTION_TIME",
                "SOURCE_TIME",
                "SEQ_NUM",
                "TICK_TYPE",
                "MARKET_CENTER",
                "SIDE",
                "PRICE",
                "SIZE",
                "NUM_ORDERS",
                "IS_IMPLIED",
                "REASON",
                "IS_PARTIAL",
            ]
        )

        for msg in parser.parse_file(f):
            msg_count += 1
            
            # Print progress if interval is set
            if progress_interval is not None and msg_count > 0 and msg_count % progress_interval == 0:
                elapsed = time.time() - start_time
                rate = msg_count / elapsed if elapsed > 0 else 0
                ts_str = ns_since_midnight_to_str(trade_date_obj, msg.timestamp) if hasattr(msg, 'timestamp') else "N/A"
                print(
                    f"[PROGRESS] Messages: {msg_count:,} | "
                    f"Relevant: {relevant_msg_count:,} | "
                    f"Ticks written: {seq_num - 1:,} | "
                    f"Time: {elapsed:.1f}s | "
                    f"Rate: {rate:,.0f} msg/s | "
                    f"Current time: {ts_str}"
                )
            
            ts_ns = msg.timestamp
            ts_str = ns_since_midnight_to_str(trade_date_obj, ts_ns)
            level_event = None
            reason = 1  # UNATTRIBUTED_CHANGE by default
            msg_relevant = False
            msg_filtered = False

            # --- ADD ORDERS: only place we look at symbol (stock) ---
            if isinstance(msg, (AddOrderNoMPIAttributionMessage, AddOrderMPIDAttribution)):
                dec = msg.decode()
                stock = dec.stock.strip().upper()
                if debug:
                    print(f"[MSG {msg_count}] ADD_ORDER ({msg.message_type.decode()}) | "
                          f"Time: {ts_str} | Stock: {stock} | "
                          f"OrderRef: {dec.order_reference_number} | "
                          f"Side: {dec.buy_sell_indicator} | Price: {dec.price:.4f} | Size: {dec.shares}")
                
                if stock != symbol:
                    if debug:
                        print(f"  -> FILTERED (symbol mismatch: {stock} != {symbol})")
                    msg_filtered = True
                    continue  # ignore other symbols

                msg_relevant = True
                side = 1 if dec.buy_sell_indicator == "B" else 2
                price = dec.price
                size = dec.shares

                level_event = book.on_add(
                    side,
                    dec.order_reference_number,
                    price,
                    size,
                )
                reason = 2  # ADD_ORDER
                if debug:
                    print(f"  -> PROCESSED | Side: {side} | Level event: {level_event}")

            # --- EXECUTIONS (E/C) ---
            elif isinstance(msg, (OrderExecutedMessage, OrderExecutedWithPriceMessage)):
                dec = msg.decode()
                executed = dec.executed_shares
                if debug:
                    msg_type = "EXEC" if isinstance(msg, OrderExecutedMessage) else "EXEC_WITH_PRICE"
                    print(f"[MSG {msg_count}] {msg_type} ({msg.message_type.decode()}) | "
                          f"Time: {ts_str} | OrderRef: {dec.order_reference_number} | "
                          f"Executed: {executed}")
                
                level_event = book.on_exec(dec.order_reference_number, executed)
                if level_event is not None:
                    msg_relevant = True
                    if debug:
                        print(f"  -> PROCESSED | Level event: {level_event}")
                else:
                    if debug:
                        print(f"  -> FILTERED (order not in book)")
                    msg_filtered = True
                reason = 5  # EXECUTED

            # --- PARTIAL CANCEL (X) ---
            elif isinstance(msg, OrderCancelMessage):
                dec = msg.decode()
                canceled = dec.cancelled_shares  # NOTE: field name from your decoder
                if debug:
                    print(f"[MSG {msg_count}] CANCEL ({msg.message_type.decode()}) | "
                          f"Time: {ts_str} | OrderRef: {dec.order_reference_number} | "
                          f"Canceled: {canceled}")
                
                level_event = book.on_cancel(dec.order_reference_number, canceled)
                if level_event is not None:
                    msg_relevant = True
                    if debug:
                        print(f"  -> PROCESSED | Level event: {level_event}")
                else:
                    if debug:
                        print(f"  -> FILTERED (order not in book)")
                    msg_filtered = True
                reason = 3  # PARTIAL_CANCEL

            # --- FULL DELETE (D) ---
            elif isinstance(msg, OrderDeleteMessage):
                dec = msg.decode()
                if debug:
                    print(f"[MSG {msg_count}] DELETE ({msg.message_type.decode()}) | "
                          f"Time: {ts_str} | OrderRef: {dec.order_reference_number}")
                
                level_event = book.on_delete(dec.order_reference_number)
                if level_event is not None:
                    msg_relevant = True
                    if debug:
                        print(f"  -> PROCESSED | Level event: {level_event}")
                else:
                    if debug:
                        print(f"  -> FILTERED (order not in book)")
                    msg_filtered = True
                reason = 4  # FULL_CANCEL

            # --- REPLACE (U) ---
            elif isinstance(msg, OrderReplaceMessage):
                dec = msg.decode()
                if debug:
                    print(f"[MSG {msg_count}] REPLACE ({msg.message_type.decode()}) | "
                          f"Time: {ts_str} | OldOrderRef: {dec.order_reference_number} | "
                          f"NewOrderRef: {dec.new_order_reference_number} | "
                          f"Price: {dec.price:.4f} | Size: {dec.shares}")
                
                level_event = book.on_replace(
                    dec.order_reference_number,
                    dec.new_order_reference_number,
                    dec.price,
                    dec.shares,
                )
                if level_event is not None:
                    msg_relevant = True
                    if debug:
                        print(f"  -> PROCESSED | Level events: {level_event}")
                else:
                    if debug:
                        print(f"  -> FILTERED (order not in book)")
                    msg_filtered = True
                reason = 8  # CANCEL_REPLACE

            # --- OTHER MESSAGE TYPES ---
            else:
                if debug:
                    msg_type_name = msg.__class__.__name__ if hasattr(msg, '__class__') else "Unknown"
                    print(f"[MSG {msg_count}] OTHER ({msg.message_type.decode() if hasattr(msg, 'message_type') else '?'}) | "
                          f"Time: {ts_str} | Type: {msg_type_name} | -> IGNORED")

            # Nothing relevant to this symbol - skip emitting P ticks
            if level_event is None:
                if debug:
                    print(f"  -> NO LEVEL EVENT (skipping P tick emission)")
                continue

            relevant_msg_count += 1

            # on_replace can return a list of events, others return a single tuple
            if isinstance(level_event, list):
                events = level_event
            else:
                events = [level_event]

            if debug:
                print(f"  -> EMITTING {len(events)} P tick(s)")

            for side, price, size, num_orders in events:
                if debug:
                    side_name = "BID" if side == 1 else "ASK"
                    print(f"    P TICK #{seq_num}: {side_name} | Price: {price:.4f} | Size: {size} | Orders: {num_orders} | Reason: {reason}")
                emit_p_line(
                    writer,
                    trade_date_obj,
                    ts_ns,
                    seq_num,
                    market_center,
                    side,
                    price,
                    size,
                    num_orders,
                    reason=reason,
                    is_implied=0,
                    is_partial=0,
                )
                seq_num += 1

            # Print order book status if conditions are met
            should_print = False
            if print_after_messages is not None and not printed_after and relevant_msg_count >= print_after_messages:
                print(f"\n[After {relevant_msg_count} relevant messages]")
                should_print = True
                printed_after = True  # Only print once
            elif print_interval is not None and relevant_msg_count > 0 and relevant_msg_count % print_interval == 0:
                ts_str = ns_since_midnight_to_str(trade_date_obj, ts_ns)
                print(f"\n[At message {msg_count}, relevant: {relevant_msg_count}, time: {ts_str}]")
                should_print = True

            if should_print:
                book.print_status(max_levels=max_levels)

        # Print final summary
        elapsed = time.time() - start_time
        rate = msg_count / elapsed if elapsed > 0 else 0
        print(
            f"\n[COMPLETE] Processed {msg_count:,} total messages | "
            f"{relevant_msg_count:,} relevant | "
            f"{seq_num - 1:,} ticks written | "
            f"Time: {elapsed:.1f}s | "
            f"Rate: {rate:,.0f} msg/s"
        )
        
        # Print at end if requested
        if print_at_end:
            print(f"\n[ORDER BOOK STATUS AT END]")
            book.print_status(max_levels=max_levels)


def main():
    ap = argparse.ArgumentParser(
        description="Convert NASDAQ ITCH to Strategy Studio depth-by-price P ticks for a single symbol."
    )
    ap.add_argument("itch_file", help="Path to raw ITCH 5.0 binary file")
    ap.add_argument("symbol", help="Symbol to filter on, e.g. USO")
    ap.add_argument("trade_date", help="Trading date in YYYY-MM-DD (UTC)")
    ap.add_argument(
        "-o",
        "--output",
        default="tick_SYMBOL_YYYYMMDD.txt",
        help="Output tick file (default: tick_SYMBOL_YYYYMMDD.txt)",
    )
    ap.add_argument(
        "--market-center",
        default="NASDAQ",
        help="Market center string for Strategy Studio (default: NASDAQ)",
    )
    ap.add_argument(
        "--print-interval",
        type=int,
        default=None,
        help="Print order book status every N relevant messages (default: disabled)",
    )
    ap.add_argument(
        "--print-after",
        type=int,
        default=None,
        help="Print order book status after N relevant messages (default: disabled)",
    )
    ap.add_argument(
        "--print-at-end",
        action="store_true",
        help="Print order book status at end of processing",
    )
    ap.add_argument(
        "--max-levels",
        type=int,
        default=10,
        help="Maximum number of price levels to show per side when printing (default: 10)",
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
        help="Print debug information for every message processed",
    )
    args = ap.parse_args()

    dump_depth_by_price(
        args.itch_file,
        args.symbol,
        args.output,
        args.trade_date,
        market_center=args.market_center,
        print_interval=args.print_interval,
        print_after_messages=args.print_after,
        print_at_end=args.print_at_end,
        max_levels=args.max_levels,
        progress_interval=args.progress_interval,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
