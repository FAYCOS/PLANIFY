#!/usr/bin/env python3
"""
Script de migration pour ajouter les champs client_telephone et client_email
"""

import sqlite3
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

def migrate_database():
    """Ajoute les nouveaux champs client_telephone et client_email à la table prestations"""
    
    db_path = 'instance/dj_prestations.db'
    
    if not os.path.exists(db_path):
        logger.error("❌ Base de données non trouvée. Assurez-vous que l'application a été initialisée.")
        return False
    
    try:
        # Connexion à la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("🔄 Migration de la base de données...")
        
        # Vérifier si les colonnes existent déjà
        cursor.execute("PRAGMA table_info(prestations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'client_telephone' not in columns:
            logger.info("➕ Ajout de la colonne client_telephone...")
            cursor.execute("ALTER TABLE prestations ADD COLUMN client_telephone VARCHAR(20)")
        
        if 'client_email' not in columns:
            logger.info("➕ Ajout de la colonne client_email...")
            cursor.execute("ALTER TABLE prestations ADD COLUMN client_email VARCHAR(120)")
        
        # Commit des changements
        conn.commit()
        
        logger.info("✅ Migration terminée avec succès !")
        logger.info("📋 Les nouveaux champs ont été ajoutés :")
        logger.info("   - client_telephone (VARCHAR(20))")
        logger.info("   - client_email (VARCHAR(120))")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration : {str(e)}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    logger.info("🎵 Planify - Migration des champs client")
    logger.info("=" * 50)
    
    if migrate_database():
        logger.info("\n🎉 Migration réussie !")
        logger.info("📱 Vous pouvez maintenant utiliser les nouveaux champs téléphone et email")
    else:
        logger.error("\n❌ Échec de la migration")










