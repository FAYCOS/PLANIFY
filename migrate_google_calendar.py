#!/usr/bin/env python3
"""
Script de migration pour ajouter les champs Google Calendar au modèle DJ
"""

import sqlite3
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

def migrate_google_calendar():
    """Ajoute les nouveaux champs Google Calendar à la table djs"""
    
    db_path = 'instance/dj_prestations.db'
    
    if not os.path.exists(db_path):
        logger.error("❌ Base de données non trouvée. Assurez-vous que l'application a été initialisée.")
        return False
    
    try:
        # Connexion à la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("🔄 Migration Google Calendar...")
        
        # Vérifier si les colonnes existent déjà
        cursor.execute("PRAGMA table_info(djs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ('google_calendar_enabled', 'BOOLEAN DEFAULT 0'),
            ('google_calendar_id', 'VARCHAR(200)'),
            ('google_access_token', 'TEXT'),
            ('google_refresh_token', 'TEXT'),
            ('google_token_expiry', 'DATETIME'),
            ('last_sync', 'DATETIME')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                logger.info(f"➕ Ajout de la colonne {column_name}...")
                cursor.execute(f"ALTER TABLE djs ADD COLUMN {column_name} {column_type}")
            else:
                logger.info(f"✅ Colonne {column_name} déjà présente")
        
        # Commit des changements
        conn.commit()
        
        logger.info("✅ Migration Google Calendar terminée avec succès !")
        logger.info("📋 Les nouveaux champs ont été ajoutés :")
        for column_name, _ in new_columns:
            logger.info(f"   - {column_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration : {str(e)}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    logger.info("🎵 Planify - Migration Google Calendar")
    logger.info("=" * 50)
    
    if migrate_google_calendar():
        logger.info("\n🎉 Migration réussie !")
        logger.info("📱 Les DJs peuvent maintenant se connecter à Google Calendar")
    else:
        logger.error("\n❌ Échec de la migration")










