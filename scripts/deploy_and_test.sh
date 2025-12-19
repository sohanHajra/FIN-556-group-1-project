#!/usr/bin/env bash
set -euo pipefail

# ================================
# Resolve script directory
# ================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ================================
# Load config
# ================================
CONFIG_FILE="$SCRIPT_DIR/bt_config.sh"
LOCAL_CONFIG_FILE="$SCRIPT_DIR/bt_config.local.sh"

[[ -f "$CONFIG_FILE" ]] || {
  echo "❌ Missing config: $CONFIG_FILE"
  exit 1
}

source "$CONFIG_FILE"
[[ -f "$LOCAL_CONFIG_FILE" ]] && source "$LOCAL_CONFIG_FILE"

# ================================
# Defaults from config
# ================================
STRATEGY_NAME="${BT_STRATEGY_TYPE:-}"
INSTANCE="${BT_INSTANCE_NAME:-}"
START="${BT_BACKTEST_START:-}"
END="${BT_BACKTEST_END:-}"
MODE="${BT_BACKTEST_MODE:-0}"

# ================================
# Script dependencies
# ================================
BT_SERVER="$SCRIPT_DIR/bt_server.sh"
DEPLOY="$SCRIPT_DIR/deploy_strategy.sh"
RUN_STRATEGY="$SCRIPT_DIR/run_strategy.sh"
BT_INSTANCE="$SCRIPT_DIR/bt_instance.sh"
SS_LOGS="$SCRIPT_DIR/ss_logs.sh"
SS_LOG_MANAGER="$SCRIPT_DIR/ss_log_manager.sh"

# ================================
usage() {
  cat <<EOF
Usage:
  $0 [options]

Convenience script that:
  1. Stops and restarts the backtest server
  2. Deploys the strategy (builds and copies)
  3. Runs a backtest
  4. Shows backtest server logs

Options (override config):
  --strategy STRATEGY_NAME    Strategy name (required)
  --instance INSTANCE_NAME     Instance name (from config or required)
  --start YYYY-MM-DD          Backtest start date (from config or required)
  --end YYYY-MM-DD            Backtest end date (from config or required)
  --mode 0|1                  Backtest mode (0=quotes+trades, 1=trades only)
  --clean                     Clean backtest server logs before starting
  --no-logs                   Don't show logs at the end

Examples:
  $0 --strategy venue_arb --instance MyTest --start 2023-09-05 --end 2023-09-05
  $0 --strategy venue_arb  # uses config defaults for instance/start/end
EOF
}

# ================================
# Parse flags
# ================================
SHOW_LOGS=1
CLEAN_LOGS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strategy) STRATEGY_NAME="$2"; shift 2;;
    --instance) INSTANCE="$2"; shift 2;;
    --start) START="$2"; shift 2;;
    --end) END="$2"; shift 2;;
    --mode) MODE="$2"; shift 2;;
    --clean) CLEAN_LOGS=1; shift;;
    --no-logs) SHOW_LOGS=0; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

# ================================
# Validate required params
# ================================
[[ -n "$STRATEGY_NAME" ]] || {
  echo "❌ --strategy is required"
  usage
  exit 1
}

[[ -n "$INSTANCE" ]] || {
  echo "❌ --instance is required (set in bt_config.sh or pass --instance)"
  usage
  exit 1
}

[[ -n "$START" ]] || {
  echo "❌ --start is required (set in bt_config.sh or pass --start)"
  usage
  exit 1
}

[[ -n "$END" ]] || {
  echo "❌ --end is required (set in bt_config.sh or pass --end)"
  usage
  exit 1
}

# ================================
# Main workflow
# ================================
echo "=========================================="
echo "( O_O ) Deploy and Test Workflow"
echo "=========================================="
echo "Strategy: $STRATEGY_NAME"
echo "Instance: $INSTANCE"
echo "Date range: $START to $END"
echo ""

# Step 0: Clean logs (if requested)
if [[ "$CLEAN_LOGS" -eq 1 ]]; then
  echo "=== Step 0: Cleaning backtest server logs ==="
  "$SS_LOG_MANAGER" clean bt
  echo "Logs cleaned."
  echo ""
  sleep 2
fi

# Step 1: Restart server
echo "=== Step 1: Restarting backtest server ==="
echo "Stopping server (if running)..."
"$BT_SERVER" stop || true
echo "Waiting for server to fully stop..."
sleep 5
echo "Starting backtest server..."
"$BT_SERVER" start
echo "Waiting for server to fully initialize..."
sleep 5
if "$BT_SERVER" status >/dev/null 2>&1; then
  echo "✓ Server is running"
else
  echo "✗ Server failed to start!"
  exit 1
fi
echo ""

# Step 2: Deploy strategy
echo "=== Step 2: Deploying strategy ==="
echo "Copying source files and building..."
"$DEPLOY" --name "$STRATEGY_NAME"
echo "Waiting for build to complete and server to see new DLL..."
sleep 5
echo "✓ Strategy deployed and built"
echo ""

# Step 2.5: Recheck strategy DLLs (reload after deploy)
echo "=== Step 2.5: Rechecking strategy DLLs ==="
echo "Waiting before recheck to ensure server is ready..."
sleep 2
"$BT_INSTANCE" recheck
echo "Waiting for DLL reload to complete..."
sleep 3
echo ""

# Step 2.6: Terminate all instances
echo "=== Step 2.6: Terminating all existing instances ==="
echo "Terminating all strategy instances..."
"$RUN_STRATEGY" killall || true
echo "Waiting for server to stabilize after termination..."
sleep 5

# Verify server is still running
echo "Verifying server is still running..."
if ! "$BT_SERVER" status >/dev/null 2>&1; then
  echo "⚠ Server disconnected, restarting..."
  "$BT_SERVER" start
  echo "Waiting for server to restart..."
  sleep 5
  if "$BT_SERVER" status >/dev/null 2>&1; then
    echo "✓ Server restarted successfully"
  else
    echo "✗ Server failed to restart!"
    exit 1
  fi
else
  echo "✓ Server is still running"
fi
echo ""

# Step 3: Run backtest
echo "=== Step 3: Running backtest ==="
echo "Starting backtest for instance: $INSTANCE"
echo "Date range: $START to $END"
"$RUN_STRATEGY" backtest \
  --instance "$INSTANCE" \
  --start "$START" \
  --end "$END" \
  --mode "$MODE"
echo "Waiting for backtest to initialize..."
sleep 3
echo "✓ Backtest command sent"
echo ""

# Step 4: Show logs
if [[ "$SHOW_LOGS" -eq 1 ]]; then
  echo "=== Step 4: Showing backtest server logs ==="
  echo "Waiting before showing logs..."
  sleep 2
  echo "(Press 'q' to quit the log viewer)"
  echo ""
  "$SS_LOGS" bt
else
  echo "=== Step 4: Skipping logs (use --no-logs to suppress this message) ==="
  echo "To view logs later: ./scripts/ss_logs.sh bt"
fi

echo ""
echo "=========================================="
echo "✓ Workflow complete!"
echo "=========================================="

