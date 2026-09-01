#!/usr/bin/env bash
set -euo pipefail

# ---- CLI Logging (ADDED) ----
CLI_LOG_DIR="/student_work/${USER}/ss_logs"
CLI_LOG="$CLI_LOG_DIR/bt_cli.log"
mkdir -p "$CLI_LOG_DIR"
# Log to file AND terminal
exec > >(tee -a "$CLI_LOG") 2>&1
# ----------------------------

UTIL_DIR="${HOME}/ss/bt/utilities"
CLI="${UTIL_DIR}/StrategyCommandLine"
# Load per-user config
CONFIG_FILE="$(dirname "$0")/bt_config.sh"
if [[ -f "$CONFIG_FILE" ]]; then
  source "$CONFIG_FILE"
else
  echo "Missing config file: scripts/bt_config.sh"
  echo "Copy scripts/bt_config.example.sh → bt_config.sh"
  exit 1
fi

# ---- Paths ----
BT_DIR="$HOME/ss/bt"
BIN="$BT_DIR/StrategyServerBacktesting"

# Put logs OUTSIDE home quota
LOG_DIR="/student_work/${USER}/ss_logs"
LOG="$LOG_DIR/bt_server.log"

PIDFILE="$BT_DIR/bt_server.pid"

# ---- Setup ----
mkdir -p "$LOG_DIR"

usage() {
  echo "Usage: $0 start|stop|status|logs|restart"
}

is_running() {
  [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

case "${1:-}" in
  start)
    if is_running; then
      echo "Backtest server already running (pid $(cat "$PIDFILE"))"
      exit 0
    fi

    [[ -x "$BIN" ]] || {
      echo "StrategyServerBacktesting not executable: $BIN"
      exit 1
    }

    echo "➡️ Starting StrategyServerBacktesting..."
    echo "   Logs → $LOG"

    cd "$BT_DIR"

    nohup "$BIN" >> "$LOG" 2>&1 &
    PID=$!

    sleep 1

    if kill -0 "$PID" 2>/dev/null; then
      echo "$PID" > "$PIDFILE"
      echo "Started (pid $PID)"
    else
      echo "Failed to start. Last log lines:"
      tail -n 50 "$LOG" || true
      exit 1
    fi
    ;;

  stop)
    if is_running; then
      PID=$(cat "$PIDFILE")
      echo "➡️ Stopping StrategyServerBacktesting (pid $PID)"
      kill "$PID" || true
      rm -f "$PIDFILE"
      echo "Stopped"
    else
      echo "Not running"
    fi
    ;;

  status)
    if is_running; then
      echo "Running (pid $(cat "$PIDFILE"))"
    else
      echo "Not running"
      exit 1
    fi
    ;;

  logs)
    if [[ -f "$LOG" ]]; then
      tail -n 100 "$LOG"
    else
      echo "No log file found at $LOG"
      exit 1
    fi
    ;;

  restart)
    echo "Restarting StrategyServerBacktesting..."
    "$0" stop
    echo "Waiting for server to fully stop..."
    sleep 5
    "$0" start
    echo "Restart complete"
    ;;

  *)
    usage
    exit 1
    ;;
esac
