#!/usr/bin/env python3
"""
Script de migration pour ajouter les champs de branding
"""

import sqlite3
import os
import logging
logger = logging.getLogger(__name__)

# Chemin vers la base de données
db_path = 'instance/dj_prestations.db'

def migrate():
    """Ajoute les nouveaux champs de branding à la table parametres_entreprise"""
    
    if not os.path.exists(db_path):
        logger.error(f"❌ Base de données non trouvée : {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Vérifier quels champs existent déjà
        cursor.execute("PRAGMA table_info(parametres_entreprise)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        logger.info(f"📋 Colonnes existantes : {existing_columns}")
        
        # Nouveaux champs à ajouter
        new_columns = [
            ('slogan', 'VARCHAR(200)'),
            ('description_courte', 'TEXT'),
            ('afficher_logo_login', 'BOOLEAN', '1'),
            ('afficher_logo_sidebar', 'BOOLEAN', '1'),
        ]
        
        added_count = 0
        
        for column_info in new_columns:
            column_name = column_info[0]
            column_type = column_info[1]
            default_value = column_info[2] if len(column_info) > 2 else None
            
            if column_name not in existing_columns:
                if default_value:
                    logger.info(f"➕ Ajout de la colonne : {column_name} (default: {default_value})")
                    cursor.execute(f"ALTER TABLE parametres_entreprise ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
                else:
                    logger.info(f"➕ Ajout de la colonne : {column_name}")
                    cursor.execute(f"ALTER TABLE parametres_entreprise ADD COLUMN {column_name} {column_type}")
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
    logger.info("🎨 Démarrage de la migration du branding...")
    logger.info("=" * 60)
    
    if migrate():
        logger.info("=" * 60)
        logger.info("✨ Migration terminée avec succès !")
    else:
        logger.info("=" * 60)
        logger.error("❌ La migration a échoué.")
        exit(1)


