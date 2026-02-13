"""
Migration : Créer la table grille_tarifaire et ajouter des tarifs par défaut
"""

import sqlite3
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

def migrate_grille_tarifaire():
    """Créer la table grille_tarifaire et ajouter des tarifs par défaut"""
    db_path = 'instance/dj_prestations.db'
    
    if not os.path.exists(db_path):
        logger.error(f"❌ Base de données introuvable : {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si la table existe déjà
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grille_tarifaire'")
        if cursor.fetchone():
            logger.info("ℹ️ La table 'grille_tarifaire' existe déjà.")
            conn.close()
            return True
        
        logger.info("🔧 Création de la table 'grille_tarifaire'...")
        
        # Créer la table
        cursor.execute("""
            CREATE TABLE grille_tarifaire (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom VARCHAR(100) NOT NULL,
                type_evenement VARCHAR(50) NOT NULL UNIQUE,
                tarif_horaire_base REAL DEFAULT 100.0,
                duree_minimum REAL DEFAULT 4.0,
                majoration_weekend REAL DEFAULT 0.0,
                majoration_jour_ferie REAL DEFAULT 0.0,
                majoration_nuit REAL DEFAULT 0.0,
                frais_deplacement_base REAL DEFAULT 50.0,
                frais_deplacement_par_km REAL DEFAULT 0.5,
                distance_gratuite_km REAL DEFAULT 30.0,
                description TEXT,
                actif BOOLEAN DEFAULT 1,
                date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_modification DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("✅ Table 'grille_tarifaire' créée.")
        
        # Ajouter des tarifs par défaut
        logger.info("📋 Ajout des tarifs par défaut...")
        
        tarifs_defaut = [
            {
                'nom': 'Mariage',
                'type_evenement': 'mariage',
                'tarif_horaire_base': 150.0,
                'duree_minimum': 6.0,
                'majoration_weekend': 20.0,
                'majoration_jour_ferie': 30.0,
                'majoration_nuit': 15.0,
                'frais_deplacement_base': 80.0,
                'description': 'Tarif pour mariages - Prestation premium avec matériel professionnel'
            },
            {
                'nom': 'Anniversaire',
                'type_evenement': 'anniversaire',
                'tarif_horaire_base': 100.0,
                'duree_minimum': 4.0,
                'majoration_weekend': 15.0,
                'majoration_jour_ferie': 20.0,
                'majoration_nuit': 10.0,
                'frais_deplacement_base': 50.0,
                'description': 'Tarif pour anniversaires - Formule standard'
            },
            {
                'nom': 'Événement d\'Entreprise',
                'type_evenement': 'entreprise',
                'tarif_horaire_base': 180.0,
                'duree_minimum': 4.0,
                'majoration_weekend': 0.0,  # Pas de majoration weekend en entreprise
                'majoration_jour_ferie': 50.0,
                'majoration_nuit': 25.0,
                'frais_deplacement_base': 100.0,
                'description': 'Tarif pour événements d\'entreprise - Formule professionnelle'
            },
            {
                'nom': 'Soirée Privée',
                'type_evenement': 'prive',
                'tarif_horaire_base': 120.0,
                'duree_minimum': 3.0,
                'majoration_weekend': 10.0,
                'majoration_jour_ferie': 15.0,
                'majoration_nuit': 10.0,
                'frais_deplacement_base': 40.0,
                'description': 'Tarif pour soirées privées - Formule flexible'
            },
            {
                'nom': 'Festival / Grand Événement',
                'type_evenement': 'festival',
                'tarif_horaire_base': 200.0,
                'duree_minimum': 8.0,
                'majoration_weekend': 0.0,  # Prix déjà élevé
                'majoration_jour_ferie': 0.0,
                'majoration_nuit': 0.0,
                'frais_deplacement_base': 150.0,
                'frais_deplacement_par_km': 1.0,
                'distance_gratuite_km': 50.0,
                'description': 'Tarif pour festivals et grands événements - Formule premium longue durée'
            }
        ]
        
        for tarif in tarifs_defaut:
            cursor.execute("""
                INSERT INTO grille_tarifaire 
                (nom, type_evenement, tarif_horaire_base, duree_minimum, 
                 majoration_weekend, majoration_jour_ferie, majoration_nuit,
                 frais_deplacement_base, frais_deplacement_par_km, distance_gratuite_km,
                 description, actif)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tarif['nom'],
                tarif['type_evenement'],
                tarif['tarif_horaire_base'],
                tarif['duree_minimum'],
                tarif['majoration_weekend'],
                tarif['majoration_jour_ferie'],
                tarif['majoration_nuit'],
                tarif['frais_deplacement_base'],
                tarif.get('frais_deplacement_par_km', 0.5),
                tarif.get('distance_gratuite_km', 30.0),
                tarif['description'],
                True
            ))
            logger.info(f"  ✓ {tarif['nom']} ({tarif['tarif_horaire_base']}€/h)")
        
        conn.commit()
        
        logger.info("\n✅ Migration terminée avec succès !")
        logger.info("\n📝 TARIFS CRÉÉS:")
        logger.info("  • Mariage: 150€/h (min 6h) + majorations weekend/férié/nuit")
        logger.info("  • Anniversaire: 100€/h (min 4h)")
        logger.info("  • Entreprise: 180€/h (min 4h)")
        logger.info("  • Privé: 120€/h (min 3h)")
        logger.info("  • Festival: 200€/h (min 8h)")
        logger.info("\n🎯 Ces tarifs sont modifiables depuis l'interface admin")
        logger.info("   (Gestion > Grille Tarifaire)")
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"❌ Erreur SQLite lors de la migration : {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    logger.info("============================================================")
    logger.info("🔧 MIGRATION : Grille Tarifaire")
    logger.info("============================================================")
    migrate_grille_tarifaire()


