#!/usr/bin/env python3
"""
Script de build complet pour Mac et Windows
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def create_icon():
    """Crée une icône simple si elle n'existe pas"""
    if not os.path.exists('static/favicon.ico'):
        logger.info("📝 Création d'une icône simple...")
        # Créer un fichier icône basique
        os.makedirs('static', exist_ok=True)
        # Pour l'instant, on utilisera l'icône par défaut

def build_for_platform():
    """Build selon la plateforme"""
    system = platform.system().lower()
    logger.info(f"🖥️  Plateforme détectée : {system}")
    
    if system == "darwin":  # macOS
        return build_mac()
    elif system == "windows":  # Windows
        return build_windows()
    else:
        return build_linux()

def build_mac():
    """Build pour macOS (.app)"""
    logger.info("🍎 Build pour macOS...")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=Planify',
        '--osx-bundle-identifier=com.planify.djmanager',
        '--add-data=templates:templates',
        '--add-data=static:static',
        '--hidden-import=reportlab',
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=PIL',
        'start_force.py'
    ]
    
    return run_build(cmd, "Planify.app")

def build_windows():
    """Build pour Windows (.exe)"""
    logger.info("🪟 Build pour Windows...")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=Planify',
        '--add-data=templates;templates',
        '--add-data=static;static',
        '--hidden-import=reportlab',
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=PIL',
        'start_force.py'
    ]
    
    return run_build(cmd, "Planify.exe")

def build_linux():
    """Build pour Linux"""
    logger.info("🐧 Build pour Linux...")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name=Planify',
        '--add-data=templates:templates',
        '--add-data=static:static',
        '--hidden-import=reportlab',
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=PIL',
        'start_force.py'
    ]
    
    return run_build(cmd, "Planify")

def run_build(cmd, output_name):
    """Exécute la commande de build"""
    logger.info("🔨 Construction en cours...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info(f"✅ Application construite avec succès !")
        logger.info(f"📁 Fichier créé : dist/{output_name}")
        
        # Créer un package d'installation
        create_installer_package(output_name)
        return True
    else:
        logger.error("❌ Erreur lors de la construction :")
        logger.info(result.stderr)
        return False

def create_installer_package(output_name):
    """Crée un package d'installation"""
    logger.info("📦 Création du package d'installation...")
    
    # Créer le dossier d'installation
    install_dir = f"Planify_Install_{platform.system()}"
    if os.path.exists(install_dir):
        shutil.rmtree(install_dir)
    os.makedirs(install_dir)
    
    # Copier l'exécutable
    if os.path.exists(f"dist/{output_name}"):
        if output_name.endswith('.app'):
            # Pour macOS, copier tout le dossier .app
            shutil.copytree(f"dist/{output_name}", f"{install_dir}/{output_name}")
        else:
            # Pour les autres plateformes, copier le fichier
            shutil.copy2(f"dist/{output_name}", install_dir)
    
    # Créer un script de lancement
    create_launcher_script(install_dir)
    
    # Créer un README
    create_readme(install_dir)
    
    logger.info(f"📁 Package créé : {install_dir}/")

def create_launcher_script(install_dir):
    """Crée un script de lancement"""
    launcher_content = '''#!/bin/bash
# Script de lancement pour Planify

echo "🎵 Démarrage de Planify..."
echo "📱 L'application va s'ouvrir dans votre navigateur"
echo ""

# Lancer l'application
./Planify

echo ""
echo "👋 Merci d'avoir utilisé Planify !"
'''
    
    with open(f"{install_dir}/launch.sh", 'w') as f:
        f.write(launcher_content)
    
    # Rendre le script exécutable sur Unix
    os.chmod(f"{install_dir}/launch.sh", 0o755)

def create_readme(install_dir):
    """Crée un fichier README"""
    readme_content = '''# 🎵 Planify - Gestion de Prestations DJ

## Installation

1. Double-cliquez sur l'exécutable Planify
2. L'application va s'ouvrir automatiquement dans votre navigateur
3. Suivez les instructions d'initialisation

## Première utilisation

1. Renseignez vos informations personnelles
2. Vérifiez votre email avec le code reçu
3. Configurez les informations de votre entreprise
4. Votre compte administrateur sera créé

## Fonctionnalités

- Gestion des prestations DJ
- Gestion du matériel et des locaux
- Système de facturation et devis
- Rapports et statistiques
- Interface multi-utilisateurs avec rôles

## Support

Pour toute question, contactez le support technique.

---
Planify v2.1 - Logiciel de gestion de prestations DJ
'''
    
    with open(f"{install_dir}/README.txt", 'w', encoding='utf-8') as f:
        f.write(readme_content)

def main():
    """Fonction principale"""
    logger.info("🎵 Planify - Build Complet")
    logger.info("=" * 50)
    
    # Vérifier que PyInstaller est installé
    try:
        subprocess.run(['pyinstaller', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ PyInstaller n'est pas installé !")
        logger.info("💡 Installez-le avec : pip install pyinstaller")
        return False
    
    # Créer l'icône si nécessaire
    create_icon()
    
    # Nettoyer les builds précédents
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # Build selon la plateforme
    success = build_for_platform()
    
    if success:
        logger.info("\n🎉 Build terminé avec succès !")
        logger.info("📁 Vérifiez le dossier 'dist' pour votre application")
    else:
        logger.error("\n❌ Échec du build")
        return False
    
    return True

if __name__ == '__main__':
    main()
