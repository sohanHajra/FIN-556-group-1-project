#!/usr/bin/env python

import argparse
import csv
from itch.parser import MessageParser
from itch.messages import NonCrossTradeMessage  # Type 'P'


def dump_trades(itch_path: str, symbol: str, out_csv: str):
    symbol = symbol.upper()
    parser = MessageParser(message_type=b"P")  # Only parse NonCrossTrade (P) messages

    with open(itch_path, "rb") as f, open(out_csv, "w", newline="") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(["ts_ns", "symbol", "price", "shares"])

        for msg in parser.parse_file(f):
            # We only asked for 'P' messages, so all should be NonCrossTradeMessage
            if not isinstance(msg, NonCrossTradeMessage):
                continue

            dec = msg.decode()   # get nice dataclass with Python types
            stock = dec.stock.strip().upper()  # e.g. "SPY"

            if stock != symbol:
                continue

            ts_ns = msg.timestamp          # nanoseconds since midnight
            price = dec.price              # float
            shares = dec.shares            # int

            writer.writerow([ts_ns, stock, price, shares])


def main():
    ap = argparse.ArgumentParser(
        description="Dump trades for a single symbol from a raw ITCH file."
    )
    ap.add_argument("itch_file", help="Path to raw ITCH 5.0 binary file")
    ap.add_argument("symbol", help="Symbol to filter on, e.g. SPY")
    ap.add_argument(
        "-o", "--output",
        default="trades.csv",
        help="Output CSV path (default: trades.csv)",
    )
    args = ap.parse_args()

    dump_trades(args.itch_file, args.symbol, args.output)


if __name__ == "__main__":
    main()
