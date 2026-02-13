#!/usr/bin/env python3
"""
Script principal pour build et déploiement de Planify
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def install_dependencies():
    """Installe les dépendances nécessaires"""
    logger.info("📦 Installation des dépendances...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        logger.info("✅ Dépendances installées")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur installation dépendances : {e}")
        return False

def build_application():
    """Build l'application"""
    logger.info("🔨 Build de l'application...")
    
    try:
        subprocess.run([sys.executable, 'build_complete.py'], check=True)
        logger.info("✅ Build terminé")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur build : {e}")
        return False

def test_application():
    """Test l'application buildée"""
    logger.info("🧪 Test de l'application...")
    
    try:
        subprocess.run([sys.executable, 'test_build.py'], check=True)
        logger.info("✅ Test réussi")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur test : {e}")
        return False

def deploy_application():
    """Déploie l'application"""
    logger.info("🚀 Déploiement de l'application...")
    
    try:
        subprocess.run([sys.executable, 'deploy.py'], check=True)
        logger.info("✅ Déploiement terminé")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur déploiement : {e}")
        return False

def main():
    """Fonction principale"""
    logger.info("🎵 Planify - Build & Deploy Complet")
    logger.info("=" * 50)
    
    steps = [
        ("Installation des dépendances", install_dependencies),
        ("Build de l'application", build_application),
        ("Test de l'application", test_application),
        ("Déploiement", deploy_application)
    ]
    
    for step_name, step_func in steps:
        logger.info(f"\n🔄 {step_name}...")
        if not step_func():
            logger.error(f"❌ Échec à l'étape : {step_name}")
            return False
    
    logger.info("\n🎉 Processus complet terminé avec succès !")
    logger.info("📁 Vérifiez le fichier ZIP créé pour la distribution")
    return True

if __name__ == '__main__':
    main()








