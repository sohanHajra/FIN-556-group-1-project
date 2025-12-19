#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $0 [--netid NETID] [--template TEMPLATE_DIR] [--name NEW_STRATEGY_DIRNAME]

This script creates a new strategy directory in StrategyStudio by cloning a template.
This is typically the FIRST STEP when setting up a new strategy.

Workflow:
  1. Run this script to create the StrategyStudio directory
  2. Then either:
     a) Use deploy_strategy.sh to copy from repo src/ and build:
        ./scripts/deploy_strategy.sh --name <STRATEGY_NAME>
     b) Or manually edit files and use build_copy_strategy.sh:
        ./scripts/build_copy_strategy.sh --name <STRATEGY_NAME>

Defaults:
  --netid     \$USER
  --template  dia_index_arb_strategy
  --name      <netid>_strategy

Examples:
  $0
  $0 --netid acharov2
  $0 --name AntonArb
  $0 --template dia_index_arb_strategy --name nvda_momo
EOF
}

NETID="${USER}"
TEMPLATE="dia_index_arb_strategy"
NEWNAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --netid) NETID="$2"; shift 2;;
    --template) TEMPLATE="$2"; shift 2;;
    --name) NEWNAME="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

STRATS_DIR="${HOME}/ss/sdk/RCM/StrategyStudio/examples/strategies"
[[ -d "$STRATS_DIR" ]] || { echo "❌ Missing: $STRATS_DIR"; exit 1; }

cd "$STRATS_DIR"

[[ -d "$TEMPLATE" ]] || { echo "❌ Template not found: $STRATS_DIR/$TEMPLATE"; exit 1; }

if [[ -z "$NEWNAME" ]]; then
  NEWNAME="${NETID}_strategy"
fi

if [[ -e "$NEWNAME" ]]; then
  echo "Target already exists: $STRATS_DIR/$NEWNAME"
  exit 1
fi

echo "➡️  Cloning $TEMPLATE -> $NEWNAME"
cp -r "$TEMPLATE" "$NEWNAME"

cd "$NEWNAME"

# Detect the "main" header/cpp/so in template folder (common patterns)
# If your template always has DiaIndexArb.* you can keep it simple,
# but this is a bit more robust.
OLD_H="$(ls *.h 2>/dev/null | head -n 1 || true)"
OLD_CPP="$(ls *.cpp 2>/dev/null | head -n 1 || true)"
OLD_SO="$(ls *.so 2>/dev/null | head -n 1 || true)"

if [[ -z "$OLD_H" || -z "$OLD_CPP" ]]; then
  echo "Could not find .h/.cpp in $STRATS_DIR/$NEWNAME"
  exit 1
fi

NEW_H="${NEWNAME}.h"
NEW_CPP="${NEWNAME}.cpp"
NEW_SO="${NEWNAME}.so"

echo "➡️  Renaming:"
echo "    $OLD_H   -> $NEW_H"
echo "    $OLD_CPP -> $NEW_CPP"
mv "$OLD_H" "$NEW_H"
mv "$OLD_CPP" "$NEW_CPP"

if [[ -n "$OLD_SO" ]]; then
  echo "    $OLD_SO  -> $NEW_SO"
  mv "$OLD_SO" "$NEW_SO" || true
fi

# Fix include line in cpp (replace old header name with new header)
if grep -qE "^\s*#include\s+\"${OLD_H}\"" "$NEW_CPP" 2>/dev/null; then
  sed -i.bak "s|#include \"${OLD_H}\"|#include \"${NEW_H}\"|g" "$NEW_CPP"
else
  # If it included a different header, best-effort replace first local include.
  sed -i.bak "0,/^\\s*#include\\s\\+\".*\\.h\"/s//#include \"${NEW_H}\"/" "$NEW_CPP" || true
fi

# Update Makefile if present
if [[ -f Makefile ]]; then
  echo "➡️  Updating Makefile..."
  cp Makefile "Makefile.preclone.bak"

  # Replace or add variables
  if grep -q '^LIBRARY=' Makefile; then
    sed -i.bak "s|^LIBRARY=.*|LIBRARY=${NEW_SO}|" Makefile
  else
    echo "LIBRARY=${NEW_SO}" >> Makefile
  fi

  if grep -q '^SOURCES=' Makefile; then
    sed -i.bak "s|^SOURCES=.*|SOURCES=${NEW_CPP}|" Makefile
  else
    echo "SOURCES=${NEW_CPP}" >> Makefile
  fi

  if grep -q '^HEADERS=' Makefile; then
    sed -i.bak "s|^HEADERS=.*|HEADERS=${NEW_H}|" Makefile
  else
    echo "HEADERS=${NEW_H}" >> Makefile
  fi

  echo "Makefile updated (backup: Makefile.preclone.bak)"
else
  echo "No Makefile found; skipping Makefile updates."
fi

echo ""
echo "✅ Strategy cloned at: $STRATS_DIR/$NEWNAME"
echo ""
echo "📋 Next steps:"
echo "   Option 1 (recommended for repo-based workflows):"
echo "     ./scripts/deploy_strategy.sh --name $NEWNAME"
echo "     (Copies from ./src/$NEWNAME/ and builds)"
echo ""
echo "   Option 2 (if editing directly in StrategyStudio):"
echo "     ./scripts/build_copy_strategy.sh --name $NEWNAME"
echo "     (Builds the strategy in place)"
