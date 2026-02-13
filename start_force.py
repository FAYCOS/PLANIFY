#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement forcé - libère le port 5000 puis démarre l'app
"""

import os
import sys
import webbrowser
import threading
import time
import signal
import logging
logger = logging.getLogger(__name__)


def kill_port(port):
    """Tue le processus qui utilise le port"""
    try:
        result = os.popen(f"lsof -ti:{port}").read().strip()
        if result:
            os.system(f"kill -9 {result}")
            logger.info(f"🔪 Port {port} libéré")
            time.sleep(1)
    except Exception:
        logger.exception('Erreur kill_port')


def open_browser(port):
    """Ouvre le navigateur après un délai"""
    time.sleep(3)
    try:
        webbrowser.open(f'http://localhost:{port}')
        logger.info("🌐 Ouverture du navigateur...")
    except Exception as e:
        logger.warning(f"⚠️ Impossible d'ouvrir le navigateur : {e}")
        logger.info(f"💡 Ouvrez manuellement : http://localhost:{port}")


def signal_handler(sig, frame):
    """Gestionnaire pour Ctrl+C"""
    logger.info("\n👋 Arrêt de l'application...")
    sys.exit(0)


def main():
    """Fonction principale de lancement"""
    os.environ.setdefault('PLANIFY_DISABLE_MULTI_DB', '1')
    logger.info("🎵 Planify - Lancement Forcé")
    logger.info("=" * 50)

    if not os.path.exists('app.py'):
        logger.error("❌ Fichier app.py non trouvé")
        sys.exit(1)

    port = 5000

    logger.info("🧹 Nettoyage du port 5000...")
    kill_port(port)

    signal.signal(signal.SIGINT, signal_handler)

    logger.info("🚀 Démarrage du serveur...")
    logger.info(f"📱 L'application sera disponible sur : http://localhost:{port}")
    logger.info("⏹️  Appuyez sur Ctrl+C pour arrêter le serveur")
    logger.info("-" * 50)

    browser_thread = threading.Thread(target=open_browser, args=(port,))
    browser_thread.daemon = True
    browser_thread.start()

    try:
        from app import app, init_db
        init_db()
        app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("\n👋 Arrêt de l'application")
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement : {e}")
        sys.exit(1)

    return True


if __name__ == "__main__":
    main()
