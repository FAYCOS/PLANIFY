#!/usr/bin/env python3
"""
Script de déploiement automatique pour Planify
"""

import os
import sys
import subprocess
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def create_release_package():
    """Crée un package de release complet"""
    logger.info("📦 Création du package de release...")
    
    # Nom du package avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"Planify_v2.1_{timestamp}"
    
    # Créer le dossier de release
    if os.path.exists(package_name):
        shutil.rmtree(package_name)
    os.makedirs(package_name)
    
    # Copier l'exécutable
    exe_found = False
    for exe_name in ["Planify", "Planify.exe", "Planify.app"]:
        exe_path = f"dist/{exe_name}"
        if os.path.exists(exe_path):
            if exe_name.endswith('.app'):
                # Pour macOS, copier tout le dossier .app
                shutil.copytree(exe_path, f"{package_name}/{exe_name}")
            else:
                shutil.copy2(exe_path, package_name)
            exe_found = True
            break
    
    if not exe_found:
        logger.error("❌ Aucun exécutable trouvé ! Lancez d'abord le build.")
        return False
    
    # Créer les fichiers d'accompagnement
    create_installer_files(package_name)
    
    # Créer une archive ZIP
    create_zip_package(package_name)
    
    logger.info(f"✅ Package créé : {package_name}.zip")
    return True

def create_installer_files(package_name):
    """Crée les fichiers d'installation"""
    
    # Script de lancement
    launcher_content = '''#!/bin/bash
# Planify - Script de lancement

echo "🎵 Bienvenue dans Planify !"
echo "📱 Démarrage de l'application..."
echo ""

# Lancer l'application
if [ -f "./Planify" ]; then
    ./Planify
elif [ -f "./Planify.exe" ]; then
    ./Planify.exe
elif [ -d "./Planify.app" ]; then
    open ./Planify.app
else
    echo "❌ Exécutable non trouvé !"
    exit 1
fi

echo ""
echo "👋 Merci d'avoir utilisé Planify !"
'''
    
    with open(f"{package_name}/launch.sh", 'w') as f:
        f.write(launcher_content)
    os.chmod(f"{package_name}/launch.sh", 0o755)
    
    # Script Windows
    launcher_bat = '''@echo off
echo 🎵 Bienvenue dans Planify !
echo 📱 Démarrage de l'application...
echo.

if exist "Planify.exe" (
    Planify.exe
) else (
    echo ❌ Exécutable non trouvé !
    pause
    exit /b 1
)

echo.
echo 👋 Merci d'avoir utilisé Planify !
pause
'''
    
    with open(f"{package_name}/launch.bat", 'w') as f:
        f.write(launcher_bat)
    
    # README complet
    readme_content = '''# 🎵 Planify v2.1 - Gestion de Prestations DJ

## 🚀 Installation Rapide

### Sur Mac :
1. Double-cliquez sur `Planify.app`
2. Ou lancez `./launch.sh` dans le terminal

### Sur Windows :
1. Double-cliquez sur `Planify.exe`
2. Ou lancez `launch.bat`

## 📋 Première Utilisation

1. **Initialisation** : Renseignez vos informations personnelles
2. **Vérification Email** : Entrez le code reçu par email
3. **Configuration Entreprise** : Renseignez les infos de votre boîte
4. **C'est parti !** : Votre compte admin est créé

## 🎯 Fonctionnalités Principales

### 👥 Gestion des Utilisateurs
- **4 rôles** : Admin, Manager, DJ, Technicien
- **Permissions différenciées** selon le rôle
- **Sessions persistantes**

### 📅 Gestion des Prestations
- **Création/Modification** des prestations
- **Horaires précis** avec vérification matériel
- **Calendrier interactif**
- **Statuts** : Planifiée, Confirmée, Terminée

### 🎧 Gestion des DJs
- **Profils complets** avec historique
- **Calendrier personnel**
- **Statistiques de performance**

### 🏢 Gestion des Locaux
- **Interface en temps réel** par local
- **Disponibilité matériel** en direct
- **Auto-refresh** des données

### 🔧 Gestion du Matériel
- **Inventaire complet** avec statuts
- **Réservation intelligente** (blocage uniquement pendant prestation)
- **Calendrier par matériel**
- **Historique des mouvements**

### 💰 Facturation & Devis
- **Factures professionnelles** avec PDF
- **Devis automatiques** depuis les prestations
- **Tarification flexible** (horaires, frais, remises)
- **Suivi des paiements**
- **Exports Excel**

### 📊 Rapports & Statistiques
- **Dashboard temps réel** avec graphiques
- **Rapports financiers** détaillés
- **Exports Excel** complets
- **Analyse des performances**

## 🛠️ Support Technique

- **Base de données** : SQLite intégrée
- **Port** : Détection automatique (5000+)
- **Sécurité** : Validation, CSRF, limitation de taux
- **Interface** : Responsive, moderne, intuitive

## 📱 Utilisation

1. **Connexion** : Utilisez vos identifiants
2. **Navigation** : Menu latéral avec toutes les fonctionnalités
3. **Création** : Boutons "+" pour ajouter du contenu
4. **Modification** : Clic sur les éléments pour les éditer
5. **Suppression** : Boutons de suppression avec confirmation

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

## 📞 Contact

Pour toute question ou problème :
- Support technique intégré
- Documentation complète dans l'application

---
**Planify v2.1** - Logiciel professionnel de gestion de prestations DJ
Développé avec ❤️ pour les professionnels du spectacle
'''
    
    with open(f"{package_name}/README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)

def create_zip_package(package_name):
    """Crée une archive ZIP du package"""
    logger.info(f"📦 Création de l'archive {package_name}.zip...")
    
    with zipfile.ZipFile(f"{package_name}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_name):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, package_name)
                zipf.write(file_path, arc_path)
    
    logger.info(f"✅ Archive créée : {package_name}.zip")

def main():
    """Fonction principale"""
    logger.info("🚀 Planify - Déploiement")
    logger.info("=" * 40)
    
    # Vérifier que le build existe
    if not os.path.exists("dist"):
        logger.error("❌ Aucun build trouvé ! Lancez d'abord : python build_complete.py")
        return False
    
    # Créer le package de release
    if create_release_package():
        logger.info("\n🎉 Déploiement terminé avec succès !")
        logger.info("📁 Vérifiez le fichier ZIP créé")
        return True
    else:
        logger.error("\n❌ Échec du déploiement")
        return False

if __name__ == '__main__':
    main()








