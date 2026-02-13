#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daemon de synchronisation offline
- Peut être lancé en arrière-plan (Tauri sidecar)
- Envoie les changements toutes les N secondes si activé
"""

import time
import logging

from app import app, db, SyncConfig, ensure_sync_config, _sync_once

logger = logging.getLogger(__name__)


def main():
    with app.app_context():
        ensure_sync_config()

    while True:
        try:
            with app.app_context():
                cfg = db.session.get(SyncConfig, 1)
                interval = cfg.sync_interval_seconds if cfg and cfg.sync_interval_seconds else 20
                if cfg and cfg.enabled:
                    _sync_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.warning(f"Sync daemon error: {e}")
            time.sleep(20)


if __name__ == "__main__":
    main()
