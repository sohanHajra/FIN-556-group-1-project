#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $0 --name STRATEGY_DIRNAME

Builds and copies a strategy that already exists in StrategyStudio.
Use this when you've edited files directly in the StrategyStudio directory.

For repo-based workflows (editing in ./src/), use deploy_strategy.sh instead:
  ./scripts/deploy_strategy.sh --name STRATEGY_NAME

Note: The strategy directory must already exist (created via clone_strategy.sh).

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

[[ -d "$TARGET" ]] || { echo "Missing strategy dir: $TARGET"; exit 1; }

cd "$TARGET"

echo "➡️  Building in: $TARGET"
make clean
make
make copy_strategy

echo ""
echo "Built + copied strategy: $NAME"
echo ""
echo "Tip: If you're editing in ./src/$NAME/, use deploy_strategy.sh instead:"
echo "   ./scripts/deploy_strategy.sh --name $NAME"
