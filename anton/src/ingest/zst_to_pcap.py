#!/usr/bin/env python
"""
Decompress Zstandard (.zst) compressed PCAP files to regular .pcap files.

This script automatically decompresses .zst files (like those from Databento)
into standard .pcap files that can be processed by pcap_to_itch_converter.py.
"""

import argparse
import time
from pathlib import Path

try:
    import zstandard as zstd
except ImportError:
    print("ERROR: zstandard library not found. Install it with:")
    print("  pip install zstandard")
    exit(1)


def decompress_zst(input_path: Path, output_path: Path | None = None, chunk_size: int = 1024 * 1024):
    """
    Decompress a .zst file to a .pcap file.
    
    Args:
        input_path: Path to the .zst file
        output_path: Optional output path. If None, auto-generates from input path
        chunk_size: Size of chunks to read/write (default: 1MB)
    
    Returns:
        Path to the output file
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if not input_path.suffix == '.zst':
        raise ValueError(f"Input file must have .zst extension: {input_path}")
    
    # Auto-generate output path if not provided
    if output_path is None:
        output_path = input_path.with_suffix('')  # Remove .zst extension
    
    # Ensure output path has .pcap extension if it doesn't already
    if output_path.suffix != '.pcap':
        output_path = output_path.with_suffix('.pcap')
    
    print(f"[START] Decompressing Zstandard file")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print()
    
    start_time = time.time()
    input_size = input_path.stat().st_size
    bytes_read = 0
    bytes_written = 0
    last_log_time = start_time
    
    # Create Zstandard decompressor
    dctx = zstd.ZstdDecompressor()
    
    with input_path.open("rb") as f_in, output_path.open("wb") as f_out:
        # Create streaming decompressor
        with dctx.stream_reader(f_in) as reader:
            while True:
                chunk = reader.read(chunk_size)
                if not chunk:
                    break
                
                f_out.write(chunk)
                bytes_read += len(chunk)
                bytes_written += len(chunk)
                
                # Progress logging every 10MB or every 5 seconds
                elapsed = time.time() - start_time
                if bytes_written - (bytes_written % (10 * 1024 * 1024)) >= 10 * 1024 * 1024 or \
                   time.time() - last_log_time >= 5.0:
                    rate = bytes_written / elapsed if elapsed > 0 else 0
                    compression_ratio = (1 - input_size / bytes_written) * 100 if bytes_written > 0 else 0
                    print(
                        f"[PROGRESS] Decompressed: {bytes_written / (1024*1024):.1f} MB | "
                        f"Time: {elapsed:.1f}s | "
                        f"Rate: {rate / (1024*1024):.1f} MB/s"
                    )
                    last_log_time = time.time()
    
    # Final summary
    elapsed = time.time() - start_time
    output_size = output_path.stat().st_size
    compression_ratio = (1 - input_size / output_size) * 100 if output_size > 0 else 0
    rate = output_size / elapsed if elapsed > 0 else 0
    
    print()
    print("=" * 80)
    print("[COMPLETE] Zstandard decompression finished")
    print("=" * 80)
    print(f"  Input file size:        {input_size / (1024*1024):.2f} MB")
    print(f"  Output file size:      {output_size / (1024*1024):.2f} MB")
    print(f"  Compression ratio:     {compression_ratio:.1f}%")
    print(f"  Processing time:      {elapsed:.1f}s")
    print(f"  Decompression rate:    {rate / (1024*1024):.1f} MB/s")
    print(f"  Output file:           {output_path}")
    print("=" * 80)
    
    return output_path


def main():
    ap = argparse.ArgumentParser(
        description="Decompress Zstandard (.zst) compressed PCAP files to regular .pcap files."
    )
    ap.add_argument(
        "input_file",
        type=Path,
        help="Path to .zst file to decompress",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .pcap file path (default: auto-generated from input filename)",
    )
    ap.add_argument(
        "--chunk-size",
        type=int,
        default=1024 * 1024,
        help="Chunk size for reading/writing in bytes (default: 1MB)",
    )
    args = ap.parse_args()
    
    try:
        output_path = decompress_zst(args.input_file, args.output, args.chunk_size)
        print(f"\n✓ Successfully decompressed to: {output_path}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()

