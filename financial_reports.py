#!/usr/bin/env python3
"""
Système de rapports financiers avancés pour Planify
"""

from datetime import datetime, date, timedelta
# Import sera fait dans les fonctions pour éviter les imports circulaires
import pandas as pd
from io import BytesIO
import json
import logging
logger = logging.getLogger(__name__)

class FinancialReportGenerator:
    """Générateur de rapports financiers avancés"""
    
    def __init__(self):
        pass
    
    def generate_revenue_report(self, start_date, end_date, dj_id=None):
        """Génère un rapport de revenus"""
        try:
            from app import app, db, Prestation
            with app.app_context():
                # Filtrer par DJ si spécifié
                if dj_id:
                    prestations = Prestation.query.filter(
                        Prestation.dj_id == dj_id,
                        Prestation.date_debut.between(start_date, end_date)
                    ).all()
                else:
                    prestations = Prestation.query.filter(
                        Prestation.date_debut.between(start_date, end_date)
                    ).all()
                
                # Calculer les revenus estimés
                total_revenue = 0
                revenue_by_dj = {}
                revenue_by_month = {}
                
                for prestation in prestations:
                    # Calculer le revenu estimé (tarif par défaut)
                    start_time = datetime.combine(prestation.date_debut, prestation.heure_debut)
                    end_time = datetime.combine(prestation.date_fin, prestation.heure_fin)
                    
                    if prestation.date_fin > prestation.date_debut:
                        end_time += timedelta(days=1)
                    
                    duration = end_time - start_time
                    hours = duration.total_seconds() / 3600
                    hourly_rate = 150.0  # €/heure par défaut
                    estimated_revenue = hours * hourly_rate
                    
                    total_revenue += estimated_revenue
                    
                    # Par DJ
                    dj_name = prestation.dj.nom if prestation.dj else 'Non assigné'
                    if dj_name not in revenue_by_dj:
                        revenue_by_dj[dj_name] = 0
                    revenue_by_dj[dj_name] += estimated_revenue
                    
                    # Par mois
                    month_key = prestation.date_debut.strftime('%Y-%m')
                    if month_key not in revenue_by_month:
                        revenue_by_month[month_key] = 0
                    revenue_by_month[month_key] += estimated_revenue
                
                return {
                    'total_revenue': total_revenue,
                    'revenue_by_dj': revenue_by_dj,
                    'revenue_by_month': revenue_by_month,
                    'prestations_count': len(prestations)
                }
                
        except Exception as e:
            logger.error(f"Erreur génération rapport revenus : {e}")
            return None
    
    def generate_profitability_report(self, start_date, end_date):
        """Génère un rapport de rentabilité"""
        try:
            from app import app, db, Prestation
            with app.app_context():
                # Récupérer les prestations
                prestations = Prestation.query.filter(
                    Prestation.date_debut.between(start_date, end_date)
                ).all()
                
                # Calculer les coûts et revenus
                total_revenue = 0
                total_costs = 0
                profitability_by_dj = {}
                
                for prestation in prestations:
                    # Revenus
                    start_time = datetime.combine(prestation.date_debut, prestation.heure_debut)
                    end_time = datetime.combine(prestation.date_fin, prestation.heure_fin)
                    
                    if prestation.date_fin > prestation.date_debut:
                        end_time += timedelta(days=1)
                    
                    duration = end_time - start_time
                    hours = duration.total_seconds() / 3600
                    hourly_rate = 150.0
                    revenue = hours * hourly_rate
                    total_revenue += revenue
                    
                    # Coûts (estimation)
                    dj_cost = hours * 50.0  # Coût DJ
                    material_cost = len(prestation.materiels) * 20.0  # Coût matériel
                    transport_cost = 30.0  # Coût transport
                    total_prestation_cost = dj_cost + material_cost + transport_cost
                    total_costs += total_prestation_cost
                    
                    # Rentabilité par DJ
                    dj_name = prestation.dj.nom if prestation.dj else 'Non assigné'
                    if dj_name not in profitability_by_dj:
                        profitability_by_dj[dj_name] = {'revenue': 0, 'costs': 0}
                    profitability_by_dj[dj_name]['revenue'] += revenue
                    profitability_by_dj[dj_name]['costs'] += total_prestation_cost
                
                # Calculer la rentabilité
                profit = total_revenue - total_costs
                profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
                
                return {
                    'total_revenue': total_revenue,
                    'total_costs': total_costs,
                    'profit': profit,
                    'profit_margin': profit_margin,
                    'profitability_by_dj': profitability_by_dj
                }
                
        except Exception as e:
            logger.error(f"Erreur génération rapport rentabilité : {e}")
            return None
    
    def generate_client_analysis(self, start_date, end_date):
        """Génère une analyse des clients"""
        try:
            from app import app, db, Prestation
            with app.app_context():
                prestations = Prestation.query.filter(
                    Prestation.date_debut.between(start_date, end_date)
                ).all()
                
                # Analyser les clients
                client_stats = {}
                client_locations = {}
                client_frequency = {}
                
                for prestation in prestations:
                    client = prestation.client
                    
                    # Statistiques par client
                    if client not in client_stats:
                        client_stats[client] = {
                            'prestations_count': 0,
                            'total_hours': 0,
                            'total_revenue': 0,
                            'first_prestation': prestation.date_debut,
                            'last_prestation': prestation.date_debut
                        }
                    
                    client_stats[client]['prestations_count'] += 1
                    
                    # Calculer les heures
                    start_time = datetime.combine(prestation.date_debut, prestation.heure_debut)
                    end_time = datetime.combine(prestation.date_fin, prestation.heure_fin)
                    
                    if prestation.date_fin > prestation.date_debut:
                        end_time += timedelta(days=1)
                    
                    duration = end_time - start_time
                    hours = duration.total_seconds() / 3600
                    client_stats[client]['total_hours'] += hours
                    
                    # Revenus
                    hourly_rate = 150.0
                    revenue = hours * hourly_rate
                    client_stats[client]['total_revenue'] += revenue
                    
                    # Mise à jour des dates
                    if prestation.date_debut < client_stats[client]['first_prestation']:
                        client_stats[client]['first_prestation'] = prestation.date_debut
                    if prestation.date_debut > client_stats[client]['last_prestation']:
                        client_stats[client]['last_prestation'] = prestation.date_debut
                    
                    # Lieux
                    location = prestation.lieu
                    if location not in client_locations:
                        client_locations[location] = 0
                    client_locations[location] += 1
                
                # Calculer la fréquence des clients
                for client, stats in client_stats.items():
                    days_between = (stats['last_prestation'] - stats['first_prestation']).days
                    if days_between > 0:
                        frequency = stats['prestations_count'] / (days_between / 30)  # Prestations par mois
                    else:
                        frequency = stats['prestations_count']
                    client_frequency[client] = frequency
                
                # Top clients
                top_clients = sorted(client_stats.items(), 
                                   key=lambda x: x[1]['total_revenue'], 
                                   reverse=True)[:10]
                
                return {
                    'client_stats': client_stats,
                    'client_locations': client_locations,
                    'client_frequency': client_frequency,
                    'top_clients': top_clients,
                    'total_clients': len(client_stats)
                }
                
        except Exception as e:
            logger.error(f"Erreur génération analyse clients : {e}")
            return None
    
    def generate_performance_report(self, start_date, end_date):
        """Génère un rapport de performance des DJs"""
        try:
            from app import app, db, Prestation, DJ
            with app.app_context():
                djs = DJ.query.all()
                dj_performance = {}
                
                for dj in djs:
                    # Prestations du DJ
                    prestations = Prestation.query.filter(
                        Prestation.dj_id == dj.id,
                        Prestation.date_debut.between(start_date, end_date)
                    ).all()
                    
                    if not prestations:
                        continue
                    
                    # Calculer les métriques
                    total_hours = 0
                    total_revenue = 0
                    confirmed_prestations = 0
                    cancelled_prestations = 0
                    
                    for prestation in prestations:
                        # Heures
                        start_time = datetime.combine(prestation.date_debut, prestation.heure_debut)
                        end_time = datetime.combine(prestation.date_fin, prestation.heure_fin)
                        
                        if prestation.date_fin > prestation.date_debut:
                            end_time += timedelta(days=1)
                        
                        duration = end_time - start_time
                        hours = duration.total_seconds() / 3600
                        total_hours += hours
                        
                        # Revenus
                        hourly_rate = 150.0
                        revenue = hours * hourly_rate
                        total_revenue += revenue
                        
                        # Statuts
                        if prestation.statut == 'confirmee':
                            confirmed_prestations += 1
                        elif prestation.statut == 'annulee':
                            cancelled_prestations += 1
                    
                    # Calculer les ratios
                    total_prestations = len(prestations)
                    confirmation_rate = (confirmed_prestations / total_prestations * 100) if total_prestations > 0 else 0
                    cancellation_rate = (cancelled_prestations / total_prestations * 100) if total_prestations > 0 else 0
                    avg_hours_per_prestation = total_hours / total_prestations if total_prestations > 0 else 0
                    revenue_per_hour = total_revenue / total_hours if total_hours > 0 else 0
                    
                    dj_performance[dj.nom] = {
                        'total_prestations': total_prestations,
                        'total_hours': total_hours,
                        'total_revenue': total_revenue,
                        'confirmed_prestations': confirmed_prestations,
                        'cancelled_prestations': cancelled_prestations,
                        'confirmation_rate': confirmation_rate,
                        'cancellation_rate': cancellation_rate,
                        'avg_hours_per_prestation': avg_hours_per_prestation,
                        'revenue_per_hour': revenue_per_hour
                    }
                
                # Trier par revenus
                sorted_djs = sorted(dj_performance.items(), 
                                 key=lambda x: x[1]['total_revenue'], 
                                 reverse=True)
                
                return {
                    'dj_performance': dj_performance,
                    'sorted_djs': sorted_djs,
                    'total_djs': len(dj_performance)
                }
                
        except Exception as e:
            logger.error(f"Erreur génération rapport performance : {e}")
            return None
    
    def generate_comprehensive_report(self, start_date, end_date):
        """Génère un rapport complet"""
        try:
            # Générer tous les rapports
            revenue_report = self.generate_revenue_report(start_date, end_date)
            profitability_report = self.generate_profitability_report(start_date, end_date)
            client_analysis = self.generate_client_analysis(start_date, end_date)
            performance_report = self.generate_performance_report(start_date, end_date)
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': (end_date - start_date).days
                },
                'revenue': revenue_report,
                'profitability': profitability_report,
                'clients': client_analysis,
                'performance': performance_report,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur génération rapport complet : {e}")
            return None

# Instance globale
financial_report_generator = FinancialReportGenerator()
