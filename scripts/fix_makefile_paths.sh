#!/usr/bin/env bash
set -euo pipefail

# Fix Makefile paths script
# Replaces hardcoded /home/vagrant paths with $(HOME) for portability

usage() {
  cat <<EOF
Usage:
  $0 [--strategy STRATEGY_NAME]

Fixes Makefile copy paths in Strategy Studio strategy directories.

If --strategy is provided, only fixes that strategy's Makefile.
Otherwise, fixes all Makefiles found in strategy directories.

This fixes the issue where Makefiles hardcode /home/vagrant/ss/bt/strategies_dlls
and replaces it with \$(HOME)/ss/bt/strategies_dlls for portability.

Example:
  $0 --strategy venue_arb
  $0  # Fix all strategies
EOF
}

STRATEGY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strategy) STRATEGY="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

STRATS_DIR="${HOME}/ss/sdk/RCM/StrategyStudio/examples/strategies"
DLLS_DIR="${HOME}/ss/bt/strategies_dlls"

# Ensure strategies_dlls directory exists
echo "➡️  Ensuring runtime directory exists: $DLLS_DIR"
mkdir -p "$DLLS_DIR"
echo "✅ Directory ready: $DLLS_DIR"

# Function to fix a single Makefile
fix_makefile() {
  local makefile="$1"
  local strategy_name="$2"
  
  if [[ ! -f "$makefile" ]]; then
    echo "⚠️  Makefile not found: $makefile"
    return 1
  fi
  
  # Check if it needs fixing
  if grep -q "/home/vagrant/ss/bt/strategies_dlls" "$makefile"; then
    echo "🔧 Fixing: $makefile"
    
    # Create backup
    cp "$makefile" "${makefile}.bak"
    
    # Replace hardcoded path with $(HOME)
    sed -i "s|/home/vagrant/ss/bt/strategies_dlls|\$(HOME)/ss/bt/strategies_dlls|g" "$makefile"
    
    echo "✅ Fixed: $strategy_name"
    return 0
  else
    # Check if already using $(HOME) or different path
    if grep -q "\$(HOME)/ss/bt/strategies_dlls" "$makefile"; then
      echo "✓ Already correct: $strategy_name"
      return 0
    else
      echo "⚠️  No copy_strategy target found or using different path: $strategy_name"
      echo "   Makefile location: $makefile"
      return 1
    fi
  fi
}

# Fix specific strategy or all strategies
if [[ -n "$STRATEGY" ]]; then
  # Fix single strategy
  STRAT_DIR="${STRATS_DIR}/${STRATEGY}"
  if [[ ! -d "$STRAT_DIR" ]]; then
    echo "❌ Strategy directory not found: $STRAT_DIR"
    echo "   Did you run clone_strategy.sh first?"
    exit 1
  fi
  
  fix_makefile "${STRAT_DIR}/Makefile" "$STRATEGY"
else
  # Fix all strategies
  if [[ ! -d "$STRATS_DIR" ]]; then
    echo "❌ Strategies directory not found: $STRATS_DIR"
    exit 1
  fi
  
  echo "🔍 Scanning for Makefiles in: $STRATS_DIR"
  echo ""
  
  fixed_count=0
  already_correct=0
  not_found=0
  
  for strat_dir in "$STRATS_DIR"/*; do
    if [[ -d "$strat_dir" ]]; then
      strat_name=$(basename "$strat_dir")
      makefile="${strat_dir}/Makefile"
      
      if [[ -f "$makefile" ]]; then
        if fix_makefile "$makefile" "$strat_name"; then
          if grep -q "\$(HOME)/ss/bt/strategies_dlls" "$makefile"; then
            if grep -q "/home/vagrant" "${makefile}.bak" 2>/dev/null; then
              ((fixed_count++))
            else
              ((already_correct++))
            fi
          fi
        else
          ((not_found++))
        fi
      fi
    fi
  done
  
  echo ""
  echo "📊 Summary:"
  echo "   Fixed: $fixed_count"
  echo "   Already correct: $already_correct"
  echo "   No copy_strategy target: $not_found"
fi

echo ""
echo "✅ Makefile path fix complete!"
echo ""
echo "💡 Next steps:"
echo "   1. Deploy your strategy: ./scripts/deploy_strategy.sh --name <strategy>"
echo "   2. Verify .so file was copied: ls -lh $DLLS_DIR/"

