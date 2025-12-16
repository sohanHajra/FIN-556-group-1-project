#!/usr/bin/env bash
set -euo pipefail

USER_NAME="${USER}"
HOME_SS="$HOME/ss"

# Log locations
BT_LOG_DIR="/student_work/${USER_NAME}/ss_logs"
BT_LOG="${BT_LOG_DIR}/bt_server.log"

SDK_LOG_DIR="$HOME_SS/sdk/RCM/StrategyStudio/logs"
BT_RESULTS_DIR="$HOME_SS/bt/backtesting-results"

usage() {
  cat <<EOF
StrategyStudio Log Manager

Usage:
  $0 summary
  $0 largest
  $0 bt
  $0 sdk
  $0 results
  $0 clean bt
  $0 clean sdk
  $0 clean results
  $0 clean all
  $0 purge --days N

Commands:
  summary        Show total disk usage of all SS logs
  largest        Show largest log files
  bt             Show size of backtest server logs
  sdk            Show size of SDK logs
  results        Show size of backtest result files (.cra)
  clean bt       Delete backtest server logs
  clean sdk      Delete SDK logs
  clean results  Delete backtest result (.cra) files
  clean all      Delete ALL StrategyStudio logs/results
  purge --days N Delete logs older than N days (safe)

Examples:
  $0 summary
  $0 largest
  $0 clean bt
  $0 purge --days 7
EOF
}

require_dir() {
  [[ -d "$1" ]] || return 1
}

cmd="${1:-}"
shift || true

case "$cmd" in
  summary)
    echo "=== StrategyStudio Log Usage Summary ==="
    echo

    require_dir "$BT_LOG_DIR" && du -sh "$BT_LOG_DIR" || echo "BT logs: none"
    require_dir "$SDK_LOG_DIR" && du -sh "$SDK_LOG_DIR" || echo "SDK logs: none"
    require_dir "$BT_RESULTS_DIR" && du -sh "$BT_RESULTS_DIR" || echo "Backtest results: none"

    echo
    echo "Total:"
    du -sh "$BT_LOG_DIR" "$SDK_LOG_DIR" "$BT_RESULTS_DIR" 2>/dev/null | awk '{s+=$1} END {print "(see breakdown above)"}'
    ;;

  largest)
    echo "=== Largest StrategyStudio Files ==="
    find "$BT_LOG_DIR" "$SDK_LOG_DIR" "$BT_RESULTS_DIR" \
      -type f -size +10M -exec ls -lh {} \; 2>/dev/null | sort -k5 -h
    ;;

  bt)
    require_dir "$BT_LOG_DIR" || { echo "No BT log dir"; exit 0; }
    du -sh "$BT_LOG_DIR"
    ls -lh "$BT_LOG_DIR"
    ;;

  sdk)
    require_dir "$SDK_LOG_DIR" || { echo "No SDK log dir"; exit 0; }
    du -sh "$SDK_LOG_DIR"
    ls -lh "$SDK_LOG_DIR"
    ;;

  results)
    require_dir "$BT_RESULTS_DIR" || { echo "No results dir"; exit 0; }
    du -sh "$BT_RESULTS_DIR"
    ls -lh "$BT_RESULTS_DIR"
    ;;

  clean)
    TARGET="${1:-}"
    case "$TARGET" in
      bt)
        echo "⚠️ Deleting backtest server logs"
        rm -f "$BT_LOG_DIR"/*.log
        ;;
      sdk)
        echo "⚠️ Deleting SDK logs"
        rm -f "$SDK_LOG_DIR"/*
        ;;
      results)
        echo "⚠️ Deleting backtest result files (.cra)"
        rm -f "$BT_RESULTS_DIR"/*.cra
        ;;
      all)
        echo "⚠️ Deleting ALL StrategyStudio logs and results"
        rm -f "$BT_LOG_DIR"/*.log
        rm -f "$SDK_LOG_DIR"/*
        rm -f "$BT_RESULTS_DIR"/*.cra
        ;;
      *)
        echo "❌ Specify what to clean: bt | sdk | results | all"
        exit 1
        ;;
    esac
    echo "✅ Done."
    ;;

  purge)
    DAYS=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --days) DAYS="$2"; shift 2;;
        *) usage; exit 1;;
      esac
    done

    [[ -n "$DAYS" ]] || {
      echo "❌ Must specify --days N"
      exit 1
    }

    echo "⚠️ Deleting files older than $DAYS days"

    find "$BT_LOG_DIR" "$SDK_LOG_DIR" "$BT_RESULTS_DIR" \
      -type f -mtime +"$DAYS" -print -delete 2>/dev/null

    echo "✅ Purge complete."
    ;;

  *)
    usage
    exit 1
    ;;
esac
