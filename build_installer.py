#!/usr/bin/env python3
"""
Script pour créer l'installateur Windows de Planify
Crée un installateur NSIS autonome qui inclut Python embarqué
"""

import os
import sys
import shutil
import subprocess
import logging
logger = logging.getLogger(__name__)

logger.info("=" * 70)
logger.info("🔨 CONSTRUCTION DE L'INSTALLATEUR WINDOWS PLANIFY v2.1")
logger.info("=" * 70)
# blank logger.info() removed

# Étape 1 : Créer le script NSIS
logger.info("📝 1. Création du script d'installation NSIS...")

nsis_script = r"""
; Script d'installation Planify v2.1 pour Windows
; Auteur: Greg Nizery
; Email: greg.nizery@outlook.fr

!define APP_NAME "Planify"
!define APP_VERSION "2.1"
!define APP_PUBLISHER "Greg Nizery"
!define APP_URL "http://planify.app"
!define APP_DIR "$PROGRAMFILES\Planify"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "Planify_v2.1_Setup.exe"
InstallDir "${APP_DIR}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "Install_Dir"
RequestExecutionLevel admin

; Interface moderne
!include "MUI2.nsh"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "English"

; Installation
Section "Installation principale" SecMain
    SetOutPath "$INSTDIR"
    
    ; Afficher un message
    DetailPrint "Installation de Planify v2.1..."
    
    ; Créer les répertoires
    CreateDirectory "$INSTDIR\python"
    CreateDirectory "$INSTDIR\app"
    CreateDirectory "$INSTDIR\instance"
    CreateDirectory "$INSTDIR\templates"
    CreateDirectory "$INSTDIR\static"
    
    ; Copier les fichiers
    File /r "python-embed\*.*"
    SetOutPath "$INSTDIR\app"
    File "app.py"
    File "requirements.txt"
    File "run_production.py"
    
    SetOutPath "$INSTDIR\templates"
    File /r "templates\*.*"
    
    SetOutPath "$INSTDIR\static"
    File /r "static\*.*"
    
    ; Installer Python embarqué et les dépendances
    SetOutPath "$INSTDIR"
    DetailPrint "Installation de Python embarqué..."
    
    ; Télécharger et installer les dépendances
    DetailPrint "Installation des dépendances Python..."
    nsExec::ExecToLog '"$INSTDIR\python\python.exe" -m pip install --upgrade pip'
    nsExec::ExecToLog '"$INSTDIR\python\python.exe" -m pip install -r "$INSTDIR\app\requirements.txt"'
    
    ; Créer les raccourcis
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\start_planify.bat" "" "$INSTDIR\icon.ico"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Désinstaller.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\start_planify.bat" "" "$INSTDIR\icon.ico"
    
    ; Créer le script de démarrage
    FileOpen $0 "$INSTDIR\start_planify.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "echo =====================================$\r$\n"
    FileWrite $0 "echo    PLANIFY v2.1 - Démarrage$\r$\n"
    FileWrite $0 "echo =====================================$\r$\n"
    FileWrite $0 "echo.$\r$\n"
    FileWrite $0 'cd /d "$INSTDIR\app"$\r$\n'
    FileWrite $0 'start http://localhost:5000$\r$\n'
    FileWrite $0 '"$INSTDIR\python\python.exe" run_production.py$\r$\n'
    FileWrite $0 "pause$\r$\n"
    FileClose $0
    
    ; Enregistrer l'application
    WriteRegStr HKLM "Software\${APP_NAME}" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME} ${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\icon.ico"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Configurer le pare-feu Windows
    DetailPrint "Configuration du pare-feu Windows..."
    nsExec::ExecToLog 'netsh advfirewall firewall add rule name="Planify Server" dir=in action=allow protocol=TCP localport=5000'
    
    MessageBox MB_OK "Installation terminée !$\r$\n$\r$\nPlanify v2.1 est maintenant installé.$\r$\n$\r$\nUtilisez le raccourci sur le bureau pour démarrer l'application."
SectionEnd

; Désinstallation
Section "Uninstall"
    ; Supprimer les fichiers
    Delete "$INSTDIR\*.*"
    RMDir /r "$INSTDIR\python"
    RMDir /r "$INSTDIR\app"
    RMDir /r "$INSTDIR\instance"
    RMDir /r "$INSTDIR\templates"
    RMDir /r "$INSTDIR\static"
    RMDir /r "$INSTDIR"
    
    ; Supprimer les raccourcis
    Delete "$SMPROGRAMS\${APP_NAME}\*.*"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    ; Supprimer la règle de pare-feu
    nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="Planify Server"'
    
    ; Supprimer les clés de registre
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKLM "Software\${APP_NAME}"
    
    MessageBox MB_OK "Planify a été désinstallé avec succès."
SectionEnd
"""

with open("installer.nsi", "w", encoding="utf-8") as f:
    f.write(nsis_script)

logger.info("   ✅ Script NSIS créé : installer.nsi")
logger.info()

# Étape 2 : Créer la licence
logger.info("📝 2. Création du fichier LICENSE.txt...")

license_text = """
PLANIFY v2.1 - CONDITIONS DE LICENCE

Copyright (c) 2025 Greg Nizery

Ce logiciel est fourni "tel quel", sans garantie d'aucune sorte, expresse ou implicite.

DROITS D'UTILISATION :
- Vous pouvez installer et utiliser ce logiciel sur vos ordinateurs
- Vous pouvez créer des copies de sauvegarde
- Vous ne pouvez pas redistribuer ou revendre ce logiciel

LIMITATION DE RESPONSABILITÉ :
L'auteur ne pourra en aucun cas être tenu responsable de tout dommage direct, indirect, 
accessoire ou consécutif résultant de l'utilisation ou de l'incapacité d'utiliser ce logiciel.

SUPPORT :
Email : greg.nizery@outlook.fr
Téléphone : 06 46 42 97 06

VERSION : 2.1
DATE : 2025
"""

with open("LICENSE.txt", "w", encoding="utf-8") as f:
    f.write(license_text)

logger.info("   ✅ Licence créée : LICENSE.txt")
logger.info()

# Étape 3 : Créer le guide d'installation
logger.info("📝 3. Création du guide d'installation...")

install_guide = """
# 🪟 GUIDE D'INSTALLATION PLANIFY v2.1 POUR WINDOWS

## PRÉREQUIS

Aucun ! L'installateur inclut tout ce dont vous avez besoin :
- Python 3.11 embarqué
- Toutes les dépendances
- Configuration automatique

## INSTALLATION

1. **Télécharger l'installateur**
   - Fichier : Planify_v2.1_Setup.exe

2. **Exécuter l'installateur**
   - Double-cliquez sur Planify_v2.1_Setup.exe
   - Cliquez sur "Oui" si Windows demande les droits administrateur

3. **Suivre les étapes**
   - Acceptez la licence
   - Choisissez le dossier d'installation (par défaut : C:\\Program Files\\Planify)
   - Cliquez sur "Installer"

4. **Patienter**
   - L'installation peut prendre 2-5 minutes
   - Python et toutes les dépendances sont installés automatiquement

5. **Terminer**
   - Un raccourci "Planify" sera créé sur le bureau
   - L'application sera aussi dans le menu Démarrer

## PREMIER DÉMARRAGE

1. Double-cliquez sur le raccourci "Planify" sur le bureau
2. Une fenêtre de commande s'ouvre et affiche le démarrage
3. Votre navigateur s'ouvre automatiquement à http://localhost:5000
4. Suivez les instructions de configuration initiale

## UTILISATION

**Démarrer Planify :**
- Double-cliquez sur le raccourci bureau
- Ou : Menu Démarrer → Planify → Planify

**Accéder depuis un autre appareil :**
1. Notez l'adresse IP affichée au démarrage
2. Sur l'autre appareil, ouvrez : http://[ADRESSE_IP]:5000

**Arrêter Planify :**
- Fermez la fenêtre de commande
- Ou : Appuyez sur Ctrl+C dans la fenêtre

## DÉSINSTALLATION

**Option 1 : Panneau de configuration**
1. Paramètres Windows → Applications
2. Cherchez "Planify"
3. Cliquez sur "Désinstaller"

**Option 2 : Menu Démarrer**
1. Menu Démarrer → Planify
2. Cliquez sur "Désinstaller"

## DÉPANNAGE

**L'application ne démarre pas :**
- Vérifiez que le port 5000 n'est pas utilisé
- Désactivez temporairement l'antivirus
- Exécutez en tant qu'administrateur

**Erreur "Port déjà utilisé" :**
- Fermez toutes les instances de Planify
- Redémarrez l'ordinateur
- Relancez Planify

**L'application n'est pas accessible depuis un autre appareil :**
- Vérifiez que les deux appareils sont sur le même réseau WiFi
- Le pare-feu Windows est configuré automatiquement lors de l'installation
- Si problème, ajoutez manuellement une exception pour le port 5000

## SUPPORT

**Email :** greg.nizery@outlook.fr
**Téléphone :** 06 46 42 97 06

## MISES À JOUR

Les mises à jour seront disponibles sur demande.
Pour mettre à jour :
1. Désinstallez l'ancienne version
2. Installez la nouvelle version

**Votre base de données est conservée lors de la mise à jour.**
"""

with open("GUIDE_INSTALLATION_WINDOWS.md", "w", encoding="utf-8") as f:
    f.write(install_guide)

logger.info("   ✅ Guide créé : GUIDE_INSTALLATION_WINDOWS.md")
logger.info()

# Étape 4 : Créer le script de build
logger.info("📝 4. Création du script de build complet...")

build_script = """@echo off
echo ====================================
echo  BUILD PLANIFY WINDOWS INSTALLER
echo ====================================
echo.

echo Etape 1/3 : Verification de NSIS...
where makensis >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] NSIS n'est pas installe !
    echo Telechargez NSIS sur : https://nsis.sourceforge.io/Download
    pause
    exit /b 1
)
echo [OK] NSIS trouve

echo.
echo Etape 2/3 : Preparation des fichiers...
if not exist "python-embed" (
    echo [INFO] Telechargement de Python embarque...
    echo Veuillez telecharger manuellement :
    echo https://www.python.org/ftp/python/3.11.0/python-3.11.0-embed-amd64.zip
    echo Extrayez dans le dossier "python-embed"
    pause
)

echo.
echo Etape 3/3 : Compilation de l'installateur...
makensis installer.nsi

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo  BUILD REUSSI !
    echo ====================================
    echo.
    echo Fichier cree : Planify_v2.1_Setup.exe
    echo.
    echo Vous pouvez maintenant distribuer cet installateur.
) else (
    echo.
    echo [ERREUR] La compilation a echoue.
    echo Verifiez les messages d'erreur ci-dessus.
)

echo.
pause
"""

with open("build_windows.bat", "w", encoding="utf-8") as f:
    f.write(build_script)

logger.info("   ✅ Script de build créé : build_windows.bat")
logger.info()

logger.info("=" * 70)
logger.info("✅ FICHIERS D'INSTALLATION CRÉÉS AVEC SUCCÈS")
logger.info("=" * 70)
logger.info()
logger.info("📦 FICHIERS GÉNÉRÉS :")
logger.info("   - installer.nsi (Script NSIS)")
logger.info("   - LICENSE.txt (Licence)")
logger.info("   - GUIDE_INSTALLATION_WINDOWS.md (Guide)")
logger.info("   - build_windows.bat (Script de build)")
logger.info()
logger.info("📋 PROCHAINES ÉTAPES :")
logger.info()
logger.info("1. Sur un PC Windows avec Python :")
logger.info("   pip install cx_Freeze")
logger.info()
logger.info("2. Créer le package :")
logger.info("   python setup.py build")
logger.info()
logger.info("3. Installer NSIS :")
logger.info("   https://nsis.sourceforge.io/Download")
logger.info()
logger.info("4. Télécharger Python embarqué :")
logger.info("   https://www.python.org/ftp/python/3.11.0/python-3.11.0-embed-amd64.zip")
logger.info("   Extraire dans : python-embed/")
logger.info()
logger.info("5. Compiler l'installateur :")
logger.info("   build_windows.bat")
logger.info()
logger.info("6. Distribuer :")
logger.info("   Planify_v2.1_Setup.exe")
logger.info()

