#!/usr/bin/env bash
set -euo pipefail

# ================================
# Resolve script directory
# ================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ================================
# Load shared config (required)
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
NETID="${BT_NETID:-$USER}"
STRAT_DIR="${BT_STRATEGY_DIR:-}"
INSTANCE="${BT_INSTANCE_NAME:-}"
ACCOUNT="${BT_ACCOUNT:-UIUC}"
SIM="${BT_SIM:-}"
USERNAME="${BT_USER:-}"
CASH="${BT_CASH:-9900000}"
SYMBOLS="${BT_SYMBOLS:-}"

START="${BT_BACKTEST_START:-}"
END="${BT_BACKTEST_END:-}"
MODE="${BT_BACKTEST_MODE:-0}"

# ================================
# Script dependencies
# ================================
BUILD_SCRIPT="$SCRIPT_DIR/build_copy_strategy.sh"
BT_SERVER="$SCRIPT_DIR/bt_server.sh"
BT_INSTANCE="$SCRIPT_DIR/bt_instance.sh"

# ================================
usage() {
  cat <<EOF
Usage:
  $0 <command> [options]

Commands:
  build        Build + copy strategy
  start        Start backtest server
  create       Create strategy instance
  backtest     Run backtest
  run          build → start → recheck → create → backtest
  list         List strategy instances

Options (override config):
  --strategy_dir STRATEGY_DIR
  --instance INSTANCE_NAME
  --account ACCOUNT
  --sim SIM-XXXX-XXX
  --user USERNAME
  --cash CASH
  --symbols "A|B|C"
  --start YYYY-MM-DD
  --end YYYY-MM-DD
  --mode 0|1

Examples:
  $0 run
  $0 backtest --start 2023-10-01 --end 2023-10-31
  $0 create --instance Test1
EOF
}

# ================================
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
    --strategy_dir) STRAT_DIR="$2"; shift 2;;
    --instance) INSTANCE="$2"; shift 2;;
    --account) ACCOUNT="$2"; shift 2;;
    --sim) SIM="$2"; shift 2;;
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
  build)
    require STRAT_DIR
    echo "=== Build strategy: $STRAT_DIR ==="
    "$BUILD_SCRIPT" --name "$STRAT_DIR"
    ;;

  start)
    echo "=== Start backtest server ==="
    "$BT_SERVER" start
    ;;

  create)
    require STRAT_DIR INSTANCE SIM USERNAME SYMBOLS
    echo "=== Create instance: $INSTANCE ==="
    "$BT_INSTANCE" create \
      --instance "$INSTANCE" \
      --strategy "$STRAT_DIR" \
      --account "$ACCOUNT" \
      --sim "$SIM" \
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

  run)
    require STRAT_DIR INSTANCE SIM USERNAME SYMBOLS START END
    echo "=== FULL PIPELINE ==="
    "$BUILD_SCRIPT" --name "$STRAT_DIR"
    "$BT_SERVER" start
    "$BT_INSTANCE" recheck
    "$BT_INSTANCE" create \
      --instance "$INSTANCE" \
      --strategy "$STRAT_DIR" \
      --account "$ACCOUNT" \
      --sim "$SIM" \
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
