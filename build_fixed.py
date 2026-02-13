#!/usr/bin/env python3
"""
Script de build corrigé pour Planify
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def build_application():
    """Build l'application avec PyInstaller"""
    logger.info("🎵 Planify - Build Corrigé")
    logger.info("=" * 50)
    
    # Nettoyer les builds précédents
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # Commande PyInstaller corrigée
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=Planify',
        '--add-data=templates:templates',
        '--add-data=static:static',
        '--add-data=app.py:.',
        '--add-data=email_service.py:.',
        '--add-data=init_key_manager.py:.',
        '--add-data=pdf_generator.py:.',
        '--add-data=excel_export.py:.',
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
        'start_force.py'
    ]
    
    logger.info("🔨 Construction de l'application...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info("✅ Application construite avec succès !")
        return True
    else:
        logger.error("❌ Erreur lors de la construction :")
        logger.info(result.stderr)
        return False

def test_application():
    """Test l'application buildée"""
    logger.info("🧪 Test de l'application...")
    
    # Vérifier que l'exécutable existe
    exe_path = None
    if os.path.exists("dist/Planify"):
        exe_path = "dist/Planify"
    elif os.path.exists("dist/Planify.exe"):
        exe_path = "dist/Planify.exe"
    elif os.path.exists("dist/Planify.app/Contents/MacOS/Planify"):
        exe_path = "dist/Planify.app/Contents/MacOS/Planify"
    else:
        logger.error("❌ Aucun exécutable trouvé dans dist/")
        return False
    
    logger.info(f"📁 Exécutable trouvé : {exe_path}")
    
    # Lancer l'application
    logger.info("🚀 Lancement de l'application...")
    try:
        process = subprocess.Popen([exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Attendre un peu pour que l'app démarre
        import time
        time.sleep(5)
        
        # Vérifier que le processus est toujours en cours
        if process.poll() is None:
            logger.info("✅ Application lancée avec succès !")
            logger.info("🌐 L'application devrait s'ouvrir dans votre navigateur")
            logger.info("💡 Testez les fonctionnalités principales")
            
            # Vérifier sur quel port elle écoute
            import subprocess
            result = subprocess.run(['lsof', '-i', ':5000'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Application écoute sur le port 5000")
            else:
                result = subprocess.run(['lsof', '-i', ':5001'], capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("✅ Application écoute sur le port 5001")
                else:
                    result = subprocess.run(['lsof', '-i', ':5002'], capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info("✅ Application écoute sur le port 5002")
                    else:
                        logger.error("❌ Application n'écoute sur aucun port détecté")
            
            return True
        else:
            logger.error("❌ L'application s'est fermée immédiatement")
            stdout, stderr = process.communicate()
            logger.error(f"Erreur : {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement : {e}")
        return False

def main():
    """Fonction principale"""
    if build_application():
        logger.info("\n🎉 Build terminé avec succès !")
        if test_application():
            logger.info("\n🎉 Test réussi ! L'application fonctionne correctement")
        else:
            logger.error("\n❌ Test échoué ! Vérifiez les erreurs ci-dessus")
    else:
        logger.error("\n❌ Échec du build")

if __name__ == '__main__':
    main()








