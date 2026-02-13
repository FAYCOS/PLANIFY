#!/usr/bin/env python3
"""
Script pour créer automatiquement un utilisateur pour chaque DJ qui n'en a pas
"""

import os
import sys
import secrets
import string

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, DJ, User
from werkzeug.security import generate_password_hash
import logging
logger = logging.getLogger(__name__)

def generate_random_password(length=12):
    """Génère un mot de passe aléatoire sécurisé"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def generate_username_from_name(nom):
    """Génère un nom d'utilisateur à partir du nom du DJ"""
    # Enlever les espaces et caractères spéciaux
    username = nom.lower().replace(' ', '_').replace("'", '').replace('-', '_')
    # Limiter à 30 caractères
    username = username[:30]
    return username

def migrate_dj_to_users():
    with app.app_context():
        logger.info("🔄 Démarrage de la migration DJ → Users...")
        logger.info("=" * 70)
        
        # Récupérer tous les DJs
        all_djs = DJ.query.all()
        logger.info(f"📋 Nombre total de DJs : {len(all_djs)}")
        
        djs_without_user = [dj for dj in all_djs if not dj.user_id]
        logger.warning(f"⚠️  DJs sans utilisateur : {len(djs_without_user)}")
        
        if len(djs_without_user) == 0:
            logger.info("\n✅ Tous les DJs ont déjà un utilisateur associé !")
            return
        
        logger.info("\n" + "=" * 70)
        logger.info("🚀 Création des utilisateurs manquants...")
        logger.info("=" * 70 + "\n")
        
        created_count = 0
        credentials = []
        
        for dj in djs_without_user:
            try:
                # Générer un nom d'utilisateur unique
                base_username = generate_username_from_name(dj.nom)
                username = base_username
                counter = 1
                
                # Vérifier si le username existe déjà
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Générer un mot de passe aléatoire
                password = generate_random_password()
                
                # Extraire l'email du contact si possible
                email = None
                if dj.contact and '@' in dj.contact:
                    # Si le contact contient un @, c'est probablement un email
                    parts = dj.contact.split()
                    for part in parts:
                        if '@' in part:
                            email = part.strip()
                            break
                
                # Si pas d'email, générer un email temporaire
                if not email:
                    email = f"{username}@temp.local"
                
                # Créer l'utilisateur
                new_user = User(
                    username=username,
                    nom=dj.nom.split()[0] if ' ' in dj.nom else dj.nom,  # Premier mot = nom
                    prenom=dj.nom.split()[1] if ' ' in dj.nom and len(dj.nom.split()) > 1 else '',  # Deuxième mot = prénom
                    email=email,
                    password_hash=generate_password_hash(password),
                    role='dj',
                    actif=True
                )
                
                db.session.add(new_user)
                db.session.flush()  # Pour obtenir l'ID
                
                # Lier le DJ à l'utilisateur
                dj.user_id = new_user.id
                
                db.session.commit()
                
                logger.info(f"✅ DJ '{dj.nom}' → Utilisateur créé")
                logger.info(f"   📝 Username: {username}")
                logger.warning(f"   🔑 Password: {password}")
                if email:
                    logger.info(f"   📧 Email: {email}")
                logger.info()
                
                credentials.append({
                    'dj_nom': dj.nom,
                    'username': username,
                    'password': password,
                    'email': email
                })
                
                created_count += 1
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"❌ Erreur pour DJ '{dj.nom}': {e}")
                import traceback
                traceback.print_exc()
        
        logger.info("=" * 70)
        logger.info(f"✅ Migration terminée : {created_count}/{len(djs_without_user)} utilisateurs créés")
        logger.info("=" * 70)
        
        # Sauvegarder les identifiants dans un fichier
        if credentials:
            filename = 'dj_credentials.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("IDENTIFIANTS DES COMPTES DJ CRÉÉS\n")
                f.write("=" * 70 + "\n\n")
                f.write("⚠️  IMPORTANT : Partagez ces identifiants avec les DJs concernés\n")
                f.write("⚠️  Ils devront changer leur mot de passe à la première connexion\n\n")
                f.write("=" * 70 + "\n\n")
                
                for cred in credentials:
                    f.write(f"DJ : {cred['dj_nom']}\n")
                    f.write(f"Username : {cred['username']}\n")
                    f.write(f"Password : {cred['password']}\n")
                    if cred['email']:
                        f.write(f"Email : {cred['email']}\n")
                    f.write("-" * 70 + "\n\n")
            
            logger.info(f"\n📄 Identifiants sauvegardés dans : {filename}")
            logger.warning("⚠️  IMPORTANT : Partagez ces identifiants avec les DJs concernés !")

if __name__ == '__main__':
    try:
        migrate_dj_to_users()
        logger.info("\n✨ Script terminé avec succès !")
    except Exception as e:
        logger.error(f"\n❌ Erreur fatale : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

