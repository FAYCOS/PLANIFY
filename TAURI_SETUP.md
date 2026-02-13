# Tauri Desktop (Win/Mac) — Plan

## Objectif
- App desktop installable Windows/macOS.
- App Flask locale + UI web + sync offline.
- Service background pour sync (sidecar).

## Structure proposée
- Tauri app (frontend minimal) qui ouvre l'URL locale de Flask.
- Sidecar: `sync_daemon.py` lancé en arrière-plan pour la sync 20s.

## Étapes
1) Installer Rust (cargo).
2) Lancer `./scripts/setup_tauri.sh` (crée le projet Tauri + patch config).
3) Configurer le **sidecar** `sync_daemon.py`.
4) Packaging Windows (MSI/EXE) + macOS (DMG/PKG).

## Notes
- Le backend Flask tourne en local.
- Les données restent dans `instance/dj_prestations.db`.
- La synchro serveur est activable dans l'UI (Paramètres → Synchronisation).
