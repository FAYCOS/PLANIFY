#!/usr/bin/env python3
"""
Lancement de Planify en mode production avec Waitress
Plus rapide et plus stable que le serveur de développement Flask
"""

from waitress import serve
from app import app
import socket
import logging
logger = logging.getLogger(__name__)

# Obtenir l'IP locale
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80))
    local_ip = s.getsockname()[0]
except:
    local_ip = '127.0.0.1'
finally:
    s.close()

logger.info('=' * 70)
logger.info('🚀 PLANIFY v2.1 - MODE PRODUCTION')
logger.info('=' * 70)
logger.info('✅ Serveur Waitress démarré')
logger.info(f'🌐 Accès local   : http://localhost:5000')
logger.info(f'📱 Accès réseau  : http://{local_ip}:5000')
logger.info(f'🔗 Page connexion: http://{local_ip}:5000/login')
logger.info('')
logger.info('⚡ Performance optimisée pour mobile')
logger.info('⏹️  Appuyez sur Ctrl+C pour arrêter')
logger.info('=' * 70)
logger.info('')

# Lancer le serveur avec Waitress
# threads=8 pour gérer plusieurs connexions simultanées
# channel_timeout=300 pour éviter les timeouts
serve(
    app, 
    host='0.0.0.0', 
    port=5000, 
    threads=8,
    channel_timeout=300,
    url_scheme='http'
)

