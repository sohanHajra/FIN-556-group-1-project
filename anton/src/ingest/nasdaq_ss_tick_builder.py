#!/usr/bin/env python

import argparse
import csv
from datetime import datetime, date, timedelta

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
):
    symbol = symbol.upper()
    trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()

    parser = MessageParser()  # parse all ITCH messages
    book = PriceLevelBook()
    seq_num = 1  # synthetic sequence number

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
            ts_ns = msg.timestamp
            level_event = None
            reason = 1  # UNATTRIBUTED_CHANGE by default

            # --- ADD ORDERS: only place we look at symbol (stock) ---
            if isinstance(msg, (AddOrderNoMPIAttributionMessage, AddOrderMPIDAttribution)):
                dec = msg.decode()
                stock = dec.stock.strip().upper()
                if stock != symbol:
                    continue  # ignore other symbols

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

            # --- EXECUTIONS (E/C) ---
            elif isinstance(msg, (OrderExecutedMessage, OrderExecutedWithPriceMessage)):
                dec = msg.decode()
                executed = dec.executed_shares
                level_event = book.on_exec(dec.order_reference_number, executed)
                reason = 5  # EXECUTED

            # --- PARTIAL CANCEL (X) ---
            elif isinstance(msg, OrderCancelMessage):
                dec = msg.decode()
                canceled = dec.cancelled_shares  # NOTE: field name from your decoder
                level_event = book.on_cancel(dec.order_reference_number, canceled)
                reason = 3  # PARTIAL_CANCEL

            # --- FULL DELETE (D) ---
            elif isinstance(msg, OrderDeleteMessage):
                dec = msg.decode()
                level_event = book.on_delete(dec.order_reference_number)
                reason = 4  # FULL_CANCEL

            # --- REPLACE (U) ---
            elif isinstance(msg, OrderReplaceMessage):
                dec = msg.decode()
                level_event = book.on_replace(
                    dec.order_reference_number,
                    dec.new_order_reference_number,
                    dec.price,
                    dec.shares,
                )
                reason = 8  # CANCEL_REPLACE

            # Nothing relevant to this symbol
            if level_event is None:
                continue

            # on_replace can return a list of events, others return a single tuple
            if isinstance(level_event, list):
                events = level_event
            else:
                events = [level_event]

            for side, price, size, num_orders in events:
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
