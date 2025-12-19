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

# ================================
# Script dependencies
# ================================
BT_SERVER="$SCRIPT_DIR/bt_server.sh"
DEPLOY="$SCRIPT_DIR/deploy_strategy.sh"
RUN_STRATEGY="$SCRIPT_DIR/run_strategy.sh"
SS_LOGS="$SCRIPT_DIR/ss_logs.sh"
SS_LOG_MANAGER="$SCRIPT_DIR/ss_log_manager.sh"

# ================================
usage() {
  cat <<EOF
Usage:
  $0 [options]

Simple convenience script that:
  1. (Optional) Cleans backtest server logs
  2. Stops and restarts the backtest server
  3. Deploys the strategy (builds and copies)
  4. Terminates all existing instances
  5. Runs the full pipeline (recheck → create → backtest) via run_strategy.sh
  6. (Optional) Shows backtest server logs

Options:
  --strategy STRATEGY_NAME    Strategy name (required)
  --clean                     Clean backtest server logs before starting
  --no-logs                   Don't show logs at the end

All other parameters (instance, start, end, mode, etc.) are read from bt_config.sh
and can be overridden by passing them to run_strategy.sh run.

Examples:
  $0 --strategy venue_arb
  $0 --strategy venue_arb --clean
EOF
}

# ================================
# Parse flags
# ================================
SHOW_LOGS=1
CLEAN_LOGS=0
RUN_STRATEGY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strategy) STRATEGY_NAME="$2"; shift 2;;
    --clean) CLEAN_LOGS=1; shift;;
    --no-logs) SHOW_LOGS=0; shift;;
    -h|--help) usage; exit 0;;
    *) 
      # Pass through any other args to run_strategy.sh
      RUN_STRATEGY_ARGS+=("$1")
      shift
      ;;
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

# ================================
# Main workflow
# ================================
echo "=========================================="
echo "( O_O ) Deploy and Test Workflow"
echo "=========================================="
echo "Strategy: $STRATEGY_NAME"
echo ""

# Step 0: Clean logs (if requested)
if [[ "$CLEAN_LOGS" -eq 1 ]]; then
  echo "=== Step 0: Cleaning backtest server logs ==="
  "$SS_LOG_MANAGER" clean bt
  echo "✓ Logs cleaned"
  echo ""
fi

# Step 1: Restart server
echo "=== Step 1: Restarting backtest server ==="
"$BT_SERVER" stop || true
sleep 3
"$BT_SERVER" start
sleep 3
echo "✓ Server restarted"
echo ""

# Step 2: Deploy strategy
echo "=== Step 2: Deploying strategy ==="
"$DEPLOY" --name "$STRATEGY_NAME"
sleep 2
echo "✓ Strategy deployed and built"
echo ""

# Step 3: Terminate all instances
echo "=== Step 3: Terminating all existing instances ==="
"$RUN_STRATEGY" killall || true
sleep 3
echo "✓ All instances terminated"
echo ""

# Step 4: Run full pipeline (recheck → create → backtest)
echo "=== Step 4: Running full pipeline ==="
"$RUN_STRATEGY" run "${RUN_STRATEGY_ARGS[@]}"
echo ""

# Step 5: Show logs
if [[ "$SHOW_LOGS" -eq 1 ]]; then
  echo "=== Step 5: Showing backtest server logs ==="
  sleep 2
  echo "(Press 'q' to quit the log viewer)"
  echo ""
  "$SS_LOGS" bt
fi

echo ""
echo "=========================================="
echo "✓ Workflow complete!"
echo "=========================================="

