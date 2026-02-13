#!/bin/bash

echo "📱 CONNEXION AU HOTSPOT DU TÉLÉPHONE"
echo "===================================="
echo ""
echo "1. Activez le partage de connexion sur votre téléphone"
echo "2. Sur votre Mac, cliquez sur l'icône WiFi en haut à droite"
echo "3. Sélectionnez le réseau de votre téléphone"
echo "4. Entrez le mot de passe si demandé"
echo ""
echo "⏳ Patientez pendant la connexion..."
echo ""
echo "Une fois connecté, appuyez sur Entrée pour continuer..."
read

echo ""
echo "🔍 Recherche de la nouvelle adresse IP..."
sleep 2

NEW_IP=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}')

if [ -z "$NEW_IP" ]; then
    echo "❌ Impossible de trouver l'adresse IP"
    echo "Vérifiez que vous êtes bien connecté au hotspot"
    exit 1
fi

echo "✅ Nouvelle adresse IP : $NEW_IP"
echo ""
echo "📱 URLs à utiliser sur votre téléphone :"
echo "   - http://$NEW_IP:5000"
echo "   - http://$NEW_IP:8080 (test)"
echo ""

# Créer un nouveau QR code
python3 << EOF
import qrcode

url = 'http://$NEW_IP:5000'
qr = qrcode.QRCode(version=1, box_size=10, border=5)
qr.add_data(url)
qr.make(fit=True)

img = qr.make_image(fill_color='black', back_color='white')
img.save('planify_hotspot_qr.png')

print(f'✅ QR Code créé : planify_hotspot_qr.png')
print(f'📱 URL : {url}')
EOF

open planify_hotspot_qr.png

echo ""
echo "🎯 Maintenant, ouvrez sur votre téléphone :"
echo "   http://$NEW_IP:5000"
echo ""

