#!/usr/bin/env bash
# Ralph Dashboard - Automated Setup Script
# Works on Ubuntu 24.04+ and other Linux distributions
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "========================================="
echo "  Ralph Dashboard - Setup"
echo "========================================="
echo ""

# Verify we are in the right directory (must contain pyproject.toml)
if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
    echo "[ERROR] pyproject.toml non trovato in: $SCRIPT_DIR"
    echo ""
    echo "  Sei nella cartella sbagliata!"
    echo "  Devi essere dentro la cartella ralph-dashboard."
    echo ""
    echo "  Prova:"
    echo "    cd ~/Projects/ralph-dashboard"
    echo "    ./setup.sh"
    exit 1
fi

echo "[OK] Directory progetto: $SCRIPT_DIR"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found. Install with: sudo apt install python3"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "[ERROR] Python 3.10+ required, found $PY_VERSION"
    exit 1
fi
echo "[OK] Python $PY_VERSION"

# Check python3-venv is installed
if ! python3 -m venv --help &> /dev/null 2>&1; then
    echo ""
    echo "[ERROR] python3-venv non installato."
    echo "  Esegui: sudo apt install python3-venv"
    exit 1
fi

# Create virtual environment (or recreate if broken)
if [ -f "$VENV_DIR/bin/activate" ]; then
    echo "[OK] Virtual environment esistente in .venv/"
elif [ -d "$VENV_DIR" ]; then
    echo "[WARN] .venv/ esiste ma e' corrotto (manca bin/activate). Ricreo..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    echo "[OK] Virtual environment ricreato"
else
    echo "[...] Creo virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "[OK] Virtual environment creato"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
echo "[OK] Virtual environment attivato"

# Upgrade pip
echo "[...] Aggiornamento pip..."
pip install --upgrade pip --quiet

# Install ralph-dashboard
echo "[...] Installazione ralph-dashboard e dipendenze..."
pip install -e "$SCRIPT_DIR" --quiet

# Optional: GPU support
if command -v nvidia-smi &> /dev/null; then
    echo "[...] GPU NVIDIA rilevata, installo GPUtil..."
    pip install GPUtil --quiet
    echo "[OK] Monitoraggio GPU abilitato"
else
    echo "[INFO] Nessuna GPU NVIDIA rilevata, il monitoraggio GPU mostrera' N/A"
fi

echo ""
echo "========================================="
echo "  Setup completato!"
echo "========================================="
echo ""
echo "Per avviare il dashboard:"
echo ""
echo "  cd $SCRIPT_DIR"
echo "  ./run.sh --projects-dir ~/Projects"
echo ""
echo "Poi apri nel browser: http://127.0.0.1:8420"
echo ""
