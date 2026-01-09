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

show_usage() {
    echo "Usage: $0 <status|migrate|reset|start|stop>"
    echo ""
    echo "Commands:"
    echo "  status    Show migration status and pending migrations"
    echo "  migrate   Apply pending migrations"
    echo "  reset     Reset database (re-run all migrations + seed)"
    echo "  start     Start local Supabase (local env only)"
    echo "  stop      Stop local Supabase (local env only)"
    echo ""
    echo "Environment is determined from .env file (use ./scripts/env.sh to switch)"
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

check_environment() {
    local env_name
    env_name=$(get_environment)

    if [ -z "$env_name" ]; then
        echo "Error: No environment configured"
        echo "Run: ./scripts/env.sh local"
        exit 1
    fi

    echo "Environment: $env_name"
    echo "Supabase: $(get_supabase_url)"
    echo ""
}

require_local() {
    if ! is_local_env; then
        echo "Error: This command only works with local environment"
        echo "Current environment: $(get_environment)"
        echo ""
        echo "Switch to local: ./scripts/env.sh local"
        exit 1
    fi
}

warn_production() {
    local env_name
    env_name=$(get_environment)

    if [[ "$env_name" == "production" ]]; then
        echo "WARNING: You are operating on PRODUCTION database"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled"
            exit 1
        fi
    fi
}

do_status() {
    check_environment

    if is_local_env; then
        echo "Migration status (local):"
        npx supabase migration list --local
    else
        echo "Migration status (remote):"
        npx supabase migration list
    fi
}

do_migrate() {
    check_environment
    warn_production

    if is_local_env; then
        echo "Applying migrations (local)..."
        npx supabase migration up --local
    else
        echo "Applying migrations (remote)..."
        npx supabase migration up
    fi

    echo ""
    echo "Done. Run './scripts/db.sh status' to verify."
}

do_reset() {
    check_environment

    if ! is_local_env; then
        echo "Error: Database reset is only allowed for local environment"
        echo "Current environment: $(get_environment)"
        echo ""
        echo "For cloud environments, use migrations or the Supabase dashboard"
        exit 1
    fi

    echo "WARNING: This will destroy all local data and re-run migrations + seed"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 1
    fi

    echo "Resetting database..."
    npx supabase db reset
    echo ""
    echo "Database reset complete."
}

do_start() {
    require_local
    echo "Starting local Supabase..."
    npx supabase start
}

do_stop() {
    require_local
    echo "Stopping local Supabase..."
    npx supabase stop
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
