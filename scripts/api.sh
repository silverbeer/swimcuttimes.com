#!/bin/bash
# Manage the backend API server
# Usage:
#   ./scripts/api.sh start    # Start the API server
#   ./scripts/api.sh stop     # Stop the API server
#   ./scripts/api.sh status   # Check if running
#   ./scripts/api.sh restart  # Restart the API server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/.api.pid"
LOG_FILE="$PROJECT_ROOT/.api.log"
APP_PATH="src/swimcuttimes/api/app.py"

show_usage() {
    echo "Usage: $0 <start|stop|status|restart|logs|tail>"
    echo ""
    echo "Commands:"
    echo "  start      Start the API server (background)"
    echo "  stop       Stop the API server"
    echo "  status     Check if the API server is running"
    echo "  restart    Restart the API server"
    echo "  logs       Follow logs (tail -f) with color"
    echo "  tail [N]   Show last N lines (default: 50) with color"
    exit 1
}

is_running() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

do_start() {
    if is_running; then
        echo "API server is already running (PID: $(cat "$PID_FILE"))"
        exit 1
    fi

    echo "Starting API server..."
    cd "$PROJECT_ROOT"
    nohup uv run fastapi dev "$APP_PATH" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1

    if is_running; then
        echo "API server started (PID: $(cat "$PID_FILE"))"
        echo "  URL: http://127.0.0.1:8000"
        echo "  Docs: http://127.0.0.1:8000/docs"
        echo "  Logs: ./scripts/api.sh logs"
    else
        echo "Failed to start API server. Check logs:"
        tail -20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

do_stop() {
    if ! is_running; then
        echo "API server is not running"
        rm -f "$PID_FILE"
        exit 0
    fi

    pid=$(cat "$PID_FILE")
    echo "Stopping API server (PID: $pid)..."
    kill "$pid" 2>/dev/null || true

    # Wait for process to stop
    for i in {1..10}; do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done

    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "API server stopped"
}

do_status() {
    if is_running; then
        pid=$(cat "$PID_FILE")
        echo "API server is running (PID: $pid)"
        echo "  URL: http://127.0.0.1:8000"
        echo "  Docs: http://127.0.0.1:8000/docs"
    else
        echo "API server is not running"
        rm -f "$PID_FILE" 2>/dev/null || true
    fi
}

do_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE" | colorize_logs
    else
        echo "No log file found. Is the server running?"
        exit 1
    fi
}

do_tail() {
    local lines="${2:-50}"
    if [ -f "$LOG_FILE" ]; then
        tail -n "$lines" "$LOG_FILE" | colorize_logs
    else
        echo "No log file found. Is the server running?"
        exit 1
    fi
}

colorize_logs() {
    # ANSI color codes
    local RED='\033[0;31m'
    local YELLOW='\033[0;33m'
    local GREEN='\033[0;32m'
    local CYAN='\033[0;36m'
    local GRAY='\033[0;90m'
    local BOLD='\033[1m'
    local RESET='\033[0m'

    awk -v RED="$RED" -v YELLOW="$YELLOW" -v GREEN="$GREEN" \
        -v CYAN="$CYAN" -v GRAY="$GRAY" -v BOLD="$BOLD" -v RESET="$RESET" '
    /ERROR|error|Error|CRITICAL|critical|Critical|Traceback|Exception/ {
        print BOLD RED $0 RESET
        next
    }
    /WARNING|warning|Warning|WARN|warn/ {
        print YELLOW $0 RESET
        next
    }
    /INFO|info/ {
        print CYAN $0 RESET
        next
    }
    /DEBUG|debug/ {
        print GRAY $0 RESET
        next
    }
    /HTTP.*200|HTTP.*201|HTTP.*204/ {
        print GREEN $0 RESET
        next
    }
    /HTTP.*[45][0-9][0-9]/ {
        print RED $0 RESET
        next
    }
    {
        print $0
    }
    '
}

# Main
if [ $# -eq 0 ]; then
    show_usage
fi

case "$1" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    restart)
        do_stop
        sleep 1
        do_start
        ;;
    logs)
        do_logs
        ;;
    tail)
        do_tail "$@"
        ;;
    *)
        show_usage
        ;;
esac
