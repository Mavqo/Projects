#!/usr/bin/env bash
# Ralph Dashboard - Quick Start Script
# Activates the virtual environment and starts the dashboard
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Verify we are in the right directory
if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
    echo "[ERROR] Sei nella cartella sbagliata!"
    echo ""
    echo "  Devi essere dentro la cartella ralph-dashboard."
    echo "  Prova:"
    echo "    cd ~/Projects/ralph-dashboard"
    echo "    ./run.sh --projects-dir ~/Projects"
    exit 1
fi

# Check venv exists and is valid
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[ERROR] Virtual environment non trovato o corrotto."
    echo ""
    echo "  Esegui prima: ./setup.sh"
    exit 1
fi

source "$VENV_DIR/bin/activate"

# Pass all arguments to ralph-dashboard
exec ralph-dashboard "$@"
