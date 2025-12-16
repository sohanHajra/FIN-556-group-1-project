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
INSTANCE="${BT_INSTANCE_NAME:-}"
STRATEGY_TYPE="${BT_STRATEGY_TYPE:-}"
SYMBOLS="${BT_SYMBOLS:-}"

GROUP="${BT_GROUP:-UIUC}"          # e.g. UIUC
ACCOUNT="${BT_ACCOUNT:-}"          # e.g. SIM-1001-101
USERNAME="${BT_USER:-}"
CASH="${BT_CASH:-9900000}"

START="${BT_BACKTEST_START:-}"
END="${BT_BACKTEST_END:-}"
MODE="${BT_BACKTEST_MODE:-0}"

# ================================
# Script dependencies
# ================================
BT_SERVER="$SCRIPT_DIR/bt_server.sh"
BT_INSTANCE="$SCRIPT_DIR/bt_instance.sh"

# ================================
usage() {
  cat <<EOF
Usage:
  $0 <command> [options]

Commands:
  start        Start backtest server
  create       Create strategy instance
  backtest     Run backtest
  list         List strategy instances
  killall      Terminate ALL strategy instances
  run          start → recheck → create → backtest

Options (override config):
  --instance INSTANCE_NAME
  --strategy_type STRATEGY_TYPE
  --symbols "A|B|C"
  --start YYYY-MM-DD
  --end YYYY-MM-DD
  --mode 0|1
EOF
}

require() {
  for v in "$@"; do
    [[ -n "${!v}" ]] || {
      echo "❌ Missing required value: $v"
      exit 1
    }
  done
}

# ================================
# Parse command
# ================================
CMD="${1:-}"
[[ -n "$CMD" ]] || { usage; exit 1; }
shift

# ================================
# Parse flags (override config)
# ================================
while [[ $# -gt 0 ]]; do
  case "$1" in
    --instance) INSTANCE="$2"; shift 2;;
    --strategy_type) STRATEGY_TYPE="$2"; shift 2;;
    --symbols) SYMBOLS="$2"; shift 2;;
    --start) START="$2"; shift 2;;
    --end) END="$2"; shift 2;;
    --mode) MODE="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

# ================================
# Commands
# ================================
case "$CMD" in
  start)
    echo "=== Start backtest server ==="
    "$BT_SERVER" start
    ;;

  create)
    require INSTANCE STRATEGY_TYPE GROUP ACCOUNT USERNAME SYMBOLS
    echo "=== Creating instance: $INSTANCE ==="

    "$BT_INSTANCE" create \
      "$INSTANCE" \
      "$STRATEGY_TYPE" \
      "$GROUP" \
      "$ACCOUNT" \
      "$USERNAME" \
      "$CASH" \
      "$SYMBOLS"
    ;;

  backtest)
    require INSTANCE START END
    echo "=== Backtest: $INSTANCE ==="

    "$BT_INSTANCE" backtest \
      --instance "$INSTANCE" \
      --start "$START" \
      --end "$END" \
      --mode "$MODE"
    ;;

  list)
    "$BT_INSTANCE" list
    ;;

  killall)
    echo "=== Terminating ALL strategy instances ==="
    "$BT_INSTANCE" terminate --all
    echo "All strategy instances terminated."
    ;;

  run)
    require INSTANCE STRATEGY_TYPE GROUP ACCOUNT USERNAME SYMBOLS START END

    echo "=== FULL PIPELINE (NO BUILD) ==="

    "$BT_SERVER" start
    "$BT_INSTANCE" recheck

    echo "=== Creating instance ==="
    "$BT_INSTANCE" create \
      "$INSTANCE" \
      "$STRATEGY_TYPE" \
      "$GROUP" \
      "$ACCOUNT" \
      "$USERNAME" \
      "$CASH" \
      "$SYMBOLS"

    echo "=== Starting backtest ==="
    "$BT_INSTANCE" backtest \
      --instance "$INSTANCE" \
      --start "$START" \
      --end "$END" \
      --mode "$MODE"

    echo "Backtest launched."
    ;;

  *)
    usage
    exit 1
    ;;
esac
