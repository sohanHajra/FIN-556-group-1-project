#!/usr/bin/env python

import argparse
import csv
from datetime import datetime, date, timedelta

from itch.parser import MessageParser
from itch.messages import (
    AddOrderNoMPIAttributionMessage,   # A
    AddOrderMPIDAttribution,          # F
    OrderExecutedMessage,             # E
    OrderExecutedWithPriceMessage,    # C
    OrderCancelMessage,               # X
    OrderDeleteMessage,               # D
    OrderReplaceMessage,              # U,
)

# ---------------------------------------------------------------------
# Utility: convert ns since midnight -> 'YYYY-MM-DD HH:MM:SS.ffffff'
# ---------------------------------------------------------------------
def ns_since_midnight_to_str(trade_date: date, ts_ns: int) -> str:
    seconds = ts_ns // 1_000_000_000
    micros  = (ts_ns % 1_000_000_000) // 1_000
    dt = datetime.combine(trade_date, datetime.min.time()) + timedelta(
        seconds=seconds,
        microseconds=micros
    )
    # Strategy Studio wants UTC; assume trade_date is already UTC
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


# ---------------------------------------------------------------------
# Simple price-level order book
# ---------------------------------------------------------------------
class PriceLevelBook:
    """
    Maintains:
      - per-order state (id -> side, price, size)
      - aggregated levels: side -> price -> {size, num_orders}

    SIDE: 1 = bid, 2 = ask  (Strategy Studio convention)
    """

    def __init__(self):
        self.orders = {}          # order_ref -> {"side": int, "price": float, "size": int}
        self.levels = {1: {}, 2: {}}  # side -> price -> {"size": int, "num_orders": int}

    def _bump_level(self, side: int, price: float, d_size: int, d_orders: int):
        lvl = self.levels[side].get(price, {"size": 0, "num_orders": 0})
        old_size = lvl["size"]
        old_n    = lvl["num_orders"]

        new_size = old_size + d_size
        new_n    = old_n + d_orders

        # Remove level if completely empty
        if new_size <= 0 or new_n <= 0:
            # if it didn't exist before, nothing to emit
            if price in self.levels[side]:
                del self.levels[side][price]
                return side, price, 0, 0      # level cleared -> SIZE = 0
            else:
                return None
        else:
            lvl["size"] = new_size
            lvl["num_orders"] = new_n
            self.levels[side][price] = lvl

        # Only emit if something changed
        if new_size != old_size or new_n != old_n:
            return side, price, new_size, new_n
        return None

    # ---- Handlers for ITCH messages ----

    def on_add(self, side: int, order_id: int, price: float, size: int):
        # new order
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
        # Remove old
        o = self.orders.get(old_id)
        if o:
            side, price, size = o["side"], o["price"], o["size"]
            del self.orders[old_id]
            evt1 = self._bump_level(side, price, -size, -1)
        else:
            # if somehow missing, treat as new
            side = None
            evt1 = None

        # Add new (if old existed, use same side)
        if side is None:
            return evt1

        self.orders[new_id] = {"side": side, "price": new_price, "size": new_size}
        evt2 = self._bump_level(side, new_price, +new_size, +1)
        # Could return both; for simplicity just return last non-None
        return evt2 or evt1


# ---------------------------------------------------------------------
# Emit Strategy Studio Depth-by-Price (P) line
# ---------------------------------------------------------------------
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
        ts_str,                 # SOURCE_TIME (same for offline)
        str(seq_num),           # SEQ_NUM
        "P",                    # TICK_TYPE
        market_center,          # MARKET_CENTER
        str(side),              # SIDE 1/2
        f"{price:.4f}",         # PRICE (adjust precision if needed)
        str(size),              # SIZE (agg at that level)
        str(num_orders),        # NUM_ORDERS
        str(is_implied),        # IS_IMPLIED
        str(reason),            # REASON
        str(is_partial),        # IS_PARTIAL
    ]
    writer.writerow(row)


# ---------------------------------------------------------------------
# Main: ITCH -> tick_SYMBOL_YYYYMMDD.txt (P lines)
# ---------------------------------------------------------------------
def dump_depth_by_price(itch_path: str, symbol: str, out_csv: str,
                        trade_date: str, market_center: str = "NASDAQ"):
    symbol = symbol.upper()
    trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()

    # Parse ALL messages (no message_type filter)
    parser = MessageParser()

    book = PriceLevelBook()
    seq_num = 1  # synthetic seq_num for Strategy Studio

    with open(itch_path, "rb") as f, open(out_csv, "w", newline="") as out_file:
        writer = csv.writer(out_file)

        # Strategy Studio P header is not strictly required, but helpful for debugging
        writer.writerow([
            "COLLECTION_TIME", "SOURCE_TIME", "SEQ_NUM", "TICK_TYPE",
            "MARKET_CENTER", "SIDE", "PRICE", "SIZE", "NUM_ORDERS",
            "IS_IMPLIED", "REASON", "IS_PARTIAL"
        ])

        for msg in parser.parse_file(f):
            # Only care about book-related messages
            if not isinstance(msg, (
                AddOrderNoMPIAttributionMessage,
                AddOrderMPIDAttribution,
                OrderExecutedMessage,
                OrderExecutedWithPriceMessage,
                OrderCancelMessage,
                OrderDeleteMessage,
                OrderReplaceMessage,
            )):
                continue

            dec = msg.decode()
            stock = dec.stock.strip().upper()
            if stock != symbol:
                continue

            ts_ns = msg.timestamp

            # Map message types to book ops
            level_event = None
            reason = 1  # UNATTRIBUTED_CHANGE by default

            if isinstance(msg, (AddOrderNoMPIAttributionMessage, AddOrderMPIDAttribution)):
                side = 1 if dec.buy_sell_indicator == "B" else 2
                price = dec.price
                size = dec.shares
                level_event = book.on_add(side, dec.order_reference_number, price, size)
                reason = 2  # ADD_ORDER

            elif isinstance(msg, (OrderExecutedMessage, OrderExecutedWithPriceMessage)):
                executed = dec.executed_shares
                level_event = book.on_exec(dec.order_reference_number, executed)
                # choose 5 or 6 depending on price match; keep simple:
                reason = 5  # EXECUTED

            elif isinstance(msg, OrderCancelMessage):
                canceled = dec.canceled_shares
                level_event = book.on_cancel(dec.order_reference_number, canceled)
                reason = 3  # PARTIAL_CANCEL

            elif isinstance(msg, OrderDeleteMessage):
                level_event = book.on_delete(dec.order_reference_number)
                reason = 4  # FULL_CANCEL

            elif isinstance(msg, OrderReplaceMessage):
                # replace: old_id -> new_id, new_price, new_size
                level_event = book.on_replace(
                    dec.order_reference_number, dec.new_order_reference_number,
                    dec.price, dec.shares
                )
                reason = 8  # CANCEL_REPLACE

            if level_event is not None:
                side, price, size, num_orders = level_event
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


def main():
    ap = argparse.ArgumentParser(
        description="Convert ITCH 5.0 to Strategy Studio depth-by-price P ticks for one symbol."
    )
    ap.add_argument("itch_file", help="Path to raw ITCH 5.0 binary file")
    ap.add_argument("symbol", help="Symbol to filter on, e.g. USO")
    ap.add_argument("trade_date", help="Trading date in YYYY-MM-DD (UTC)")
    ap.add_argument(
        "-o", "--output",
        default="tick_SYMBOL_YYYYMMDD.txt",
        help="Output tick file (default: tick_SYMBOL_YYYYMMDD.txt)",
    )
    ap.add_argument(
        "--market-center",
        default="NASDAQ",
        help="Market center name for Strategy Studio (default: NASDAQ)",
    )
    args = ap.parse_args()

    dump_depth_by_price(
        args.itch_file,
        args.symbol,
        args.output,
        args.trade_date,
        market_center=args.market_center,
    )


if __name__ == "__main__":
    main()
