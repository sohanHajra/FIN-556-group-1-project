#!/usr/bin/env python
"""
Convert NASDAQ timestamps from EDT/EST to UTC in combined CSV files.

Processes files from output/combined/ and converts COLLECTION_TIME and SOURCE_TIME
columns from EDT/EST (adds 4 hours) to UTC, writing to output/converted_combined/.

EXAMPLES:
    # Process all files in output/combined/
    python utc_nasdaq_timestamp_converter.py
    
    # Process a specific file
    python utc_nasdaq_timestamp_converter.py --input output/combined/combined_tick_20250401.csv
    
    # Process all files for a specific date
    python utc_nasdaq_timestamp_converter.py --date 20250401
    
    # Custom input and output directories
    python utc_nasdaq_timestamp_converter.py --input-dir ./combined --output-dir ./converted
"""

import sys
import argparse
import pandas as pd
from pathlib import Path
from typing import Optional


def convert_timestamps_to_utc(
    input_file: Path,
    output_file: Path,
    hours_offset: int = 4,
) -> bool:
    """
    Convert timestamps in CSV file from EDT/EST to UTC.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
        hours_offset: Hours to add (default: 4 for EDT/EST to UTC)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read CSV file
        print(f"  Reading: {input_file.name}")
        df = pd.read_csv(input_file, parse_dates=["COLLECTION_TIME", "SOURCE_TIME"])
        
        # Convert timestamps to UTC by adding offset
        if "COLLECTION_TIME" in df.columns:
            df["COLLECTION_TIME"] = df["COLLECTION_TIME"] + pd.Timedelta(hours=hours_offset)
            print(f"    Converted COLLECTION_TIME to UTC (+{hours_offset} hours)")
        
        if "SOURCE_TIME" in df.columns:
            df["SOURCE_TIME"] = df["SOURCE_TIME"] + pd.Timedelta(hours=hours_offset)
            print(f"    Converted SOURCE_TIME to UTC (+{hours_offset} hours)")
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write output
        df.to_csv(output_file, index=False)
        print(f"  ✓ Wrote: {output_file.name} ({len(df)} rows)")
        return True
        
    except KeyError as e:
        print(f"  ✗ ERROR: Missing required column: {e}")
        return False
    except Exception as e:
        print(f"  ✗ ERROR processing {input_file.name}: {e}")
        return False


def process_file(input_file: Path, output_dir: Path, hours_offset: int = 4) -> bool:
    """Process a single file and write to output directory."""
    output_file = output_dir / input_file.name
    return convert_timestamps_to_utc(input_file, output_file, hours_offset)


def process_directory(
    input_dir: Path,
    output_dir: Path,
    date_filter: Optional[str] = None,
    hours_offset: int = 4,
) -> tuple[int, int]:
    """
    Process all CSV files in input directory.
    
    Args:
        input_dir: Directory containing CSV files to process
        output_dir: Directory to write converted files
        date_filter: Optional date string (YYYYMMDD) to filter files
        hours_offset: Hours to add for UTC conversion
    
    Returns:
        Tuple of (successful_count, failed_count)
    """
    if not input_dir.exists():
        print(f"✗ ERROR: Input directory not found: {input_dir}")
        return (0, 0)
    
    # Find all CSV files
    csv_files = sorted(input_dir.glob("*.csv"))
    
    if date_filter:
        # Filter files by date string in filename
        csv_files = [f for f in csv_files if date_filter in f.name]
    
    if not csv_files:
        print(f"⚠ WARNING: No CSV files found in {input_dir}")
        if date_filter:
            print(f"  (filtered by date: {date_filter})")
        return (0, 0)
    
    print(f"  Found {len(csv_files)} file(s) to process")
    
    successful = 0
    failed = 0
    
    for csv_file in csv_files:
        if process_file(csv_file, output_dir, hours_offset):
            successful += 1
        else:
            failed += 1
    
    return (successful, failed)


def main():
    ap = argparse.ArgumentParser(
        description="Convert NASDAQ timestamps from EDT/EST to UTC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    ap.add_argument(
        "--input",
        "--input-file",
        dest="input_file",
        type=Path,
        default=None,
        help="Specific input CSV file to process",
    )
    ap.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Input directory containing CSV files (default: output/combined/)",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for converted files (default: output/converted_combined/)",
    )
    ap.add_argument(
        "--date",
        type=str,
        default=None,
        help="Filter files by date in YYYYMMDD format (e.g., 20250401)",
    )
    ap.add_argument(
        "--hours-offset",
        type=int,
        default=4,
        help="Hours to add for UTC conversion (default: 4 for EDT/EST)",
    )
    
    args = ap.parse_args()
    
    # Determine project root
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    
    # Determine input path
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.is_absolute():
            input_path = PROJECT_ROOT / input_path
        if not input_path.exists():
            print(f"✗ ERROR: Input file not found: {input_path}")
            sys.exit(1)
        
        # Determine output path
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = PROJECT_ROOT / "output" / "converted_combined"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / input_path.name
        
        print("=" * 80)
        print("NASDAQ Timestamp UTC Converter")
        print("=" * 80)
        print(f"Input:  {input_path}")
        print(f"Output: {output_file}")
        print(f"Offset: +{args.hours_offset} hours")
        print("=" * 80)
        print()
        
        success = convert_timestamps_to_utc(input_path, output_file, args.hours_offset)
        sys.exit(0 if success else 1)
    
    else:
        # Process directory
        if args.input_dir:
            input_dir = Path(args.input_dir)
            if not input_dir.is_absolute():
                input_dir = PROJECT_ROOT / input_dir
        else:
            input_dir = PROJECT_ROOT / "output" / "combined"
        
        if args.output_dir:
            output_dir = Path(args.output_dir)
            if not output_dir.is_absolute():
                output_dir = PROJECT_ROOT / output_dir
        else:
            output_dir = PROJECT_ROOT / "output" / "converted_combined"
        
        print("=" * 80)
        print("NASDAQ Timestamp UTC Converter")
        print("=" * 80)
        print(f"Input:  {input_dir}")
        print(f"Output: {output_dir}")
        print(f"Offset: +{args.hours_offset} hours")
        if args.date:
            print(f"Filter: {args.date}")
        print("=" * 80)
        print()
        
        successful, failed = process_directory(
            input_dir,
            output_dir,
            date_filter=args.date,
            hours_offset=args.hours_offset,
        )
        
        print()
        print("=" * 80)
        print("CONVERSION COMPLETE")
        print("=" * 80)
        print(f"Successful: {successful}")
        print(f"Failed:     {failed}")
        print(f"Output:     {output_dir}")
        print("=" * 80)
        
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
