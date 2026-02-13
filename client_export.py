#!/usr/bin/env python3
"""
Fichier client pour l'export des données
Permet d'exporter toutes les données de l'application vers des formats externes
"""

import os
import sys
import json
import csv
import sqlite3
from datetime import datetime
import pandas as pd

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import *
import logging
logger = logging.getLogger(__name__)

class ClientExport:
    """Classe pour exporter les données de l'application"""
    
    def __init__(self, db_path=None):
        """Initialiser l'export avec le chemin de la base de données"""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
        self.db_path = db_path
        self.export_dir = os.path.join(os.path.dirname(__file__), 'exports')
        
        # Créer le dossier d'export s'il n'existe pas
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_all_data(self, format='json'):
        """Exporter toutes les données de l'application"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with app.app_context():
            # Récupérer toutes les données
            data = {
                'export_info': {
                    'date_export': datetime.now().isoformat(),
                    'version': '2.1',
                    'format': format
                },
                'parametres_entreprise': self._get_parametres_entreprise(),
                'users': self._get_users(),
                'djs': self._get_djs(),
                'locals': self._get_locals(),
                'materiels': self._get_materiels(),
                'prestations': self._get_prestations(),
                'devis': self._get_devis(),
                'materiel_presta': self._get_materiel_presta()
            }
            
            if format == 'json':
                filename = f'export_complet_{timestamp}.json'
                filepath = os.path.join(self.export_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            elif format == 'csv':
                # Exporter chaque table en CSV séparé
                for table_name, table_data in data.items():
                    if table_name != 'export_info' and isinstance(table_data, list):
                        filename = f'export_{table_name}_{timestamp}.csv'
                        filepath = os.path.join(self.export_dir, filename)
                        self._export_to_csv(table_data, filepath)
            
            elif format == 'excel':
                filename = f'export_complet_{timestamp}.xlsx'
                filepath = os.path.join(self.export_dir, filename)
                self._export_to_excel(data, filepath)
            
            return filepath
    
    def _get_parametres_entreprise(self):
        """Récupérer les paramètres d'entreprise"""
        try:
            parametres = ParametresEntreprise.query.first()
            if parametres:
                return {
                    'id': parametres.id,
                    'nom_entreprise': parametres.nom_entreprise,
                    'adresse': parametres.adresse,
                    'code_postal': parametres.code_postal,
                    'ville': parametres.ville,
                    'telephone': parametres.telephone,
                    'email': parametres.email,
                    'site_web': parametres.site_web,
                    'siret': parametres.siret,
                    'tva_intracommunautaire': parametres.tva_intracommunautaire,
                    'couleur_principale': parametres.couleur_principale,
                    'couleur_secondaire': parametres.couleur_secondaire,
                    'devise': parametres.devise,
                    'langue': parametres.langue,
                    'date_creation': parametres.date_creation.isoformat() if parametres.date_creation else None,
                    'date_modification': parametres.date_modification.isoformat() if parametres.date_modification else None
                }
        except:
            pass
        return {}
    
    def _get_users(self):
        """Récupérer tous les utilisateurs"""
        users = User.query.all()
        return [{
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'is_active': user.is_active,
            'date_creation': user.date_creation.isoformat() if user.date_creation else None
        } for user in users]
    
    def _get_djs(self):
        """Récupérer tous les DJs"""
        djs = DJ.query.all()
        return [{
            'id': dj.id,
            'nom': dj.nom,
            'contact': dj.contact,
            'notes': dj.notes,
            'user_id': dj.user_id
        } for dj in djs]
    
    def _get_locals(self):
        """Récupérer tous les locaux"""
        locals = Local.query.all()
        return [{
            'id': local.id,
            'nom': local.nom,
            'adresse': local.adresse
        } for local in locals]
    
    def _get_materiels(self):
        """Récupérer tous les matériels"""
        materiels = Materiel.query.all()
        return [{
            'id': materiel.id,
            'nom': materiel.nom,
            'categorie': materiel.categorie,
            'quantite': materiel.quantite,
            'statut': materiel.statut,
            'local_id': materiel.local_id,
            'date_creation': getattr(materiel, 'date_creation', None).isoformat() if getattr(materiel, 'date_creation', None) else None
        } for materiel in materiels]
    
    def _get_prestations(self):
        """Récupérer toutes les prestations"""
        prestations = Prestation.query.all()
        return [{
            'id': prestation.id,
            'client': prestation.client,
            'lieu': prestation.lieu,
            'date_debut': prestation.date_debut.isoformat() if prestation.date_debut else None,
            'date_fin': prestation.date_fin.isoformat() if prestation.date_fin else None,
            'heure_debut': prestation.heure_debut.isoformat() if prestation.heure_debut else None,
            'heure_fin': prestation.heure_fin.isoformat() if prestation.heure_fin else None,
            'dj_id': prestation.dj_id,
            'createur_id': prestation.createur_id,
            'notes': prestation.notes,
            'statut': prestation.statut,
            'date_creation': prestation.date_creation.isoformat() if prestation.date_creation else None,
            'date_modification': prestation.date_modification.isoformat() if prestation.date_modification else None
        } for prestation in prestations]
    
    def _get_devis(self):
        """Récupérer tous les devis"""
        devis = Devis.query.all()
        return [{
            'id': devis_item.id,
            'numero': devis_item.numero,
            'client_nom': devis_item.client_nom,
            'client_email': devis_item.client_email,
            'client_telephone': devis_item.client_telephone,
            'client_adresse': devis_item.client_adresse,
            'prestation_titre': devis_item.prestation_titre,
            'prestation_description': devis_item.prestation_description,
            'date_prestation': devis_item.date_prestation.isoformat() if devis_item.date_prestation else None,
            'heure_debut': devis_item.heure_debut.isoformat() if devis_item.heure_debut else None,
            'heure_fin': devis_item.heure_fin.isoformat() if devis_item.heure_fin else None,
            'lieu': devis_item.lieu,
            'tarif_horaire': float(devis_item.tarif_horaire) if devis_item.tarif_horaire else 0,
            'duree_heures': float(devis_item.duree_heures) if devis_item.duree_heures else 0,
            'montant_ht': float(devis_item.montant_ht) if devis_item.montant_ht else 0,
            'taux_tva': float(devis_item.taux_tva) if devis_item.taux_tva else 0,
            'montant_tva': float(devis_item.montant_tva) if devis_item.montant_tva else 0,
            'montant_ttc': float(devis_item.montant_ttc) if devis_item.montant_ttc else 0,
            'remise_pourcentage': float(devis_item.remise_pourcentage) if devis_item.remise_pourcentage else 0,
            'remise_montant': float(devis_item.remise_montant) if devis_item.remise_montant else 0,
            'frais_transport': float(devis_item.frais_transport) if devis_item.frais_transport else 0,
            'frais_materiel': float(devis_item.frais_materiel) if devis_item.frais_materiel else 0,
            'statut': devis_item.statut,
            'date_creation': devis_item.date_creation.isoformat() if devis_item.date_creation else None,
            'date_validite': devis_item.date_validite.isoformat() if devis_item.date_validite else None,
            'date_envoi': devis_item.date_envoi.isoformat() if devis_item.date_envoi else None,
            'date_acceptation': devis_item.date_acceptation.isoformat() if devis_item.date_acceptation else None,
            'dj_id': devis_item.dj_id,
            'createur_id': devis_item.createur_id,
            'prestation_id': devis_item.prestation_id
        } for devis_item in devis]
    
    def _get_materiel_presta(self):
        """Récupérer toutes les associations matériel-prestation"""
        associations = MaterielPrestation.query.all()
        return [{
            'id': assoc.id,
            'materiel_id': assoc.materiel_id,
            'prestation_id': assoc.prestation_id,
            'quantite_utilisee': assoc.quantite_utilisee
        } for assoc in associations]
    
    def _export_to_csv(self, data, filepath):
        """Exporter des données vers un fichier CSV"""
        if not data:
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    def _export_to_excel(self, data, filepath):
        """Exporter toutes les données vers un fichier Excel"""
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for sheet_name, sheet_data in data.items():
                if sheet_name != 'export_info' and isinstance(sheet_data, list) and sheet_data:
                    df = pd.DataFrame(sheet_data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    def export_statistics(self):
        """Exporter des statistiques de l'application"""
        with app.app_context():
            stats = {
                'total_users': User.query.count(),
                'total_djs': DJ.query.count(),
                'total_locals': Local.query.count(),
                'total_materiels': Materiel.query.count(),
                'total_prestations': Prestation.query.count(),
                'total_devis': Devis.query.count(),
                'prestations_par_statut': {
                    statut: Prestation.query.filter_by(statut=statut).count()
                    for statut in ['planifiee', 'confirmee', 'terminee', 'annulee']
                },
                'devis_par_statut': {
                    statut: Devis.query.filter_by(statut=statut).count()
                    for statut in ['brouillon', 'envoye', 'accepte', 'refuse', 'expire']
                }
            }
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'statistiques_{timestamp}.json'
            filepath = os.path.join(self.export_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
            
            return filepath

def main():
    """Fonction principale pour l'export"""
    logger.info("🎵 DJ Prestations Manager - Export des données")
    logger.info("=" * 50)
    
    exporter = ClientExport()
    
    logger.info("📊 Export des statistiques...")
    stats_file = exporter.export_statistics()
    logger.info(f"✅ Statistiques exportées : {stats_file}")
    
    logger.info("\n📁 Export complet des données...")
    logger.info("1. JSON")
    logger.info("2. CSV")
    logger.info("3. Excel")
    
    choice = input("\nChoisissez le format (1-3) : ").strip()
    
    if choice == '1':
        format_type = 'json'
    elif choice == '2':
        format_type = 'csv'
    elif choice == '3':
        format_type = 'excel'
    else:
        logger.error("❌ Choix invalide, export en JSON par défaut")
        format_type = 'json'
    
    try:
        export_file = exporter.export_all_data(format_type)
        logger.info(f"✅ Export réussi : {export_file}")
        logger.info(f"📂 Fichier disponible dans : {exporter.export_dir}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export : {str(e)}")

if __name__ == '__main__':
    main()










