#!/usr/bin/env python3
"""
Système d'export Excel pour les rapports
"""

import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
from flask import make_response
import os
import logging
logger = logging.getLogger(__name__)

class ExcelExporter:
    def __init__(self):
        self.output_dir = 'exports'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def export_prestations(self, prestations, filename=None):
        """Export des prestations en Excel"""
        if not filename:
            filename = f"prestations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Préparation des données
        data = []
        for prestation in prestations:
            data.append({
                'ID': prestation.id,
                'Client': prestation.client,
                'Date': prestation.date_debut.strftime('%d/%m/%Y'),
                'Heure début': prestation.heure_debut.strftime('%H:%M'),
                'Heure fin': prestation.heure_fin.strftime('%H:%M'),
                'Lieu': prestation.lieu,
                'DJ': prestation.dj.nom if prestation.dj else 'Non assigné',
                'Statut': prestation.statut,
                'Notes': prestation.notes or '',
                'Date création': prestation.date_creation.strftime('%d/%m/%Y %H:%M')
            })
        
        # Création du DataFrame
        df = pd.DataFrame(data)
        
        # Création du fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille principale
            df.to_excel(writer, sheet_name='Prestations', index=False)
            
            # Feuille de statistiques
            stats_data = {
                'Métrique': ['Total prestations', 'Prestations confirmées', 'Prestations planifiées'],
                'Valeur': [
                    len(prestations),
                    len([p for p in prestations if p.statut == 'confirmee']),
                    len([p for p in prestations if p.statut == 'planifiee'])
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
        
        output.seek(0)
        return output.getvalue(), filename
    
    def export_materiels(self, materiels, filename=None):
        """Export du matériel en Excel"""
        if not filename:
            filename = f"materiels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Préparation des données
        data = []
        for materiel in materiels:
            date_creation = getattr(materiel, 'date_creation', None)
            data.append({
                'ID': materiel.id,
                'Nom': materiel.nom,
                'Catégorie': materiel.categorie,
                'Quantité': materiel.quantite,
                'Statut': materiel.statut,
                'Local': materiel.local.nom if materiel.local else 'Non assigné',
                'Notes': materiel.notes_technicien or '',
                'Date création': date_creation.strftime('%d/%m/%Y %H:%M') if date_creation else ''
            })
        
        # Création du DataFrame
        df = pd.DataFrame(data)
        
        # Création du fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille principale
            df.to_excel(writer, sheet_name='Matériel', index=False)
            
            # Feuille de statistiques
            stats_data = {
                'Statut': ['Disponible', 'Maintenance', 'Hors service'],
                'Quantité': [
                    len([m for m in materiels if m.statut == 'disponible']),
                    len([m for m in materiels if m.statut == 'maintenance']),
                    len([m for m in materiels if m.statut == 'hors_service'])
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
        
        output.seek(0)
        return output.getvalue(), filename
    
    def export_djs(self, djs, filename=None):
        """Export des DJs en Excel"""
        if not filename:
            filename = f"djs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Préparation des données
        data = []
        for dj in djs:
            date_creation = getattr(dj, 'date_creation', None)
            data.append({
                'ID': dj.id,
                'Nom': dj.nom,
                'Email': dj.email or '',
                'Téléphone': dj.telephone or '',
                'Spécialités': dj.specialites or '',
                'Notes': dj.notes or '',
                'Date création': date_creation.strftime('%d/%m/%Y %H:%M') if date_creation else ''
            })
        
        # Création du DataFrame
        df = pd.DataFrame(data)
        
        # Création du fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='DJs', index=False)
        
        output.seek(0)
        return output.getvalue(), filename
    
    def export_devis(self, devis, filename=None):
        """Export des devis en Excel"""
        if not filename:
            filename = f"devis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Préparation des données
        data = []
        for devi in devis:
            data.append({
                'ID': devi.id,
                'Numéro': devi.numero,
                'Client': devi.client_nom,
                'Email': devi.client_email or '',
                'Téléphone': devi.client_telephone or '',
                'SIREN Client': getattr(devi, 'client_siren', '') or '',
                'TVA Client': getattr(devi, 'client_tva', '') or '',
                'Bon de commande': getattr(devi, 'numero_bon_commande', '') or '',
                'Client Professionnel': 'Oui' if getattr(devi, 'client_professionnel', False) else 'Non',
                'Adresse Livraison': getattr(devi, 'adresse_livraison', '') or '',
                'Nature Opération': getattr(devi, 'nature_operation', '') or '',
                'TVA sur débits': 'Oui' if getattr(devi, 'tva_sur_debits', False) else 'Non',
                'TVA incluse': 'Oui' if (getattr(devi, 'tva_incluse', None) is None or getattr(devi, 'tva_incluse', False)) else 'Non',
                'Prestation': devi.prestation_titre,
                'Date prestation': devi.date_prestation.strftime('%d/%m/%Y'),
                'Lieu': devi.lieu,
                'Montant HT': f"{devi.montant_ht:.2f}€",
                'TVA': f"{devi.montant_tva:.2f}€",
                'Montant TTC': f"{devi.montant_ttc:.2f}€",
                'Statut': devi.statut,
                'Date création': devi.date_creation.strftime('%d/%m/%Y %H:%M')
            })
        
        # Création du DataFrame
        df = pd.DataFrame(data)
        
        # Création du fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille principale
            df.to_excel(writer, sheet_name='Devis', index=False)
            
            # Feuille de statistiques
            stats_data = {
                'Statut': ['Brouillon', 'Envoyé', 'Accepté', 'Refusé'],
                'Quantité': [
                    len([d for d in devis if d.statut == 'brouillon']),
                    len([d for d in devis if d.statut == 'envoye']),
                    len([d for d in devis if d.statut == 'accepte']),
                    len([d for d in devis if d.statut == 'refuse'])
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
        
        output.seek(0)
        return output.getvalue(), filename
    
    def export_rapport_complet(self, start_date, end_date):
        """Export d'un rapport complet sur une période"""
        filename = f"rapport_complet_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        
        # Import des modèles
        from app import Prestation, Materiel, DJ, Devis
        
        # Récupération des données
        prestations = Prestation.query.filter(
            Prestation.date_debut.between(start_date, end_date)
        ).all()
        
        materiels = Materiel.query.all()
        djs = DJ.query.all()
        devis = Devis.query.filter(
            Devis.date_creation.between(start_date, end_date)
        ).all()
        
        # Création du fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille Prestations
            prestations_data = []
            for p in prestations:
                prestations_data.append({
                    'ID': p.id,
                    'Client': p.client,
                    'Date': p.date_debut.strftime('%d/%m/%Y'),
                    'Heure': f"{p.heure_debut.strftime('%H:%M')} - {p.heure_fin.strftime('%H:%M')}",
                    'Lieu': p.lieu,
                    'DJ': p.dj.nom if p.dj else 'Non assigné',
                    'Statut': p.statut
                })
            
            if prestations_data:
                pd.DataFrame(prestations_data).to_excel(writer, sheet_name='Prestations', index=False)
            
            # Feuille Matériel
            materiels_data = []
            for m in materiels:
                materiels_data.append({
                    'ID': m.id,
                    'Nom': m.nom,
                    'Catégorie': m.categorie,
                    'Quantité': m.quantite,
                    'Statut': m.statut,
                    'Local': m.local.nom if m.local else 'Non assigné'
                })
            
            if materiels_data:
                pd.DataFrame(materiels_data).to_excel(writer, sheet_name='Matériel', index=False)
            
            # Feuille DJs
            djs_data = []
            for d in djs:
                djs_data.append({
                    'ID': d.id,
                    'Nom': d.nom,
                    'Email': d.email or '',
                    'Téléphone': d.telephone or ''
                })
            
            if djs_data:
                pd.DataFrame(djs_data).to_excel(writer, sheet_name='DJs', index=False)
            
            # Feuille Devis
            devis_data = []
            for d in devis:
                devis_data.append({
                    'ID': d.id,
                    'Numéro': d.numero,
                    'Client': d.client_nom,
                    'Montant TTC': f"{d.montant_ttc:.2f}€",
                    'Statut': d.statut
                })
            
            if devis_data:
                pd.DataFrame(devis_data).to_excel(writer, sheet_name='Devis', index=False)
            
            # Feuille Résumé
            resume_data = {
                'Métrique': [
                    'Période',
                    'Prestations totales',
                    'Prestations confirmées',
                    'Matériel disponible',
                    'Matériel en maintenance',
                    'DJs actifs',
                    'Devis envoyés',
                    'CA estimé'
                ],
                'Valeur': [
                    f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
                    len(prestations),
                    len([p for p in prestations if p.statut == 'confirmee']),
                    len([m for m in materiels if m.statut == 'disponible']),
                    len([m for m in materiels if m.statut == 'maintenance']),
                    len(djs),
                    len([d for d in devis if d.statut == 'envoye']),
                    f"{sum(d.montant_ttc for d in devis):.2f}€"
                ]
            }
            
            pd.DataFrame(resume_data).to_excel(writer, sheet_name='Résumé', index=False)
        
        output.seek(0)
        return output.getvalue(), filename
    
    def export_clients_data(self, clients_data):
        """Export des données clients en Excel"""
        # Création du DataFrame
        df = pd.DataFrame(clients_data)
        
        # Création du fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille principale des clients
            df.to_excel(writer, sheet_name='Données Clients', index=False)
            
            # Feuille de statistiques
            stats_data = {
                'Métrique': [
                    'Total clients',
                    'Clients avec téléphone',
                    'Clients avec email',
                    'Clients avec téléphone et email',
                    'Moyenne prestations par client'
                ],
                'Valeur': [
                    len(clients_data),
                    len([c for c in clients_data if c['Téléphone']]),
                    len([c for c in clients_data if c['Email']]),
                    len([c for c in clients_data if c['Téléphone'] and c['Email']]),
                    round(sum(c['Nombre de prestations'] for c in clients_data) / len(clients_data), 2) if clients_data else 0
                ]
            }
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
            
            # Feuille des lieux les plus fréquents
            lieux_data = {}
            for client in clients_data:
                lieux = client['Lieux'].split(', ')
                for lieu in lieux:
                    if lieu.strip():
                        lieux_data[lieu.strip()] = lieux_data.get(lieu.strip(), 0) + 1
            
            lieux_df = pd.DataFrame([
                {'Lieu': lieu, 'Nombre de clients': count}
                for lieu, count in sorted(lieux_data.items(), key=lambda x: x[1], reverse=True)
            ])
            lieux_df.to_excel(writer, sheet_name='Lieux', index=False)
        
        output.seek(0)
        return output.getvalue()
    
    def export_factures(self, factures):
        """Export des factures en Excel"""
        # Préparation des données
        data = []
        for facture in factures:
            data.append({
                'Numéro': facture.numero,
                'Client': facture.client_nom,
                'Email': facture.client_email or '',
                'Téléphone': facture.client_telephone or '',
                'Client Professionnel': 'Oui' if getattr(facture, 'client_professionnel', False) else 'Non',
                'SIREN Client': getattr(facture, 'client_siren', '') or '',
                'TVA Client': getattr(facture, 'client_tva', '') or '',
                'Bon de commande': getattr(facture, 'numero_bon_commande', '') or '',
                'Adresse Livraison': getattr(facture, 'adresse_livraison', '') or '',
                'Nature Opération': getattr(facture, 'nature_operation', '') or '',
                'TVA sur débits': 'Oui' if getattr(facture, 'tva_sur_debits', False) else 'Non',
                'Prestation': facture.prestation_titre,
                'Date Prestation': facture.date_prestation.strftime('%d/%m/%Y'),
                'Lieu': facture.lieu,
                'DJ': facture.dj.nom if facture.dj else '',
                'Tarif Horaire': facture.tarif_horaire,
                'Durée (h)': facture.duree_heures,
                'Frais Transport': facture.frais_transport,
                'Frais Matériel': facture.frais_materiel,
                'Remise (%)': facture.remise_pourcentage,
                'Remise (€)': facture.remise_montant,
                'Montant HT': facture.montant_ht,
                'Taux TVA (%)': facture.taux_tva,
                'Montant TVA': facture.montant_tva,
                'Montant TTC': facture.montant_ttc,
                'Montant Payé': facture.montant_paye,
                'Montant Restant': facture.montant_restant,
                'Statut': facture.statut.title(),
                'Date Création': facture.date_creation.strftime('%d/%m/%Y %H:%M'),
                'Date Échéance': facture.date_echeance.strftime('%d/%m/%Y') if facture.date_echeance else '',
                'Date Paiement': facture.date_paiement.strftime('%d/%m/%Y') if facture.date_paiement else '',
                'Mode Paiement': facture.mode_paiement or '',
                'Référence Paiement': facture.reference_paiement or '',
                'Conditions Paiement': facture.conditions_paiement or '',
                'Notes': facture.notes or ''
            })
        
        # Création du DataFrame
        df = pd.DataFrame(data)
        
        # Création du fichier Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Feuille principale des factures
            df.to_excel(writer, sheet_name='Factures', index=False)
            
            # Feuille de statistiques
            total_factures = len(factures)
            factures_payees = len([f for f in factures if f.statut == 'payee'])
            factures_en_attente = len([f for f in factures if f.statut == 'envoyee'])
            factures_en_retard = len([f for f in factures if f.est_en_retard])
            montant_total = sum(f.montant_ttc for f in factures)
            montant_paye = sum(f.montant_paye for f in factures)
            montant_restant = sum(f.montant_restant for f in factures)
            
            stats_data = {
                'Métrique': [
                    'Total factures',
                    'Factures payées',
                    'Factures en attente',
                    'Factures en retard',
                    'Montant total TTC',
                    'Montant payé',
                    'Montant restant à payer'
                ],
                'Valeur': [
                    total_factures,
                    factures_payees,
                    factures_en_attente,
                    factures_en_retard,
                    f"{montant_total:.2f}€",
                    f"{montant_paye:.2f}€",
                    f"{montant_restant:.2f}€"
                ]
            }
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
            
            # Feuille par statut
            statuts = {}
            for facture in factures:
                statut = facture.statut
                if statut not in statuts:
                    statuts[statut] = []
                statuts[statut].append(facture)
            
            for statut, factures_statut in statuts.items():
                statut_data = []
                for facture in factures_statut:
                    statut_data.append({
                        'Numéro': facture.numero,
                        'Client': facture.client_nom,
                        'Montant TTC': facture.montant_ttc,
                        'Montant Payé': facture.montant_paye,
                        'Date Échéance': facture.date_echeance.strftime('%d/%m/%Y') if facture.date_echeance else '',
                        'Date Création': facture.date_creation.strftime('%d/%m/%Y')
                    })
                
                statut_df = pd.DataFrame(statut_data)
                sheet_name = f"Factures {statut.title()}"[:31]  # Limite de 31 caractères
                statut_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Nom du fichier
        filename = f"factures_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return output.getvalue(), filename

# Instance globale
excel_exporter = ExcelExporter()
