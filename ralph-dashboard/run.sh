#!/usr/bin/env bash
# Ralph Dashboard - Quick Start Script
# Activates the virtual environment and starts the dashboard
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "  Run first: ./setup.sh"
    exit 1
fi

source "$VENV_DIR/bin/activate"

# Pass all arguments to ralph-dashboard
exec ralph-dashboard "$@"
