#!/usr/bin/env python3
"""
Migration : Ajouter les colonnes d'acompte à la table factures
"""

import sqlite3
import os
from datetime import datetime

def migrate_factures_acompte():
    """Ajouter les colonnes d'acompte à la table factures"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'dj_prestations.db')
    
    if not os.path.exists(db_path):
        logger.error(f"❌ Base de données non trouvée : {db_path}")
        return False
    
    logger.info(f"📁 Base de données : {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si les colonnes existent déjà
        cursor.execute("PRAGMA table_info(factures)")
        columns = [col[1] for col in cursor.fetchall()]
        
        logger.info(f"\n📊 Colonnes actuelles de la table factures : {len(columns)}")
        
        # Colonnes à ajouter (mêmes que pour devis)
        new_columns = [
            ("acompte_requis", "BOOLEAN DEFAULT 0"),
            ("acompte_pourcentage", "FLOAT DEFAULT 0.0"),
            ("acompte_montant", "FLOAT DEFAULT 0.0"),
            ("acompte_paye", "BOOLEAN DEFAULT 0"),
            ("date_paiement_acompte", "DATETIME"),
            ("stripe_payment_intent_id", "VARCHAR(200)"),
            ("stripe_payment_link", "TEXT"),
        ]
        
        added = []
        already_exists = []
        
        for col_name, col_type in new_columns:
            if col_name in columns:
                already_exists.append(col_name)
                logger.info(f"  ⏭️  Colonne '{col_name}' existe déjà")
            else:
                try:
                    sql = f"ALTER TABLE factures ADD COLUMN {col_name} {col_type}"
                    cursor.execute(sql)
                    added.append(col_name)
                    logger.info(f"  ✅ Colonne '{col_name}' ajoutée ({col_type})")
                except sqlite3.OperationalError as e:
                    logger.error(f"  ⚠️  Erreur pour '{col_name}': {e}")
        
        conn.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Migration terminée avec succès !")
        logger.info(f"{'='*60}")
        logger.info(f"  📊 Colonnes ajoutées : {len(added)}")
        logger.info(f"  ⏭️  Colonnes existantes : {len(already_exists)}")
        
        if added:
            logger.info(f"\n  Nouvelles colonnes : {', '.join(added)}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Erreur lors de la migration : {e}")
        import traceback
import logging
logger = logging.getLogger(__name__)
        traceback.print_exc()
        return False

if __name__ == '__main__':
    logger.info("\n" + "="*60)
    logger.info("  MIGRATION : Acomptes pour Factures")
    logger.info("="*60 + "\n")
    
    success = migrate_factures_acompte()
    
    if success:
        logger.info("\n✅ Migration réussie !")
        logger.info("   Redémarrez l'application pour appliquer les changements")
    else:
        logger.error("\n❌ La migration a échoué")

