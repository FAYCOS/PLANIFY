#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration pour ajouter les colonnes des modules optionnels
"""

import sqlite3
import os
import logging
logger = logging.getLogger(__name__)

def migrate_database():
    """Ajoute les colonnes des modules optionnels à la base de données"""
    
    db_path = 'instance/dj_prestations.db'
    
    if not os.path.exists(db_path):
        logger.error("❌ Base de données non trouvée")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si les colonnes existent déjà
        cursor.execute("PRAGMA table_info(parametres_entreprise)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Colonnes à ajouter
        new_columns = [
            ('module_google_calendar', 'BOOLEAN DEFAULT 0'),
            ('module_excel_export', 'BOOLEAN DEFAULT 1'),
            ('module_pdf_generation', 'BOOLEAN DEFAULT 1'),
            ('module_financial_reports', 'BOOLEAN DEFAULT 0'),
            ('module_notifications', 'BOOLEAN DEFAULT 1'),
            ('module_icalendar', 'BOOLEAN DEFAULT 1')
        ]
        
        added_columns = []
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE parametres_entreprise ADD COLUMN {column_name} {column_type}")
                    added_columns.append(column_name)
                    logger.info(f"✅ Colonne {column_name} ajoutée")
                except sqlite3.Error as e:
                    logger.error(f"❌ Erreur pour {column_name}: {e}")
            else:
                logger.info(f"ℹ️  Colonne {column_name} existe déjà")
        
        conn.commit()
        
        if added_columns:
            logger.info(f"\n🎉 Migration réussie ! {len(added_columns)} colonne(s) ajoutée(s)")
            logger.info("Colonnes ajoutées:", ", ".join(added_columns))
        else:
            logger.info("\n✅ Aucune migration nécessaire - toutes les colonnes existent déjà")
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Erreur de migration: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("🔄 Migration de la base de données...")
    logger.info("=" * 50)
    
    if migrate_database():
        logger.info("\n✅ Migration terminée avec succès !")
    else:
        logger.error("\n❌ Échec de la migration")






