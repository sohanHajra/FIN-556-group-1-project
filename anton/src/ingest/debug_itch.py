#!/usr/bin/env python
"""
Print the first N decoded ITCH messages from a raw ITCH file.
Useful for verifying that MoldUDP64 → itchfeed framing is correct.
"""

import argparse
from itch.parser import MessageParser


def debug_dump(itch_path: str, limit: int = 20):
    parser = MessageParser()  # parse ALL message types

    print(f"Reading: {itch_path}")
    print(f"--- First {limit} ITCH messages ---")

    count = 0

    with open(itch_path, "rb") as f:
        for msg in parser.parse_file(f):
            dec = msg.decode()

            mtype = msg.message_type.decode()   # e.g., 'S', 'R', 'A', 'P'
            ts_ns = msg.timestamp

            # Most messages have a 'stock' field, some don't (e.g., SystemEvent)
            stock = getattr(dec, "stock", "").strip() if hasattr(dec, "stock") else ""

            # Optional price field (only exists on some messages)
            price = getattr(dec, "price", None)

            print(f"{count:02d}: type={mtype}, ts={ts_ns}, stock={stock}, price={price}")

            count += 1
            if count >= limit:
                break

    print("--- End ---")


def main():
    ap = argparse.ArgumentParser(description="Debug dump first ITCH messages")
    ap.add_argument("itch_file", help="Raw ITCH file path")
    ap.add_argument("-n", "--num", type=int, default=20,
                    help="How many messages to print (default 20)")
    args = ap.parse_args()

    debug_dump(args.itch_file, args.num)


if __name__ == "__main__":
    main()
