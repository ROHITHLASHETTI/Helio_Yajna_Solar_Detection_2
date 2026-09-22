#!/bin/bash
set -e

# Configuration
VENV_DIR="venv"
REQUIREMENTS="environment_details/requirements.txt"
SCRIPT="pipeline_code/inference.py"
MODEL="trained_model/weights.pt"
INPUT="input_data/input.xlsx"

echo "==========================================="
echo "Solar Panel Detection - Automation Script"
echo "==========================================="

# 1. Check/Create Virtual Environment
if [ -d "$VENV_DIR" ]; then
    echo "[*] Venv found."
else
    echo "[*] Creating virtual environment..."
    python3 -m venv $VENV_DIR
fi

# 2. Activate Venv
echo "[*] Activating virtual environment..."
source $VENV_DIR/bin/activate

# 3. Install Dependencies
if [ -f "$REQUIREMENTS" ]; then
    echo "[*] Installing dependencies..."
    pip install --upgrade pip
    pip install -r $REQUIREMENTS
else
    echo "[!] Error: $REQUIREMENTS not found!"
    exit 1
fi

# 4. Run Inference
echo "[*] Running inference..."
if [ -f "$SCRIPT" ]; then
    # Check if first argument is a file (for backward compatibility)
    # If first arg exists and doesn't start with --, treat it as --input
    if [ -n "$1" ] && [[ ! "$1" == --* ]]; then
        INPUT_FILE="$1"
        shift
        python $SCRIPT --model $MODEL --input "$INPUT_FILE" "$@"
    else
        # Pass all arguments as-is
        python $SCRIPT --model $MODEL "$@"
    fi
else
    echo "[!] Error: $SCRIPT not found!"
    exit 1
fi

echo "==========================================="
echo "Inference Complete."
echo "==========================================="
