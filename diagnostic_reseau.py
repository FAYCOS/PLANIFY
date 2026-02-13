#!/usr/bin/env python3
"""
Diagnostic réseau complet pour Planify
"""

import socket
import subprocess
import qrcode
import os
import logging
logger = logging.getLogger(__name__)

def run_diagnostic():
    logger.info('=' * 70)
    logger.info('🔍 DIAGNOSTIC RÉSEAU PLANIFY')
    logger.info('=' * 70)

    # 1. Obtenir toutes les adresses IP
    logger.info('📡 1. ADRESSES IP DISPONIBLES')
    logger.info('-' * 70)

    result = subprocess.run(['ifconfig'], capture_output=True, text=True)
    lines = result.stdout.split('\n')

    ip_addresses = []
    current_interface = None

    for line in lines:
        if line and not line.startswith('\t'):
            current_interface = line.split(':')[0]
        if '\tinet ' in line and '127.0.0.1' not in line:
            parts = line.strip().split()
            if len(parts) >= 2:
                ip = parts[1]
                ip_addresses.append((current_interface, ip))
                logger.info(f'   ✅ {current_interface}: {ip}')

    if not ip_addresses:
        logger.error('   ❌ Aucune adresse IP réseau trouvée')
        logger.info('   → Connectez-vous à un réseau WiFi ou activez le hotspot')
        return 1

    logger.info()

    # 2. Réseau WiFi actuel
    logger.info('📶 2. RÉSEAU WIFI ACTUEL')
    logger.info('-' * 70)

    result = subprocess.run(['networksetup', '-getairportnetwork', 'en0'],
                           capture_output=True, text=True)
    wifi_network = result.stdout.strip().replace('Current Wi-Fi Network: ', '')
    logger.info(f'   📡 Réseau : {wifi_network}')
    logger.info()

    # 3. Serveurs actifs
    logger.info('🖥️  3. SERVEURS ACTIFS')
    logger.info('-' * 70)

    result = subprocess.run(['lsof', '-i', ':5000,8080'],
                           capture_output=True, text=True)
    if result.stdout:
        if '5000' in result.stdout:
            logger.info('   ✅ Port 5000 (Planify) : ACTIF')
        else:
            logger.error('   ❌ Port 5000 (Planify) : INACTIF')

        if '8080' in result.stdout:
            logger.info('   ✅ Port 8080 (Test) : ACTIF')
        else:
            logger.warning('   ⚠️  Port 8080 (Test) : INACTIF')
    else:
        logger.error('   ❌ Aucun serveur actif')

    logger.info()

    # 4. URLs d'accès et QR codes
    logger.info('🌐 4. URLS D\'ACCÈS')
    logger.info('-' * 70)

    for interface, ip in ip_addresses:
        logger.info(f'\n   Interface {interface} ({ip}) :')
        logger.info(f'   - Test    : http://{ip}:8080')
        logger.info(f'   - Planify : http://{ip}:5000')

        # Créer un QR code pour cette IP
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f'http://{ip}:5000')
        qr.make(fit=True)

        img = qr.make_image(fill_color='black', back_color='white')
        filename = f'qr_code_{interface}_{ip.replace(".", "_")}.png'
        img.save(filename)
        logger.info(f'   - QR Code : {filename}')

    logger.info()

    # 5. Instructions
    logger.info('📋 5. INSTRUCTIONS')
    logger.info('-' * 70)
    print('''
OPTION A - Si le téléphone et le Mac sont sur le même WiFi "wifipass" :

   1. Sur votre téléphone, ouvrez le navigateur
   2. Tapez une des URLs ci-dessus (commencez par le test port 8080)
   3. Si "unreachable" → Votre routeur bloque la communication
      → Passez à l'OPTION B

OPTION B - Utiliser le Hotspot du téléphone (RECOMMANDÉ) :

   1. Activez le partage de connexion sur votre téléphone
   2. Connectez votre Mac au hotspot du téléphone
   3. Relancez ce script pour obtenir la nouvelle IP
   4. Utilisez la nouvelle URL sur votre téléphone

OPTION C - Vérifier les paramètres du routeur :

   1. Connectez-vous à votre routeur (généralement 192.168.1.1)
   2. Désactivez "Isolation des clients WiFi" ou "AP Isolation"
   3. Redémarrez le routeur
   4. Reconnectez les deux appareils

''')

    logger.info('=' * 70)
    logger.info('✅ Diagnostic terminé')
    logger.info('=' * 70)


if __name__ == '__main__':
    sys.exit(run_diagnostic() or 0)

