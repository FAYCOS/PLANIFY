#!/usr/bin/env python3
"""
Migration pour ajouter les champs de signature électronique
"""

import os
import sys

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate_signature_electronique():
    with app.app_context():
        logger.info("🔐 Démarrage de la migration Signature Électronique...")
        logger.info("=" * 60)
        
        # Récupérer les colonnes existantes
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('devis')
        existing_column_names = {col['name'] for col in columns}
        
        logger.info(f"📋 Colonnes existantes dans 'devis' : {len(existing_column_names)}")
        
        # Ajouter 'signature_token' (sans UNIQUE car SQLite ne le supporte pas en ALTER TABLE)
        if 'signature_token' not in existing_column_names:
            with db.engine.connect() as connection:
                connection.execute(db.text("ALTER TABLE devis ADD COLUMN signature_token VARCHAR(100)"))
                connection.commit()
            logger.info("➕ Ajout de la colonne : signature_token")
        else:
            logger.info("✓ Colonne déjà existante : signature_token")
        
        # Ajouter 'signature_image'
        if 'signature_image' not in existing_column_names:
            with db.engine.connect() as connection:
                connection.execute(db.text("ALTER TABLE devis ADD COLUMN signature_image TEXT"))
                connection.commit()
            logger.info("➕ Ajout de la colonne : signature_image")
        else:
            logger.info("✓ Colonne déjà existante : signature_image")
        
        # Ajouter 'signature_date'
        if 'signature_date' not in existing_column_names:
            with db.engine.connect() as connection:
                connection.execute(db.text("ALTER TABLE devis ADD COLUMN signature_date DATETIME"))
                connection.commit()
            logger.info("➕ Ajout de la colonne : signature_date")
        else:
            logger.info("✓ Colonne déjà existante : signature_date")
        
        # Ajouter 'signature_ip'
        if 'signature_ip' not in existing_column_names:
            with db.engine.connect() as connection:
                connection.execute(db.text("ALTER TABLE devis ADD COLUMN signature_ip VARCHAR(50)"))
                connection.commit()
            logger.info("➕ Ajout de la colonne : signature_ip")
        else:
            logger.info("✓ Colonne déjà existante : signature_ip")
        
        # Ajouter 'est_signe'
        if 'est_signe' not in existing_column_names:
            with db.engine.connect() as connection:
                connection.execute(db.text("ALTER TABLE devis ADD COLUMN est_signe BOOLEAN DEFAULT 0"))
                connection.commit()
            logger.info("➕ Ajout de la colonne : est_signe (default: 0)")
        else:
            logger.info("✓ Colonne déjà existante : est_signe")
        
        logger.info("\n✅ Migration réussie ! 5 colonnes ajoutées/vérifiées.")
        logger.info("=" * 60)
        
if __name__ == '__main__':
    try:
        migrate_signature_electronique()
        logger.info("\n✨ Migration terminée avec succès !")
    except Exception as e:
        logger.error(f"\n❌ Erreur lors de la migration : {e}")
        import traceback
import logging
logger = logging.getLogger(__name__)
        traceback.print_exc()
        sys.exit(1)

