#!/usr/bin/env python3
"""
Script de migration pour créer automatiquement des DJs pour les utilisateurs existants avec le rôle 'dj'
"""

import sqlite3
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

def migrate_dj_users():
    """Crée automatiquement des DJs pour les utilisateurs existants avec le rôle 'dj'"""
    
    db_path = 'instance/dj_prestations.db'
    
    if not os.path.exists(db_path):
        logger.error("❌ Base de données non trouvée. Assurez-vous que l'application a été initialisée.")
        return False
    
    try:
        # Connexion à la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("🔄 Migration des utilisateurs DJ...")
        
        # Récupérer tous les utilisateurs avec le rôle 'dj' qui n'ont pas encore de DJ associé
        cursor.execute("""
            SELECT u.id, u.nom, u.prenom, u.telephone, u.email
            FROM users u
            LEFT JOIN djs d ON u.id = d.user_id
            WHERE u.role = 'dj' AND d.user_id IS NULL
        """)
        
        users_to_migrate = cursor.fetchall()
        
        if not users_to_migrate:
            logger.info("✅ Aucun utilisateur DJ à migrer")
            return True
        
        logger.info(f"📋 {len(users_to_migrate)} utilisateur(s) DJ trouvé(s) à migrer")
        
        # Créer un DJ pour chaque utilisateur
        for user_id, nom, prenom, telephone, email in users_to_migrate:
            dj_nom = f"{prenom} {nom}".strip()
            contact = telephone if telephone else email
            
            cursor.execute("""
                INSERT INTO djs (nom, contact, user_id)
                VALUES (?, ?, ?)
            """, (dj_nom, contact, user_id))
            
            logger.info(f"✅ DJ créé pour {dj_nom}")
        
        # Commit des changements
        conn.commit()
        
        logger.info(f"🎉 Migration terminée avec succès !")
        logger.info(f"📋 {len(users_to_migrate)} DJ(s) créé(s)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration : {str(e)}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    logger.info("🎵 Planify - Migration des utilisateurs DJ")
    logger.info("=" * 50)
    
    if migrate_dj_users():
        logger.info("\n🎉 Migration réussie !")
        logger.info("📱 Les utilisateurs DJ sont maintenant disponibles pour les prestations")
    else:
        logger.error("\n❌ Échec de la migration")










