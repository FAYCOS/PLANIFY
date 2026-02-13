#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement simple - Port fixe 5000
"""

import os
import sys
import webbrowser
import threading
import time
import signal
from datetime import datetime
import logging
import socket

logger = logging.getLogger(__name__)

def kill_port(port):
    """Tue le processus qui utilise le port"""
    try:
        result = os.popen(f"lsof -ti:{port}").read().strip()
        if result:
            os.system(f"kill -9 {result}")
            logger.info(f"Port {port} libéré")
            time.sleep(1)
    except Exception:
        logger.exception('Erreur kill_port')


def is_port_in_use(port):
    """Vérifie si un port TCP est déjà utilisé."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('', port))
            return False
        except OSError:
            return True

def open_browser(port):
    """Ouvre le navigateur après un délai"""
    time.sleep(3)
    webbrowser.open(f'http://localhost:{port}')
    logger.info("Ouverture du navigateur...")

def signal_handler(sig, frame):
    """Gestionnaire pour Ctrl+C"""
    logger.info("\nArrêt de l'application...")
    sys.exit(0)

def main():
    """Fonction principale de lancement"""
    logger.info("Planify - Lancement Simple")
    logger.info("=" * 40)
    
    if not os.path.exists('app.py'):
        logger.error("Fichier app.py non trouvé")
        sys.exit(1)
    
    # Priorité: 5000 puis 5001 (libérer si occupés)
    preferred_ports = [5000, 5001]
    port = None
    for p in preferred_ports:
        if is_port_in_use(p):
            logger.warning(f"Port {p} occupé, tentative de libération...")
            kill_port(p)
            time.sleep(0.5)
        if not is_port_in_use(p):
            port = p
            break
    if port is None:
        logger.error("Impossible de libérer 5000/5001. Arrêt.")
        sys.exit(1)
    logger.info(f"Utilisation du port {port}")
    
    # Gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Démarrage du serveur...")
    logger.info(f"URL : http://localhost:{port}")
    logger.info("Ctrl+C pour arrêter")
    logger.info("-" * 40)
    
    # Ouverture du navigateur
    browser_thread = threading.Thread(target=open_browser, args=(port,))
    browser_thread.daemon = True
    browser_thread.start()
    
    # Lancement Flask
    try:
        from app import app, init_db
        init_db()
        app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Arrêt de l'application par KeyboardInterrupt")
    except Exception as e:
        logger.exception('Erreur lors du démarrage du serveur')
        sys.exit(1)

if __name__ == "__main__":
    main()







