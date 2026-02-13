#!/bin/bash

# 🎵 DJ Prestations Manager - Script de démarrage rapide
# Script de lancement pour macOS

echo "🎵 DJ Prestations Manager v2.1"
echo "================================"

# Vérification de Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé."
    echo "💡 Installez Python depuis https://python.org"
    exit 1
fi

echo "✅ Python 3 trouvé : $(python3 --version)"

# Vérification de pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 n'est pas installé."
    echo "💡 Installez pip3 ou utilisez python3 -m pip"
    exit 1
fi

echo "✅ pip3 trouvé"

# Installation des dépendances
echo "📦 Installation des dépendances..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de l'installation des dépendances"
    exit 1
fi

echo "✅ Dépendances installées"

# Test de l'application
echo "🧪 Test de l'application..."
python3 test_app.py

if [ $? -ne 0 ]; then
    echo "⚠️ Certains tests ont échoué, mais l'application peut fonctionner"
fi

# Lancement de l'application
echo "🚀 Lancement de l'application..."
echo "📱 L'application sera disponible sur : http://localhost:5000"
echo "⏹️  Appuyez sur Ctrl+C pour arrêter"
echo ""

python3 launch.py

