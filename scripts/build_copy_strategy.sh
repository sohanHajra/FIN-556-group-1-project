#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $0 --name STRATEGY_DIRNAME

Example:
  $0 --name acharov2_strategy
EOF
}

NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

[[ -n "$NAME" ]] || { usage; exit 1; }

STRATS_DIR="${HOME}/ss/sdk/RCM/StrategyStudio/examples/strategies"
TARGET="${STRATS_DIR}/${NAME}"

[[ -d "$TARGET" ]] || { echo "❌ Missing strategy dir: $TARGET"; exit 1; }

cd "$TARGET"

echo "➡️  Building in: $TARGET"
make clean
make
make copy_strategy

echo "Built + copied strategy: $NAME"
