#!/usr/bin/env python
"""
Simple entry point for NASDAQ ITCH processing pipeline.

EXAMPLES (copy-paste ready):
    
    # Generate depth-by-price ticks (default, fastest)
    # Output: output/tick_messages/YYYYMMDD/tick_SYMBOL_YYYYMMDDTHHMMSS.csv
    python process.py file.pcap.zst USO
    
    # Generate trade ticks only
    # Output: output/trade_messages/YYYYMMDD/trade_SYMBOL_YYYYMMDDTHHMMSS.csv
    python process.py file.pcap.zst USO --trades
    
    # Generate both ticks and trades
    # Output: output/tick_messages/YYYYMMDD/tick_SYMBOL_YYYYMMDDTHHMMSS.csv
    #         output/trade_messages/YYYYMMDD/trade_SYMBOL_YYYYMMDDTHHMMSS.csv
    python process.py file.pcap.zst USO --both
    
    # With explicit date (if auto-detection fails)
    python process.py file.pcap SPY --date 2025-04-01
    
    # Performance: show progress every 100k messages
    python process.py file.pcap.zst USO --progress 100000
    
    # Skip steps if intermediate files exist
    python process.py file.pcap.zst USO --skip-decompress --skip-pcap
    
    # Custom output directory
    python process.py file.pcap.zst USO --output ./output

PERFORMANCE TIPS:
    - Default progress interval: 100000 messages (good balance)
    - Optimizations enabled by default (10-20x faster)
    - Use --skip-* flags if intermediate files already exist
    - Processing ~1M messages/second on modern hardware
"""

import sys
import argparse
from pathlib import Path

# All imports at the top (all modules are in the same directory)
from process_nasdaq import (
    extract_date_from_filename,
    DEFAULT_MARKET_CENTER,
    DEFAULT_PROGRESS_INTERVAL,
)
from config import OUTPUT_DIR, NASDAQ_PCAPS_DIR
from nasdaq_ss_trade_builder import dump_trades
from nasdaq_ss_tick_builder import dump_depth_by_price
from zst_to_pcap import decompress_zst
from pcap_to_itch_converter import pcap_to_itch


def extract_datetime_from_filename(filename: str) -> tuple[str | None, str | None]:
    """
    Extract date and time from filename like: ny4-xnas-tvitch-a-20250401T083000.pcap.zst
    Returns: (YYYY-MM-DD, HHMMSS) or (None, None) if not found
    """
    import re
    # Look for pattern: YYYYMMDDTHHMMSS
    match = re.search(r'(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})', filename)
    if match:
        year, month, day, hour, minute, second = match.groups()
        date_str = f"{year}-{month}-{day}"
        time_str = f"{hour}{minute}{second}"
        return date_str, time_str
    # Fallback: just date YYYYMMDD
    match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        year, month, day = match.groups()
        date_str = f"{year}-{month}-{day}"
        return date_str, None
    return None, None


def run_trade_builder(itch_file: Path, symbol: str, trade_date: str, output_dir: Path, progress_interval: int, input_filename: str = ""):
    """Run the trade builder to generate trade ticks."""
    
    # Extract date and time from input filename
    _, time_str = extract_datetime_from_filename(input_filename)
    
    # Create date folder (YYYYMMDD)
    date_str = trade_date.replace("-", "")
    date_folder = output_dir / "trade_messages" / date_str
    date_folder.mkdir(parents=True, exist_ok=True)
    
    # Build filename with time if available
    if time_str:
        filename = f"trade_{symbol}_{date_str}T{time_str}.csv"
    else:
        filename = f"trade_{symbol}_{date_str}.csv"
    
    trade_output = date_folder / filename
    
    print("\n" + "=" * 80)
    print("[STEP] Generating Trade (T) Ticks")
    print("=" * 80)
    print(f"Input:  {itch_file}")
    print(f"Output: {trade_output}")
    print("=" * 80)
    print()
    
    dump_trades(
        str(itch_file),
        symbol,
        str(trade_output),
        trade_date,
        market_center=DEFAULT_MARKET_CENTER,
        trade_types={'P', 'E'},  # Default: all trades
        feed_type=1,
        include_cross_trades=True,
        progress_interval=progress_interval,
        debug=None,
        optimized=True,
    )
    
    return trade_output


def run_tick_builder(itch_file: Path, symbol: str, trade_date: str, output_dir: Path, progress_interval: int, input_filename: str = ""):
    """Run the tick builder to generate depth-by-price ticks."""
    
    # Extract date and time from input filename
    _, time_str = extract_datetime_from_filename(input_filename)
    
    # Create date folder (YYYYMMDD)
    date_str = trade_date.replace("-", "")
    date_folder = output_dir / "tick_messages" / date_str
    date_folder.mkdir(parents=True, exist_ok=True)
    
    # Build filename with time if available
    if time_str:
        filename = f"tick_{symbol}_{date_str}T{time_str}.csv"
    else:
        filename = f"tick_{symbol}_{date_str}.csv"
    
    tick_output = date_folder / filename
    
    print("\n" + "=" * 80)
    print("[STEP] Generating Depth-by-Price (P) Ticks")
    print("=" * 80)
    print(f"Input:  {itch_file}")
    print(f"Output: {tick_output}")
    print("=" * 80)
    print()
    
    dump_depth_by_price(
        str(itch_file),
        symbol,
        str(tick_output),
        trade_date,
        market_center=DEFAULT_MARKET_CENTER,
        print_interval=None,
        print_after_messages=None,
        print_at_end=False,
        max_levels=10,
        progress_interval=progress_interval,
        debug=None,
        optimized=True,
    )
    
    return tick_output


def main():
    ap = argparse.ArgumentParser(
        description="Process NASDAQ ITCH data: .zst/.pcap → Strategy Studio ticks/trades",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    ap.add_argument(
        "input_file",
        help="Input file (.zst or .pcap). Can be filename in data/nasdaq_pcaps/ or full path.",
    )
    ap.add_argument(
        "symbol",
        help="Stock symbol to extract (e.g., USO, SPY)",
    )
    ap.add_argument(
        "--date",
        "--trade-date",
        dest="trade_date",
        default=None,
        help="Trading date in YYYY-MM-DD format (auto-detected from filename if not provided)",
    )
    ap.add_argument(
        "--output",
        "--output-dir",
        dest="output_dir",
        type=Path,
        default=None,
        help="Custom output directory (default: output/ in project root)",
    )
    ap.add_argument(
        "--ticks",
        action="store_true",
        help="Generate depth-by-price (P) ticks only (default if no mode specified). Output: output/tick_messages/",
    )
    ap.add_argument(
        "--trades",
        action="store_true",
        help="Generate trade (T) ticks only. Output: output/trade_messages/",
    )
    ap.add_argument(
        "--both",
        action="store_true",
        help="Generate both depth-by-price (P) and trade (T) ticks. Outputs: output/tick_messages/ and output/trade_messages/",
    )
    ap.add_argument(
        "--progress",
        "--progress-interval",
        dest="progress_interval",
        type=int,
        default=DEFAULT_PROGRESS_INTERVAL,
        help=f"Progress reporting interval in messages (default: {DEFAULT_PROGRESS_INTERVAL})",
    )
    ap.add_argument(
        "--skip-decompress",
        action="store_true",
        help="Skip .zst decompression step (use existing .pcap)",
    )
    ap.add_argument(
        "--skip-pcap",
        action="store_true",
        help="Skip PCAP to ITCH conversion (use existing .itch)",
    )
    
    args = ap.parse_args()
    
    # Determine output mode
    if args.both:
        generate_ticks = True
        generate_trades = True
    elif args.trades:
        generate_ticks = False
        generate_trades = True
    elif args.ticks:
        generate_ticks = True
        generate_trades = False
    else:
        # Default: generate ticks only
        generate_ticks = True
        generate_trades = False
    
    # Resolve input file
    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = NASDAQ_PCAPS_DIR / args.input_file
    
    if not input_path.exists():
        print(f"✗ ERROR: Input file not found: {input_path}")
        print(f"  Searched in: {NASDAQ_PCAPS_DIR}")
        sys.exit(1)
    
    # Auto-detect trade date if not provided
    trade_date = args.trade_date
    if trade_date is None:
        trade_date = extract_date_from_filename(input_path.name)
        if trade_date:
            print(f"ℹ Auto-detected trade date: {trade_date}")
        else:
            print("✗ ERROR: Could not auto-detect trade date from filename.")
            print("  Please provide --date YYYY-MM-DD")
            sys.exit(1)
    
    # Determine output directory
    # Default to PROJECT_ROOT / "output" if not specified
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine intermediate file paths with date-organized folders
    input_stem = input_path.stem
    if input_path.suffix == '.zst':
        input_stem = Path(input_stem).stem
    
    # Extract date and time for folder organization
    date_str = trade_date.replace("-", "")
    _, time_str = extract_datetime_from_filename(input_path.name)
    
    # Organize PCAP files by date: output/pcap_decompressed/YYYYMMDD/
    pcap_dir = output_dir / "pcap_decompressed" / date_str
    pcap_dir.mkdir(parents=True, exist_ok=True)
    
    # Build PCAP filename with time if available
    if time_str:
        pcap_filename = f"{input_stem}T{time_str}.pcap"
    else:
        pcap_filename = f"{input_stem}.pcap"
    pcap_path = pcap_dir / pcap_filename
    
    # Organize ITCH files by date: output/itch_converted_pcaps/YYYYMMDD/
    itch_dir = output_dir / "itch_converted_pcaps" / date_str
    itch_dir.mkdir(parents=True, exist_ok=True)
    
    # Build ITCH filename with time if available
    if time_str:
        itch_filename = f"{input_stem}T{time_str}.itch"
    else:
        itch_filename = f"{input_stem}.itch"
    itch_path = itch_dir / itch_filename
    
    # Print summary
    print("=" * 80)
    print("NASDAQ ITCH Processing Pipeline")
    print("=" * 80)
    print(f"Input:     {input_path}")
    print(f"Symbol:    {args.symbol}")
    print(f"Date:      {trade_date}")
    print(f"Output:    {output_dir}")
    # Extract date for folder structure display
    date_str = trade_date.replace("-", "")
    _, time_str = extract_datetime_from_filename(input_path.name)
    
    print(f"Intermediate files:")
    print(f"  PCAP:    {output_dir / 'pcap_decompressed' / date_str}")
    print(f"  ITCH:    {output_dir / 'itch_converted_pcaps' / date_str}")
    print(f"Mode:      ", end="")
    if generate_ticks and generate_trades:
        print("Both (P ticks + T trades)")
        print(f"           → {output_dir / 'tick_messages' / date_str}")
        print(f"           → {output_dir / 'trade_messages' / date_str}")
    elif generate_ticks:
        print("Depth-by-price (P) ticks")
        print(f"           → {output_dir / 'tick_messages' / date_str}")
    else:
        print("Trade (T) ticks")
        print(f"           → {output_dir / 'trade_messages' / date_str}")
    print(f"Progress:  Every {args.progress_interval:,} messages")
    print("=" * 80)
    print()
    
    # Step 1: Decompress .zst to .pcap (if needed)
    if not args.skip_decompress and input_path.suffix == '.zst':
        print("=" * 80)
        print("[STEP 1] Decompressing .zst → .pcap")
        print("=" * 80)
        decompress_zst(input_path, pcap_path)
        print()
    elif input_path.suffix == '.pcap':
        # If input is already .pcap, we still need to organize the output ITCH file
        # But we'll use the input pcap as-is (don't copy it)
        pcap_path = input_path
        print(f"ℹ Input is already .pcap, using: {pcap_path}\n")
        print(f"ℹ ITCH output will be saved to: {itch_path}\n")
    
    # Step 2: Convert .pcap to .itch
    if not args.skip_pcap:
        print("=" * 80)
        print("[STEP 2] Converting .pcap → .itch")
        print("=" * 80)
        pcap_to_itch(pcap_path, itch_path, udp_port=None)
        print()
    else:
        print(f"ℹ Skipping PCAP conversion (using existing: {itch_path})\n")
    
    # Step 3: Generate ticks and/or trades
    outputs = []
    
    # Pass input filename to extract time information
    input_filename = input_path.name
    
    if generate_ticks:
        tick_output = run_tick_builder(itch_path, args.symbol, trade_date, output_dir, args.progress_interval, input_filename)
        outputs.append(("Depth-by-price ticks", tick_output))
    
    if generate_trades:
        trade_output = run_trade_builder(itch_path, args.symbol, trade_date, output_dir, args.progress_interval, input_filename)
        outputs.append(("Trade ticks", trade_output))
    
    # Cleanup: Delete .itch file after processing to save storage
    # Only delete if we created it (not if --skip-pcap was used)
    if not args.skip_pcap and itch_path.exists():
        try:
            itch_path.unlink()
            print(f"ℹ Cleaned up intermediate file: {itch_path.name}")
        except Exception as e:
            print(f"⚠ WARNING: Could not delete .itch file: {e}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("✓ PIPELINE COMPLETE")
    print("=" * 80)
    print("Generated files:")
    for name, path in outputs:
        print(f"  {name:25} {path}")
    print("=" * 80)


if __name__ == "__main__":
    main()

