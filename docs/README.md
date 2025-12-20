# Documentation Index

This directory contains additional documentation and serves as a central index to all README files throughout the project.

## Project Documentation

### Main Documentation

- **[Main Project README](../README.md)** - Comprehensive project overview, including:
  - Project overview and team biographies
  - Phase 1: Understanding PCAPs and Data Sources
  - NASDAQ Data Processing Pipeline
  - Phase 2: Strategy Studio Integration and Automation
  - Phase 3: The Strategies (Venue Arbitrage and ETF Arbitrage)
  - Key Technical Challenges & Solutions
  - Results and Performance
  - Conclusion and Summary

### Data Processing Documentation

- **[Anton's Data Processing Tools](../anton/README.md)** - Overview of data processing and visualization tools
- **[NASDAQ ITCH Processing Pipeline](../anton/src/ingest/README.md)** - Complete guide to processing NASDAQ ITCH data:
  - System requirements and installation
  - Quick start guide
  - Setup and configuration
  - Usage guide and batch processing
  - File combining and timestamp conversion
  - Output format specifications
  - Troubleshooting
- **[Event Stream Visualizer](../anton/src/visualize/README.md)** - Interactive visualization tool documentation:
  - Purpose and features
  - Installation and quick start
  - Interface guide
  - Data format requirements
  - Integration with processing pipeline
  - Examples and tips

### Strategy Studio Documentation

- **[Strategy Studio Scripts](../scripts/README.md)** - Automation scripts for Strategy Studio:
  - One-time setup
  - Daily workflow
  - Managing running strategies
  - Logs and debugging
  - Common problems & fixes
  - Strategy loading troubleshooting

### IEX Data Documentation

- **[IEX Downloader and Parser](../danny/IEX/iexdownloaderparser/README.md)** - Documentation for IEX data download and parsing tools

## Additional Documentation Files

This directory also contains:

- **[Strategy Studio Backtest Prerequisites](ss_backtest_prereqs.md)** - Prerequisites for running venue arbitrage strategies
- **[Strategy Studio Structure](ss_structure.md)** - Notes on Strategy Studio directory structure and workflow

## Quick Navigation by Task

### Getting Started
1. Read the [Main Project README](../README.md) for project overview
2. Review [Strategy Studio Scripts README](../scripts/README.md) for setup instructions
3. Check [Strategy Studio Backtest Prerequisites](ss_backtest_prereqs.md) for configuration

### Processing NASDAQ Data
1. Start with [Anton's Data Processing Tools](../anton/README.md) for overview
2. Follow [NASDAQ ITCH Processing Pipeline](../anton/src/ingest/README.md) for detailed instructions
3. Use [Event Stream Visualizer](../anton/src/visualize/README.md) to analyze results

### Working with Strategies
1. Review [Strategy Studio Scripts README](../scripts/README.md) for automation
2. Check [Strategy Studio Structure](ss_structure.md) for directory organization
3. See [Strategy Studio Backtest Prerequisites](ss_backtest_prereqs.md) for configuration

### Troubleshooting
- **Data Processing Issues**: See [NASDAQ ITCH Processing Pipeline Troubleshooting](../anton/src/ingest/README.md#troubleshooting)
- **Strategy Loading Issues**: See [Strategy Studio Scripts Troubleshooting](../scripts/README.md#strategy-not-loading-or-not-found)
- **Visualization Issues**: See [Event Stream Visualizer Troubleshooting](../anton/src/visualize/README.md#troubleshooting)

---

For questions or issues, refer to the specific README file for the component you're working with.

