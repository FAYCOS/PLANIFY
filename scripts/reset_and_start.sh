#!/usr/bin/env bash
set -euo pipefail

# Script pour réinitialiser les données (DB, clé d'init, uploads, logs) puis relancer l'app
# Usage: ./scripts/reset_and_start.sh [--force]

FORCE=false
if [ "${1:-}" = "--force" ]; then
  FORCE=true
fi

if [ "$FORCE" = false ]; then
  echo "Ce script va SUPPRIMER la base de données et les uploads."
  read -p "Confirmez-vous ? (oui/NO) : " CONF
  if [ "$CONF" != "oui" ]; then
    echo "Annulé. Exécutez avec --force pour forcer la suppression." >&2
    exit 1
  fi
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/backup_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

# Stop app
pkill -f "app.py" || true
sleep 1

# Backup and remove DB and init key
if [ -f dj_prestations.db ]; then
  mv dj_prestations.db "$BACKUP_DIR/"
  echo "Moved dj_prestations.db -> $BACKUP_DIR/"
else
  echo "dj_prestations.db not found"
fi

if [ -f init_key.json ]; then
  mv init_key.json "$BACKUP_DIR/"
  echo "Moved init_key.json -> $BACKUP_DIR/"
else
  echo "init_key.json not found"
fi

# Clean uploads and logs
if [ -d static/uploads ]; then
  rm -rf static/uploads/*
  echo "static/uploads cleared"
fi

rm -f planify.log planify_stdout.log || true

# Optionally keep a small marker of the reset
echo "reset_at: $(date --iso-8601=seconds 2>/dev/null || date)" > "$BACKUP_DIR/RESET_INFO.txt"

# Restart app using start script
./scripts/start_app.sh

echo "Reset terminé. Backups dans $BACKUP_DIR"
