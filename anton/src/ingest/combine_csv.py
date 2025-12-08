#!/usr/bin/env python
"""
Combine CSV files by day for tick and trade messages.

Combines all tick CSV files in output/tick_messages/YYYYMMDD/ into one file per day.
Combines all trade CSV files in output/trade_messages/YYYYMMDD/ into one file per day.

EXAMPLES:
    # Combine files for a single day
    python combine_csv.py 20250401
    
    # Combine files for a date range
    python combine_csv.py 20250401 20250402
    
    # Combine only tick files
    python combine_csv.py 20250401 --ticks-only
    
    # Combine only trade files
    python combine_csv.py 20250401 --trades-only
    
    # Custom output directory
    python combine_csv.py 20250401 --output ./combined
"""

import sys
import argparse
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYYMMDD format."""
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYYMMDD (e.g., 20250401)")


def get_date_range(start_date_str: str, end_date_str: Optional[str] = None) -> list[str]:
    """Generate list of date strings (YYYYMMDD) from start to end (inclusive)."""
    start = parse_date(start_date_str)
    if end_date_str:
        end = parse_date(end_date_str)
        if start > end:
            raise ValueError(f"Start date {start_date_str} must be <= end date {end_date_str}")
    else:
        end = start
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    return dates


def parse_timestamp(row: dict, time_col: str = "COLLECTION_TIME") -> Optional[datetime]:
    """Parse timestamp from CSV row for sorting."""
    try:
        ts_str = row.get(time_col, "")
        if not ts_str:
            return None
        # Format: "2025-04-01 04:30:00.072353"
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
    except (ValueError, KeyError):
        return None


def combine_csv_files(
    input_dir: Path,
    output_file: Path,
    file_type: str = "tick",
    sort_by_time: bool = True,
):
    """
    Combine all CSV files in input_dir into a single output_file.
    
    Args:
        input_dir: Directory containing CSV files to combine
        output_file: Path to output combined CSV file
        file_type: Type of files ("tick" or "trade") for logging
        sort_by_time: Whether to sort rows by timestamp (default: True)
    """
    if not input_dir.exists():
        print(f"⚠ WARNING: Directory not found: {input_dir}")
        return False
    
    # Find all CSV files
    csv_files = sorted(input_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"⚠ WARNING: No CSV files found in {input_dir}")
        return False
    
    print(f"  Found {len(csv_files)} {file_type} file(s)")
    
    all_rows = []
    header = None
    files_processed = 0
    
    # Read all files
    for csv_file in csv_files:
        try:
            with open(csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                
                # Get header from first file
                if header is None:
                    header = reader.fieldnames
                    if header is None:
                        print(f"⚠ WARNING: No header in {csv_file.name}, skipping")
                        continue
                
                # Verify header matches
                if reader.fieldnames != header:
                    print(f"⚠ WARNING: Header mismatch in {csv_file.name}, skipping")
                    continue
                
                # Read all rows
                file_rows = list(reader)
                all_rows.extend(file_rows)
                files_processed += 1
                
        except Exception as e:
            print(f"⚠ WARNING: Error reading {csv_file.name}: {e}")
            continue
    
    if not all_rows:
        print(f"⚠ WARNING: No data rows found in {input_dir}")
        return False
    
    # Sort by timestamp if requested
    if sort_by_time and header and "COLLECTION_TIME" in header:
        print(f"  Sorting {len(all_rows)} rows by timestamp...")
        all_rows.sort(key=lambda row: parse_timestamp(row) or datetime.min)
    
    # Write combined file
    if header is None:
        print(f"✗ ERROR: No header found, cannot write output")
        return False
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(all_rows)
        
        print(f"  ✓ Combined {files_processed} files → {output_file.name} ({len(all_rows)} rows)")
        return True
    except Exception as e:
        print(f"✗ ERROR writing {output_file}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Combine CSV files by day for tick and trade messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    ap.add_argument(
        "start_date",
        help="Start date in YYYYMMDD format (e.g., 20250401)",
    )
    ap.add_argument(
        "end_date",
        nargs="?",
        default=None,
        help="End date in YYYYMMDD format (optional, defaults to start_date)",
    )
    ap.add_argument(
        "--output",
        "--output-dir",
        dest="output_dir",
        type=Path,
        default=None,
        help="Output directory for combined files (default: output/combined/)",
    )
    ap.add_argument(
        "--ticks-only",
        action="store_true",
        help="Combine only tick files",
    )
    ap.add_argument(
        "--trades-only",
        action="store_true",
        help="Combine only trade files",
    )
    ap.add_argument(
        "--no-sort",
        action="store_true",
        help="Don't sort by timestamp (faster, but files must already be in order)",
    )
    
    args = ap.parse_args()
    
    # Determine what to combine
    combine_ticks = not args.trades_only
    combine_trades = not args.ticks_only
    
    if not combine_ticks and not combine_trades:
        print("✗ ERROR: Must combine at least ticks or trades")
        sys.exit(1)
    
    # Get date range
    try:
        dates = get_date_range(args.start_date, args.end_date)
    except ValueError as e:
        print(f"✗ ERROR: {e}")
        sys.exit(1)
    
    # Determine output directory
    if args.output_dir:
        output_base = Path(args.output_dir)
    else:
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        output_base = PROJECT_ROOT / "output" / "combined"
    output_base.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("CSV File Combiner")
    print("=" * 80)
    print(f"Date range: {args.start_date} to {dates[-1]} ({len(dates)} day(s))")
    print(f"Output:    {output_base}")
    print(f"Mode:      ", end="")
    if combine_ticks and combine_trades:
        print("Both (ticks + trades)")
    elif combine_ticks:
        print("Ticks only")
    else:
        print("Trades only")
    print("=" * 80)
    print()
    
    # Process each date
    total_ticks = 0
    total_trades = 0
    successful_days = 0
    
    for date_str in dates:
        print(f"\n{'='*80}")
        print(f"Processing date: {date_str}")
        print(f"{'='*80}")
        
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        tick_dir = PROJECT_ROOT / "output" / "tick_messages" / date_str
        trade_dir = PROJECT_ROOT / "output" / "trade_messages" / date_str
        
        day_success = True
        
        # Combine tick files
        if combine_ticks:
            print(f"\n[TICKS] Combining files from: {tick_dir}")
            tick_output = output_base / f"combined_tick_{date_str}.csv"
            if combine_csv_files(tick_dir, tick_output, "tick", sort_by_time=not args.no_sort):
                total_ticks += 1
            else:
                day_success = False
        
        # Combine trade files
        if combine_trades:
            print(f"\n[TRADES] Combining files from: {trade_dir}")
            trade_output = output_base / f"combined_trade_{date_str}.csv"
            if combine_csv_files(trade_dir, trade_output, "trade", sort_by_time=not args.no_sort):
                total_trades += 1
            else:
                day_success = False
        
        if day_success:
            successful_days += 1
    
    # Final summary
    print("\n" + "=" * 80)
    print("COMBINING COMPLETE")
    print("=" * 80)
    print(f"Days processed: {len(dates)}")
    print(f"Successful days: {successful_days}")
    if combine_ticks:
        print(f"Combined tick files: {total_ticks}")
    if combine_trades:
        print(f"Combined trade files: {total_trades}")
    print(f"Output directory: {output_base}")
    print("=" * 80)


if __name__ == "__main__":
    main()

