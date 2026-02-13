#!/usr/bin/env bash
set -euo pipefail

# Script pour (re)lancer l'application Planify
# Usage: ./scripts/start_app.sh

# Arrêter toute instance en cours
pkill -f "app.py" || true
sleep 1

# Démarrer l'application en arrière-plan et enregistrer le PID
nohup python3 app.py > planify_stdout.log 2>&1 &
PID=$!
echo $PID > .app_pid

echo "Planify démarré (PID: $PID)"
echo "Logs: planify_stdout.log"
