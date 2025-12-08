#!/usr/bin/env python
"""
Batch processor for multiple NASDAQ ITCH files across date ranges.

Processes all .zst files in date-organized folders for a given date range.

EXAMPLES:
    # Process all files from 2025-04-01 to 2025-04-02 for USO
    python batch_process.py USO 20250401 20250402
    
    # Process trades only for a single day
    python batch_process.py SPY 20250401 20250401 --trades
    
    # Process both ticks and trades for date range
    python batch_process.py USO 20250401 20250405 --both
    
    # Skip steps if intermediate files exist (faster re-runs)
    python batch_process.py USO 20250401 20250402 --skip-decompress --skip-pcap
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Import the main processing functions from process.py
from process import (
    run_tick_builder,
    run_trade_builder,
)
from process_nasdaq import (
    extract_date_from_filename,
    DEFAULT_MARKET_CENTER,
    DEFAULT_PROGRESS_INTERVAL,
)
from config import NASDAQ_PCAPS_DIR
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


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYYMMDD format."""
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYYMMDD (e.g., 20250401)")


def get_date_range(start_date_str: str, end_date_str: str) -> list[str]:
    """Generate list of date strings (YYYYMMDD) from start to end (inclusive)."""
    start = parse_date(start_date_str)
    end = parse_date(end_date_str)
    
    if start > end:
        raise ValueError(f"Start date {start_date_str} must be <= end date {end_date_str}")
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    return dates


def find_zst_files(date_folder: Path) -> list[Path]:
    """Find all .zst files in a date folder, sorted by filename."""
    if not date_folder.exists():
        return []
    
    zst_files = sorted(date_folder.glob("*.pcap.zst"))
    return zst_files


def process_single_file(
    zst_file: Path,
    symbol: str,
    output_dir: Path,
    generate_ticks: bool,
    generate_trades: bool,
    progress_interval: int,
    skip_decompress: bool,
    skip_pcap: bool,
):
    """Process a single .zst file using the same logic as process.py."""
    
    # Extract date and time from filename
    trade_date = extract_date_from_filename(zst_file.name)
    if not trade_date:
        print(f"⚠ WARNING: Could not extract date from {zst_file.name}, skipping")
        return False
    
    date_str = trade_date.replace("-", "")
    _, time_str = extract_datetime_from_filename(zst_file.name)
    
    # Determine intermediate file paths
    input_stem = zst_file.stem  # Remove .zst
    if zst_file.suffix == '.zst':
        input_stem = Path(input_stem).stem  # Remove .pcap if it was .pcap.zst
    
    # Organize PCAP files by date
    pcap_dir = output_dir / "pcap_decompressed" / date_str
    pcap_dir.mkdir(parents=True, exist_ok=True)
    
    if time_str:
        pcap_filename = f"{input_stem}T{time_str}.pcap"
    else:
        pcap_filename = f"{input_stem}.pcap"
    pcap_path = pcap_dir / pcap_filename
    
    # Organize ITCH files by date
    itch_dir = output_dir / "itch_converted_pcaps" / date_str
    itch_dir.mkdir(parents=True, exist_ok=True)
    
    if time_str:
        itch_filename = f"{input_stem}T{time_str}.itch"
    else:
        itch_filename = f"{input_stem}.itch"
    itch_path = itch_dir / itch_filename
    
    print(f"\n{'='*80}")
    print(f"Processing: {zst_file.name}")
    print(f"Date: {trade_date} | Time: {time_str if time_str else 'N/A'}")
    print(f"{'='*80}")
    
    # Step 1: Decompress .zst to .pcap
    if not skip_decompress:
        print(f"[STEP 1] Decompressing .zst → .pcap")
        try:
            decompress_zst(zst_file, pcap_path)
        except Exception as e:
            print(f"✗ ERROR decompressing {zst_file.name}: {e}")
            return False
    else:
        if not pcap_path.exists():
            print(f"⚠ WARNING: PCAP file not found: {pcap_path}")
            print(f"  Skipping decompression step, but file doesn't exist")
            return False
        print(f"ℹ Skipping decompression (using existing: {pcap_path})")
    
    # Step 2: Convert .pcap to .itch
    if not skip_pcap:
        print(f"[STEP 2] Converting .pcap → .itch")
        try:
            pcap_to_itch(pcap_path, itch_path, udp_port=None)
        except Exception as e:
            print(f"✗ ERROR converting PCAP to ITCH: {e}")
            return False
    else:
        if not itch_path.exists():
            print(f"⚠ WARNING: ITCH file not found: {itch_path}")
            print(f"  Skipping PCAP conversion, but file doesn't exist")
            return False
        print(f"ℹ Skipping PCAP conversion (using existing: {itch_path})")
    
    # Step 3: Generate ticks and/or trades
    success = True
    
    if generate_ticks:
        try:
            run_tick_builder(itch_path, symbol, trade_date, output_dir, progress_interval, zst_file.name)
        except Exception as e:
            print(f"✗ ERROR generating ticks: {e}")
            success = False
    
    if generate_trades:
        try:
            run_trade_builder(itch_path, symbol, trade_date, output_dir, progress_interval, zst_file.name)
        except Exception as e:
            print(f"✗ ERROR generating trades: {e}")
            success = False
    
    # Cleanup: Delete .itch file after processing to save storage
    # Only delete if we created it (not if skip_pcap was used)
    if not skip_pcap and itch_path.exists():
        try:
            itch_path.unlink()
            print(f"ℹ Cleaned up intermediate file: {itch_path.name}")
        except Exception as e:
            print(f"⚠ WARNING: Could not delete .itch file: {e}")
    
    return success


def main():
    ap = argparse.ArgumentParser(
        description="Batch process NASDAQ ITCH files across date ranges",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    ap.add_argument(
        "symbol",
        help="Stock symbol to extract (e.g., USO, SPY)",
    )
    ap.add_argument(
        "start_date",
        help="Start date in YYYYMMDD format (e.g., 20250401)",
    )
    ap.add_argument(
        "end_date",
        help="End date in YYYYMMDD format (e.g., 20250402). Use same as start_date for single day.",
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
        help="Generate depth-by-price (P) ticks only (default if no mode specified)",
    )
    ap.add_argument(
        "--trades",
        action="store_true",
        help="Generate trade (T) ticks only",
    )
    ap.add_argument(
        "--both",
        action="store_true",
        help="Generate both depth-by-price (P) and trade (T) ticks",
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
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get date range
    try:
        dates = get_date_range(args.start_date, args.end_date)
    except ValueError as e:
        print(f"✗ ERROR: {e}")
        sys.exit(1)
    
    print("=" * 80)
    print("BATCH PROCESSING - NASDAQ ITCH Pipeline")
    print("=" * 80)
    print(f"Symbol:    {args.symbol}")
    print(f"Date range: {args.start_date} to {args.end_date} ({len(dates)} day(s))")
    print(f"Output:    {output_dir}")
    print(f"Mode:      ", end="")
    if generate_ticks and generate_trades:
        print("Both (P ticks + T trades)")
    elif generate_ticks:
        print("Depth-by-price (P) ticks")
    else:
        print("Trade (T) ticks")
    print("=" * 80)
    
    # Process each date
    total_files = 0
    successful_files = 0
    failed_files = 0
    
    for date_str in dates:
        date_folder = NASDAQ_PCAPS_DIR / date_str
        zst_files = find_zst_files(date_folder)
        
        if not zst_files:
            print(f"\n⚠ No .zst files found in {date_folder}")
            continue
        
        print(f"\n{'='*80}")
        print(f"Date: {date_str} | Found {len(zst_files)} file(s)")
        print(f"{'='*80}")
        
        for zst_file in zst_files:
            total_files += 1
            success = process_single_file(
                zst_file,
                args.symbol,
                output_dir,
                generate_ticks,
                generate_trades,
                args.progress_interval,
                args.skip_decompress,
                args.skip_pcap,
            )
            
            if success:
                successful_files += 1
            else:
                failed_files += 1
    
    # Final summary
    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Total files processed: {total_files}")
    print(f"Successful: {successful_files}")
    print(f"Failed: {failed_files}")
    print("=" * 80)


if __name__ == "__main__":
    main()

