#!/bin/bash

echo "🔧 Configuration du Pare-feu pour Planify"
echo ""

# Vérifier le statut du pare-feu
echo "📊 Statut actuel du pare-feu :"
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

echo ""
echo "🔓 Pour autoriser Python à recevoir des connexions :"
echo "1. Ouvrez 'Préférences Système'"
echo "2. Allez dans 'Sécurité et confidentialité'"
echo "3. Cliquez sur l'onglet 'Pare-feu'"
echo "4. Cliquez sur le cadenas pour déverrouiller"
echo "5. Cliquez sur 'Options du pare-feu...'"
echo "6. Ajoutez Python3 ou autorisez toutes les connexions entrantes"
echo ""

# Alternative : désactiver temporairement le pare-feu (nécessite sudo)
echo "⚠️  Alternative (nécessite mot de passe admin) :"
echo "sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off"
echo ""

