#!/usr/bin/env python3
"""
Script de migration pour ajouter les champs de profil utilisateur
"""

import sqlite3
import os
import logging
logger = logging.getLogger(__name__)

# Chemin vers la base de données
db_path = 'instance/dj_prestations.db'

def migrate():
    """Ajoute les nouveaux champs à la table users"""
    
    if not os.path.exists(db_path):
        logger.error(f"❌ Base de données non trouvée : {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Vérifier quels champs existent déjà
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        logger.info(f"📋 Colonnes existantes : {existing_columns}")
        
        # Nouveaux champs à ajouter
        new_columns = [
            ('photo_profil', 'VARCHAR(200)'),
            ('bio', 'TEXT'),
            ('adresse', 'VARCHAR(200)'),
            ('ville', 'VARCHAR(100)'),
            ('code_postal', 'VARCHAR(10)'),
            ('date_naissance', 'DATE'),
        ]
        
        added_count = 0
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                logger.info(f"➕ Ajout de la colonne : {column_name}")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                added_count += 1
            else:
                logger.info(f"✓ Colonne déjà existante : {column_name}")
        
        conn.commit()
        
        if added_count > 0:
            logger.info(f"\n✅ Migration réussie ! {added_count} colonnes ajoutées.")
        else:
            logger.info(f"\n✅ Aucune migration nécessaire. Tous les champs existent déjà.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration : {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    logger.info("🔄 Démarrage de la migration de la base de données...")
    logger.info("=" * 60)
    
    if migrate():
        logger.info("=" * 60)
        logger.info("✨ Migration terminée avec succès !")
    else:
        logger.info("=" * 60)
        logger.error("❌ La migration a échoué.")
        exit(1)


