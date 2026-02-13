import logging
logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
Script pour nettoyer complètement l'app.py en supprimant les parties non fonctionnelles
"""

def clean_app_file():
    # Lire le fichier
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Trouver la ligne où commencent les routes commentées
    start_comment_line = None
    for i, line in enumerate(lines):
        if '# Routes pour l\'intégration Google Calendar' in line:
            start_comment_line = i
            break
    
    if start_comment_line:
        # Garder seulement les lignes jusqu'à cette ligne
        cleaned_lines = lines[:start_comment_line]
        
        # Ajouter la fin du fichier
        cleaned_lines.append('\n')
        cleaned_lines.append('if __name__ == \'__main__\':\n')
        cleaned_lines.append('    main()\n')
        
        # Écrire le fichier nettoyé
        with open('app.py', 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        logger.info("✅ Fichier app.py nettoyé - parties non fonctionnelles supprimées")
    else:
        logger.warning("⚠️  Aucune section commentée trouvée")

if __name__ == '__main__':
    clean_app_file()









