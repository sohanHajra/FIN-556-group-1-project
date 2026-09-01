# Strategy Studio Backtest Prerequisites

Before running venue arbitrage or ETF arbitrage strategies, you must configure Strategy Studio to point to your processed data and market centers.

## Required Configuration Steps

### 1. Configure Tick Data Directory

Edit `$HOME/ss/bt/backtester_config.txt` to point to the directory containing your processed tick data files.

**Example:**
```
/student_work/$USER/group_01_project/danny/merger/merged_data/
```

**Important:**
- The directory should contain `.txt.gz` files (compressed tick data)
- Files should be named with date prefixes (e.g., `combined_tick_20250401.txt.gz`)
- Use your actual username: replace `$USER` with your netid, or use the full path

**To find your data directory:**
```bash
# After processing and merging data, your files should be in:
ls -la danny/merger/merged_data/
```

### 2. Configure Market Centers

Edit `$HOME/ss/bt/preferred_feeds.csv` to include all market centers (venues) you're using.

**Required entries:**
- `NASDAQ` - For NASDAQ data
- `IEX` - For IEX data (if using cross-venue arbitrage)

### 3. Strategy Setup (Automated)

**You do NOT need to manually copy strategies anymore.** Use the automation scripts:

1. **Clone strategy template (one-time):**
   ```bash
   ./scripts/clone_strategy.sh --name venue_arb
   ```

2. **Deploy strategy (whenever you edit code):**
   ```bash
   ./scripts/deploy_strategy.sh --name venue_arb
   ```

The scripts automatically:
- Copy source files from `src/venue_arb/` to StrategyStudio directory
- Build the `.so` file
- Copy the `.so` to the backtest runtime directory

## Verification

### Check Configuration Files

```bash
# Verify backtester_config.txt points to correct directory
cat $HOME/ss/bt/backtester_config.txt

# Verify preferred_feeds.csv includes required market centers
cat $HOME/ss/bt/preferred_feeds.csv
```

### Verify Data Files Exist

```bash
# Check that processed data files exist
ls -lh /student_work/$USER/group_01_project/danny/merger/merged_data/*.txt.gz

# Or if using a different path, verify your configured path
ls -lh $(cat $HOME/ss/bt/backtester_config.txt | head -1)*.txt.gz
```

### Test Strategy Loading

```bash
# Start backtest server
./scripts/bt_server.sh start

# Recheck strategies
./scripts/bt_instance.sh recheck

# Check server logs for your strategy
./scripts/bt_server.sh logs | grep -i "venue_arb"
```

## Data Processing Pipeline

Before configuring Strategy Studio, ensure your data has been processed:

1. **Process NASDAQ data:** See [`anton/src/ingest/README.md`](../anton/src/ingest/README.md)
2. **Merge NASDAQ and IEX data:** See `danny/merger/` scripts
3. **Convert to Strategy Studio format:** See `danny/merger/merged_data/to_txtgz.sh`

## Common Issues

### "Cannot find tick data"

- Verify `backtester_config.txt` path is correct and absolute
- Check that `.txt.gz` files exist in the specified directory
- Ensure files are readable: `chmod +r *.txt.gz`

### "Market center not found"

- Verify `preferred_feeds.csv` includes all required market centers
- Check spelling matches exactly (e.g., "NASDAQ" not "Nasdaq")
- Restart backtest server after editing: `./scripts/bt_server.sh restart`

### "Strategy not found"

- Ensure you've cloned the strategy: `./scripts/clone_strategy.sh --name venue_arb`
- Deploy the strategy: `./scripts/deploy_strategy.sh --name venue_arb`
- Recheck strategies: `./scripts/bt_instance.sh recheck`

## See Also

- **[Strategy Studio Structure](ss_structure.md)** - Directory organization
- **[Strategy Studio Scripts README](../scripts/README.md)** - Complete automation guide
- **[Main Project README](../README.md)** - Data processing pipeline overview
