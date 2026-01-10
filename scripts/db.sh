#!/bin/bash
# Database management wrapper for Supabase
# Usage:
#   ./scripts/db.sh status    # Show migration status
#   ./scripts/db.sh migrate   # Apply pending migrations
#   ./scripts/db.sh reset     # Reset database (migrations + seed)
#   ./scripts/db.sh start     # Start local Supabase
#   ./scripts/db.sh stop      # Stop local Supabase

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# Emojis
DB="🗄️ "
CHECK="✅"
CROSS="❌"
WARN="⚠️ "
ROCKET="🚀"
STOP="🛑"
INFO="📋"
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

show_usage() {
    print_header "${DB}Database Management"
    echo ""
    echo -e "Usage: ${BOLD}$0${RESET} <command>"
    echo ""
    echo "Commands:"
    echo -e "  ${BOLD}status${RESET}    Show migration status and pending migrations"
    echo -e "  ${BOLD}migrate${RESET}   Apply pending migrations"
    echo -e "  ${BOLD}reset${RESET}     Reset database (re-run all migrations + seed)"
    echo -e "  ${BOLD}start${RESET}     Start local Supabase (local env only)"
    echo -e "  ${BOLD}stop${RESET}      Stop local Supabase (local env only)"
    echo ""
    echo -e "${DIM}Environment is determined from .env file (use ./scripts/env.sh to switch)${RESET}"
    exit 1
}

get_environment() {
    if [ ! -f "$ENV_FILE" ]; then
        echo ""
        return
    fi
    grep -E "^ENVIRONMENT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2
}

get_supabase_url() {
    if [ ! -f "$ENV_FILE" ]; then
        echo ""
        return
    fi
    grep -E "^SUPABASE_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2
}

is_local_env() {
    local env_name
    env_name=$(get_environment)
    [[ "$env_name" == "local" ]]
}

format_env_badge() {
    local env_name="$1"
    case "$env_name" in
        local)
            echo -e "${GREEN}LOCAL${RESET}"
            ;;
        development)
            echo -e "${YELLOW}DEV${RESET}"
            ;;
        production)
            echo -e "${RED}${BOLD}PROD${RESET}"
            ;;
        *)
            echo -e "${DIM}$env_name${RESET}"
            ;;
    esac
}

check_environment() {
    local env_name
    env_name=$(get_environment)

    if [ -z "$env_name" ]; then
        print_error "No environment configured"
        echo -e "  Run: ${BOLD}./scripts/env.sh local${RESET}"
        exit 1
    fi

    local badge
    badge=$(format_env_badge "$env_name")
    echo -e "${DB}Environment: $badge"
    echo -e "   Database: ${DIM}$(get_supabase_url)${RESET}"
    echo ""
}

require_local() {
    if ! is_local_env; then
        print_error "This command only works with local environment"
        echo -e "   Current: $(format_env_badge "$(get_environment)")"
        echo ""
        echo -e "   Switch to local: ${BOLD}./scripts/env.sh local${RESET}"
        exit 1
    fi
}

warn_production() {
    local env_name
    env_name=$(get_environment)

    if [[ "$env_name" == "production" ]]; then
        echo ""
        print_warning "You are operating on PRODUCTION database"
        echo ""
        echo -ne "   Are you sure? [y/N] "
        read -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cancelled"
            exit 1
        fi
        echo ""
    fi
}

do_status() {
    print_header "${DB}Migration Status"
    check_environment

    if is_local_env; then
        npx supabase migration list --local
    else
        npx supabase migration list
    fi
}

do_migrate() {
    print_header "${DB}Apply Migrations"
    check_environment
    warn_production

    print_step "Applying pending migrations..."
    echo ""

    if is_local_env; then
        npx supabase migration up --local
    else
        npx supabase migration up
    fi

    echo ""
    print_success "Migrations applied"
    echo -e "   ${DIM}Run './scripts/db.sh status' to verify${RESET}"
}

do_reset() {
    print_header "${DB}Reset Database"
    check_environment

    if ! is_local_env; then
        print_error "Database reset is only allowed for local environment"
        echo -e "   Current: $(format_env_badge "$(get_environment)")"
        echo ""
        echo -e "   ${DIM}For cloud environments, use migrations or the Supabase dashboard${RESET}"
        exit 1
    fi

    print_warning "This will destroy all local data and re-run migrations + seed"
    echo ""
    echo -ne "   Are you sure? [y/N] "
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cancelled"
        exit 1
    fi

    echo ""
    print_step "Resetting database..."
    echo ""
    npx supabase db reset
    echo ""
    print_success "Database reset complete"
}

do_start() {
    print_header "${DB}Start Local Supabase"
    require_local

    print_step "Starting services..."
    echo ""
    npx supabase start
    echo ""
    print_success "Local Supabase is running"
    echo -e "   Studio:  ${BOLD}http://127.0.0.1:54323${RESET}"
    echo -e "   API:     ${DIM}http://127.0.0.1:54321${RESET}"
}

do_stop() {
    print_header "${DB}Stop Local Supabase"
    require_local

    print_step "Stopping services..."
    npx supabase stop
    echo ""
    print_success "Local Supabase stopped"
}

# Main
if [ $# -eq 0 ]; then
    show_usage
fi

case "$1" in
    status)
        do_status
        ;;
    migrate)
        do_migrate
        ;;
    reset)
        do_reset
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    *)
        show_usage
        ;;
esac
