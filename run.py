#!/usr/bin/env python3
import os
import logging
from app import app, db, init_db, init_smart_assistant, init_automation_system, find_available_port

# Logger configuration (mirrors app.py just in case)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Initialize the database
    with app.app_context():
        init_db()

        # Initialize AI and Automation systems
        try:
            init_smart_assistant(app, db)
            init_automation_system(app, db)
            logger.info("✅ Systèmes IA et automatisations initialisés")
        except Exception as e:
            logger.warning(f"Erreur initialisation IA/automations: {e}")

    # Find available port
    port = find_available_port()
    
    logger.info(f"Lancement sur le port {port}")
    if port != 5000:
        logger.warning(f"Le port 5000 était occupé, utilisation du port {port}")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get('FLASK_ENV') != 'production'))
