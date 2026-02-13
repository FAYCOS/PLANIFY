#!/usr/bin/env python3
"""
IA Intelligente pour Planify v3.0
Fonctionnalités pratiques sans analyse de sentiment
"""

import os
import json
import logging
from datetime import datetime, timedelta, date
from collections import Counter
import statistics

logger = logging.getLogger(__name__)


class SmartAssistant:
    """Assistant IA avec fonctionnalités pratiques"""
    
    def __init__(self, app=None, db=None):
        self.app = app
        self.db = db
    
    # ==================== PRÉDICTIONS DE PRIX ====================
    
    def predict_optimal_price(self, type_evenement, nombre_invites, mois, duree_heures):
        """
        Prédit le prix optimal basé sur l'historique
        """
        try:
            from app import Devis, Facture

            def _extract_price(item):
                if getattr(item, 'montant_ttc', None):
                    return float(item.montant_ttc)
                if getattr(item, 'tarif_horaire', None) and getattr(item, 'duree_heures', None):
                    return float(item.tarif_horaire) * float(item.duree_heures)
                return None

            def _match_type(text):
                return bool(type_evenement and text and type_evenement.lower() in text.lower())
            
            # Récupérer les prestations similaires
            with self.app.app_context():
                devis = Devis.query.filter(
                    Devis.statut.in_(['accepte', 'envoye', 'brouillon'])
                ).all()
                factures = Facture.query.filter(
                    Facture.statut.in_(['payee', 'envoyee', 'partiellement_payee'])
                ).all()
                
                # Filtrer par critères similaires (titre/description)
                similar = []
                for item in devis + factures:
                    if _match_type(getattr(item, 'prestation_titre', None)) or _match_type(getattr(item, 'prestation_description', None)):
                        price = _extract_price(item)
                        if price:
                            similar.append(price)
                
                if not similar:
                    # Prix par défaut selon type
                    base_prices = {
                        'mariage': 585,
                        'anniversaire': 400,
                        'soirée entreprise': 1000,
                        'festival': 2000,
                        'bar': 300,
                        'club': 400
                    }
                    if type_evenement:
                        default_price = base_prices.get(type_evenement.lower())
                        if default_price:
                            return default_price
                    # Fallback sur historique global si possible
                    all_prices = [_extract_price(item) for item in devis + factures]
                    all_prices = [p for p in all_prices if p]
                    if all_prices:
                        similar = all_prices
                    else:
                        return 1000
                
                # Calculer prix moyen + ajustements
                prix_moyen = statistics.mean(similar)
                
                # Ajustement selon saison (été +20%, hiver -10%)
                if mois in [6, 7, 8]:
                    prix_moyen *= 1.20
                elif mois in [12, 1, 2]:
                    prix_moyen *= 0.90
                
                # Ajustement selon nombre d'invités
                if nombre_invites > 200:
                    prix_moyen *= 1.15
                elif nombre_invites < 50:
                    prix_moyen *= 0.85
                
                # Ajustement selon durée
                prix_moyen *= (duree_heures / 4)  # Base 4h
                
                return round(prix_moyen, 2)
        except Exception as e:
            logger.error(f"❌ Erreur prédiction prix: {e}")
            return 1000
    
    # ==================== AUTO-ASSIGNATION PRESTATAIRES ====================
    
    def suggest_best_dj(self, date_prestation, style_musical, localisation=None):
        """
        Suggère le meilleur prestataire disponible selon critères
        """
        try:
            from app import DJ, Prestation
            
            with self.app.app_context():
                djs = DJ.query.all()
                
                # Scorer chaque prestataire
                scores = {}
                for dj in djs:
                    if dj.user and not dj.user.actif:
                        continue
                    score = 0
                    
                    # Vérifier disponibilité
                    prestations = Prestation.query.filter(
                        Prestation.dj_id == dj.id,
                        Prestation.date_debut == date_prestation,
                        Prestation.statut != 'annulee'
                    ).all()
                    
                    if prestations:
                        continue  # Prestataire non disponible
                    
                    # Points pour spécialité musicale
                    if dj.specialite_musicale and style_musical:
                        if style_musical.lower() in dj.specialite_musicale.lower():
                            score += 50
                    
                    # Points pour expérience (nombre de prestations)
                    nb_prestations = Prestation.query.filter_by(
                        dj_id=dj.id,
                        statut='terminee'
                    ).count()
                    score += min(nb_prestations, 30)  # Max 30 points
                    
                    # Points pour évaluation moyenne (si disponible)
                    if hasattr(dj, 'evaluation_moyenne') and dj.evaluation_moyenne:
                        score += (dj.evaluation_moyenne / 5) * 20
                    
                    scores[dj.id] = {
                        'dj': dj,
                        'score': score
                    }
                
                if not scores:
                    return None
                
                # Retourner le prestataire avec le meilleur score
                best = max(scores.items(), key=lambda x: x[1]['score'])
                return best[1]['dj']
                
        except Exception as e:
            logger.error(f"❌ Erreur suggestion prestataire: {e}")
            return None
    
    # ==================== RECOMMANDATIONS MATÉRIEL ====================
    
    def recommend_equipment(self, type_evenement, nombre_invites, duree_heures):
        """
        Recommande le matériel nécessaire selon l'événement
        """
        recommendations = []
        
        # Base selon type d'événement
        event_mapping = {
            'mariage': {
                'obligatoire': ['Sonorisation complète', 'Micro sans fil', 'Éclairage LED'],
                'optionnel': ['Projecteur gobo', 'Machine à fumée', 'Écran LED']
            },
            'anniversaire': {
                'obligatoire': ['Sonorisation', 'Éclairage de base'],
                'optionnel': ['Karaoké', 'Machine à fumée']
            },
            'soirée entreprise': {
                'obligatoire': ['Sonorisation professionnelle', 'Éclairage LED', 'Micro filaire'],
                'optionnel': ['Vidéoprojecteur', 'Écran']
            },
            'festival': {
                'obligatoire': ['Sonorisation haute puissance', 'Éclairage scénique', 'Praticables'],
                'optionnel': ['Lasers', 'LED wall', 'Effets spéciaux']
            }
        }
        
        # Récupérer recommandations par défaut
        default = event_mapping.get(type_evenement.lower(), {
            'obligatoire': ['Sonorisation', 'Éclairage'],
            'optionnel': []
        })
        
        recommendations.extend([
            {'nom': item, 'priorite': 'haute', 'raison': 'Indispensable pour ce type d\'événement'}
            for item in default['obligatoire']
        ])
        
        # Ajustements selon nombre d'invités
        if nombre_invites > 200:
            recommendations.append({
                'nom': 'Sonorisation renforcée',
                'priorite': 'haute',
                'raison': f'Plus de {nombre_invites} invités'
            })
        
        if nombre_invites > 100:
            recommendations.append({
                'nom': 'Double éclairage',
                'priorite': 'moyenne',
                'raison': 'Grande salle recommandée'
            })
        
        # Ajustements selon durée
        if duree_heures > 6:
            recommendations.append({
                'nom': 'Matériel de secours',
                'priorite': 'moyenne',
                'raison': 'Longue durée (backup recommandé)'
            })
        
        return recommendations
    
    # ==================== DÉTECTION DE CONFLITS ====================
    
    def detect_conflicts(self, date, heure_debut, heure_fin, materiel_ids=None, dj_id=None, exclude_prestation_id=None):
        """
        Détecte les conflits de planning
        """
        conflicts = []
        
        try:
            from app import Prestation
            
            with self.app.app_context():
                # Vérifier prestations à la même date
                prestations = Prestation.query.filter(
                    Prestation.date_debut == date,
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).all()
                
                if exclude_prestation_id:
                    prestations = [p for p in prestations if p.id != exclude_prestation_id]
                
                for prestation in prestations:
                    # Conflit prestataire
                    if dj_id and prestation.dj_id == dj_id:
                        if self._horaires_overlap(
                            heure_debut, heure_fin,
                            prestation.heure_debut, prestation.heure_fin
                        ):
                            conflicts.append({
                                'type': 'dj',
                                'message': f"Prestataire déjà réservé pour {prestation.client} ({prestation.heure_debut}-{prestation.heure_fin})",
                                'prestation': prestation
                            })
                    
                    # Conflit matériel
                    if materiel_ids and prestation.materiels:
                        materiel_commun = set(materiel_ids) & set([m.id for m in prestation.materiels])
                        if materiel_commun:
                            if self._horaires_overlap(
                                heure_debut, heure_fin,
                                prestation.heure_debut, prestation.heure_fin
                            ):
                                conflicts.append({
                                    'type': 'materiel',
                                    'message': f"Matériel déjà réservé pour {prestation.client}",
                                    'prestation': prestation,
                                    'materiel_ids': list(materiel_commun)
                                })
        except Exception as e:
            logger.error(f"❌ Erreur détection conflits: {e}")
        
        return conflicts
    
    def _horaires_overlap(self, debut1, fin1, debut2, fin2):
        """Vérifie si deux plages horaires se chevauchent"""
        if not all([debut1, fin1, debut2, fin2]):
            return False
        
        # Convertir en objets time si nécessaire
        if isinstance(debut1, str):
            debut1 = datetime.strptime(debut1, '%H:%M').time()
        if isinstance(fin1, str):
            fin1 = datetime.strptime(fin1, '%H:%M').time()
        if isinstance(debut2, str):
            debut2 = datetime.strptime(debut2, '%H:%M').time()
        if isinstance(fin2, str):
            fin2 = datetime.strptime(fin2, '%H:%M').time()
        
        return not (fin1 <= debut2 or debut1 >= fin2)
    
    # ==================== PRÉVISIONS CHIFFRE D'AFFAIRES ====================
    
    def forecast_revenue(self, mois_ahead=3):
        """
        Prévoit le chiffre d'affaires pour les prochains mois
        """
        try:
            from app import Facture, Devis
            
            with self.app.app_context():
                # Récupérer l'historique des 12 derniers mois
                date_limite = datetime.now().date() - timedelta(days=365)
                
                factures = Facture.query.filter(
                    Facture.date_prestation >= date_limite,
                    Facture.statut.in_(['payee', 'envoyee', 'partiellement_payee'])
                ).all()
                if not factures:
                    factures = Facture.query.filter(
                        Facture.date_creation >= datetime.now() - timedelta(days=365)
                    ).all()
                
                # Grouper par mois
                monthly_revenue = {}
                for f in factures:
                    ref_date = f.date_prestation or f.date_creation.date()
                    mois_key = ref_date.strftime('%Y-%m')
                    monthly_revenue[mois_key] = monthly_revenue.get(mois_key, 0) + float(f.montant_ttc or 0)

                if not monthly_revenue:
                    devis = Devis.query.filter(
                        Devis.date_prestation >= date_limite,
                        Devis.statut.in_(['accepte', 'envoye'])
                    ).all()
                    for d in devis:
                        mois_key = d.date_prestation.strftime('%Y-%m')
                        monthly_revenue[mois_key] = monthly_revenue.get(mois_key, 0) + float(d.montant_ttc or 0)
                
                if not monthly_revenue:
                    return []
                
                # Calculer moyenne mobile
                values = list(monthly_revenue.values())
                avg_monthly = statistics.mean(values)
                
                # Générer prévisions
                forecasts = []
                current_date = datetime.now()
                
                for i in range(mois_ahead):
                    future_date = current_date + timedelta(days=30 * (i + 1))
                    mois = future_date.month
                    
                    # Ajustements saisonniers
                    seasonal_factor = 1.0
                    if mois in [6, 7, 8, 12]:  # Haute saison
                        seasonal_factor = 1.3
                    elif mois in [1, 2, 11]:  # Basse saison
                        seasonal_factor = 0.7
                    
                    forecast_value = avg_monthly * seasonal_factor
                    
                    forecasts.append({
                        'mois': future_date.strftime('%B %Y'),
                        'prevision': round(forecast_value, 2),
                        'confiance': 'moyenne' if i < 2 else 'faible'
                    })
                
                return forecasts
                
        except Exception as e:
            logger.error(f"❌ Erreur prévision CA: {e}")
            return []
    
    # ==================== SUGGESTIONS PRESTATIONS SIMILAIRES ====================
    
    def suggest_similar_events(self, type_evenement, localisation=None, limit=5):
        """
        Suggère des prestations similaires (pour s'inspirer)
        """
        try:
            from app import Devis, Facture
            
            with self.app.app_context():
                def _match_text(text):
                    return bool(type_evenement and text and type_evenement.lower() in text.lower())

                suggestions = []
                devis = Devis.query.order_by(Devis.date_prestation.desc()).limit(limit * 2).all()
                factures = Facture.query.order_by(Facture.date_prestation.desc()).limit(limit * 2).all()

                for item in devis + factures:
                    if type_evenement and not (_match_text(getattr(item, 'prestation_titre', None)) or _match_text(getattr(item, 'prestation_description', None))):
                        continue
                    if localisation and localisation.lower() not in (getattr(item, 'lieu', '') or '').lower():
                        continue
                    suggestions.append({
                        'nom': getattr(item, 'prestation_titre', 'Prestation'),
                        'type': getattr(item, 'prestation_titre', None),
                        'tarif': float(getattr(item, 'montant_ttc', 0) or 0),
                        'materiels': [],
                        'dj': item.dj.nom if getattr(item, 'dj', None) else None
                    })
                    if len(suggestions) >= limit:
                        break

                return suggestions
                
        except Exception as e:
            logger.error(f"❌ Erreur suggestions: {e}")
            return []
    
    # ==================== ANALYSE DE PERFORMANCE ====================
    
    def analyze_dj_performance(self, dj_id):
        """
        Analyse les performances d'un prestataire
        """
        try:
            from app import db, Facture, Devis, DJ
            
            with self.app.app_context():
                dj = db.session.get(DJ, dj_id)
                if not dj:
                    return None
                
                factures = Facture.query.filter_by(dj_id=dj_id).all()
                devis = Devis.query.filter_by(dj_id=dj_id).all()
                if not factures and not devis:
                    return {
                        'prestations_total': 0,
                        'chiffre_affaires': 0,
                        'types_evenements': []
                    }
                
                # Calculer métriques
                ca_total = sum(float(f.montant_ttc or 0) for f in factures) + sum(float(d.montant_ttc or 0) for d in devis)
                types = []
                for item in factures + devis:
                    if getattr(item, 'prestation_titre', None):
                        types.append(item.prestation_titre)
                type_counts = Counter(types)
                
                return {
                    'prestations_total': len(factures) + len(devis),
                    'chiffre_affaires': ca_total,
                    'ca_moyen_prestation': round(ca_total / max(len(factures) + len(devis), 1), 2),
                    'types_evenements': dict(type_counts.most_common(3)),
                    'specialite_detectee': type_counts.most_common(1)[0][0] if type_counts else None
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur analyse performance: {e}")
            return None
    
    # ==================== OPTIMISATION PLANNING ====================
    
    def optimize_schedule(self, date_debut, date_fin):
        """
        Optimise le planning pour maximiser l'utilisation du matériel
        """
        try:
            from app import Prestation
            import logging
            logger = logging.getLogger(__name__)

            with self.app.app_context():
                prestations = Prestation.query.filter(
                    Prestation.date_debut >= date_debut,
                    Prestation.date_debut <= date_fin,
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).order_by(Prestation.date_debut, Prestation.heure_debut).all()
                
                suggestions = []
                
                # Analyser l'utilisation du matériel
                dates_chargees = {}
                for p in prestations:
                    if p.date_debut not in dates_chargees:
                        dates_chargees[p.date_debut] = []
                    dates_chargees[p.date_debut].append(p)
                
                # Détecter les jours sous-utilisés
                for date_key, prests in dates_chargees.items():
                    if len(prests) == 1:
                        suggestions.append({
                            'type': 'optimisation',
                            'date': date_key,
                            'message': f'Seulement {len(prests)} prestation ce jour. Possibilité d\'en ajouter une autre ?'
                        })
                
                return suggestions
                
        except Exception as e:
            logger.error(f"❌ Erreur optimisation planning: {e}")
            return []

    # ==================== BRIEF ÉVÉNEMENT ====================

    def generate_event_brief(self, prestation_id=None, devis_id=None):
        """Génère un brief opérationnel pour une prestation ou un devis."""
        try:
            from app import Prestation, Devis, db

            with self.app.app_context():
                if prestation_id:
                    prestation = db.session.get(Prestation, prestation_id)
                    if not prestation:
                        return None
                    dj_nom = prestation.dj.nom if prestation.dj else None
                    materiels = [m.nom for m in prestation.materiels] if prestation.materiels else []
                    duration = self._duration_hours(prestation.heure_debut, prestation.heure_fin)
                    checklist = [
                        "Confirmer l'adresse et l'accès",
                        "Vérifier le matériel assigné",
                        "Test son et lumières avant l'événement"
                    ]
                    if duration >= 5:
                        checklist.append("Prévoir matériel de secours pour longue durée")
                    return {
                        'source': 'prestation',
                        'client': prestation.client,
                        'date': prestation.date_debut.strftime('%Y-%m-%d'),
                        'heure_debut': prestation.heure_debut.strftime('%H:%M'),
                        'heure_fin': prestation.heure_fin.strftime('%H:%M'),
                        'lieu': prestation.lieu,
                        'dj': dj_nom,
                        'materiels': materiels,
                        'notes': prestation.notes or '',
                        'checklist': checklist
                    }

                if devis_id:
                    devis = db.session.get(Devis, devis_id)
                    if not devis:
                        return None
                    duration = self._duration_hours(devis.heure_debut, devis.heure_fin)
                    checklist = [
                        "Valider le devis avec le client",
                        "Confirmer le planning et les horaires",
                        "Préparer le matériel recommandé"
                    ]
                    if duration >= 5:
                        checklist.append("Prévoir un second prestataire ou un support technique")
                    return {
                        'source': 'devis',
                        'client': devis.client_nom,
                        'date': devis.date_prestation.strftime('%Y-%m-%d'),
                        'heure_debut': devis.heure_debut.strftime('%H:%M'),
                        'heure_fin': devis.heure_fin.strftime('%H:%M'),
                        'lieu': devis.lieu,
                        'dj': devis.dj.nom if devis.dj else None,
                        'materiels': [],
                        'notes': devis.prestation_description or '',
                        'checklist': checklist
                    }
        except Exception as e:
            logger.error(f"❌ Erreur génération brief: {e}")
        return None

    # ==================== DÉTECTION D'ANOMALIES ====================

    def detect_anomalies(self, scope='all', limit=200):
        """Détecte des anomalies de données (prix, durées, incohérences)."""
        anomalies = []
        try:
            from app import Devis, Facture, Prestation

            with self.app.app_context():
                devis = []
                factures = []
                prestations = []

                if scope in ['all', 'devis']:
                    devis = Devis.query.order_by(Devis.date_creation.desc()).limit(limit).all()
                if scope in ['all', 'factures']:
                    factures = Facture.query.order_by(Facture.date_creation.desc()).limit(limit).all()
                if scope in ['all', 'prestations']:
                    prestations = Prestation.query.order_by(Prestation.date_creation.desc()).limit(limit).all()

                prices = [float(d.montant_ttc or 0) for d in devis] + [float(f.montant_ttc or 0) for f in factures]
                avg_price = statistics.mean(prices) if prices else 0

                def _check_amount(amount, entity, label):
                    if amount <= 0:
                        anomalies.append({
                            'type': 'montant',
                            'entity': entity,
                            'message': f'{label} montant invalide ({amount})'
                        })
                    elif avg_price and (amount > avg_price * 3 or amount < avg_price * 0.3):
                        anomalies.append({
                            'type': 'outlier',
                            'entity': entity,
                            'message': f'{label} montant atypique ({amount:.2f}€)'
                        })

                for d in devis:
                    duration = self._duration_hours(d.heure_debut, d.heure_fin)
                    if duration <= 0 or duration > 12:
                        anomalies.append({
                            'type': 'duree',
                            'entity': f'devis:{d.numero}',
                            'message': f'Durée anormale ({duration}h)'
                        })
                    _check_amount(float(d.montant_ttc or 0), f'devis:{d.numero}', 'Devis')

                for f in factures:
                    duration = self._duration_hours(f.heure_debut, f.heure_fin)
                    if duration <= 0 or duration > 12:
                        anomalies.append({
                            'type': 'duree',
                            'entity': f'facture:{f.numero}',
                            'message': f'Durée anormale ({duration}h)'
                        })
                    _check_amount(float(f.montant_ttc or 0), f'facture:{f.numero}', 'Facture')

                for p in prestations:
                    if p.date_fin < p.date_debut:
                        anomalies.append({
                            'type': 'date',
                            'entity': f'prestation:{p.id}',
                            'message': 'Date de fin avant la date de début'
                        })
                    duration = self._duration_hours(p.heure_debut, p.heure_fin)
                    if duration <= 0 or duration > 12:
                        anomalies.append({
                            'type': 'duree',
                            'entity': f'prestation:{p.id}',
                            'message': f'Durée anormale ({duration}h)'
                        })
        except Exception as e:
            logger.error(f"❌ Erreur détection anomalies: {e}")
        return anomalies

    # ==================== UPSELL INTELLIGENT ====================

    def suggest_upsell(self, type_evenement, nombre_invites, budget=None):
        """Suggère des options upsell pertinentes."""
        suggestions = []
        event_type = (type_evenement or '').lower()
        if event_type in ['mariage', 'anniversaire']:
            suggestions.extend([
                {'nom': 'Éclairage premium', 'raison': 'Ambiance renforcée'},
                {'nom': 'Machine à fumée', 'raison': 'Effets visuels populaires'}
            ])
        if event_type in ['festival', 'concert', 'gala']:
            suggestions.extend([
                {'nom': 'Éclairage scénique', 'raison': 'Besoin de visibilité'},
                {'nom': 'Laser show', 'raison': 'Effet spectaculaire'}
            ])
        if nombre_invites and nombre_invites > 150:
            suggestions.append({'nom': 'Sonorisation renforcée', 'raison': 'Grand public'})
        if budget and budget > 1500:
            suggestions.append({'nom': 'Vidéoprojecteur / écran', 'raison': 'Expérience premium'})
        return suggestions

    # ==================== PRÉVISION DE CHARGE ====================

    def forecast_load(self, mois_ahead=3):
        """Prévoit le volume de prestations futures."""
        try:
            from app import Prestation
            with self.app.app_context():
                date_limite = datetime.now().date() - timedelta(days=365)
                prestations = Prestation.query.filter(Prestation.date_debut >= date_limite).all()
                monthly_counts = {}
                for p in prestations:
                    mois_key = p.date_debut.strftime('%Y-%m')
                    monthly_counts[mois_key] = monthly_counts.get(mois_key, 0) + 1
                if not monthly_counts:
                    return []
                avg_monthly = statistics.mean(monthly_counts.values())
                forecasts = []
                current_date = datetime.now()
                for i in range(mois_ahead):
                    future_date = current_date + timedelta(days=30 * (i + 1))
                    mois = future_date.month
                    seasonal_factor = 1.0
                    if mois in [6, 7, 8, 12]:
                        seasonal_factor = 1.3
                    elif mois in [1, 2, 11]:
                        seasonal_factor = 0.7
                    forecasts.append({
                        'mois': future_date.strftime('%B %Y'),
                        'prestations_prevues': round(avg_monthly * seasonal_factor, 1)
                    })
                return forecasts
        except Exception as e:
            logger.error(f"❌ Erreur prévision charge: {e}")
            return []

    # ==================== OPTIMISATION LOGISTIQUE ====================

    def optimize_logistics(self, date_debut, date_fin):
        """Suggère des optimisations logistiques par lieu/date."""
        suggestions = []
        try:
            from app import Prestation
            with self.app.app_context():
                prestations = Prestation.query.filter(
                    Prestation.date_debut >= date_debut,
                    Prestation.date_debut <= date_fin,
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).all()
                grouped = {}
                for p in prestations:
                    key = (p.date_debut, (p.lieu or '').lower())
                    grouped.setdefault(key, []).append(p)
                for (day, lieu), items in grouped.items():
                    if len(items) > 1:
                        suggestions.append({
                            'type': 'grouping',
                            'date': day,
                            'message': f"{len(items)} prestations le {day.strftime('%d/%m/%Y')} à {lieu}. Regrouper la logistique."
                        })
        except Exception as e:
            logger.error(f"❌ Erreur optimisation logistique: {e}")
        return suggestions

    # ==================== ANALYSE CONVERSIONS ====================

    def analyze_conversions(self, start_date=None, end_date=None):
        """Analyse conversions devis -> acceptés -> factures."""
        try:
            from app import Devis, Facture
            with self.app.app_context():
                query = Devis.query
                if start_date:
                    query = query.filter(Devis.date_creation >= start_date)
                if end_date:
                    query = query.filter(Devis.date_creation <= end_date)
                devis = query.all()
                total = len(devis)
                accepted = len([d for d in devis if d.statut == 'accepte'])
                refused = len([d for d in devis if d.statut == 'refuse'])
                expired = len([d for d in devis if d.statut == 'expire'])
                factures = Facture.query.filter(Facture.devis_id.isnot(None)).all()
                devis_to_facture = len({f.devis_id for f in factures if f.devis_id})
                acceptance_rate = round((accepted / total) * 100, 1) if total else 0
                conversion_rate = round((devis_to_facture / total) * 100, 1) if total else 0
                return {
                    'total_devis': total,
                    'acceptes': accepted,
                    'refuses': refused,
                    'expires': expired,
                    'acceptance_rate': acceptance_rate,
                    'conversion_rate': conversion_rate
                }
        except Exception as e:
            logger.error(f"❌ Erreur analyse conversions: {e}")
            return None

    # ==================== ASSISTANT EMAIL ====================

    def generate_email(self, purpose, client_name, event_type=None, date_prestation=None, extra_notes=None):
        """Génère un email type selon un objectif."""
        client_name = client_name or 'Client'
        event_part = f" pour votre {event_type}" if event_type else ""
        date_part = f" le {date_prestation}" if date_prestation else ""
        if purpose == 'confirmation':
            body = (
                f"Bonjour {client_name},\n\n"
                f"Nous confirmons votre réservation{event_part}{date_part}.\n"
                f"Nous revenons vers vous avec les détails finaux très rapidement.\n\n"
                f"Merci pour votre confiance.\n"
                f"L'équipe Planify"
            )
        elif purpose == 'relance':
            body = (
                f"Bonjour {client_name},\n\n"
                f"Nous nous permettons de revenir vers vous concernant votre devis{event_part}{date_part}.\n"
                f"N'hésitez pas à nous poser vos questions ou à valider le devis.\n\n"
                f"Cordialement,\n"
                f"L'équipe Planify"
            )
        else:
            body = (
                f"Bonjour {client_name},\n\n"
                f"Pour finaliser votre projet{event_part}{date_part}, "
                f"pouvez-vous nous confirmer les derniers détails ?\n\n"
                f"Merci,\n"
                f"L'équipe Planify"
            )
        if extra_notes:
            body += f"\n\nNotes: {extra_notes}"
        return body

    # ==================== SCORING CLIENT ====================

    def score_client(self, reservation_id=None, devis_id=None, client_name=None, nb_invites=None, budget=None, lead_days=None):
        """Attribue un score simple (0-100) à un client."""
        score = 50
        reasons = []
        try:
            from app import ReservationClient, Devis, db
            with self.app.app_context():
                if reservation_id:
                    reservation = db.session.get(ReservationClient, reservation_id)
                    if reservation:
                        nb_invites = reservation.nb_invites
                        budget = reservation.prix_prestation
                        lead_days = (reservation.date_souhaitee - date.today()).days
                        client_name = reservation.nom
                if devis_id:
                    devis = db.session.get(Devis, devis_id)
                    if devis:
                        client_name = devis.client_nom
                        budget = devis.montant_ttc
                        lead_days = (devis.date_prestation - date.today()).days
        except Exception as e:
            logger.error(f"❌ Erreur chargement client: {e}")

        if budget:
            if budget > 1500:
                score += 15
                reasons.append("Budget élevé")
            elif budget < 400:
                score -= 10
                reasons.append("Budget faible")
        if nb_invites:
            if nb_invites > 200:
                score += 10
                reasons.append("Grand événement")
            elif nb_invites < 40:
                score -= 5
                reasons.append("Petit événement")
        if lead_days is not None:
            if lead_days < 7:
                score -= 15
                reasons.append("Délai court")
            elif lead_days > 30:
                score += 5
                reasons.append("Délai confortable")

        score = max(0, min(100, score))
        return {
            'client': client_name or 'Client',
            'score': score,
            'reasons': reasons
        }

    def _duration_hours(self, debut, fin):
        if not debut or not fin:
            return 0
        try:
            if isinstance(debut, str):
                debut = datetime.strptime(debut, '%H:%M').time()
            if isinstance(fin, str):
                fin = datetime.strptime(fin, '%H:%M').time()
            start = datetime.combine(date.today(), debut)
            end = datetime.combine(date.today(), fin)
            if end <= start:
                end += timedelta(days=1)
            return round((end - start).total_seconds() / 3600, 2)
        except Exception:
            return 0


# Instance globale
smart_assistant = SmartAssistant()

def init_smart_assistant(app, db):
    """Initialise l'assistant avec l'app Flask"""
    smart_assistant.app = app
    smart_assistant.db = db
    return smart_assistant
