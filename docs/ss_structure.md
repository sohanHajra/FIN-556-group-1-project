# Strategy Studio Directory Structure

This document describes the Strategy Studio directory structure and how the project integrates with it.

## Overview

The project uses a **source-of-truth** approach where:
- **Strategy source code** lives in `src/` (this repository)
- **StrategyStudio directories** are treated as build/deploy targets
- **Automation scripts** handle copying, building, and running

You should **never manually edit StrategyStudio files** - use the provided scripts instead.

## Key Strategy Studio Directories

### Strategy Source Code Location
```
$HOME/ss/sdk/RCM/StrategyStudio/examples/strategies/
├── venue_arb/              # Strategy directory (created by clone_strategy.sh)
│   ├── venue_arb.cpp       # Copied from src/venue_arb/venue_arb.cpp
│   ├── venue_arb.h         # Copied from src/venue_arb/venue_arb.h
│   ├── Makefile            # Auto-updated by clone_strategy.sh
│   └── venue_arb.so        # Built output (after make)
```

**Note:** Strategies are cloned from templates (e.g., `dia_index_arb_strategy`) using `./scripts/clone_strategy.sh`.

### Backtest Runtime Directory
```
$HOME/ss/bt/
├── StrategyServerBacktesting    # Backtest server executable
├── utilities/
│   └── StrategyCommandLine      # CLI tool for managing instances
├── backtester_config.txt        # Points to tick data directory
├── preferred_feeds.csv           # Market center configuration
└── backtesting-results/         # CRA files (backtest results)
```

## Workflow

### Initial Setup (One-Time)

1. **Clone strategy template:**
   ```bash
   ./scripts/clone_strategy.sh --name venue_arb
   ```
   This creates the StrategyStudio directory and sets up the Makefile.

2. **Configure data paths:**
   - Edit `$HOME/ss/bt/backtester_config.txt` to point to your tick data
   - Edit `$HOME/ss/bt/preferred_feeds.csv` to include market centers (e.g., NASDAQ, IEX)

### Daily Development Workflow

1. **Edit code in repository:**
   ```bash
   # Edit files in src/venue_arb/
   vim src/venue_arb/venue_arb.cpp
   ```

2. **Deploy and build:**
   ```bash
   ./scripts/deploy_strategy.sh --name venue_arb
   ```
   This:
   - Copies `.cpp` and `.h` from `src/` to StrategyStudio directory
   - Runs `make` to build the `.so` file
   - Runs `make copy_strategy` to copy `.so` to backtest runtime directory

3. **Run backtest:**
   ```bash
   ./scripts/run_strategy.sh run
   ```

## Important Paths

| Purpose | Path |
|---------|------|
| Strategy source code (edit here) | `group_01_project/src/venue_arb/` |
| StrategyStudio strategy directory | `$HOME/ss/sdk/RCM/StrategyStudio/examples/strategies/venue_arb/` |
| Compiled strategy library | `$HOME/StrategyStudio/Backtesting/Strategies/venue_arb.so` |
| Backtest server | `$HOME/ss/bt/StrategyServerBacktesting` |
| Backtest configuration | `$HOME/ss/bt/backtester_config.txt` |
| Market center config | `$HOME/ss/bt/preferred_feeds.csv` |
| Backtest results | `$HOME/ss/bt/backtesting-results/` |
| Server logs | `/student_work/$USER/ss_logs/bt_server.log` |

## Build Process

When you run `./scripts/deploy_strategy.sh --name venue_arb`:

1. **Copy source files:**
   - `src/venue_arb/venue_arb.cpp` → `$HOME/ss/sdk/.../strategies/venue_arb/venue_arb.cpp`
   - `src/venue_arb/venue_arb.h` → `$HOME/ss/sdk/.../strategies/venue_arb/venue_arb.h`

2. **Build:**
   - Runs `make` in the strategy directory
   - Produces `venue_arb.so`

3. **Install:**
   - Runs `make copy_strategy`
   - Copies `venue_arb.so` to `$HOME/StrategyStudio/Backtesting/Strategies/`

4. **Load:**
   - Backtest server loads `.so` files from `$HOME/StrategyStudio/Backtesting/Strategies/`
   - Use `./scripts/bt_instance.sh recheck` to force reload

## Strategy Exports

Each strategy must export these functions (defined in the `.h` file):

```cpp
extern "C" {
    _STRATEGY_EXPORTS const char* GetType() {
        return "venue_arb";  // Must match strategy name used in scripts
    }
    
    _STRATEGY_EXPORTS IStrategy* CreateStrategy(...) { ... }
    _STRATEGY_EXPORTS const char* GetAuthor() { ... }
    _STRATEGY_EXPORTS const char* GetAuthorGroup() { ... }
    _STRATEGY_EXPORTS const char* GetReleaseVersion() { ... }
}
```

The `GetType()` return value **must exactly match** the strategy name used in:
- `scripts/bt_config.sh`: `BT_STRATEGY_TYPE="venue_arb"`
- Command-line flags: `--strategy_type venue_arb`

## Troubleshooting

### Strategy Not Loading

1. Verify strategy type matches in source code and config
2. Restart backtest server: `./scripts/bt_server.sh restart`
3. Recheck strategies: `./scripts/bt_instance.sh recheck`
4. Check server logs: `./scripts/bt_server.sh logs | grep -i "venue_arb"`

### Build Errors

If build fails:
```bash
cd $HOME/ss/sdk/RCM/StrategyStudio/examples/strategies/venue_arb/
make clean
make
make copy_strategy
```

### See Also

- **[Strategy Studio Scripts README](../scripts/README.md)** - Complete automation guide
- **[Strategy Studio Backtest Prerequisites](ss_backtest_prereqs.md)** - Configuration requirements
