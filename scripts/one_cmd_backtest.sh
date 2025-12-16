#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $0 --netid NETID --strategy_dir STRAT_DIRNAME --instance INSTANCE \
     --account UIUC --sim SIM-XXXX-XXX --user USERNAME --cash 9900000 \
     --symbols "SPY|NVDA|GOOG" --start YYYY-MM-DD --end YYYY-MM-DD

Defaults:
  --netid defaults to \$USER
EOF
}

NETID="${USER}"
STRAT_DIR=""
INSTANCE=""
ACCOUNT="UIUC"
SIM=""
USERNAME="dlariviere"
CASH="9900000"
SYMBOLS=""
START=""
END=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --netid) NETID="$2"; shift 2;;
    --strategy_dir) STRAT_DIR="$2"; shift 2;;
    --instance) INSTANCE="$2"; shift 2;;
    --account) ACCOUNT="$2"; shift 2;;
    --sim) SIM="$2"; shift 2;;
    --user) USERNAME="$2"; shift 2;;
    --cash) CASH="$2"; shift 2;;
    --symbols) SYMBOLS="$2"; shift 2;;
    --start) START="$2"; shift 2;;
    --end) END="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

[[ -n "$STRAT_DIR" && -n "$INSTANCE" && -n "$SIM" && -n "$USERNAME" && -n "$SYMBOLS" && -n "$START" && -n "$END" ]] || { usage; exit 1; }

echo "=== 1) Build + copy strategy ==="
./scripts/build_copy_strategy.sh --name "$STRAT_DIR"

echo "=== 2) Ensure backtest server running ==="
./scripts/bt_server.sh start

echo "=== 3) Create instance (ok if already exists; you can delete manually if needed) ==="
# Strategy name is directory name; .so will be appended by bt_instance wrapper
./scripts/bt_instance.sh create \
  --instance "$INSTANCE" \
  --strategy "$STRAT_DIR" \
  --account "$ACCOUNT" \
  --sim "$SIM" \
  --user "$USERNAME" \
  --cash "$CASH" \
  --symbols "$SYMBOLS" || true

echo "=== 4) Run backtest ==="
./scripts/bt_instance.sh backtest \
  --instance "$INSTANCE" \
  --start "$START" \
  --end "$END" \
  --mode 0

echo "Launched backtest. Results will appear in: $HOME/ss/bt/backtesting-results/"
