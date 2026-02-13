#!/usr/bin/env python3
"""
Script pour réinitialiser complètement la base de données
"""

import os
import sys
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, DJ, Local, Materiel, Prestation, Devis
import logging
logger = logging.getLogger(__name__)

def reset_complete():
    """Réinitialiser complètement la base de données"""
    with app.app_context():
        try:
            logger.info("🗑️  Suppression complète de la base de données...")
            
            # Supprimer toutes les données
            logger.info("👥 Suppression des utilisateurs...")
            User.query.delete()
            
            logger.info("🎵 Suppression des DJs...")
            DJ.query.delete()
            
            logger.info("🏢 Suppression des locaux...")
            Local.query.delete()
            
            logger.info("🔧 Suppression des matériels...")
            Materiel.query.delete()
            
            logger.info("📅 Suppression des prestations...")
            Prestation.query.delete()
            
            logger.info("📄 Suppression des devis...")
            Devis.query.delete()
            
            logger.info("⚙️  Suppression des paramètres d'entreprise...")
            try:
                # Supprimer via SQL direct pour éviter import cyclique du modèle
                db.session.execute('DELETE FROM parametres_entreprise')
            except Exception:
                logger.exception('Impossible de supprimer parametres_entreprise via SQL')
            
            # Commit des changements
            db.session.commit()
            
            logger.info("✅ Base de données complètement vidée !")
            logger.info("📱 L'application va maintenant afficher la page de première connexion")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la réinitialisation : {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    logger.info("🎵 Planify - Réinitialisation complète de la base de données")
    logger.info("=" * 60)
    
    if reset_complete():
        logger.info("\n🎉 Réinitialisation terminée avec succès !")
        logger.info("📱 Redémarrez l'application pour voir la page de première connexion")
    else:
        logger.error("\n❌ Échec de la réinitialisation")
        sys.exit(1)











