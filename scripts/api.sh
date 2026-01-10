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
BACKEND_DIR="$PROJECT_ROOT/backend"
PID_FILE="$PROJECT_ROOT/.api.pid"
LOG_FILE="$PROJECT_ROOT/.api.log"
APP_PATH="src/swimcuttimes/api/app.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# Emojis
API="🚀"
CHECK="✅"
CROSS="❌"
WARN="⚠️ "
INFO="📋"
STOP="🛑"
LOGS="📜"
SYNC="🔄"

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}$1${RESET}"
    echo -e "${DIM}────────────────────────────────────────${RESET}"
}

print_success() {
    echo -e "${GREEN}${CHECK} $1${RESET}"
}

print_error() {
    echo -e "${RED}${CROSS} $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}${WARN}$1${RESET}"
}

print_info() {
    echo -e "${CYAN}${INFO} $1${RESET}"
}

print_step() {
    echo -e "${SYNC} $1"
}

format_env_badge() {
    local env_name="$1"
    case "$env_name" in
        local)
            echo -e "${GREEN}${BOLD}LOCAL${RESET}"
            ;;
        development)
            echo -e "${YELLOW}${BOLD}DEV${RESET}"
            ;;
        production)
            echo -e "${RED}${BOLD}PROD${RESET}"
            ;;
        *)
            echo -e "${DIM}$env_name${RESET}"
            ;;
    esac
}

show_usage() {
    print_header "${API} API Server Management"
    echo ""
    echo -e "Usage: ${BOLD}$0${RESET} <command>"
    echo ""
    echo "Commands:"
    echo -e "  ${BOLD}start${RESET}      Start the API server (background)"
    echo -e "  ${BOLD}stop${RESET}       Stop the API server"
    echo -e "  ${BOLD}status${RESET}     Check if the API server is running"
    echo -e "  ${BOLD}restart${RESET}    Restart the API server"
    echo -e "  ${BOLD}logs${RESET}       Follow logs (tail -f) with color"
    echo -e "  ${BOLD}tail${RESET} [N]   Show last N lines (default: 50) with color"
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
    print_header "${API} Start API Server"

    if is_running; then
        print_warning "API server is already running (PID: $(cat "$PID_FILE"))"
        exit 1
    fi

    print_step "Starting server..."
    cd "$BACKEND_DIR"
    nohup uv run fastapi dev "$APP_PATH" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1

    if is_running; then
        echo ""
        print_success "API server started (PID: $(cat "$PID_FILE"))"
        echo ""
        echo -e "   ${BOLD}URL${RESET}:   http://127.0.0.1:8000"
        echo -e "   ${BOLD}Docs${RESET}:  http://127.0.0.1:8000/docs"
        echo -e "   ${BOLD}Logs${RESET}:  ${DIM}./scripts/api.sh logs${RESET}"
    else
        print_error "Failed to start API server"
        echo ""
        echo -e "   ${DIM}Recent logs:${RESET}"
        tail -20 "$LOG_FILE" | sed 's/^/   /'
        rm -f "$PID_FILE"
        exit 1
    fi
}

do_stop() {
    print_header "${STOP} Stop API Server"

    if ! is_running; then
        print_info "API server is not running"
        rm -f "$PID_FILE"
        exit 0
    fi

    pid=$(cat "$PID_FILE")
    print_step "Stopping server (PID: $pid)..."
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
    echo ""
    print_success "API server stopped"
}

do_status() {
    print_header "${API} API Server Status"

    if is_running; then
        pid=$(cat "$PID_FILE")
        echo ""
        print_success "Server is running (PID: $pid)"
        echo ""
        echo -e "   ${BOLD}URL${RESET}:   http://127.0.0.1:8000"
        echo -e "   ${BOLD}Docs${RESET}:  http://127.0.0.1:8000/docs"
    else
        echo ""
        print_info "Server is not running"
        rm -f "$PID_FILE" 2>/dev/null || true
    fi

    # Show environment info
    local env_file="$PROJECT_ROOT/.env"
    if [ -f "$env_file" ]; then
        local env_name
        env_name=$(grep -E "^ENVIRONMENT=" "$env_file" 2>/dev/null | cut -d= -f2)
        local supabase_url
        supabase_url=$(grep -E "^SUPABASE_URL=" "$env_file" 2>/dev/null | cut -d= -f2)

        echo ""
        echo -e "   ${BOLD}Environment${RESET}"
        if [ -n "$env_name" ]; then
            echo -e "   ├─ Config:   $(format_env_badge "$env_name")"
        else
            echo -e "   ├─ Config:   ${DIM}not set${RESET}"
        fi
        if [ -n "$supabase_url" ]; then
            echo -e "   └─ Supabase: ${DIM}$supabase_url${RESET}"
            # Determine Studio URL
            if [[ "$supabase_url" == *"127.0.0.1"* ]] || [[ "$supabase_url" == *"localhost"* ]]; then
                echo -e "      Studio:   ${DIM}http://127.0.0.1:54323${RESET}"
            else
                # Extract project ref from cloud URL (e.g., https://abcdefgh.supabase.co)
                local project_ref
                project_ref=$(echo "$supabase_url" | sed -E 's|https://([^.]+)\.supabase\.co.*|\1|')
                if [ -n "$project_ref" ] && [ "$project_ref" != "$supabase_url" ]; then
                    echo -e "      Dashboard: ${DIM}https://supabase.com/dashboard/project/$project_ref${RESET}"
                fi
            fi
        fi
    else
        echo ""
        echo -e "   ${YELLOW}${WARN}Environment: .env not found${RESET}"
        echo -e "   ${DIM}Run: ./scripts/env.sh local${RESET}"
    fi
}

do_logs() {
    print_header "${LOGS} API Server Logs"

    if [ -f "$LOG_FILE" ]; then
        echo -e "${DIM}Following logs... (Ctrl+C to exit)${RESET}"
        echo ""
        tail -f "$LOG_FILE" | colorize_logs
    else
        print_error "No log file found"
        echo -e "   ${DIM}Is the server running?${RESET}"
        exit 1
    fi
}

do_tail() {
    local lines="${2:-50}"

    print_header "${LOGS} API Server Logs (last $lines lines)"

    if [ -f "$LOG_FILE" ]; then
        echo ""
        tail -n "$lines" "$LOG_FILE" | colorize_logs
    else
        print_error "No log file found"
        echo -e "   ${DIM}Is the server running?${RESET}"
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
