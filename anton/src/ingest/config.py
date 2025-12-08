"""
Configuration file for NASDAQ ITCH processing pipeline.

Customize these paths to match your directory structure.
All paths can be absolute or relative to the project root.
"""

from pathlib import Path

# Project root directory (adjust if needed)
# This assumes the config file is in src/ingest/
PROJECT_ROOT = Path(__file__).parent.parent.parent

# =====================================================================
# Directory Configuration
# =====================================================================

# Input directories
NASDAQ_PCAPS_DIR = PROJECT_ROOT / "data" / "nasdaq_pcaps"
# Where .zst and .pcap files are stored

# Output directories
OUTPUT_DIR = PROJECT_ROOT / "data" / "nasdaq_pcaps"
# Where intermediate files (.pcap, .itch) and final outputs (.txt) are stored

# Scripts directory (where this file is located)
SCRIPTS_DIR = Path(__file__).parent

# Utils directory (where utility scripts are located)
UTILS_DIR = Path(__file__).parent.parent / "utils"

# =====================================================================
# Script Paths (relative to UTILS_DIR and SCRIPTS_DIR)
# =====================================================================

ZST_TO_PCAP_SCRIPT = UTILS_DIR / "zst_to_pcap.py"
PCAP_TO_ITCH_SCRIPT = UTILS_DIR / "pcap_to_itch_converter.py"
ITCH_TO_TICKS_SCRIPT = SCRIPTS_DIR / "nasdaq_ss_tick_builder.py"

# =====================================================================
# Default Settings
# =====================================================================

# Default UDP port for PCAP filtering (None = no filter)
DEFAULT_UDP_PORT = None

# Default market center for Strategy Studio
DEFAULT_MARKET_CENTER = "NASDAQ"

# Default progress interval for tick builder
DEFAULT_PROGRESS_INTERVAL = 100000

# =====================================================================
# Helper Functions
# =====================================================================

def get_input_file(input_name: str) -> Path:
    """
    Get full path to an input file in nasdaq_pcaps directory.
    
    Args:
        input_name: Filename (e.g., "file.pcap.zst" or "file.pcap")
    
    Returns:
        Full path to the input file
    """
    return NASDAQ_PCAPS_DIR / input_name


def get_output_file(output_name: str, subdir: str | None = None) -> Path:
    """
    Get full path to an output file.
    
    Args:
        output_name: Filename (e.g., "file.itch" or "tick_SPY.txt")
        subdir: Optional subdirectory (e.g., "ticks", "itch")
    
    Returns:
        Full path to the output file
    """
    if subdir:
        return OUTPUT_DIR / subdir / output_name
    return OUTPUT_DIR / output_name


def ensure_directories():
    """Create output directories if they don't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    NASDAQ_PCAPS_DIR.mkdir(parents=True, exist_ok=True)

