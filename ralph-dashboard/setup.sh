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
    echo "[ERROR] python3-venv not installed."
    echo "  Run: sudo apt install python3-venv"
    exit 1
fi

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "[OK] Virtual environment already exists at .venv/"
else
    echo "[...] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "[OK] Virtual environment created"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
echo "[OK] Virtual environment activated"

# Upgrade pip
echo "[...] Upgrading pip..."
pip install --upgrade pip --quiet

# Install ralph-dashboard
echo "[...] Installing ralph-dashboard and dependencies..."
pip install -e "$SCRIPT_DIR" --quiet

# Optional: GPU support
if command -v nvidia-smi &> /dev/null; then
    echo "[...] NVIDIA GPU detected, installing GPUtil..."
    pip install GPUtil --quiet
    echo "[OK] GPU monitoring enabled"
else
    echo "[INFO] No NVIDIA GPU detected, GPU monitoring will show N/A"
fi

echo ""
echo "========================================="
echo "  Setup complete!"
echo "========================================="
echo ""
echo "Per avviare il dashboard:"
echo ""
echo "  cd $SCRIPT_DIR"
echo "  source .venv/bin/activate"
echo "  ralph-dashboard --projects-dir ~/Projects"
echo ""
echo "Oppure usa lo script rapido:"
echo ""
echo "  ./run.sh --projects-dir ~/Projects"
echo ""
echo "Poi apri: http://127.0.0.1:8420"
echo ""
