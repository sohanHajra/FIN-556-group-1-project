#!/usr/bin/env bash
set -euo pipefail

SS_HOME="$HOME/ss"

BT_DIR="$SS_HOME/bt"
BT_LOG="$BT_DIR/bt_server.log"
BT_RESULTS="$BT_DIR/backtesting-results"

SDK_LOG_DIR="$SS_HOME/sdk/RCM/StrategyStudio/logs"

usage() {
  cat <<EOF
StrategyStudio log viewer

Usage:
  $0 list
  $0 bt                # show backtest server log
  $0 bt -f             # follow backtest server log
  $0 results           # list backtest result files
  $0 result --instance NAME
  $0 errors            # grep for ERROR / FATAL across logs

Examples:
  $0 list
  $0 bt -f
  $0 result --instance MyAcharov2Instance
  $0 errors
EOF
}

cmd="${1:-}"
shift || true

case "$cmd" in
  list)
    echo "=== Backtester logs ==="
    ls -lh "$BT_DIR"/*.log 2>/dev/null || echo "(none)"

    echo
    echo "=== StrategyStudio SDK logs ==="
    ls -lh "$SDK_LOG_DIR" 2>/dev/null || echo "(none)"

    echo
    echo "=== Backtesting results ==="
    ls -lh "$BT_RESULTS" 2>/dev/null || echo "(none)"
    ;;

  bt)
    FOLLOW=0
    if [[ "${1:-}" == "-f" ]]; then
      FOLLOW=1
    fi

    [[ -f "$BT_LOG" ]] || {
      echo "No backtest server log found: $BT_LOG"
      exit 1
    }

    if [[ "$FOLLOW" -eq 1 ]]; then
      tail -f "$BT_LOG"
    else
      less "$BT_LOG"
    fi
    ;;

  results)
    ls -lh "$BT_RESULTS"
    ;;

  result)
    INSTANCE=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --instance) INSTANCE="$2"; shift 2;;
        *) usage; exit 1;;
      esac
    done

    [[ -n "$INSTANCE" ]] || {
      echo "You must specify --instance NAME"
      exit 1
    }

    echo "Results for instance: $INSTANCE"
    ls -lh "$BT_RESULTS" | grep "$INSTANCE" || echo "(none found)"
    ;;

  errors)
    echo "=== Errors in backtest server log ==="
    grep -iE "error|fatal|exception" "$BT_LOG" 2>/dev/null || echo "(none)"

    echo
    echo "=== Errors in SDK logs ==="
    grep -iE "error|fatal|exception" "$SDK_LOG_DIR"/* 2>/dev/null || echo "(none)"
    ;;

  *)
    usage
    exit 1
    ;;
esac
