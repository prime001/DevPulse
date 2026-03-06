#!/bin/bash
# Cron: refresh ADO cache every 2 hours
# 0 */2 * * * "$HOME/Scripts/DevPulse/scripts/devpulse-refresh.sh"
cd "$HOME/Scripts/DevPulse" || exit 1
source ~/.zshrc 2>/dev/null || true
./venv/bin/python -m devpulse refresh
