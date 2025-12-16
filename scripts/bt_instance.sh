#!/usr/bin/env bash
set -euo pipefail

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
  $0 recheck

Examples:
  $0 create --instance MyAcharov2Instance --strategy acharov2_strategy --account UIUC --sim SIM-1001-101 --user dlariviere --cash 9900000 --symbols "SPY|NVDA|GOOG"
  $0 backtest --instance MyAcharov2Instance --start 2023-09-05 --end 2023-09-05
  $0 list
  $0 terminate --instance MyAcharov2Instance
  $0 export --cra "\$HOME/ss/bt/backtesting-results/BACK_....cra"
EOF
}

[[ -x "$CLI" ]] || { echo "Missing CLI: $CLI"; exit 1; }

SUB="${1:-}"
shift || true

case "$SUB" in
    create)
    INSTANCE="${BT_INSTANCE_NAME:-}"
    STRAT_TYPE="${BT_STRATEGY_TYPE:-}"
    GROUP="${BT_GROUP:-UIUC}"
    ACCOUNT="${BT_ACCOUNT:-}"
    USERNAME="${BT_USER:-}"
    CASH="${BT_CASH:-}"
    SYMBOLS="${BT_SYMBOLS:-}"

    while [[ $# -gt 0 ]]; do
      case "$1" in
        --instance) INSTANCE="$2"; shift 2;;
        --strategy) STRAT_TYPE="$2"; shift 2;;
        --group) GROUP="$2"; shift 2;;
        --account) ACCOUNT="$2"; shift 2;;
        --user) USERNAME="$2"; shift 2;;
        --cash) CASH="$2"; shift 2;;
        --symbols) SYMBOLS="$2"; shift 2;;
        -h|--help) usage; exit 0;;
        *) echo "Unknown arg: $1"; usage; exit 1;;
      esac
    done

    [[ -n "$INSTANCE" && -n "$STRAT_TYPE" && -n "$ACCOUNT" && -n "$USERNAME" && -n "$CASH" ]] || {
      echo "Missing required config or args"
      usage
      exit 1
    }

    echo "[ O_O ] Creating instance!"
    echo "   instance = $INSTANCE"
    echo "   strategy = $STRAT_TYPE"
    echo "   account  = $ACCOUNT"
    echo "   user     = $USERNAME"
    echo "   cash     = $CASH"
    echo "   symbols  = $SYMBOLS"


    (cd "$UTIL_DIR" && "$CLI" cmd create_instance \
        "$INSTANCE" \
        "$STRAT_TYPE" \
        "$GROUP" \
        "$ACCOUNT" \
        "$USERNAME" \
        "$CASH" \
        -symbols "$SYMBOLS")

    echo "Created."
    ;;


  backtest)
    INSTANCE="${BT_INSTANCE_NAME:-}"
    START="${BT_BACKTEST_START:-}"
    END="${BT_BACKTEST_END:-}"
    MODE="${BT_BACKTEST_MODE:-0}"

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

    [[ -n "$INSTANCE" && -n "$START" && -n "$END" ]] || {
      echo "Missing instance or backtest date range"
      usage
      exit 1
    }

    echo "[ O_O ] Starting backtest! Sit tight..."
    echo "   instance = $INSTANCE"
    echo "   start    = $START"
    echo "   end      = $END"
    echo "   mode     = $MODE"


    (cd "$UTIL_DIR" && "$CLI" cmd start_backtest "$START" "$END" "$INSTANCE" "$MODE")
    echo "Started."
    ;;

  list)
    (cd "$UTIL_DIR" && "$CLI" cmd strategy_instance_list)
    ;;

  terminate|stop|pause)
    INSTANCE=""
    ALL="false"

    while [[ $# -gt 0 ]]; do
        case "$1" in
        --instance)
            INSTANCE="$2"
            shift 2
            ;;
        --all)
            ALL="true"
            shift 1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown arg: $1"
            usage
            exit 1
            ;;
        esac
    done

    # Validation
    if [[ "$ALL" == "true" && -n "$INSTANCE" ]]; then
        echo "❌ Cannot use --all and --instance together"
        exit 1
    fi

    if [[ "$ALL" == "false" && -z "$INSTANCE" ]]; then
        echo "❌ You must specify either --instance NAME or --all"
        exit 1
    fi

    if [[ "$ALL" == "true" ]]; then
        echo "➡️  $SUB ALL strategy instances"
        (cd "$UTIL_DIR" && "$CLI" cmd "$SUB" -all)
    else
        echo "➡️  $SUB instance: $INSTANCE"
        (cd "$UTIL_DIR" && "$CLI" cmd "$SUB" "$INSTANCE")
    fi

    echo "Done."
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
    echo "Export done."
    ;;

  recheck)
    echo "➡️ Rechecking strategy DLLs..."
    (cd "$UTIL_DIR" && "$CLI" cmd recheck_strategies)
    echo "Done."
    ;;


  *)
    usage
    exit 1
    ;;
esac
