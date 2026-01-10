#!/bin/bash
# Switch or show environment configuration
# Usage:
#   ./scripts/env.sh local     # Switch to local Supabase
#   ./scripts/env.sh dev       # Switch to dev cloud
#   ./scripts/env.sh prod      # Switch to prod cloud (prompts for confirmation)
#   ./scripts/env.sh status    # Show current environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
ENV="🌍"
CHECK="✅"
CROSS="❌"
WARN="⚠️ "
INFO="📋"
SWITCH="🔀"

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
    print_header "${ENV} Environment Management"
    echo ""
    echo -e "Usage: ${BOLD}$0${RESET} <command>"
    echo ""
    echo "Commands:"
    echo -e "  ${BOLD}local${RESET}    Switch to local Supabase environment"
    echo -e "  ${BOLD}dev${RESET}      Switch to development cloud environment"
    echo -e "  ${BOLD}prod${RESET}     Switch to production cloud environment"
    echo -e "  ${BOLD}status${RESET}   Show current environment configuration"
    exit 1
}

show_status() {
    print_header "${ENV} Current Environment"

    ENV_FILE="$PROJECT_ROOT/.env"

    if [ ! -f "$ENV_FILE" ]; then
        print_error "No .env file found"
        echo -e "   Run: ${BOLD}./scripts/env.sh local${RESET}"
        exit 1
    fi

    local env_name
    env_name=$(grep -E "^ENVIRONMENT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
    local supabase_url
    supabase_url=$(grep -E "^SUPABASE_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
    local log_level
    log_level=$(grep -E "^LOG_LEVEL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
    local log_format
    log_format=$(grep -E "^LOG_FORMAT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)

    echo ""
    echo -e "  Environment:  $(format_env_badge "$env_name")"
    echo ""
    echo -e "  ${BOLD}Database${RESET}"
    echo -e "  └─ URL:       ${DIM}$supabase_url${RESET}"

    # Show Studio URL
    if [[ "$supabase_url" == *"127.0.0.1"* ]] || [[ "$supabase_url" == *"localhost"* ]]; then
        echo -e "  └─ Studio:    ${DIM}http://127.0.0.1:54323${RESET}"
    else
        local project_ref
        project_ref=$(echo "$supabase_url" | sed -E 's|https://([^.]+)\.supabase\.co.*|\1|')
        if [ -n "$project_ref" ] && [ "$project_ref" != "$supabase_url" ]; then
            echo -e "  └─ Dashboard: ${DIM}https://supabase.com/dashboard/project/$project_ref${RESET}"
        fi
    fi

    echo ""
    echo -e "  ${BOLD}Logging${RESET}"
    echo -e "  ├─ Level:     ${DIM}${log_level:-INFO}${RESET}"
    echo -e "  └─ Format:    ${DIM}${log_format:-console}${RESET}"
}

switch_env() {
    local env_name="$1"
    local env_file
    local display_name

    case "$env_name" in
        local)
            env_file="$PROJECT_ROOT/.env.local"
            display_name="LOCAL"
            ;;
        dev)
            env_file="$PROJECT_ROOT/.env.dev"
            display_name="DEV"
            ;;
        prod)
            env_file="$PROJECT_ROOT/.env.prod"
            display_name="PROD"
            ;;
        *)
            show_usage
            ;;
    esac

    print_header "${SWITCH} Switch Environment"

    if [ ! -f "$env_file" ]; then
        print_error "$env_file not found"
        echo -e "   Copy ${BOLD}.env.${env_name}.example${RESET} to ${BOLD}.env.${env_name}${RESET} and fill in your values"
        exit 1
    fi

    # Warn when switching to production
    if [ "$env_name" = "prod" ]; then
        echo ""
        print_warning "You are switching to PRODUCTION environment"
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

    cp "$env_file" "$PROJECT_ROOT/.env"

    local supabase_url
    supabase_url=$(grep SUPABASE_URL "$PROJECT_ROOT/.env" | cut -d= -f2)

    echo ""
    print_success "Switched to $(format_env_badge "$env_name")"
    echo -e "   Database: ${DIM}$supabase_url${RESET}"
}

# Main
if [ $# -eq 0 ]; then
    show_usage
fi

case "$1" in
    status)
        show_status
        ;;
    local|dev|prod)
        switch_env "$1"
        ;;
    *)
        show_usage
        ;;
esac
