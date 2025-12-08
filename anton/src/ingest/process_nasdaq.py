#!/usr/bin/env python
"""
Master script to automate the entire NASDAQ ITCH processing pipeline.

This script orchestrates:
1. Decompress .zst → .pcap (if input is .zst)
2. Convert .pcap → .itch
3. Convert .itch → Strategy Studio ticks

Usage:
    python process_nasdaq.py input_file.zst SYMBOL YYYY-MM-DD
    python process_nasdaq.py input_file.pcap SYMBOL YYYY-MM-DD
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Import configuration
try:
    from config import (
        DEFAULT_MARKET_CENTER,
        DEFAULT_PROGRESS_INTERVAL,
        DEFAULT_UDP_PORT,
        ensure_directories,
        get_input_file,
        get_output_file,
        NASDAQ_PCAPS_DIR,
        OUTPUT_DIR,
        PCAP_TO_ITCH_SCRIPT,
        SCRIPTS_DIR,
        ITCH_TO_TICKS_SCRIPT,
        ZST_TO_PCAP_SCRIPT,
    )
except ImportError:
    print("ERROR: Could not import config.py. Make sure it exists in the same directory.")
    sys.exit(1)


def run_command(cmd: list[str], description: str) -> bool:
    """
    Run a command and handle errors.
    
    Args:
        cmd: Command to run as list of strings
        description: Description of what the command does
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"[STEP] {description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error running command: {e}")
        return False
    except FileNotFoundError as e:
        print(f"\n✗ Script not found: {e}")
        print(f"  Make sure all scripts are in: {SCRIPTS_DIR}")
        return False


def extract_date_from_filename(filename: str) -> str | None:
    """
    Try to extract date from filename like: ny4-xnas-tvitch-a-20250401T083000.pcap.zst
    Returns YYYY-MM-DD format or None if not found.
    """
    # Look for pattern: YYYYMMDD
    import re
    match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    return None


def process_nasdaq_pipeline(
    input_file: str | Path,
    symbol: str,
    trade_date: str | None = None,
    output_dir: Path | None = None,
    udp_port: int | None = None,
    market_center: str = DEFAULT_MARKET_CENTER,
    progress_interval: int = DEFAULT_PROGRESS_INTERVAL,
    skip_decompress: bool = False,
    skip_pcap_to_itch: bool = False,
    skip_itch_to_ticks: bool = False,
):
    """
    Run the complete NASDAQ ITCH processing pipeline.
    
    Args:
        input_file: Input file (.zst or .pcap)
        symbol: Stock symbol (e.g., "USO", "SPY")
        trade_date: Trading date in YYYY-MM-DD format (auto-detected from filename if None)
        output_dir: Custom output directory (uses config default if None)
        udp_port: UDP port filter for PCAP processing
        market_center: Market center string for Strategy Studio
        progress_interval: Progress reporting interval
        skip_decompress: Skip .zst decompression step
        skip_pcap_to_itch: Skip PCAP to ITCH conversion
        skip_itch_to_ticks: Skip ITCH to ticks conversion
    """
    start_time = time.time()
    
    # Ensure directories exist
    ensure_directories()
    
    # Resolve input file path
    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = get_input_file(input_path.name)
    
    if not input_path.exists():
        print(f"✗ ERROR: Input file not found: {input_path}")
        sys.exit(1)
    
    # Use custom output dir or default
    if output_dir:
        output_base = Path(output_dir)
    else:
        output_base = OUTPUT_DIR
    
    output_base.mkdir(parents=True, exist_ok=True)
    
    # Determine file type and set up paths
    input_stem = input_path.stem  # filename without extension
    if input_path.suffix == '.zst':
        input_stem = Path(input_stem).stem  # Remove .pcap if it was .pcap.zst
    
    pcap_path = output_base / f"{input_stem}.pcap"
    itch_path = output_base / f"{input_stem}.itch"
    
    # Auto-detect trade date from filename if not provided
    if trade_date is None:
        trade_date = extract_date_from_filename(input_path.name)
        if trade_date:
            print(f"ℹ Auto-detected trade date from filename: {trade_date}")
        else:
            print("⚠ WARNING: Could not auto-detect trade date from filename.")
            print("  Please provide --trade-date YYYY-MM-DD")
            sys.exit(1)
    
    # Generate output tick file name
    date_str = trade_date.replace("-", "")
    tick_output = output_base / f"tick_{symbol}_{date_str}.txt"
    
    print("=" * 80)
    print("NASDAQ ITCH Processing Pipeline")
    print("=" * 80)
    print(f"Input file:      {input_path}")
    print(f"Symbol:          {symbol}")
    print(f"Trade date:      {trade_date}")
    print(f"Output base:     {output_base}")
    print(f"Intermediate files:")
    print(f"  PCAP:          {pcap_path}")
    print(f"  ITCH:          {itch_path}")
    print(f"Final output:    {tick_output}")
    print("=" * 80)
    
    # Step 1: Decompress .zst to .pcap (if needed)
    if not skip_decompress and input_path.suffix == '.zst':
        if not run_command(
            [
                sys.executable,
                str(ZST_TO_PCAP_SCRIPT),
                str(input_path),
                "-o",
                str(pcap_path),
            ],
            "Step 1: Decompress .zst to .pcap",
        ):
            print("\n✗ Pipeline failed at decompression step")
            sys.exit(1)
    elif input_path.suffix == '.pcap':
        # Input is already .pcap, use it directly
        pcap_path = input_path
        print(f"\nℹ Input is already .pcap, using: {pcap_path}")
    else:
        print(f"\n⚠ WARNING: Unexpected input file type: {input_path.suffix}")
        print("  Expected .zst or .pcap")
        sys.exit(1)
    
    # Step 2: Convert .pcap to .itch
    if not skip_pcap_to_itch:
        cmd = [
            sys.executable,
            str(PCAP_TO_ITCH_SCRIPT),
            str(pcap_path),
            str(itch_path),
        ]
        if udp_port is not None:
            cmd.extend(["--port", str(udp_port)])
        
        if not run_command(cmd, "Step 2: Convert .pcap to .itch"):
            print("\n✗ Pipeline failed at PCAP to ITCH conversion step")
            sys.exit(1)
    else:
        print(f"\nℹ Skipping PCAP to ITCH conversion (using existing: {itch_path})")
    
    # Step 3: Convert .itch to Strategy Studio ticks
    if not skip_itch_to_ticks:
        cmd = [
            sys.executable,
            str(ITCH_TO_TICKS_SCRIPT),
            str(itch_path),
            symbol,
            trade_date,
            "-o",
            str(tick_output),
            "--market-center",
            market_center,
            "--progress-interval",
            str(progress_interval),
        ]
        
        if not run_command(cmd, f"Step 3: Convert .itch to Strategy Studio ticks for {symbol}"):
            print("\n✗ Pipeline failed at ITCH to ticks conversion step")
            sys.exit(1)
    else:
        print(f"\nℹ Skipping ITCH to ticks conversion")
    
    # Final summary
    elapsed = time.time() - start_time
    print()
    print("=" * 80)
    print("✓ PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Total processing time: {elapsed:.1f}s")
    print(f"Final output: {tick_output}")
    print("=" * 80)


def main():
    ap = argparse.ArgumentParser(
        description="Automated NASDAQ ITCH processing pipeline: .zst/.pcap → .itch → Strategy Studio ticks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process .zst file (auto-detects date from filename)
  python process_nasdaq.py ny4-xnas-tvitch-a-20250401T083000.pcap.zst USO
  
  # Process .pcap file with explicit date
  python process_nasdaq.py file.pcap SPY --trade-date 2025-04-01
  
  # Custom output directory
  python process_nasdaq.py file.pcap.zst USO --output-dir ./output
  
  # Skip steps (if intermediate files already exist)
  python process_nasdaq.py file.pcap.zst USO --skip-decompress --skip-pcap-to-itch
        """,
    )
    ap.add_argument(
        "input_file",
        help="Input file (.zst or .pcap). Can be filename in nasdaq_pcaps/ or full path.",
    )
    ap.add_argument(
        "symbol",
        help="Stock symbol to extract (e.g., USO, SPY)",
    )
    ap.add_argument(
        "--trade-date",
        default=None,
        help="Trading date in YYYY-MM-DD format (auto-detected from filename if not provided)",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=f"Custom output directory (default: {OUTPUT_DIR})",
    )
    ap.add_argument(
        "--udp-port",
        type=int,
        default=DEFAULT_UDP_PORT,
        help="UDP port filter for PCAP processing (default: no filter)",
    )
    ap.add_argument(
        "--market-center",
        default=DEFAULT_MARKET_CENTER,
        help=f"Market center for Strategy Studio (default: {DEFAULT_MARKET_CENTER})",
    )
    ap.add_argument(
        "--progress-interval",
        type=int,
        default=DEFAULT_PROGRESS_INTERVAL,
        help=f"Progress reporting interval (default: {DEFAULT_PROGRESS_INTERVAL})",
    )
    ap.add_argument(
        "--skip-decompress",
        action="store_true",
        help="Skip .zst decompression step (use existing .pcap)",
    )
    ap.add_argument(
        "--skip-pcap-to-itch",
        action="store_true",
        help="Skip PCAP to ITCH conversion (use existing .itch)",
    )
    ap.add_argument(
        "--skip-itch-to-ticks",
        action="store_true",
        help="Skip ITCH to ticks conversion",
    )
    args = ap.parse_args()
    
    process_nasdaq_pipeline(
        input_file=args.input_file,
        symbol=args.symbol,
        trade_date=args.trade_date,
        output_dir=args.output_dir,
        udp_port=args.udp_port,
        market_center=args.market_center,
        progress_interval=args.progress_interval,
        skip_decompress=args.skip_decompress,
        skip_pcap_to_itch=args.skip_pcap_to_itch,
        skip_itch_to_ticks=args.skip_itch_to_ticks,
    )


if __name__ == "__main__":
    main()

