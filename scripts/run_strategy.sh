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

GROUP="${BT_GROUP:-UIUC}"
ACCOUNT="${BT_ACCOUNT:-}"
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
  --strategy_type STRATEGY_TYPE
  --instance INSTANCE_NAME
  --group GROUP
  --account ACCOUNT
  --user USERNAME
  --cash CASH
  --symbols "A|B|C"
  --start YYYY-MM-DD
  --end YYYY-MM-DD
  --mode 0|1

Examples:
  $0 run
  $0 killall
  $0 backtest --start 2023-10-01 --end 2023-10-31
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
    --strategy_type) STRATEGY_TYPE="$2"; shift 2;;
    --instance) INSTANCE="$2"; shift 2;;
    --group) GROUP="$2"; shift 2;;
    --account) ACCOUNT="$2"; shift 2;;
    --user) USERNAME="$2"; shift 2;;
    --cash) CASH="$2"; shift 2;;
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
    echo "=== Create instance: $INSTANCE ==="
    "$BT_INSTANCE" create \
      --instance "$INSTANCE" \
      --strategy "$STRATEGY_TYPE" \
      --account "$ACCOUNT" \
      --sim "$GROUP" \
      --user "$USERNAME" \
      --cash "$CASH" \
      --symbols "$SYMBOLS"
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

    "$BT_INSTANCE" create \
      --instance "$INSTANCE" \
      --strategy "$STRATEGY_TYPE" \
      --account "$ACCOUNT" \
      --sim "$GROUP" \
      --user "$USERNAME" \
      --cash "$CASH" \
      --symbols "$SYMBOLS" || true

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
