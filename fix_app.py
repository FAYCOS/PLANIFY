#!/usr/bin/env python3
"""
Script pour corriger l'app.py en commentant les routes non fonctionnelles
"""

import re
import logging
logger = logging.getLogger(__name__)

def fix_app_file():
    # Lire le fichier
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Commenter toutes les routes qui utilisent des modules non existants
    patterns_to_comment = [
        r'@app\.route\([\'"]/dj/.*?google-calendar.*?[\'"]\)',
        r'@app\.route\([\'"]/auth/google.*?[\'"]\)',
        r'@app\.route\([\'"]/admin/test-reminders.*?[\'"]\)',
        r'@app\.route\([\'"]/admin/notification-settings.*?[\'"]\)',
        r'@app\.route\([\'"]/prestations/.*?facture.*?[\'"]\)',
        r'@app\.route\([\'"]/rapports-financiers.*?[\'"]\)',
        r'@app\.route\([\'"]/api/financial-reports.*?[\'"]\)',
        r'@app\.route\([\'"]/export-clients.*?[\'"]\)',
    ]
    
    # Commenter les routes
    for pattern in patterns_to_comment:
        content = re.sub(pattern, lambda m: '# ' + m.group(0), content)
    
    # Commenter les fonctions correspondantes
    function_patterns = [
        r'def connect_google_calendar\(.*?\):',
        r'def google_calendar_callback\(.*?\):',
        r'def disconnect_google_calendar\(.*?\):',
        r'def sync_google_calendar\(.*?\):',
        r'def sync_from_google_calendar\(.*?\):',
        r'def sync_prestation_to_google_calendar\(.*?\):',
        r'def test_reminders\(.*?\):',
        r'def notification_settings\(.*?\):',
        r'def generate_invoice\(.*?\):',
        r'def auto_generate_invoice\(.*?\):',
        r'def financial_reports\(.*?\):',
        r'def api_revenue_report\(.*?\):',
        r'def api_profitability_report\(.*?\):',
        r'def api_client_analysis\(.*?\):',
        r'def api_performance_report\(.*?\):',
        r'def api_comprehensive_report\(.*?\):',
        r'def export_clients\(.*?\):',
    ]
    
    for pattern in function_patterns:
        content = re.sub(pattern, lambda m: '# ' + m.group(0), content)
    
    # Écrire le fichier corrigé
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("✅ Fichier app.py corrigé - routes non fonctionnelles commentées")

if __name__ == '__main__':
    fix_app_file()









