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

show_usage() {
    echo "Usage: $0 <local|dev|prod|status>"
    echo ""
    echo "Commands:"
    echo "  local   Switch to local Supabase environment"
    echo "  dev     Switch to development cloud environment"
    echo "  prod    Switch to production cloud environment"
    echo "  status  Show current environment configuration"
    exit 1
}

show_status() {
    ENV_FILE="$PROJECT_ROOT/.env"

    if [ ! -f "$ENV_FILE" ]; then
        echo "No .env file found"
        echo "Run: ./scripts/env.sh local"
        exit 1
    fi

    echo "Current Environment:"
    echo "===================="
    grep -E "^ENVIRONMENT=" "$ENV_FILE" || echo "ENVIRONMENT=not set"
    echo ""
    echo "Database:"
    grep -E "^SUPABASE_URL=" "$ENV_FILE"
    echo ""
    echo "Logging:"
    grep -E "^LOG_LEVEL=" "$ENV_FILE" || echo "LOG_LEVEL=not set"
    grep -E "^LOG_FORMAT=" "$ENV_FILE" || echo "LOG_FORMAT=not set"
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

    if [ ! -f "$env_file" ]; then
        echo "Error: $env_file not found"
        echo "Copy .env.${env_name}.example to .env.${env_name} and fill in your values"
        exit 1
    fi

    # Warn when switching to production
    if [ "$env_name" = "prod" ]; then
        echo "WARNING: You are switching to PRODUCTION environment"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled"
            exit 1
        fi
    fi

    cp "$env_file" "$PROJECT_ROOT/.env"
    echo "Switched to $display_name environment"
    echo "  Database: $(grep SUPABASE_URL "$PROJECT_ROOT/.env" | cut -d= -f2)"
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
