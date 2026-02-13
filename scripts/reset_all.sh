#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TS=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups/backup_$TS"

FORCE=0
REMOVE_INIT=0
for arg in "${@}"; do
  if [ "$arg" = "--force" ]; then
    FORCE=1
  fi
  if [ "$arg" = "--remove-init" ]; then
    REMOVE_INIT=1
  fi
done

echo "[reset_all] Répertoire de travail: $ROOT_DIR"
echo "[reset_all] Sauvegarde dans: $BACKUP_DIR"

if [ "$FORCE" -eq 0 ]; then
  echo "ATTENTION : cette opération va sauvegarder puis SUPPRIMER définitivement la base, les clés, les uploads et les logs."
  read -p "Confirmez-vous (tapez 'yes' pour continuer) ? " CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    echo "Abandon. Aucune modification effectuée."
    exit 1
  fi
fi

mkdir -p "$BACKUP_DIR"

# List of files to backup/remove
FILES=("dj_prestations.db" "dj_prestations.db-shm" "dj_prestations.db-wal" "dj_prestations.db-journal" "planify.log" "planify_stdout.log" ".app_pid")

# Handle init_key.json according to flag: preserve by default, remove only if requested
if [ "$REMOVE_INIT" -eq 1 ]; then
  FILES+=("init_key.json")
else
  echo "[reset_all] init_key.json will be preserved (use --remove-init to delete it)"
fi

for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    mv "$f" "$BACKUP_DIR/"
    echo "Moved $f -> $BACKUP_DIR/"
  fi
done

# Archive and remove uploads
if [ -d "static/uploads" ]; then
  UP_BACKUP="$BACKUP_DIR/uploads_$TS.tar.gz"
  tar -czf "$UP_BACKUP" -C static uploads || true
  rm -rf static/uploads
  echo "Archived static/uploads -> $UP_BACKUP and removed original"
fi

# Additional cleanup targets (optional files/folders)
for d in "logs" "tmp" "uploads"; do
  if [ -d "$d" ]; then
    mv "$d" "$BACKUP_DIR/${d}_$TS" || true
    echo "Moved $d -> $BACKUP_DIR/${d}_$TS"
  fi
done

# Ensure uploads dir exists
mkdir -p static/uploads

echo "[reset_all] Sauvegardes complètes. Suppression des fichiers restants (si présents)."

# Final safety delete (already moved files). Remove any remaining sqlite files matching pattern
shopt -s nullglob
for f in dj_prestations*.db*; do
  if [ -f "$f" ]; then
    rm -f "$f" && echo "Removed $f"
  fi
done
shopt -u nullglob

echo "[reset_all] Reset terminé. Backups disponibles dans: $BACKUP_DIR"
echo "Pour relancer l'application, utilisez : ./scripts/start_app.sh"

# If init_key.json not present but older backups contain it, restore the latest one
if [ ! -f "init_key.json" ] && [ "$REMOVE_INIT" -eq 0 ]; then
  echo "[reset_all] init_key.json absent — recherche d'une sauvegarde pour restauration..."
  LATEST_BACKUP_WITH_KEY=$(ls -1d backups/*/ | sort -r | while read d; do if [ -f "${d%/}/init_key.json" ]; then echo "${d%/}"; break; fi; done)
  if [ -n "$LATEST_BACKUP_WITH_KEY" ]; then
    echo "[reset_all] Restauration de init_key.json depuis $LATEST_BACKUP_WITH_KEY"
    cp "$LATEST_BACKUP_WITH_KEY/init_key.json" ./init_key.json || true
  else
    echo "[reset_all] Aucune sauvegarde d'init_key.json trouvée"
  fi
fi

exit 0
