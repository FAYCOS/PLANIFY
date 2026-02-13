#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration pour ajouter le système de paiement Stripe
"""

import sqlite3
import os
import logging
logger = logging.getLogger(__name__)

def migrate_database():
    """Ajoute les champs de paiement et la table paiements"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'dj_prestations.db')
    
    if not os.path.exists(db_path):
        logger.error(f"❌ Base de données introuvable : {db_path}")
        return False
    
    logger.info(f"🔧 Migration de la base de données : {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. AJOUTER LES CHAMPS AUX FACTURES
        logger.info("\n📦 Migration de la table 'factures'...")
        
        factures_columns = [
            ("acompte_requis", "INTEGER DEFAULT 0"),
            ("acompte_pourcentage", "REAL DEFAULT 0.0"),
            ("acompte_montant", "REAL DEFAULT 0.0"),
            ("acompte_paye", "INTEGER DEFAULT 0"),
            ("date_paiement_acompte", "TEXT"),
            ("stripe_payment_intent_id", "TEXT"),
            ("stripe_payment_link", "TEXT"),
        ]
        
        for column_name, column_type in factures_columns:
            try:
                cursor.execute(f"ALTER TABLE factures ADD COLUMN {column_name} {column_type}")
                logger.info(f"  ✅ Colonne '{column_name}' ajoutée à 'factures'")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"  ⏭️  Colonne '{column_name}' existe déjà dans 'factures'")
                else:
                    logger.error(f"  ⚠️  Erreur sur colonne '{column_name}': {e}")
        
        # 2. AJOUTER LES CHAMPS AUX DEVIS
        logger.info("\n📦 Migration de la table 'devis'...")
        
        devis_columns = [
            ("acompte_requis", "INTEGER DEFAULT 0"),
            ("acompte_pourcentage", "REAL DEFAULT 0.0"),
            ("acompte_montant", "REAL DEFAULT 0.0"),
            ("acompte_paye", "INTEGER DEFAULT 0"),
            ("date_paiement_acompte", "TEXT"),
            ("stripe_payment_intent_id", "TEXT"),
            ("stripe_payment_link", "TEXT"),
        ]
        
        for column_name, column_type in devis_columns:
            try:
                cursor.execute(f"ALTER TABLE devis ADD COLUMN {column_name} {column_type}")
                logger.info(f"  ✅ Colonne '{column_name}' ajoutée à 'devis'")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"  ⏭️  Colonne '{column_name}' existe déjà dans 'devis'")
                else:
                    logger.error(f"  ⚠️  Erreur sur colonne '{column_name}': {e}")
        
        # 3. CRÉER LA TABLE PAIEMENTS
        logger.info("\n📦 Création de la table 'paiements'...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paiements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                montant REAL NOT NULL,
                devise TEXT DEFAULT 'EUR',
                type_paiement TEXT NOT NULL,
                description TEXT,
                statut TEXT DEFAULT 'en_attente',
                date_creation TEXT DEFAULT CURRENT_TIMESTAMP,
                date_paiement TEXT,
                date_expiration TEXT,
                stripe_payment_intent_id TEXT UNIQUE,
                stripe_checkout_session_id TEXT,
                stripe_customer_id TEXT,
                stripe_payment_method TEXT,
                stripe_charge_id TEXT,
                client_nom TEXT,
                client_email TEXT,
                client_telephone TEXT,
                client_ip TEXT,
                tentatives_paiement INTEGER DEFAULT 0,
                derniere_erreur TEXT,
                metadata TEXT,
                montant_rembourse REAL DEFAULT 0.0,
                date_remboursement TEXT,
                raison_remboursement TEXT,
                facture_id INTEGER,
                devis_id INTEGER,
                createur_id INTEGER,
                FOREIGN KEY (facture_id) REFERENCES factures (id),
                FOREIGN KEY (devis_id) REFERENCES devis (id),
                FOREIGN KEY (createur_id) REFERENCES users (id)
            )
        """)
        logger.info("  ✅ Table 'paiements' créée")
        
        # 4. CRÉER LES INDEX POUR PERFORMANCE
        logger.info("\n📊 Création des index...")
        
        indexes = [
            ("idx_paiements_facture", "paiements", "facture_id"),
            ("idx_paiements_devis", "paiements", "devis_id"),
            ("idx_paiements_statut", "paiements", "statut"),
            ("idx_paiements_stripe_intent", "paiements", "stripe_payment_intent_id"),
            ("idx_factures_stripe_intent", "factures", "stripe_payment_intent_id"),
            ("idx_devis_stripe_intent", "devis", "stripe_payment_intent_id"),
        ]
        
        for index_name, table_name, column_name in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
                logger.info(f"  ✅ Index '{index_name}' créé")
            except sqlite3.OperationalError as e:
                logger.info(f"  ⏭️  Index '{index_name}': {e}")
        
        conn.commit()
        logger.info("\n✅ Migration terminée avec succès !")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"\n❌ Erreur lors de la migration : {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🚀 MIGRATION : Système de paiement Stripe")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if migrate_database():
        logger.info("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("✅ MIGRATION RÉUSSIE")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("\n📝 PROCHAINES ÉTAPES :")
        logger.info("  1. Créer un compte Stripe sur stripe.com")
        logger.info("  2. Récupérer vos clés API (Test et Production)")
        logger.info("  3. Les ajouter dans l'interface Paramètres de l'app")
        logger.info("  4. Tester un paiement en mode test")
        logger.info("\n💡 Les champs suivants ont été ajoutés :")
        logger.info("  • Factures : acompte_requis, acompte_pourcentage, acompte_montant")
        logger.info("  • Devis : acompte_requis, acompte_pourcentage, acompte_montant")
        logger.info("  • Nouvelle table : paiements (suivi complet)")
    else:
        logger.info("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.error("❌ MIGRATION ÉCHOUÉE")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


