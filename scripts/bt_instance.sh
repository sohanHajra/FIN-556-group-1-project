#!/usr/bin/env bash
set -euo pipefail

UTIL_DIR="${HOME}/ss/bt/utilities"
CLI="${UTIL_DIR}/StrategyCommandLine"

usage() {
  cat <<EOF
Usage:
  $0 create   --instance NAME --strategy STRAT --account UIUC --sim SIM-XXXX-XXX --user USERNAME --cash 9900000 --symbols "SPY|NVDA"
  $0 backtest --instance NAME --start YYYY-MM-DD --end YYYY-MM-DD [--mode 0]
  $0 list
  $0 terminate --instance NAME
  $0 stop      --instance NAME
  $0 pause     --instance NAME
  $0 export    --cra /path/to/file.cra

Examples:
  $0 create --instance MyAcharov2Instance --strategy acharov2_strategy --account UIUC --sim SIM-1001-101 --user dlariviere --cash 9900000 --symbols "SPY|NVDA|GOOG"
  $0 backtest --instance MyAcharov2Instance --start 2023-09-05 --end 2023-09-05
  $0 list
  $0 terminate --instance MyAcharov2Instance
  $0 export --cra "\$HOME/ss/bt/backtesting-results/BACK_....cra"
EOF
}

[[ -x "$CLI" ]] || { echo "❌ Missing CLI: $CLI"; exit 1; }

SUB="${1:-}"
shift || true

case "$SUB" in
  create)
    INSTANCE=""; STRAT=""; ACCOUNT=""; SIM=""; USERNAME=""; CASH=""; SYMBOLS=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --instance) INSTANCE="$2"; shift 2;;
        --strategy) STRAT="$2"; shift 2;;   # expects "acharov2_strategy" (we append .so)
        --account) ACCOUNT="$2"; shift 2;;
        --sim) SIM="$2"; shift 2;;
        --user) USERNAME="$2"; shift 2;;
        --cash) CASH="$2"; shift 2;;
        --symbols) SYMBOLS="$2"; shift 2;;
        -h|--help) usage; exit 0;;
        *) echo "Unknown arg: $1"; usage; exit 1;;
      esac
    done

    [[ -n "$INSTANCE" && -n "$STRAT" && -n "$ACCOUNT" && -n "$SIM" && -n "$USERNAME" && -n "$CASH" && -n "$SYMBOLS" ]] || {
      usage; exit 1;
    }

    STRAT_SO="${STRAT}.so"
    echo "➡️  Creating instance: $INSTANCE"
    (cd "$UTIL_DIR" && "$CLI" cmd create_instance \
      "$INSTANCE" "$STRAT_SO" "$ACCOUNT" "$SIM" "$USERNAME" "$CASH" \
      -symbols "$SYMBOLS")
    echo "✅ Created."
    ;;

  backtest)
    INSTANCE=""; START=""; END=""; MODE="0"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --instance) INSTANCE="$2"; shift 2;;
        --start) START="$2"; shift 2;;
        --end) END="$2"; shift 2;;
        --mode) MODE="$2"; shift 2;;
        -h|--help) usage; exit 0;;
        *) echo "Unknown arg: $1"; usage; exit 1;;
      esac
    done

    [[ -n "$INSTANCE" && -n "$START" && -n "$END" ]] || { usage; exit 1; }

    echo "➡️  Starting backtest: $INSTANCE  $START → $END"
    (cd "$UTIL_DIR" && "$CLI" cmd start_backtest "$START" "$END" "$INSTANCE" "$MODE")
    echo "✅ Started."
    ;;

  list)
    (cd "$UTIL_DIR" && "$CLI" cmd strategy_instance_list)
    ;;

  terminate|stop|pause)
    INSTANCE=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --instance) INSTANCE="$2"; shift 2;;
        -h|--help) usage; exit 0;;
        *) echo "Unknown arg: $1"; usage; exit 1;;
      esac
    done

    [[ -n "$INSTANCE" ]] || {
      echo "❌ You must specify --instance NAME"
      exit 1
    }

    echo "➡️  $SUB instance: $INSTANCE"
    (cd "$UTIL_DIR" && "$CLI" cmd "$SUB" "$INSTANCE")
    echo "✅ Done."
    ;;

  export)
    CRA=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --cra) CRA="$2"; shift 2;;
        -h|--help) usage; exit 0;;
        *) echo "Unknown arg: $1"; usage; exit 1;;
      esac
    done

    [[ -n "$CRA" ]] || { usage; exit 1; }

    echo "➡️  Exporting CRA: $CRA"
    (cd "$UTIL_DIR" && "$CLI" cmd export_cra_file "$CRA")
    echo "✅ Export done."
    ;;

  *)
    usage
    exit 1
    ;;
esac
