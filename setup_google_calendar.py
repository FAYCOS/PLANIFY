#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration automatique Google Calendar
"""

import os
import webbrowser
from google_calendar_config import google_calendar_manager
import logging
logger = logging.getLogger(__name__)

def setup_google_calendar():
    """Configure Google Calendar étape par étape"""
    
    logger.info("🎵 Configuration Google Calendar - Planify")
    logger.info("=" * 50)
    logger.info()
    
    logger.info("📋 ÉTAPE 1 : Configuration Google Cloud Console")
    logger.info("1. Allez sur : https://console.cloud.google.com/")
    logger.info("2. Créez un projet ou sélectionnez un existant")
    logger.info("3. Activez l'API Google Calendar")
    logger.info("4. Créez des credentials OAuth2")
    logger.info()
    
    input("Appuyez sur Entrée quand vous avez terminé l'étape 1...")
    
    logger.info("\n📋 ÉTAPE 2 : Récupération des credentials")
    client_id = input("🔑 Entrez votre Client ID : ").strip()
    client_secret = input("🔐 Entrez votre Client Secret : ").strip()
    
    if not client_id or not client_secret:
        logger.error("❌ Credentials manquants. Configuration annulée.")
        return False
    
    # Mettre à jour le fichier de configuration
    config_file = "google_calendar_config.py"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer les credentials
        content = content.replace(
            "CLIENT_ID = '<CLIENT_ID>'",
            f\"CLIENT_ID = '{client_id}'\"
        )
        content = content.replace(
            "CLIENT_SECRET = '<CLIENT_SECRET>'",
            f\"CLIENT_SECRET = '{client_secret}'\"
        )
        
        # Sauvegarder
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ Credentials sauvegardés !")
        
        # Tester la configuration
        logger.info("\n📋 ÉTAPE 3 : Test de la configuration")
        auth_url, state = google_calendar_manager.get_authorization_url(1)
        
        if auth_url:
            logger.info("✅ Configuration valide !")
            logger.info(f"🔗 URL d'autorisation : {auth_url}")
            
            logger.info("\n📋 ÉTAPE 4 : Test de connexion")
            logger.info("1. L'application va s'ouvrir dans votre navigateur")
            logger.info("2. Autorisez l'accès à Google Calendar")
            logger.info("3. Vous serez redirigé vers l'application")
            
            input("Appuyez sur Entrée pour ouvrir le navigateur...")
            
            # Ouvrir l'URL d'autorisation
            webbrowser.open(auth_url)
            
            logger.info("\n🎉 Configuration terminée !")
            logger.info("Vous pouvez maintenant utiliser Google Calendar dans l'application.")
            
            return True
        else:
            logger.error("❌ Erreur de configuration. Vérifiez vos credentials.")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur : {e}")
        return False

if __name__ == "__main__":
    setup_google_calendar()







