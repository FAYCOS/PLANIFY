# Synchronisation Offline (préparation serveur)

## Objectif
- L'application fonctionne 100% en local (SQLite).
- Un journal de changements (`sync_change_log`) enregistre les modifications.
- Une boucle de synchronisation envoie les changements toutes les 20s quand elle est activée.

## Activer la synchronisation
1) Ouvrir **Paramètres → Synchronisation**.
2) Renseigner :
   - `URL serveur` (HTTPS requis)
   - `Token URL` (OAuth2)
   - `Client ID` / `Client Secret`
   - `Scopes` (ex: `sync:write sync:read`)
3) Activer le switch "Activer la synchronisation".
4) Optionnel : définir l'intervalle.

## Sécurité
- HTTPS requis par défaut.
- Pour les environnements de dev uniquement :
  - `SYNC_ALLOW_INSECURE=1`

## Ce qui est prêt
- Enregistrement automatique des modifications (insert/update/delete).
- Envoi des changements vers `POST {server_url}/api/sync/push`.
- Gestion basique des retours `accepted_ids`, `conflicts`, `errors`.
- Endpoint serveur **optionnel** pour réception: `POST /api/sync/push` (mode central).

## Ce qui reste à brancher côté serveur
- OAuth2 côté serveur (au lieu du token statique).
- Gestion des conflits côté serveur (retour des conflits en JSON).
- (Optionnel) Endpoint `GET /api/sync/pull` pour récupérer les changements distants.

## Limites actuelles
- Le service de sync tourne uniquement quand l'app est ouverte.
- Pour un vrai "background sync" desktop, prévoir un service dédié côté Tauri.
- Script prêt: `sync_daemon.py` (sidecar possible pour Tauri).

## Mode serveur (réception des changements)
- Activer: `SYNC_SERVER_MODE=1` et définir `SYNC_SERVER_TOKEN`.
- Les changements reçus sont stockés dans `sync_incoming_log` pour traitement ultérieur.
