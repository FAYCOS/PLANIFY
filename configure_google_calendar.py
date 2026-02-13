#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuration Google Calendar
"""

import os
import sys
import logging
import getpass

logger = logging.getLogger(__name__)

def configure_google_calendar():
    """Configure Google Calendar avec les credentials de l'utilisateur"""
    
    logger.info("Configuration Google Calendar")
    logger.info("=" * 50)
    logger.info("")
    
    logger.info("Étapes préalables :")
    logger.info("1. Allez sur https://console.cloud.google.com/")
    logger.info("2. Créez un projet et activez l'API Google Calendar")
    logger.info("3. Configurez OAuth2 avec les URIs de redirection :")
    logger.info("   - http://localhost:5000/auth/google/callback")
    logger.info("   - http://localhost:5026/auth/google/callback")
    logger.info("   - http://localhost:5027/auth/google/callback")
    logger.info("   - http://localhost:5028/auth/google/callback")
    logger.info("   - http://localhost:5029/auth/google/callback")
    logger.info("")
    
    # Demander les credentials
    client_id = input("🔑 Entrez votre Client ID : ").strip()
    client_secret = getpass.getpass("🔐 Entrez votre Client Secret (masqué) : ").strip()
    
    if not client_id or not client_secret:
        logger.error("❌ Credentials manquants. Configuration annulée.")
        return False
    
    # Lire le fichier de configuration
    config_file = "google_calendar_config.py"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer les credentials
        content = content.replace(
            "CLIENT_ID = 'your_client_id_here'",
            f"CLIENT_ID = '{client_id}'"
        )
        content = content.replace(
            "CLIENT_SECRET = 'your_client_secret_here'",
            f"CLIENT_SECRET = '{client_secret}'"
        )
        
        # Mettre à jour l'URI de redirection avec le port actuel
        current_port = 5029  # Port actuel de l'application
        content = content.replace(
            "REDIRECT_URI = 'http://localhost:5028/auth/google/callback'",
            f"REDIRECT_URI = 'http://localhost:{current_port}/auth/google/callback'"
        )
        
        # Sauvegarder le fichier
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("")
        logger.info("Configuration réussie !")
        logger.info(f"Fichier modifié : {config_file}")
        logger.info("")
        logger.info("Prochaines étapes :")
        logger.info("1. Redémarrez l'application : python3 start_force.py")
        logger.info("2. Allez dans la section 'DJs'")
        logger.info("3. Cliquez sur 'Connecter' pour un DJ")
        logger.info("4. Autorisez l'accès à Google Calendar")
        logger.info("5. Synchronisez les prestations !")
        
        return True
        
    except FileNotFoundError:
        logger.error(f"Fichier {config_file} non trouvé.")
        return False
    except Exception as e:
        logger.exception('Erreur lors de la configuration')
        return False

if __name__ == "__main__":
    logger.info("DJ Prestations Manager - Configuration Google Calendar")
    logger.info("")
    
    if configure_google_calendar():
        logger.info("")
        logger.info("Configuration terminée avec succès !")
    else:
        logger.error("")
        logger.error("Configuration échouée. Vérifiez vos credentials.")
        sys.exit(1)








