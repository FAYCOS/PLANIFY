#!/usr/bin/env python3
"""
Script pour créer un utilisateur administrateur
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from werkzeug.security import generate_password_hash
import logging

logger = logging.getLogger(__name__)

def create_admin():
    with app.app_context():
        # Vérifier si un admin existe déjà
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            logger.info("Utilisateur 'admin' existe déjà")
            logger.info(f"Email: {admin.email}")
        else:
            # Créer l'admin
            admin = User(
                username='admin',
                nom='Admin',
                prenom='Super',
                email='admin@planify.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                actif=True
            )
            db.session.add(admin)
            db.session.commit()
            
            logger.info("Utilisateur administrateur créé avec succès !")
            logger.info("IDENTIFIANTS DE CONNEXION : Username: admin (mot de passe par défaut créé)")
            logger.info("URL: http://localhost:5000/login")
            logger.warning("Le mot de passe par défaut 'admin123' doit être changé immédiatement.")

if __name__ == '__main__':
    create_admin()


