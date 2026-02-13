#!/usr/bin/env python3
"""
API REST pour l'application mobile Planify
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta, timezone
# Import sera fait dans les fonctions pour éviter les imports circulaires
from werkzeug.security import check_password_hash
import logging

# Logger module
logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Créer un Blueprint pour l'API mobile
mobile_api = Blueprint('mobile_api', __name__, url_prefix='/api/mobile')


def token_required(f):
    """Décorateur pour vérifier le token JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token manquant'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]

            # Utiliser current_app pour éviter référence à app global
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            from app import db, User
            current_user = db.session.get(User, data.get('user_id'))
        except ExpiredSignatureError:
            return jsonify({'message': 'Token expiré'}), 401
        except InvalidTokenError:
            return jsonify({'message': 'Token invalide'}), 401
        except Exception as e:
            logger.exception('Erreur lors de la vérification du token')
            return jsonify({'message': 'Erreur interne'}), 500

        return f(current_user, *args, **kwargs)
    
    return decorated

@mobile_api.route('/auth/login', methods=['POST'])
def mobile_login():
    """Authentification mobile"""
    try:
        from app import app, User, _is_rate_limited
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        if _is_rate_limited('mobile_api.mobile_login', ip_address, request.path):
            return jsonify({'error': 'Trop de tentatives. Veuillez réessayer.'}), 429
        data = request.get_json(silent=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        
        if not username or not password:
            return jsonify({'error': 'Username et password requis'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Identifiants invalides'}), 401
        
        if not user.actif:
            return jsonify({'error': 'Compte désactivé'}), 401
        
        # Générer le token JWT
        token = jwt.encode({
            'user_id': user.id,
            'exp': utcnow() + timedelta(days=30)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'nom': user.nom,
                'prenom': user.prenom,
                'email': user.email,
                'role': user.role
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mobile_api.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Récupérer le profil utilisateur"""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'nom': current_user.nom,
        'prenom': current_user.prenom,
        'email': current_user.email,
        'telephone': current_user.telephone,
        'role': current_user.role,
        'date_creation': current_user.date_creation.isoformat() if current_user.date_creation else None
    })

@mobile_api.route('/prestations', methods=['GET'])
@token_required
def get_prestations(current_user):
    """Récupérer les prestations de l'utilisateur"""
    try:
        from app import Prestation, DJ
        # Si c'est un DJ, récupérer ses prestations
        if current_user.role == 'dj':
            dj = DJ.query.filter_by(user_id=current_user.id).first()
            if not dj:
                return jsonify({'prestations': []})
            
            prestations = Prestation.query.filter_by(dj_id=dj.id).order_by(Prestation.date_debut.desc()).all()
        else:
            # Pour admin/manager, récupérer toutes les prestations
            prestations = Prestation.query.order_by(Prestation.date_debut.desc()).all()
        
        prestations_data = []
        for prestation in prestations:
            prestations_data.append({
                'id': prestation.id,
                'client': prestation.client,
                'client_telephone': prestation.client_telephone,
                'client_email': prestation.client_email,
                'date_debut': prestation.date_debut.isoformat(),
                'date_fin': prestation.date_fin.isoformat(),
                'heure_debut': prestation.heure_debut.isoformat(),
                'heure_fin': prestation.heure_fin.isoformat(),
                'lieu': prestation.lieu,
                'statut': prestation.statut,
                'notes': prestation.notes,
                'dj_nom': prestation.dj.nom if prestation.dj else None,
                'materiels': [{'nom': m.nom, 'categorie': m.categorie} for m in prestation.materiels]
            })
        
        return jsonify({'prestations': prestations_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mobile_api.route('/prestations/<int:prestation_id>', methods=['GET'])
@token_required
def get_prestation(current_user, prestation_id):
    """Récupérer une prestation spécifique"""
    try:
        from app import Prestation, DJ
        prestation = Prestation.query.get_or_404(prestation_id)
        
        # Vérifier les permissions
        if current_user.role == 'dj':
            dj = DJ.query.filter_by(user_id=current_user.id).first()
            if not dj or prestation.dj_id != dj.id:
                return jsonify({'error': 'Accès non autorisé'}), 403
        
        return jsonify({
            'id': prestation.id,
            'client': prestation.client,
            'client_telephone': prestation.client_telephone,
            'client_email': prestation.client_email,
            'date_debut': prestation.date_debut.isoformat(),
            'date_fin': prestation.date_fin.isoformat(),
            'heure_debut': prestation.heure_debut.isoformat(),
            'heure_fin': prestation.heure_fin.isoformat(),
            'lieu': prestation.lieu,
            'statut': prestation.statut,
            'notes': prestation.notes,
            'dj_nom': prestation.dj.nom if prestation.dj else None,
            'materiels': [{'nom': m.nom, 'categorie': m.categorie} for m in prestation.materiels]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mobile_api.route('/prestations/<int:prestation_id>/status', methods=['PUT'])
@token_required
def update_prestation_status(current_user, prestation_id):
    """Mettre à jour le statut d'une prestation"""
    try:
        from app import Prestation, DJ, db
        prestation = Prestation.query.get_or_404(prestation_id)
        
        # Vérifier les permissions
        if current_user.role == 'dj':
            dj = DJ.query.filter_by(user_id=current_user.id).first()
            if not dj or prestation.dj_id != dj.id:
                return jsonify({'error': 'Accès non autorisé'}), 403
        
        data = request.get_json()
        new_status = data.get('statut')
        
        if new_status not in ['planifiee', 'confirmee', 'terminee', 'annulee']:
            return jsonify({'error': 'Statut invalide'}), 400
        
        prestation.statut = new_status
        prestation.date_modification = utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Statut mis à jour avec succès'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mobile_api.route('/prestations/upcoming', methods=['GET'])
@token_required
def get_upcoming_prestations(current_user):
    """Récupérer les prestations à venir"""
    try:
        from datetime import date
        from app import Prestation, DJ
        
        if current_user.role == 'dj':
            dj = DJ.query.filter_by(user_id=current_user.id).first()
            if not dj:
                return jsonify({'prestations': []})
            
            prestations = Prestation.query.filter(
                Prestation.dj_id == dj.id,
                Prestation.date_debut >= date.today(),
                Prestation.statut.in_(['planifiee', 'confirmee'])
            ).order_by(Prestation.date_debut).all()
        else:
            prestations = Prestation.query.filter(
                Prestation.date_debut >= date.today(),
                Prestation.statut.in_(['planifiee', 'confirmee'])
            ).order_by(Prestation.date_debut).all()
        
        prestations_data = []
        for prestation in prestations:
            prestations_data.append({
                'id': prestation.id,
                'client': prestation.client,
                'date_debut': prestation.date_debut.isoformat(),
                'heure_debut': prestation.heure_debut.isoformat(),
                'lieu': prestation.lieu,
                'statut': prestation.statut
            })
        
        return jsonify({'prestations': prestations_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mobile_api.route('/materiels', methods=['GET'])
@token_required
def get_materiels(current_user):
    """Récupérer la liste du matériel"""
    try:
        from app import Materiel
        materiels = Materiel.query.all()
        
        materiels_data = []
        for materiel in materiels:
            materiels_data.append({
                'id': materiel.id,
                'nom': materiel.nom,
                'categorie': materiel.categorie,
                'statut': materiel.statut,
                'local': materiel.local.nom if materiel.local else None
            })
        
        return jsonify({'materiels': materiels_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mobile_api.route('/stats', methods=['GET'])
@token_required
def get_stats(current_user):
    """Récupérer les statistiques de l'utilisateur"""
    try:
        from datetime import date, timedelta
        from app import Prestation, DJ
        
        if current_user.role == 'dj':
            dj = DJ.query.filter_by(user_id=current_user.id).first()
            if not dj:
                return jsonify({'stats': {}})
            
            # Statistiques du DJ
            total_prestations = Prestation.query.filter_by(dj_id=dj.id).count()
            prestations_ce_mois = Prestation.query.filter(
                Prestation.dj_id == dj.id,
                Prestation.date_debut >= date.today().replace(day=1)
            ).count()
            
            prestations_a_venir = Prestation.query.filter(
                Prestation.dj_id == dj.id,
                Prestation.date_debut >= date.today(),
                Prestation.statut.in_(['planifiee', 'confirmee'])
            ).count()
            
            stats = {
                'total_prestations': total_prestations,
                'prestations_ce_mois': prestations_ce_mois,
                'prestations_a_venir': prestations_a_venir
            }
        else:
            # Statistiques globales pour admin/manager
            total_prestations = Prestation.query.count()
            prestations_ce_mois = Prestation.query.filter(
                Prestation.date_debut >= date.today().replace(day=1)
            ).count()
            
            prestations_a_venir = Prestation.query.filter(
                Prestation.date_debut >= date.today(),
                Prestation.statut.in_(['planifiee', 'confirmee'])
            ).count()
            
            stats = {
                'total_prestations': total_prestations,
                'prestations_ce_mois': prestations_ce_mois,
                'prestations_a_venir': prestations_a_venir
            }
        
        return jsonify({'stats': stats})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Le Blueprint sera enregistré dans app.py
