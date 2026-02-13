#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAURI_DIR="$PROJECT_ROOT/desktop"

if ! command -v cargo >/dev/null 2>&1; then
  echo "Rust (cargo) n'est pas installé."
  echo "Installe-le via: https://rustup.rs/ puis relance ce script."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm n'est pas installé."
  exit 1
fi

if [ ! -f "$TAURI_DIR/src-tauri/tauri.conf.json" ]; then
  echo "Création du projet Tauri dans: $TAURI_DIR"
  npm create tauri-app@latest "$TAURI_DIR" -- --template vanilla --yes
fi

node "$PROJECT_ROOT/scripts/patch_tauri.js"

echo "✅ Tauri setup terminé."
