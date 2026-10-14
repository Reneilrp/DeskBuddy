#!/usr/bin/env bash
# DeskBuddy Linux / WSL Launcher
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

.venv/bin/python main.py "$@"
