"""
Setup script pour créer l'exécutable Windows de Planify
Utilise cx_Freeze pour créer un package Windows
"""

from cx_Freeze import setup, Executable
import sys
import logging
logger = logging.getLogger(__name__)

# Dépendances à inclure
build_exe_options = {
    "packages": [
        "flask",
        "flask_sqlalchemy",
        "werkzeug",
        "jinja2",
        "sqlalchemy",
        "waitress",
        "google",
        "googleapiclient",
        "google_auth_oauthlib",
        "icalendar",
        "qrcode",
        "PIL",
        "datetime",
        "logging",
        "os",
        "sqlite3",
        "json",
        "secrets",
        "hashlib",
        "functools",
        "re",
    ],
    "include_files": [
        ("templates/", "templates/"),
        ("static/", "static/"),
        ("instance/", "instance/"),
    ],
    "excludes": ["tkinter"],
    "optimize": 2,
}

# Configuration de l'exécutable
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Pour masquer la console

executables = [
    Executable(
        "app.py",
        base=base,
        target_name="Planify.exe",
        icon=None,  # Ajoutez un .ico si vous en avez un
        shortcut_name="Planify v2.1",
        shortcut_dir="DesktopFolder",
    )
]

setup(
    name="Planify",
    version="2.1",
    description="Logiciel de Gestion de Prestations DJ",
    author="Greg Nizery",
    author_email="greg.nizery@outlook.fr",
    options={"build_exe": build_exe_options},
    executables=executables,
)

