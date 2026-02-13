#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement propre avec port fixe
"""

import os
import sys
import webbrowser
import threading
import time
import signal
from datetime import datetime
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
    except:
        pass

def open_browser(port):
    """Ouvre le navigateur après un délai"""
    time.sleep(3)  # Attendre que le serveur démarre
    webbrowser.open(f'http://localhost:{port}')
    logger.info("🌐 Ouverture du navigateur...")

def signal_handler(sig, frame):
    """Gestionnaire pour Ctrl+C"""
    logger.info("\n👋 Arrêt de l'application...")
    sys.exit(0)

def main():
    """Fonction principale de lancement"""
    logger.info("🎵 Planify - Lancement Propre")
    logger.info("=" * 50)
    
    # Vérification du fichier app.py
    if not os.path.exists('app.py'):
        logger.error("❌ Fichier app.py non trouvé")
        sys.exit(1)
    
    # Port fixe
    port = 5000
    
    # Libérer le port s'il est occupé
    logger.info("🧹 Nettoyage du port 5000...")
    kill_port(port)
    
    # Gestionnaire de signal pour Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("🚀 Démarrage du serveur...")
    logger.info(f"📱 L'application sera disponible sur : http://localhost:{port}")
    logger.info("⏹️  Appuyez sur Ctrl+C pour arrêter le serveur")
    logger.info("📧 Configuration email : noreply.planifymanagement@gmail.com")
    logger.info("🔗 Google Calendar URI : http://localhost:5000/auth/google/callback")
    logger.info("-" * 50)
    
    # Ouverture automatique du navigateur
    browser_thread = threading.Thread(target=open_browser, args=(port,))
    browser_thread.daemon = True
    browser_thread.start()
    
    # Lancement de l'application Flask avec debug activé
    try:
        from app import app, init_db
        init_db()  # Initialisation de la base de données
        app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("\n👋 Arrêt de l'application")
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement : {e}")
        sys.exit(1)
    
    return True

if __name__ == "__main__":
    main()








