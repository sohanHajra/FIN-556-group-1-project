# StrategyStudio Scripts — README

This folder contains **automation scripts** for working with **StrategyStudio** in a quota-limited student environment.

The goals are:

* avoid manual, error-prone steps
* keep **strategy source code in this repo**, not inside the SDK
* prevent disk-quota issues
* make cloning, building, running, and debugging strategies repeatable

If you follow this README, you should **never need to touch StrategyStudio files by hand**.

---

## Directory layout (important)

```
group_01_project/
├── src/
│   └── venue_arb/
│       ├── venue_arb.cpp
│       └── venue_arb.h
├── scripts/
│   ├── clone_strategy.sh
│   ├── deploy_strategy.sh
│   ├── bt_server.sh
│   ├── bt_instance.sh
│   ├── run_strategy.sh
│   ├── ss_logs.sh
│   ├── ss_log_manager.sh
│   └── README.md   <-- (this file)
```

### Key idea

* `src/` is the **source of truth** for strategy code
* StrategyStudio directories are treated as **build/deploy targets**
* Scripts handle copying, building, and running

---

## Quick Start: Essential Prerequisites

**⚠️ IMPORTANT:** Before using any scripts, you must complete these one-time setup steps:

### 1. Clone the Base Strategy Repository

You need the source strategy template before cloning/customizing your own strategies:

```bash
cd ~/ss/sdk/RCM/StrategyStudio/examples/strategies/
git clone https://oauth2:glpat-SoENCtAH9Kv7y86xNDCa@gitlab.engr.illinois.edu/shared_code/example_trading_strategies/dia_index_arb_strategy.git
```

This gives you a clean reference strategy (`dia_index_arb_strategy`) to work from.

### 2. Create Runtime Directory and Fix Makefile Paths

The default Makefiles have hardcoded paths that will cause permission errors. Run the fix script:

```bash
# From the project root
./scripts/fix_makefile_paths.sh
```

This script:
- Creates the runtime directory: `$HOME/ss/bt/strategies_dlls`
- Fixes all Makefiles to use `$(HOME)` instead of hardcoded `/home/vagrant` paths
- Creates backups before modifying files

**That's it!** After these two steps, you're ready to use the rest of the scripts.

---

# Before starting

Make sure that you environment variables are setup! Some scripts rely on environment variables and user-specific paths.

- `$HOME` is used everywhere instead of `/home/acharov2`
- `/student_work/$USER" is used for logs and large files.W
- Strategy names (e.g. `venue_arb`) are shared and unchanged.
- Make sure to check `echo $USER` (YOUR_NETID), `echo $HOME` (/home/YOUR_NETID) paths!

## One-time setup (new developer)

### 1️) Clone the template strategy once

This creates a new StrategyStudio strategy directory by copying an existing template.

```bash
./scripts/clone_strategy.sh --name venue_arb
```

This:

* copies `dia_index_arb_strategy`
* renames files (`.cpp`, `.h`, `.so`)
* updates the Makefile automatically

You only need to do this **once per strategy name**.

**After cloning**, you can use `deploy_strategy.sh` (see "Daily workflow" below) to copy your code from `src/` and build.

---

### 2️) Make sure the backtest server can run

Start the backtest server:

```bash
./scripts/bt_server.sh start
```

Check status:

```bash
./scripts/bt_server.sh status
```

Logs are written **outside `$HOME`** to avoid quota issues:

```
/student_work/$USER/ss_logs/bt_server.log
```

---

## Daily workflow (what you’ll do most of the time)

### 1️) Edit strategy code (ONLY here)

Edit files in the repo:

```
src/venue_arb/venue_arb.cpp
src/venue_arb/venue_arb.h
```

Do **not** edit StrategyStudio SDK files directly.

---

### 2️) Deploy + build the strategy

This overwrites the StrategyStudio files and rebuilds the `.so`.

**Note:** You must have run `clone_strategy.sh` first (see "One-time setup" above) to create the StrategyStudio directory.

```bash
./scripts/deploy_strategy.sh --name venue_arb
```

What this does:

* copies `.cpp` and `.h` into StrategyStudio
* runs `make`
* runs `make copy_strategy`
* places the `.so` in the backtest runtime directory

---

### 2b) Reference guide for complete workflow

**Note:** `deploy_and_test.sh` is a **reference guide only** - it does NOT execute commands. It prints the recommended pipeline structure you should follow manually.

To see the recommended workflow structure:

```bash
./scripts/deploy_and_test.sh
```

This will print a helpful guide showing the complete pipeline:
1. Restart backtest server
2. Deploy and build the strategy
3. Terminate existing instances
4. Run full pipeline (recheck → create → backtest)
5. View logs (optional)

**To actually run the workflow**, copy and execute the commands shown in the guide, or use the individual scripts:

```bash
# Restart server
./scripts/bt_server.sh stop && sleep 3 && ./scripts/bt_server.sh start

# Deploy strategy
./scripts/deploy_strategy.sh --name venue_arb

# Terminate all instances
./scripts/run_strategy.sh killall && sleep 8

# Run full pipeline (uses config defaults or override with flags)
./scripts/run_strategy.sh run
./scripts/run_strategy.sh run --start 2023-09-05 --end 2023-09-05

# View logs (optional)
./scripts/ss_logs.sh bt
```

---

### 3️) Run a backtest

Create an instance (only once per instance name):

```bash
./scripts/bt_instance.sh create \
  --instance MyVenueArb \
  --strategy venue_arb \
  --account UIUC \
  --sim SIM-1001-101 \
  --user dlariviere \
  --cash 9900000 \
  --symbols "SPY|NVDA|GOOG"
```

Start a backtest:

```bash
./scripts/bt_instance.sh backtest \
  --instance MyVenueArb \
  --start 2023-09-05 \
  --end 2023-09-05
```

---

## Managing running strategies

List instances:

```bash
./scripts/bt_instance.sh list
```

Stop / pause / terminate a specific instance:

```bash
./scripts/bt_instance.sh stop --instance MyVenueArb
./scripts/bt_instance.sh pause --instance MyVenueArb
./scripts/bt_instance.sh terminate --instance MyVenueArb
```

Terminate everything

```bash
./scripts/bt_instance.sh terminate --all
```

Or stop or pause everything

```bash
./scripts/bt_instance.sh stop --all
```

### StrategyStudio behaivor regarding these commands
- `terminate`:
  - kill the strategy
  - frees resources
  -instance disappears
- `stop`:
  - stops execution
  - instance still exists
- `pause`:
  - temporary halt
  - cant resume

---

## Convenience wrapper: `run_strategy.sh`

The `run_strategy.sh` script is a **convenience wrapper** that loads configuration from `bt_config.sh` and provides simplified commands for common workflows.

### Configuration

`run_strategy.sh` automatically loads:
- `scripts/bt_config.sh` (required)
- `scripts/bt_config.local.sh` (optional, for user-specific overrides)

All values can be overridden via command-line flags.

### Commands

**Start backtest server:**
```bash
./scripts/run_strategy.sh start
```

**Create strategy instance** (uses config defaults, or override with flags):
```bash
./scripts/run_strategy.sh create
./scripts/run_strategy.sh create --instance MyInstance --symbols "SPY|NVDA"
```

**Run backtest** (uses config defaults, or override with flags):
```bash
./scripts/run_strategy.sh backtest
./scripts/run_strategy.sh backtest --start 2023-09-05 --end 2023-09-06
```

**List instances:**
```bash
./scripts/run_strategy.sh list
```

**Terminate all instances:**
```bash
./scripts/run_strategy.sh killall
```

**Full pipeline** (start server → recheck → create → backtest):
```bash
./scripts/run_strategy.sh run
./scripts/run_strategy.sh run --start 2023-09-05 --end 2023-09-06
```

### Available flags (override config)

- `--instance INSTANCE_NAME`
- `--strategy_type STRATEGY_TYPE`
- `--symbols "A|B|C"`
- `--start YYYY-MM-DD`
- `--end YYYY-MM-DD`
- `--mode 0|1` (0 = quotes + trades, 1 = trades only)

### Example: Full workflow with overrides

```bash
./scripts/run_strategy.sh run \
  --instance MyTestInstance \
  --strategy_type venue_arb \
  --symbols "SPY|NVDA|GOOG" \
  --start 2023-09-05 \
  --end 2023-09-05
```

This single command will:
1. Start the backtest server (if not running)
2. Recheck strategy DLLs
3. Create the instance with specified parameters
4. Launch the backtest

---

## Logs & debugging

### View logs quickly

```bash
./scripts/ss_logs.sh list
./scripts/ss_logs.sh bt
./scripts/ss_logs.sh bt -f
./scripts/ss_logs.sh errors
```

### Manage disk usage (VERY IMPORTANT)

Quota issues are common. Use the log manager:

```bash
./scripts/ss_log_manager.sh summary
./scripts/ss_log_manager.sh largest
./scripts/ss_log_manager.sh clean results
./scripts/ss_log_manager.sh purge --days 7
```

If you ever see:

```
Disk quota exceeded
```

run:

```bash
./scripts/ss_log_manager.sh summary
```

and clean immediately.

---

## Common problems & fixes

### “Disk quota exceeded” even though space looks free

* Quotas are per-user, not per-filesystem
* Logs or CRA files may still be open by a running process

Fix:

```bash
./scripts/bt_server.sh stop
quota -v
```

---

### Code changes don’t seem to apply

You probably forgot to deploy.

Always run:

```bash
./scripts/deploy_strategy.sh --name venue_arb
```

before backtesting.

---

### Backtest server won't start

Check logs:

```bash
./scripts/bt_server.sh logs
```

---

### Strategy not loading or not found

If your strategy doesn't appear in the list or fails to load, follow these steps:

**1. Restart the backtest server** (forces reload of all `.so` files):

```bash
./scripts/bt_server.sh restart
```

**2. Recheck strategy DLLs** (tells StrategyStudio to scan for new strategies):

```bash
./scripts/bt_instance.sh recheck
```

**3. Verify strategy type matches source code:**

The strategy type you use in scripts/config must **exactly match** the string returned by `GetType()` in your C++ header file.

Check your source file (e.g., `src/venue_arb/venue_arb.h`):
```cpp
extern "C" {
    _STRATEGY_EXPORTS const char* GetType() {
        return "venue_arb";  // <-- This string must match
    }
}
```

Then verify it matches:
- `scripts/bt_config.sh`: `BT_STRATEGY_TYPE="venue_arb"`
- Command-line flags: `--strategy_type venue_arb`
- Instance creation: `--strategy venue_arb`

**4. Ensure strategy was deployed and built:**

```bash
# Deploy and rebuild
./scripts/deploy_strategy.sh --name venue_arb

# Verify .so file exists
ls $HOME/StrategyStudio/Backtesting/Strategies/*.so
```

**5. Check for build errors:**

Look for compilation errors in the deploy output. Common issues:
- Missing includes
- Linker errors
- Syntax errors in C++ code

**6. Check server startup logs for strategy registration:**

When the server starts, it logs which strategies are registered. Check the logs to verify your strategy was loaded:

```bash
# View recent server logs
./scripts/bt_server.sh logs | tail -50

# Search for your strategy name
./scripts/bt_server.sh logs | grep -i "venue_arb"

# Look for registration messages
./scripts/bt_server.sh logs | grep -i "register\|load\|strategy"
```

You should see messages indicating your strategy was successfully registered. If not, the strategy wasn't loaded.

**7. Verify strategy version matches source code:**

The version returned by `GetReleaseVersion()` in your header file must match what StrategyStudio sees. Check your source code:

```cpp
// In src/venue_arb/venue_arb.h
extern "C" {
    _STRATEGY_EXPORTS const char* GetReleaseVersion() {
        return Strategy::release_version();  // <-- Check what this returns
    }
}
```

After deploying, check the server logs for the version string when the strategy loads. The version should appear in the registration logs. You can also check by looking at the `.so` file's metadata or by examining the server logs when the strategy is first loaded.

**8. Full reload sequence** (if strategy still not found):

```bash
# First, terminate all running instances (they may be using old .so files)
./scripts/run_strategy.sh killall
# Or: ./scripts/bt_instance.sh terminate --all

# Stop server
./scripts/bt_server.sh stop

# Deploy and rebuild
./scripts/deploy_strategy.sh --name venue_arb

# Restart server
./scripts/bt_server.sh start

# Wait a moment for server to fully start
sleep 3

# Recheck strategies (tells StrategyStudio to scan for new .so files)
./scripts/bt_instance.sh recheck

# Check server logs to verify strategy was registered
./scripts/bt_server.sh logs | grep -i "venue_arb"

# Note: 'list' shows running instances, not available strategies
# To see if strategy is available, check the server logs or try creating an instance
```

**9. Check server logs for errors:**

```bash
# Look for errors
./scripts/bt_server.sh logs | grep -i error

# Look for your strategy specifically
./scripts/bt_server.sh logs | grep -i "venue_arb"

# Check for loading/registration issues
./scripts/bt_server.sh logs | grep -i "fail\|error\|cannot\|unable"
```

**Common mistakes:**
- Strategy type mismatch between source code and config
- Forgot to deploy after code changes
- Build failed silently (check deploy output)
- Server not restarted after deploying new strategy
- `.so` file not copied to correct location
- Running instances still using old `.so` files (use `killall` first)
- Version mismatch between source code and loaded strategy
- Strategy not appearing in server startup logs (means it wasn't registered)

---

## Mental model (read this once)

* **You never run C++ directly**
* `make` → builds a `.so`
* `make copy_strategy` → makes it available to the backtest server
* `StrategyServerBacktesting` loads `.so` files dynamically
* Backtests execute your C++ code only when started

---

## Final notes

* This setup mirrors **real trading infrastructure**
* Scripts are intentionally simple and explicit
* If something breaks, inspect logs first
* Do not manually edit StrategyStudio SDK files unless debugging

---

## Appendix: Understanding the Makefile Path Issue

### The Problem

Strategy Studio builds `.so` strategy binaries, and `make copy_strategy` copies the `.so` into a runtime directory. However, the default Makefile from cloned strategies contains a **hardcoded path**:

```makefile
cp *.so /home/vagrant/ss/bt/strategies_dlls/.
```

If you're not the `vagrant` user, this causes a **permission denied** error. The build succeeds, but the copy step fails silently, which prevents Strategy Studio from loading your strategy.

**Symptoms:**
- Build completes successfully
- `make copy_strategy` fails with "permission denied"
- Strategy doesn't appear in Strategy Studio
- No `.so` file in the runtime directory

### The Solution

**Automated Fix (Recommended):**

Run the fix script to automatically update all Makefiles:

```bash
# Fix all strategies
./scripts/fix_makefile_paths.sh

# Or fix a specific strategy
./scripts/fix_makefile_paths.sh --strategy venue_arb
```

This script:
- Replaces `/home/vagrant/ss/bt/strategies_dlls` with `$(HOME)/ss/bt/strategies_dlls`
- Creates the runtime directory if it doesn't exist: `$HOME/ss/bt/strategies_dlls`
- Creates backups (`.bak` files) of Makefiles before modifying them
- Reports which strategies were fixed

**Manual Fix (Alternative):**

If you prefer to fix manually:

1. Navigate to your strategy directory:
   ```bash
   cd ~/ss/sdk/RCM/StrategyStudio/examples/strategies/<strategy_name>
   ```

2. Edit the Makefile:
   ```bash
   nano Makefile
   ```

3. Find the `copy_strategy` target and replace:
   ```makefile
   # OLD (hardcoded - causes permission errors):
   cp *.so /home/vagrant/ss/bt/strategies_dlls/.
   
   # NEW (portable - works for any user):
   cp *.so $(HOME)/ss/bt/strategies_dlls/.
   ```

4. Ensure the directory exists:
   ```bash
   mkdir -p ~/ss/bt/strategies_dlls
   ```

### Verify the Fix

After running the patch script, verify everything is correct:

```bash
# Check that the runtime directory exists
ls -ld ~/ss/bt/strategies_dlls

# Check a Makefile was fixed (should show $(HOME), not /home/vagrant)
grep "strategies_dlls" ~/ss/sdk/RCM/StrategyStudio/examples/strategies/venue_arb/Makefile
```

You should see `$(HOME)/ss/bt/strategies_dlls` in the Makefile, not `/home/vagrant/ss/bt/strategies_dlls`.

### When to Run This

- **Before cloning your first strategy** (if you want to fix the template)
- **After cloning a strategy** (recommended - fix it immediately)
- **If you get "permission denied" errors** during `make copy_strategy`
- **After pulling updates** that might have reset Makefiles

**Note:** The patch script is safe to run multiple times - it only fixes Makefiles that need fixing and creates backups.

### Mental Model

Understanding the workflow:

1. **Git clone** → Gets raw strategy source (`dia_index_arb_strategy`)
2. **`clone_strategy.sh`** → Creates a new named strategy (e.g., `venue_arb`)
3. **Makefile copy path** → MUST point to your user's `strategies_dlls` directory
4. **`deploy_strategy.sh`** → Best for repo-based workflows (edits in `src/`)
5. **`build_copy_strategy.sh`** → Best for direct SDK edits

Once the `.so` file lands in `~/ss/bt/strategies_dlls`, Strategy Studio can see and load it ✅

---