# Setup Guide - Portable Configuration

This guide explains how to set up the pipeline on different systems with different data directory locations.

## Quick Setup

### Option 1: Environment Variable (Recommended)

Set the environment variable before running scripts:

```bash
# Linux/Mac
export NASDAQ_PCAPS_DIR=/md/nasdaq_pcaps

# Windows (PowerShell)
$env:NASDAQ_PCAPS_DIR="C:\md\nasdaq_pcaps"

# Windows (CMD)
set NASDAQ_PCAPS_DIR=C:\md\nasdaq_pcaps
```

Then run scripts normally:
```bash
python process.py file.pcap.zst USO
python batch_process.py SPY 20250401 20250402
```

### Option 2: Edit config.py

Edit `src/ingest/config.py` line 32:

```python
# Change from:
NASDAQ_PCAPS_DIR = PROJECT_ROOT / "data" / "nasdaq_pcaps"

# To:
NASDAQ_PCAPS_DIR = Path("/md/nasdaq_pcaps")
```

## System Requirements

1. **Python 3.8+**
2. **Dependencies**: Install from `src/requirements.txt`
   ```bash
   pip install -r src/requirements.txt
   ```

## Directory Structure

The system expects data organized as:
```
/md/nasdaq_pcaps/          (or your configured path)
├── 20250401/
│   ├── ny4-xnas-tvitch-a-20250401T070000.pcap.zst
│   ├── ny4-xnas-tvitch-a-20250401T071000.pcap.zst
│   └── ...
├── 20250402/
│   └── ...
└── ...
```

## Verification

Check that the path is configured correctly:

```bash
python -c "from src.ingest.config import NASDAQ_PCAPS_DIR; print(f'Data directory: {NASDAQ_PCAPS_DIR}')"
```

## Notes

- The environment variable takes priority over the config file setting
- Output directory defaults to `output/` in project root (configurable via `--output` flag)
- All scripts automatically use the configured `NASDAQ_PCAPS_DIR` path

