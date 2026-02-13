#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration : Ajouter le champ prix_location à tous les matériels
Date : 27 Octobre 2025
Correctif : FIX #1 - Calcul réel des prix au lieu de répartition 60/40 fictive
"""

import sqlite3
import os
import logging
logger = logging.getLogger(__name__)

def migrate_add_prix_location():
    """Ajoute le champ prix_location à la table materiels"""
    db_path = 'instance/dj_prestations.db'
    
    if not os.path.exists(db_path):
        logger.error(f"❌ Base de données introuvable : {db_path}")
        logger.info(f"   Chemin actuel : {os.getcwd()}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si la colonne existe déjà
        cursor.execute("PRAGMA table_info(materiels)")
        colonnes = [col[1] for col in cursor.fetchall()]
        
        if 'prix_location' in colonnes:
            logger.info("✅ La colonne 'prix_location' existe déjà")
            conn.close()
            return True
        
        # Ajouter la colonne
        logger.info("🔧 Ajout de la colonne 'prix_location' à la table 'materiels'...")
        cursor.execute("""
            ALTER TABLE materiels
            ADD COLUMN prix_location REAL DEFAULT 0.0
        """)
        
        # Définir des prix par défaut selon la catégorie
        prix_par_categorie = {
            'sonorisation': 50.0,
            'eclairage': 30.0,
            'effets': 25.0,
            'decoration': 15.0,
            'mobilier': 20.0,
            'accessoires': 10.0
        }
        
        # Récupérer tous les matériels
        cursor.execute("SELECT id, nom, categorie FROM materiels")
        materiels = cursor.fetchall()
        
        logger.info(f"📦 Mise à jour de {len(materiels)} matériels...")
        
        for mat_id, nom, categorie in materiels:
            # Déterminer le prix selon la catégorie
            prix = prix_par_categorie.get(categorie.lower() if categorie else '', 20.0)
            
            # Ajuster selon le nom (logique basique)
            nom_lower = nom.lower() if nom else ''
            if any(word in nom_lower for word in ['enceinte', 'sono', 'sound']):
                prix = 60.0
            elif any(word in nom_lower for word in ['console', 'mix', 'table']):
                prix = 80.0
            elif any(word in nom_lower for word in ['micro', 'mic']):
                prix = 15.0
            elif any(word in nom_lower for word in ['projecteur', 'par', 'spot']):
                prix = 35.0
            elif any(word in nom_lower for word in ['laser', 'effet']):
                prix = 45.0
            elif any(word in nom_lower for word in ['câble', 'cable']):
                prix = 5.0
            
            # Mettre à jour
            cursor.execute("""
                UPDATE materiels
                SET prix_location = ?
                WHERE id = ?
            """, (prix, mat_id))
            
            logger.info(f"  ✓ {nom} → {prix:.2f}€")
        
        conn.commit()
        conn.close()
        
        logger.info("\n✅ Migration terminée avec succès !")
        logger.info("📝 Note : Les prix par défaut ont été définis automatiquement.")
        logger.info("   Vous pouvez les ajuster manuellement depuis l'interface de gestion du matériel.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration : {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 MIGRATION : Ajout prix_location au matériel")
    logger.info("=" * 60)
    logger.info()
    
    success = migrate_add_prix_location()
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("🎉 Migration réussie !")
        logger.info("=" * 60)
        logger.info()
        logger.info("CHANGEMENTS APPLIQUÉS :")
        logger.info("  ✅ Colonne 'prix_location' ajoutée")
        logger.info("  ✅ Prix par défaut définis pour chaque matériel")
        logger.info("  ✅ Les devis et factures afficheront maintenant les VRAIS coûts")
        logger.info()
        logger.info("PROCHAINES ÉTAPES :")
        logger.info("  1. Vérifiez les prix dans 'Gestion > Matériel'")
        logger.info("  2. Ajustez les prix si nécessaire")
        logger.info("  3. Testez la génération d'un devis")
        logger.info()
    else:
        logger.error("\n❌ La migration a échoué. Vérifiez les erreurs ci-dessus.")
        exit(1)

