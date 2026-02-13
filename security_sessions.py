#!/usr/bin/env python3
"""
Module de sécurité des sessions
"""

import secrets
import hashlib
import time
from datetime import datetime, timedelta
from flask import session, request, current_app
import logging
logger = logging.getLogger(__name__)
from werkzeug.security import generate_password_hash
import json

class SessionSecurity:
    """Classe pour la sécurité des sessions"""
    
    def __init__(self):
        self.session_timeout = 3600  # 1 heure
        self.max_sessions_per_user = 5
        self.session_regeneration_interval = 300  # 5 minutes
        self.active_sessions = {}  # user_id -> [sessions]
        self.session_tokens = {}  # token -> session_data
    
    def create_secure_session(self, user_id, ip_address, user_agent):
        """
        Crée une session sécurisée
        """
        # Générer un token de session unique
        session_token = self._generate_session_token()
        
        # Créer les données de session
        session_data = {
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'is_active': True,
            'token': session_token
        }
        
        # Stocker la session
        self.session_tokens[session_token] = session_data
        
        # Ajouter à la liste des sessions actives de l'utilisateur
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = []
        
        self.active_sessions[user_id].append(session_token)
        
        # Limiter le nombre de sessions par utilisateur
        if len(self.active_sessions[user_id]) > self.max_sessions_per_user:
            # Supprimer la plus ancienne session
            oldest_token = self.active_sessions[user_id].pop(0)
            if oldest_token in self.session_tokens:
                del self.session_tokens[oldest_token]
        
        return session_token, session_data
    
    def validate_session(self, session_token, ip_address, user_agent):
        """
        Valide une session
        """
        if not session_token or session_token not in self.session_tokens:
            return False, "Token de session invalide"
        
        session_data = self.session_tokens[session_token]
        
        # Vérifier si la session est active
        if not session_data.get('is_active', False):
            return False, "Session inactive"
        
        # Vérifier l'expiration
        if self._is_session_expired(session_data):
            self._invalidate_session(session_token)
            return False, "Session expirée"
        
        # Vérifier l'IP (optionnel, peut être désactivé pour les proxies)
        if session_data.get('ip_address') != ip_address:
            # Log l'activité suspecte
            self._log_suspicious_activity(
                session_data.get('user_id'),
                f"Changement d'IP: {session_data.get('ip_address')} -> {ip_address}"
            )
            # Ne pas bloquer, mais logger
        
        # Vérifier l'User-Agent (optionnel)
        if session_data.get('user_agent') != user_agent:
            self._log_suspicious_activity(
                session_data.get('user_id'),
                f"Changement d'User-Agent"
            )
        
        # Mettre à jour la dernière activité
        session_data['last_activity'] = datetime.now()
        
        return True, session_data
    
    def refresh_session(self, session_token):
        """
        Rafraîchit une session
        """
        if session_token not in self.session_tokens:
            return False, "Session non trouvée"
        
        session_data = self.session_tokens[session_token]
        
        # Vérifier si la session doit être régénérée
        if self._should_regenerate_session(session_data):
            new_token = self._generate_session_token()
            session_data['token'] = new_token
            session_data['last_activity'] = datetime.now()
            
            # Mettre à jour les références
            self.session_tokens[new_token] = session_data
            del self.session_tokens[session_token]
            
            return True, new_token
        
        # Mettre à jour la dernière activité
        session_data['last_activity'] = datetime.now()
        return True, session_token
    
    def invalidate_session(self, session_token):
        """
        Invalide une session
        """
        if session_token in self.session_tokens:
            session_data = self.session_tokens[session_token]
            user_id = session_data.get('user_id')
            
            # Supprimer de la liste des sessions actives
            if user_id and user_id in self.active_sessions:
                if session_token in self.active_sessions[user_id]:
                    self.active_sessions[user_id].remove(session_token)
            
            # Supprimer la session
            del self.session_tokens[session_token]
            
            return True
        
        return False
    
    def invalidate_user_sessions(self, user_id):
        """
        Invalide toutes les sessions d'un utilisateur
        """
        if user_id in self.active_sessions:
            for session_token in self.active_sessions[user_id]:
                if session_token in self.session_tokens:
                    del self.session_tokens[session_token]
            del self.active_sessions[user_id]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """
        Nettoie les sessions expirées
        """
        expired_tokens = []
        
        for token, session_data in self.session_tokens.items():
            if self._is_session_expired(session_data):
                expired_tokens.append(token)
        
        for token in expired_tokens:
            self._invalidate_session(token)
        
        return len(expired_tokens)
    
    def get_user_sessions(self, user_id):
        """
        Récupère les sessions d'un utilisateur
        """
        if user_id not in self.active_sessions:
            return []
        
        sessions = []
        for token in self.active_sessions[user_id]:
            if token in self.session_tokens:
                session_data = self.session_tokens[token].copy()
                # Ne pas exposer le token complet
                session_data['token'] = session_data['token'][:8] + '...'
                sessions.append(session_data)
        
        return sessions
    
    def _generate_session_token(self):
        """
        Génère un token de session sécurisé
        """
        return secrets.token_urlsafe(32)
    
    def _is_session_expired(self, session_data):
        """
        Vérifie si une session est expirée
        """
        last_activity = session_data.get('last_activity')
        if not last_activity:
            return True
        
        time_since_activity = datetime.now() - last_activity
        return time_since_activity.total_seconds() > self.session_timeout
    
    def _should_regenerate_session(self, session_data):
        """
        Vérifie si une session doit être régénérée
        """
        last_activity = session_data.get('last_activity')
        if not last_activity:
            return True
        
        time_since_activity = datetime.now() - last_activity
        return time_since_activity.total_seconds() > self.session_regeneration_interval
    
    def _invalidate_session(self, session_token):
        """
        Invalide une session (méthode interne)
        """
        if session_token in self.session_tokens:
            session_data = self.session_tokens[session_token]
            session_data['is_active'] = False
            del self.session_tokens[session_token]
    
    def _log_suspicious_activity(self, user_id, details):
        """
        Log une activité suspecte
        """
        current_app.logger.warning(f"Activité suspecte - User: {user_id}, Details: {details}")

class SecureSessionManager:
    """Gestionnaire de sessions sécurisé"""
    
    def __init__(self, app=None):
        self.app = app
        self.session_security = SessionSecurity()
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le gestionnaire de sessions"""
        self.app = app
        
        # Configuration des sessions Flask
        app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS uniquement
        app.config['SESSION_COOKIE_HTTPONLY'] = True  # Pas d'accès JavaScript
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Protection CSRF
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
        
        # Configuration de sécurité
        app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', 'dev-secret-key-change-in-production')
        
        # Middleware pour la gestion des sessions
        @app.before_request
        def before_request():
            self._handle_session_security()
        
        @app.after_request
        def after_request(response):
            self._handle_session_cleanup()
            return response
    
    def _handle_session_security(self):
        """Gère la sécurité des sessions avant chaque requête"""
        # Vérifier si l'utilisateur est connecté
        if 'user_id' in session:
            user_id = session.get('user_id')
            session_token = session.get('session_token')
            
            # Valider la session
            is_valid, session_data = self.session_security.validate_session(
                session_token,
                request.remote_addr,
                request.headers.get('User-Agent', '')
            )
            
            if not is_valid:
                # Session invalide, déconnecter l'utilisateur
                self.logout_user()
                return
            
            # Rafraîchir la session si nécessaire
            refreshed, new_token = self.session_security.refresh_session(session_token)
            if refreshed and new_token != session_token:
                session['session_token'] = new_token
    
    def _handle_session_cleanup(self):
        """Nettoie les sessions après chaque requête"""
        # Nettoyer les sessions expirées périodiquement
        if hasattr(self, '_last_cleanup'):
            if time.time() - self._last_cleanup > 300:  # 5 minutes
                self.session_security.cleanup_expired_sessions()
                self._last_cleanup = time.time()
        else:
            self._last_cleanup = time.time()
    
    def login_user(self, user_id, ip_address=None, user_agent=None):
        """
        Connecte un utilisateur de manière sécurisée
        """
        ip_address = ip_address or request.remote_addr
        user_agent = user_agent or request.headers.get('User-Agent', '')
        
        # Créer une session sécurisée
        session_token, session_data = self.session_security.create_secure_session(
            user_id, ip_address, user_agent
        )
        
        # Configurer la session Flask
        session['user_id'] = user_id
        session['session_token'] = session_token
        session['username'] = session_data.get('username', '')
        session['role'] = session_data.get('role', '')
        session.permanent = True
        
        return session_token
    
    def logout_user(self):
        """
        Déconnecte un utilisateur
        """
        session_token = session.get('session_token')
        if session_token:
            self.session_security.invalidate_session(session_token)
        
        # Nettoyer la session Flask
        session.clear()
    
    def is_user_logged_in(self):
        """
        Vérifie si l'utilisateur est connecté
        """
        if 'user_id' not in session:
            return False
        
        session_token = session.get('session_token')
        if not session_token:
            return False
        
        is_valid, _ = self.session_security.validate_session(
            session_token,
            request.remote_addr,
            request.headers.get('User-Agent', '')
        )
        
        return is_valid
    
    def get_current_user_id(self):
        """
        Récupère l'ID de l'utilisateur actuel
        """
        if self.is_user_logged_in():
            return session.get('user_id')
        return None
    
    def force_logout_user(self, user_id):
        """
        Force la déconnexion d'un utilisateur
        """
        self.session_security.invalidate_user_sessions(user_id)
    
    def get_user_sessions(self, user_id):
        """
        Récupère les sessions d'un utilisateur
        """
        return self.session_security.get_user_sessions(user_id)

# Décorateurs de sécurité
def require_login(f):
    """
    Décorateur pour exiger une connexion
    """
    def wrapper(*args, **kwargs):
        from flask import redirect, url_for, flash
        
        if not session.get('user_id'):
            flash('Vous devez être connecté pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return wrapper

def require_role(required_role):
    """
    Décorateur pour exiger un rôle spécifique
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import redirect, url_for, flash, abort
            
            if not session.get('user_id'):
                flash('Vous devez être connecté pour accéder à cette page.', 'error')
                return redirect(url_for('login'))
            
            user_role = session.get('role')
            if user_role != required_role and user_role != 'admin':
                flash('Vous n\'avez pas les permissions nécessaires.', 'error')
                return abort(403)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def require_any_role(required_roles):
    """
    Décorateur pour exiger un des rôles spécifiés
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import redirect, url_for, flash, abort
            
            if not session.get('user_id'):
                flash('Vous devez être connecté pour accéder à cette page.', 'error')
                return redirect(url_for('login'))
            
            user_role = session.get('role')
            if user_role not in required_roles and user_role != 'admin':
                flash('Vous n\'avez pas les permissions nécessaires.', 'error')
                return abort(403)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator











