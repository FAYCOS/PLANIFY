#!/usr/bin/env python3
"""
Script de build simple et efficace pour Planify
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def clean_build():
    """Nettoie les builds précédents"""
    logger.info("🧹 Nettoyage des builds précédents...")
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    logger.info("✅ Nettoyage terminé")
    return True

def build_app():
    """Build l'application"""
    logger.info("🔨 Construction de l'application...")
    
    # Commande PyInstaller optimisée
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=Planify',
        '--add-data=templates:templates',
        '--add-data=static:static',
        '--hidden-import=reportlab',
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=PIL',
        '--hidden-import=email.mime.text',
        '--hidden-import=smtplib',
        '--hidden-import=sqlite3',
        '--hidden-import=datetime',
        '--hidden-import=json',
        '--hidden-import=os',
        '--hidden-import=sys',
        '--hidden-import=pathlib',
        '--hidden-import=werkzeug.security',
        '--hidden-import=flask',
        '--hidden-import=flask_sqlalchemy',
        '--hidden-import=jinja2',
        'start_force.py'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info("✅ Application construite avec succès !")
        return True
    else:
        logger.error("❌ Erreur lors de la construction :")
        logger.info(result.stderr)
        return False

def create_launcher():
    """Crée un script de lancement"""
    logger.info("📝 Création du script de lancement...")
    
    launcher_content = '''#!/bin/bash
# Script de lancement pour Planify

echo "🎵 Planify - Gestion de Prestations DJ"
echo "======================================"
echo ""
echo "🚀 Démarrage de l'application..."
echo "📱 L'application va s'ouvrir dans votre navigateur"
echo ""

# Lancer l'application
./Planify

echo ""
echo "👋 Merci d'avoir utilisé Planify !"
'''
    
    with open('dist/launch.sh', 'w') as f:
        f.write(launcher_content)
    
    os.chmod('dist/launch.sh', 0o755)
    logger.info("✅ Script de lancement créé")
    return True

def create_readme():
    """Crée un README pour l'utilisateur"""
    logger.info("📝 Création du README...")
    
    readme_content = '''# 🎵 Planify - Gestion de Prestations DJ

## 🚀 Installation et Utilisation

### Sur Mac :
1. Double-cliquez sur `Planify` ou lancez `./launch.sh`
2. L'application s'ouvrira dans votre navigateur
3. Suivez l'initialisation (première connexion)

### Sur Windows :
1. Double-cliquez sur `Planify.exe`
2. L'application s'ouvrira dans votre navigateur
3. Suivez l'initialisation (première connexion)

## 📋 Première Utilisation

1. **Initialisation** : Renseignez vos informations personnelles
2. **Vérification Email** : Entrez le code reçu par email
3. **Configuration Entreprise** : Renseignez les infos de votre boîte
4. **C'est parti !** : Votre compte admin est créé

## 🎯 Fonctionnalités

- ✅ Gestion des prestations DJ
- ✅ Gestion du matériel et des locaux
- ✅ Système de facturation et devis
- ✅ Rapports et statistiques
- ✅ Interface multi-utilisateurs avec rôles
- ✅ Base de données intégrée

## 🔧 Dépannage

### L'application ne démarre pas :
- Vérifiez que le port 5000+ est libre
- Relancez l'application

### Problème de base de données :
- L'application se réinitialise automatiquement
- Suivez le processus d'initialisation

### Email non reçu :
- Vérifiez vos spams
- Le code est valide 10 minutes

## 📞 Support

Pour toute question ou problème, consultez la documentation intégrée dans l'application.

---
**Planify v2.1** - Logiciel professionnel de gestion de prestations DJ
'''
    
    with open('dist/README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    logger.info("✅ README créé")
    return True

def main():
    """Fonction principale"""
    logger.info("🎵 Planify - Build Simple")
    logger.info("=" * 40)
    
    # Étapes du build
    steps = [
        ("Nettoyage", clean_build),
        ("Construction", build_app),
        ("Script de lancement", create_launcher),
        ("README", create_readme)
    ]
    
    for step_name, step_func in steps:
        logger.info(f"\n🔄 {step_name}...")
        if not step_func():
            logger.error(f"❌ Échec à l'étape : {step_name}")
            return False
    
    logger.info("\n🎉 Build terminé avec succès !")
    logger.info("📁 Vérifiez le dossier 'dist' pour votre application")
    logger.info("🚀 Lancez './dist/launch.sh' pour tester")
    
    return True

if __name__ == '__main__':
    main()
