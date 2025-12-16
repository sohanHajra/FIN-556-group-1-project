#!/usr/bin/env bash
set -euo pipefail

STRAT_DIR="${HOME}/ss/sdk/RCM/StrategyStudio/examples/strategies"

if [[ ! -d "$STRAT_DIR" ]]; then
  echo "Strategies directory not found: $STRAT_DIR"
  exit 1
fi

cd "$STRAT_DIR"
pwd
