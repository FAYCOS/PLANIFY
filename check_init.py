#!/usr/bin/env python3
"""
Script pour vérifier le statut d'initialisation de Planify
"""

import os
import sys
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from init_key_manager import init_key_manager
import logging
logger = logging.getLogger(__name__)

def check_initialization_status():
    """Vérifie le statut d'initialisation de l'application"""
    logger.info("🎵 Planify - Vérification du statut d'initialisation")
    logger.info("=" * 60)
    
    # Vérifier le statut d'initialisation
    if init_key_manager.is_initialized():
        logger.info("✅ Application initialisée")
        
        # Afficher les informations de la clé
        key_info = init_key_manager.get_key_info()
        logger.info(f"📅 Date d'initialisation : {key_info.get('created_at', 'Inconnue')}")
        logger.info(f"👤 Administrateur : {key_info.get('admin_name', 'Inconnu')}")
        logger.info(f"📱 Version : {key_info.get('version', 'Inconnue')}")
        logger.info(f"🏷️  Application : {key_info.get('app_name', 'Inconnue')}")
        
        # Vérifier la base de données
        try:
            from app import app, db, User
            with app.app_context():
                user_count = User.query.count()
                logger.info(f"👥 Nombre d'utilisateurs en base : {user_count}")
                
                if user_count > 0:
                    logger.info("✅ Base de données opérationnelle")
                else:
                    logger.warning("⚠️  Base de données vide")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification de la base de données : {e}")
        
    else:
        logger.warning("⚠️  Application non initialisée")
        logger.info("🔑 Aucune clé d'initialisation trouvée")
        logger.info("📱 L'application va afficher la page d'initialisation")
    
    # Vérifier les fichiers de base de données
    logger.info("\n📊 Fichiers de base de données :")
    db_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.db'):
                db_files.append(os.path.join(root, file))
    
    if db_files:
        for db_file in db_files:
            size = os.path.getsize(db_file)
            logger.info(f"  📄 {db_file} ({size} octets)")
    else:
        logger.warning("  ⚠️  Aucun fichier de base de données trouvé")
    
    # Vérifier le fichier de clé
    logger.info("\n🔑 Fichier de clé d'initialisation :")
    if os.path.exists('init_key.json'):
        size = os.path.getsize('init_key.json')
        logger.info(f"  📄 init_key.json ({size} octets)")
    else:
        logger.warning("  ⚠️  Aucun fichier de clé trouvé")
    
    logger.info("\n" + "=" * 60)
    if init_key_manager.is_initialized():
        logger.info("🎉 L'application est prête à être utilisée !")
    else:
        logger.info("🚀 L'application nécessite une initialisation")

if __name__ == '__main__':
    check_initialization_status()











