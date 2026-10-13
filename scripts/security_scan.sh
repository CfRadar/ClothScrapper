#!/usr/bin/env bash
set -e

# Run security scan runner
if [ -f "backend/.venv/bin/python" ]; then
    backend/.venv/bin/python scripts/security_scan.py
elif [ -f "backend/.venv/Scripts/python.exe" ]; then
    backend/.venv/Scripts/python.exe scripts/security_scan.py
else
    python3 scripts/security_scan.py
fi
