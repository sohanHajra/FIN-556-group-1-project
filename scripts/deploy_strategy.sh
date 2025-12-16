#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $0 --name STRATEGY_NAME

Assumes:
  repo src lives at: ./src/<STRATEGY_NAME>/
  StrategyStudio dir: \$HOME/ss/sdk/RCM/StrategyStudio/examples/strategies/<STRATEGY_NAME>

Example:
  $0 --name venue_arb
EOF
}

STRAT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) STRAT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

[[ -n "$STRAT" ]] || { usage; exit 1; }

# Paths
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_DIR="$REPO_ROOT/src/$STRAT"
SS_DIR="$HOME/ss/sdk/RCM/StrategyStudio/examples/strategies/$STRAT"

[[ -d "$SRC_DIR" ]] || {
  echo "Source directory not found: $SRC_DIR"
  exit 1
}

[[ -d "$SS_DIR" ]] || {
  echo "StrategyStudio directory not found: $SS_DIR"
  echo "Did you run clone_strategy.sh first?"
  exit 1
}

echo "➡️ Deploying strategy: $STRAT"
echo "   From: $SRC_DIR"
echo "   To:   $SS_DIR"

# Copy source files
cp "$SRC_DIR/$STRAT.cpp" "$SS_DIR/$STRAT.cpp"
cp "$SRC_DIR/$STRAT.h"   "$SS_DIR/$STRAT.h"

echo "➡️ Building strategy..."
cd "$SS_DIR"

make
make copy_strategy

echo "Deployed and built: $STRAT"
