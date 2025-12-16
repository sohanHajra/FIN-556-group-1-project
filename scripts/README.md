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

```bash
./scripts/deploy_strategy.sh --name venue_arb
```

What this does:

* copies `.cpp` and `.h` into StrategyStudio
* runs `make`
* runs `make copy_strategy`
* places the `.so` in the backtest runtime directory

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

### Backtest server won’t start

Check logs:

```bash
./scripts/bt_server.sh logs
```

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