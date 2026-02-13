#!/usr/bin/env python3
"""
Script pour créer une icône simple pour l'application
"""

from PIL import Image, ImageDraw, ImageFont
import os
import logging
logger = logging.getLogger(__name__)

def create_app_icon():
    """Crée une icône simple pour l'application"""
    logger.info("🎨 Création de l'icône de l'application...")
    
    # Créer le dossier static s'il n'existe pas
    os.makedirs('static', exist_ok=True)
    
    # Créer une image 256x256
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Couleurs
    bg_color = (52, 152, 219)  # Bleu
    text_color = (255, 255, 255)  # Blanc
    
    # Dessiner un cercle de fond
    margin = 20
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill=bg_color, outline=(41, 128, 185), width=3)
    
    # Ajouter le texte "P" pour Planify
    try:
        # Essayer d'utiliser une police système
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 120)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 120)
        except:
            # Police par défaut
            font = ImageFont.load_default()
    
    # Centrer le texte
    text = "P"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10
    
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Sauvegarder l'icône
    icon_path = 'static/favicon.ico'
    img.save(icon_path, format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    
    logger.info(f"✅ Icône créée : {icon_path}")
    return True

if __name__ == '__main__':
    create_app_icon()








