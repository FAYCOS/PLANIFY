#!/usr/bin/env python3
"""
Script pour réinitialiser complètement l'application Planify
"""

import os
import sys
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from init_key_manager import init_key_manager
import logging
logger = logging.getLogger(__name__)

def reset_application():
    """Réinitialise complètement l'application"""
    logger.info("🎵 Planify - Réinitialisation complète")
    logger.info("=" * 60)
    
    # 1. Supprimer la clé d'initialisation (optionnel)
    remove_init = False
    try:
        import argparse
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--keep-init', action='store_true', help='Préserver la clé d\'initialisation')
        args, _ = parser.parse_known_args()
        if args.keep_init:
            remove_init = False
        else:
            remove_init = True
    except Exception:
        remove_init = True

    if remove_init:
        logger.info("🗑️  Suppression de la clé d'initialisation...")
        if init_key_manager.reset_initialization():
            logger.info("✅ Clé d'initialisation supprimée")
        else:
            logger.warning("⚠️  Aucune clé d'initialisation trouvée")
    else:
        logger.info("ℹ️  Préservation de la clé d'initialisation (--keep-init)")
    
    # 2. Supprimer la base de données
    logger.info("🗑️  Suppression de la base de données...")
    db_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.db'):
                db_files.append(os.path.join(root, file))
    
    for db_file in db_files:
        try:
            os.remove(db_file)
            logger.info(f"✅ Supprimé : {db_file}")
        except Exception as e:
            logger.error(f"⚠️  Erreur lors de la suppression de {db_file} : {e}")
    
    # 3. Supprimer le dossier instance
    logger.info("🗑️  Suppression du dossier instance...")
    try:
        import shutil
        if os.path.exists('./instance'):
            shutil.rmtree('./instance')
            logger.info("✅ Dossier instance supprimé")
        else:
            logger.warning("⚠️  Dossier instance non trouvé")
    except Exception as e:
        logger.error(f"⚠️  Erreur lors de la suppression du dossier instance : {e}")
    
    # 4. Supprimer les fichiers de cache
    logger.info("🗑️  Nettoyage des fichiers de cache...")
    cache_files = ['init_key.json', '*.pyc', '__pycache__']
    for pattern in cache_files:
        if pattern == '__pycache__':
            try:
                import shutil
                for root, dirs, files in os.walk('.'):
                    if '__pycache__' in dirs:
                        shutil.rmtree(os.path.join(root, '__pycache__'))
                logger.info("✅ Cache Python supprimé")
            except:
                pass
        else:
            try:
                if os.path.exists(pattern):
                    os.remove(pattern)
                    logger.info(f"✅ Supprimé : {pattern}")
            except:
                pass
    
    logger.info("\n🎉 Réinitialisation terminée avec succès !")
    logger.info("📱 L'application va maintenant afficher la page d'initialisation")
    logger.info("🔑 Aucune clé d'initialisation trouvée - première installation")
    
    return True

if __name__ == '__main__':
    reset_application()
    logger.info("\n🚀 Redémarrez l'application avec : python3 start_force.py")











