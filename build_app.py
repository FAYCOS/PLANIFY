#!/usr/bin/env python3
"""
Script de build pour créer une application installable avec PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def build_application():
    """Build l'application avec PyInstaller"""
    logger.info("🎵 Planify - Build de l'application")
    logger.info("=" * 50)
    
    # Nettoyer les builds précédents
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Commande PyInstaller
    cmd = [
        'pyinstaller',
        '--onefile',  # Un seul fichier exécutable
        '--windowed',  # Pas de console (pour Windows)
        '--name=Planify',
        '--icon=static/favicon.ico',  # Icône de l'app
        '--add-data=templates:templates',  # Inclure les templates
        '--add-data=static:static',  # Inclure les fichiers statiques
        '--hidden-import=reportlab',
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=PIL',
        'start_force.py'
    ]
    
    logger.info("🔨 Construction de l'application...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info("✅ Application construite avec succès !")
        logger.info(f"📁 Fichier créé : dist/Planify")
        return True
    else:
        logger.error("❌ Erreur lors de la construction :")
        logger.info(result.stderr)
        return False

if __name__ == '__main__':
    build_application()








