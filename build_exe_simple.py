#!/usr/bin/env python3
"""
Script simplifié pour créer un exécutable Windows avec PyInstaller
Cette méthode est plus simple et ne nécessite qu'un PC Windows avec Python
"""

import os
import logging
logger = logging.getLogger(__name__)

# Créer le fichier spec pour PyInstaller
spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run_production.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('app.py', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'werkzeug',
        'jinja2',
        'sqlalchemy',
        'waitress',
        'google',
        'googleapiclient',
        'google_auth_oauthlib',
        'icalendar',
        'qrcode',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Planify_v2.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # True pour voir les logs, False pour masquer la console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
"""

with open("planify.spec", "w", encoding="utf-8") as f:
    f.write(spec_content)

logger.info("✅ Fichier planify.spec créé")
# logger.info() removed (no message provided)

# Créer le README pour Windows
readme = """
# 🪟 CRÉATION DE L'INSTALLATEUR WINDOWS - GUIDE COMPLET

## MÉTHODE 1 : PYINSTALLER (SIMPLE ET RAPIDE) ⭐ RECOMMANDÉ

Cette méthode crée un exécutable Windows autonome qui inclut tout.

### Sur un PC Windows :

1. **Installer Python 3.11+**
   - Téléchargez : https://www.python.org/downloads/
   - ⚠️ Cochez "Add Python to PATH" lors de l'installation

2. **Installer PyInstaller**
   ```cmd
   pip install pyinstaller
   ```

3. **Copier le projet Planify**
   - Copiez tout le dossier "v2.1" sur le PC Windows

4. **Créer l'exécutable**
   ```cmd
   cd chemin\\vers\\v2.1
   pyinstaller planify.spec
   ```

5. **Récupérer l'exécutable**
   - L'exécutable est dans : `dist\\Planify_v2.1.exe`
   - Taille : ~150-200 MB (inclut Python et toutes les dépendances)

6. **Distribuer**
   - Zipper le dossier `dist\\` complet
   - Distribuer `Planify_v2.1_Portable.zip`
   - L'utilisateur dézippe et lance `Planify_v2.1.exe`

### Avantages :
- ✅ Simple et rapide
- ✅ Un seul fichier .exe (ou dossier)
- ✅ Inclut Python et toutes les dépendances
- ✅ Fonctionne sur Windows 10/11 sans installation

---

## MÉTHODE 2 : INSTALLATEUR NSIS (PROFESSIONNEL)

Cette méthode crée un vrai installateur .exe avec désinstallateur.

### Sur un PC Windows :

1. **Installer NSIS**
   - Téléchargez : https://nsis.sourceforge.io/Download
   - Installez NSIS

2. **Télécharger Python Embarqué**
   - URL : https://www.python.org/ftp/python/3.11.0/python-3.11.0-embed-amd64.zip
   - Créez un dossier `python-embed` dans le projet
   - Extrayez le contenu du ZIP dedans

3. **Compiler l'installateur**
   - Double-cliquez sur `build_windows.bat`
   - Ou en ligne de commande :
   ```cmd
   makensis installer.nsi
   ```

4. **Récupérer l'installateur**
   - Fichier créé : `Planify_v2.1_Setup.exe`
   - Taille : ~100-150 MB

5. **Distribuer**
   - Distribuez `Planify_v2.1_Setup.exe`
   - L'utilisateur double-clique et suit l'assistant

### Avantages :
- ✅ Installation professionnelle
- ✅ Raccourcis automatiques (bureau + menu démarrer)
- ✅ Désinstallateur Windows
- ✅ Configuration pare-feu automatique
- ✅ Entrée dans "Programmes et fonctionnalités"

---

## MÉTHODE 3 : SCRIPT BATCH (ULTRA SIMPLE)

Pour un déploiement rapide sans compilation.

### Créer un ZIP avec :
- Tout le code source
- Un fichier `INSTALLER.bat` :

```batch
@echo off
echo ========================================
echo  PLANIFY v2.1 - Installation
echo ========================================
echo.

echo Verification de Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installe !
    echo Telechargez Python sur : https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Installation des dependances...
pip install -r requirements.txt

echo.
echo Creation du raccourci...
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%USERPROFILE%\\Desktop\\Planify.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%CD%\\START_PLANIFY.bat" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%CD%" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript CreateShortcut.vbs
del CreateShortcut.vbs

echo.
echo ========================================
echo  Installation terminee !
echo ========================================
echo.
echo Un raccourci a ete cree sur le bureau.
echo Double-cliquez sur "Planify" pour demarrer.
echo.
pause
```

- Un fichier `START_PLANIFY.bat` :

```batch
@echo off
title Planify v2.1
echo ====================================
echo    PLANIFY v2.1 - Demarrage
echo ====================================
echo.
start http://localhost:5000
python run_production.py
pause
```

### Avantages :
- ✅ Très simple
- ✅ Modification facile du code
- ✅ Nécessite juste Python installé sur le PC cible

---

## COMPARAISON DES MÉTHODES

| Critère | PyInstaller | NSIS | Script Batch |
|---------|-------------|------|--------------|
| **Simplicité** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Professionnel** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Taille** | ~200 MB | ~150 MB | ~50 MB |
| **Python requis** | ❌ Non | ❌ Non | ✅ Oui |
| **Installation** | Portable | Installateur | Manuel |
| **Désinstallation** | Supprimer dossier | Windows | Manuel |

---

## RECOMMANDATION

**Pour vente/distribution :** Méthode 2 (NSIS) - Le plus professionnel
**Pour test/démo :** Méthode 1 (PyInstaller) - Le plus simple
**Pour développement :** Méthode 3 (Batch) - Le plus flexible

---

## CRÉATION D'UNE ICÔNE

Pour personnaliser l'icône :

1. Créez une image 256x256 pixels du logo Planify
2. Convertissez en .ico : https://convertio.co/fr/png-ico/
3. Nommez le fichier `icon.ico`
4. Placez dans le dossier du projet

L'icône sera automatiquement utilisée par PyInstaller et NSIS.

---

## SUPPORT

**Email :** greg.nizery@outlook.fr
**Téléphone :** 06 46 42 97 06
"""

with open("README_WINDOWS_BUILD.md", "w", encoding="utf-8") as f:
    f.write(readme)

logger.info("✅ Guide complet créé : README_WINDOWS_BUILD.md")
logger.info()

# Créer les scripts batch
installer_bat = """@echo off
echo ========================================
echo  PLANIFY v2.1 - Installation
echo ========================================
echo.

echo Verification de Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installe !
    echo Telechargez Python sur : https://www.python.org/downloads/
    echo Assurez-vous de cocher "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python trouve
echo.

echo Installation des dependances...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERREUR] L'installation des dependances a echoue !
    pause
    exit /b 1
)

echo.
echo Creation du raccourci sur le bureau...
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%USERPROFILE%\\Desktop\\Planify.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%CD%\\START_PLANIFY.bat" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%CD%" >> CreateShortcut.vbs
echo oLink.Description = "Planify v2.1 - Gestion de Prestations DJ" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo.
echo Configuration du pare-feu Windows...
netsh advfirewall firewall add rule name="Planify Server" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1

echo.
echo ========================================
echo  Installation terminee !
echo ========================================
echo.
echo Un raccourci "Planify" a ete cree sur le bureau.
echo.
echo Pour demarrer Planify :
echo 1. Double-cliquez sur le raccourci "Planify" sur le bureau
echo 2. L'application s'ouvrira automatiquement dans votre navigateur
echo.
echo Contact : greg.nizery@outlook.fr
echo Telephone : 06 46 42 97 06
echo.
pause
"""

with open("INSTALLER.bat", "w", encoding="utf-8") as f:
    f.write(installer_bat)

logger.info("✅ Script d'installation créé : INSTALLER.bat")
logger.info()

start_bat = """@echo off
title Planify v2.1
color 0A

cls
echo ====================================
echo    PLANIFY v2.1 - Demarrage
echo ====================================
echo.
echo Demarrage du serveur...
echo.

REM Obtenir l'adresse IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set IP=%%a
set IP=%IP:~1%

echo Serveur demarre !
echo.
echo Acces local  : http://localhost:5000
echo Acces reseau : http://%IP%:5000
echo.
echo Le navigateur va s'ouvrir automatiquement...
echo.
echo Pour arreter le serveur : Fermez cette fenetre ou appuyez sur Ctrl+C
echo ====================================
echo.

REM Ouvrir le navigateur
start http://localhost:5000

REM Démarrer le serveur
python run_production.py

pause
"""

with open("START_PLANIFY.bat", "w", encoding="utf-8") as f:
    f.write(start_bat)

logger.info("✅ Script de démarrage créé : START_PLANIFY.bat")
logger.info()

logger.info("=" * 70)
logger.info("✅ TOUS LES FICHIERS POUR WINDOWS ONT ÉTÉ CRÉÉS !")
logger.info("=" * 70)
logger.info()
logger.info("📦 FICHIERS CRÉÉS :")
logger.info()
logger.info("   📄 setup.py - Configuration cx_Freeze")
logger.info("   📄 planify.spec - Configuration PyInstaller")
logger.info("   📄 installer.nsi - Script NSIS")
logger.info("   📄 LICENSE.txt - Fichier de licence")
logger.info("   📄 INSTALLER.bat - Script d'installation simple")
logger.info("   📄 START_PLANIFY.bat - Script de démarrage")
logger.info("   📄 build_windows.bat - Script de compilation NSIS")
logger.info("   📄 GUIDE_INSTALLATION_WINDOWS.md - Guide utilisateur")
logger.info("   📄 README_WINDOWS_BUILD.md - Guide de création")
logger.info()
logger.info("📋 POUR CRÉER L'INSTALLATEUR :")
logger.info()
logger.info("   Consultez le fichier README_WINDOWS_BUILD.md")
logger.info("   Il contient 3 méthodes détaillées")
logger.info()
logger.info("   MÉTHODE RECOMMANDÉE : PyInstaller (la plus simple)")
logger.info()

