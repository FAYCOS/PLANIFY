#!/usr/bin/env python3
"""
Routes API pour l'IA Smart Assistant
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta
from ai_smart_assistant import smart_assistant
import logging
import json
logger = logging.getLogger(__name__)

# Créer un Blueprint pour les routes IA
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

def login_required_api(f):
    """Décorateur pour vérifier l'authentification API"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Non authentifié'}), 401
        try:
            from app import get_current_user
            user = get_current_user()
        except Exception:
            user = None
        if not user:
            return jsonify({'error': 'Non authentifié'}), 401
        if user.role not in ['admin', 'manager']:
            return jsonify({'error': 'Accès refusé'}), 403
        return f(*args, **kwargs)
    return decorated_function

def require_json(f):
    """Garantit un payload JSON valide pour les routes POST."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'PATCH') and not request.is_json:
            return jsonify({'success': False, 'error': 'JSON requis'}), 400
        return f(*args, **kwargs)
    return decorated

# ==================== PRÉDICTIONS ====================

@ai_bp.route('/predict-price', methods=['POST'])
@login_required_api
@require_json
def predict_price():
    """Prédit le prix optimal pour une prestation"""
    try:
        data = request.get_json(silent=True) or {}
        
        type_evenement = data.get('type_evenement', '')
        nombre_invites = int(data.get('nombre_invites', 100))
        date_str = data.get('date', '')
        duree_heures = float(data.get('duree_heures', 4))
        
        # Parser la date pour obtenir le mois
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            mois = date_obj.month
        else:
            mois = datetime.now().month
        
        # Prédire le prix
        prix_suggere = smart_assistant.predict_optimal_price(
            type_evenement=type_evenement,
            nombre_invites=nombre_invites,
            mois=mois,
            duree_heures=duree_heures
        )
        
        return jsonify({
            'success': True,
            'prix_suggere': prix_suggere,
            'message': f'Prix recommandé : {prix_suggere}€'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/suggest-dj', methods=['POST'])
@login_required_api
@require_json
def suggest_dj():
    """Suggère le meilleur DJ disponible"""
    try:
        data = request.get_json(silent=True) or {}
        
        date_str = data.get('date', '')
        style_musical = data.get('style_musical', '')
        localisation = data.get('localisation', '')
        
        # Parser la date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Suggérer DJ
        dj = smart_assistant.suggest_best_dj(
            date_prestation=date_obj,
            style_musical=style_musical,
            localisation=localisation
        )
        
        if dj:
            return jsonify({
                'success': True,
                'dj': {
                    'id': dj.id,
                    'nom': dj.nom,
                    'prenom': dj.prenom,
                    'specialite': dj.specialite_musicale,
                    'telephone': dj.telephone,
                    'email': dj.email
                },
                'message': f'DJ recommandé : {dj.nom} {dj.prenom}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Aucun DJ disponible pour cette date'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/recommend-equipment', methods=['POST'])
@login_required_api
@require_json
def recommend_equipment():
    """Recommande le matériel nécessaire"""
    try:
        data = request.get_json(silent=True) or {}
        
        type_evenement = data.get('type_evenement', '')
        nombre_invites = int(data.get('nombre_invites', 100))
        duree_heures = float(data.get('duree_heures', 4))
        
        # Recommander matériel
        recommendations = smart_assistant.recommend_equipment(
            type_evenement=type_evenement,
            nombre_invites=nombre_invites,
            duree_heures=duree_heures
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== DÉTECTION DE CONFLITS ====================

@ai_bp.route('/detect-conflicts', methods=['POST'])
@login_required_api
@require_json
def detect_conflicts():
    """Détecte les conflits de planning"""
    try:
        data = request.get_json(silent=True) or {}
        
        date_str = data.get('date', '')
        heure_debut = data.get('heure_debut', '')
        heure_fin = data.get('heure_fin', '')
        materiel_ids = data.get('materiel_ids', [])
        dj_id = data.get('dj_id')
        exclude_prestation_id = data.get('exclude_prestation_id')
        
        # Parser la date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Détecter conflits
        conflicts = smart_assistant.detect_conflicts(
            date=date_obj,
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            materiel_ids=materiel_ids,
            dj_id=dj_id,
            exclude_prestation_id=exclude_prestation_id
        )
        
        return jsonify({
            'success': True,
            'conflicts': conflicts,
            'has_conflicts': len(conflicts) > 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== PRÉVISIONS ====================

@ai_bp.route('/forecast-revenue', methods=['GET'])
@login_required_api
def forecast_revenue():
    """Prévoit le chiffre d'affaires"""
    try:
        mois_ahead = int(request.args.get('mois', 3))
        
        forecasts = smart_assistant.forecast_revenue(mois_ahead=mois_ahead)
        
        return jsonify({
            'success': True,
            'forecasts': forecasts
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== SUGGESTIONS ====================

@ai_bp.route('/similar-events', methods=['GET'])
@login_required_api
def similar_events():
    """Suggère des événements similaires"""
    try:
        type_evenement = request.args.get('type_evenement', '')
        localisation = request.args.get('localisation', '')
        limit = int(request.args.get('limit', 5))
        
        suggestions = smart_assistant.suggest_similar_events(
            type_evenement=type_evenement,
            localisation=localisation,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== ANALYSE PERFORMANCE ====================

@ai_bp.route('/analyze-dj/<int:dj_id>', methods=['GET'])
@login_required_api
def analyze_dj(dj_id):
    """Analyse les performances d'un DJ"""
    try:
        analysis = smart_assistant.analyze_dj_performance(dj_id)
        
        if analysis:
            return jsonify({
                'success': True,
                'analysis': analysis
            })
        else:
            return jsonify({
                'success': False,
                'message': 'DJ non trouvé'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== OPTIMISATION PLANNING ====================

@ai_bp.route('/optimize-schedule', methods=['POST'])
@login_required_api
@require_json
def optimize_schedule():
    """Optimise le planning"""
    try:
        data = request.get_json(silent=True) or {}
        
        date_debut_str = data.get('date_debut', '')
        date_fin_str = data.get('date_fin', '')
        
        # Parser les dates
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        
        suggestions = smart_assistant.optimize_schedule(
            date_debut=date_debut,
            date_fin=date_fin
        )
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== AUTO-REMPLISSAGE INTELLIGENT ====================

@ai_bp.route('/autofill', methods=['POST'])
@login_required_api
@require_json
def autofill():
    """Remplit automatiquement un formulaire de prestation"""
    try:
        data = request.get_json(silent=True) or {}
        
        type_evenement = data.get('type_evenement', '')
        nombre_invites = int(data.get('nombre_invites', 100))
        date_str = data.get('date', '')
        duree_heures = float(data.get('duree_heures', 4))
        
        # Parser la date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        mois = date_obj.month
        
        # Prédictions combinées
        prix_suggere = smart_assistant.predict_optimal_price(
            type_evenement, nombre_invites, mois, duree_heures
        )
        
        dj_suggere = smart_assistant.suggest_best_dj(
            date_obj, '', None
        )
        
        materiels_suggeres = smart_assistant.recommend_equipment(
            type_evenement, nombre_invites, duree_heures
        )
        
        return jsonify({
            'success': True,
            'autofill': {
                'tarif': prix_suggere,
                'dj': {
                    'id': dj_suggere.id,
                    'nom': f'{dj_suggere.nom} {dj_suggere.prenom}'
                } if dj_suggere else None,
                'materiels': materiels_suggeres
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== BRIEF ÉVÉNEMENT ====================

@ai_bp.route('/brief', methods=['POST'])
@login_required_api
@require_json
def brief_event():
    try:
        data = request.get_json(silent=True) or {}
        prestation_id = data.get('prestation_id')
        devis_id = data.get('devis_id')
        brief = smart_assistant.generate_event_brief(prestation_id=prestation_id, devis_id=devis_id)
        if not brief:
            return jsonify({'success': False, 'message': 'Brief introuvable'}), 404
        return jsonify({'success': True, 'brief': brief})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ANOMALIES ====================

@ai_bp.route('/detect-anomalies', methods=['GET'])
@login_required_api
def detect_anomalies():
    try:
        scope = request.args.get('scope', 'all')
        limit = int(request.args.get('limit', 200))
        anomalies = smart_assistant.detect_anomalies(scope=scope, limit=limit)
        return jsonify({'success': True, 'anomalies': anomalies})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== UPSELL ====================

@ai_bp.route('/upsell', methods=['POST'])
@login_required_api
@require_json
def upsell():
    try:
        data = request.get_json(silent=True) or {}
        type_evenement = data.get('type_evenement', '')
        nombre_invites = int(data.get('nombre_invites', 100))
        budget = data.get('budget')
        budget = float(budget) if budget not in (None, '') else None
        suggestions = smart_assistant.suggest_upsell(type_evenement, nombre_invites, budget)
        return jsonify({'success': True, 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== PRÉVISION CHARGE ====================

@ai_bp.route('/forecast-load', methods=['GET'])
@login_required_api
def forecast_load():
    try:
        mois_ahead = int(request.args.get('mois', 3))
        forecasts = smart_assistant.forecast_load(mois_ahead=mois_ahead)
        return jsonify({'success': True, 'forecasts': forecasts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== OPTIMISATION LOGISTIQUE ====================

@ai_bp.route('/optimize-logistics', methods=['POST'])
@login_required_api
@require_json
def optimize_logistics():
    try:
        data = request.get_json(silent=True) or {}
        date_debut = datetime.strptime(data.get('date_debut'), '%Y-%m-%d').date()
        date_fin = datetime.strptime(data.get('date_fin'), '%Y-%m-%d').date()
        suggestions = smart_assistant.optimize_logistics(date_debut, date_fin)
        return jsonify({'success': True, 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ANALYSE CONVERSIONS ====================

@ai_bp.route('/analyze-conversions', methods=['GET'])
@login_required_api
def analyze_conversions():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        start = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        stats = smart_assistant.analyze_conversions(start_date=start, end_date=end)
        if not stats:
            return jsonify({'success': False, 'message': 'Aucune donnée'}), 404
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== EMAIL ASSISTANT ====================

@ai_bp.route('/generate-email', methods=['POST'])
@login_required_api
@require_json
def generate_email():
    try:
        data = request.get_json(silent=True) or {}
        purpose = data.get('purpose', 'confirmation')
        prestation_id = data.get('prestation_id')
        client_name = data.get('client_name', 'Client')
        event_type = data.get('event_type')
        date_prestation = data.get('date_prestation')
        extra_notes = data.get('extra_notes')

        if prestation_id:
            try:
                prestation_id_int = int(prestation_id)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'ID mission invalide'}), 400
            try:
                from app import Prestation, db
                prestation = db.session.get(Prestation, prestation_id_int)
            except Exception:
                prestation = None

            if not prestation:
                return jsonify({'success': False, 'error': 'Mission introuvable'}), 404

            if not client_name or client_name == 'Client':
                client_name = prestation.client or client_name
            if not date_prestation and prestation.date_debut:
                date_prestation = prestation.date_debut.strftime('%d/%m/%Y')

            if not event_type and prestation.custom_fields:
                try:
                    custom_fields = json.loads(prestation.custom_fields)
                    event_type = custom_fields.get('type_evenement') or custom_fields.get('type_mission') or custom_fields.get('type_prestation')
                except Exception:
                    event_type = event_type

        body = smart_assistant.generate_email(purpose, client_name, event_type, date_prestation, extra_notes)
        return jsonify({'success': True, 'email': body})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== SCORING CLIENT ====================

@ai_bp.route('/score-client', methods=['POST'])
@login_required_api
@require_json
def score_client():
    try:
        data = request.get_json(silent=True) or {}
        result = smart_assistant.score_client(
            reservation_id=data.get('reservation_id'),
            devis_id=data.get('devis_id'),
            client_name=data.get('client_name'),
            nb_invites=data.get('nb_invites'),
            budget=data.get('budget'),
            lead_days=data.get('lead_days')
        )
        return jsonify({'success': True, 'score': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== HEALTH CHECK ====================

@ai_bp.route('/health', methods=['GET'])
@login_required_api
def health():
    """Vérifie que l'IA fonctionne"""
    return jsonify({
        'success': True,
        'status': 'IA Smart Assistant opérationnelle',
        'version': '3.0'
    })
