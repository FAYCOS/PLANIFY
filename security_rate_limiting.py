#!/usr/bin/env python3
"""
Module de limitation de taux (Rate Limiting) pour la sécurité
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, current_app
import time
from collections import defaultdict, deque
import logging
logger = logging.getLogger(__name__)

class RateLimiter:
    """Classe pour gérer la limitation de taux"""
    
    def __init__(self, app=None):
        self.app = app
        self.limiter = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le rate limiter pour l'application"""
        self.limiter = Limiter(
            app,
            key_func=get_remote_address,
            default_limits=["1000 per hour", "100 per minute"],
            storage_uri="memory://",  # En production, utiliser Redis
            strategy="fixed-window"
        )
        
        # Configuration des limites spécifiques
        self.setup_rate_limits()
        
        return self.limiter
    
    def setup_rate_limits(self):
        """Configure les limites de taux spécifiques"""
        
        # Limites pour la connexion
        @self.limiter.limit("5 per minute", methods=["POST"])
        def login_limit():
            pass
        
        # Limites pour les API
        @self.limiter.limit("100 per hour", methods=["GET", "POST"])
        def api_limit():
            pass
        
        # Limites pour les uploads
        @self.limiter.limit("10 per hour", methods=["POST"])
        def upload_limit():
            pass
        
        # Limites pour les recherches
        @self.limiter.limit("50 per minute", methods=["GET"])
        def search_limit():
            pass

class AdvancedRateLimiter:
    """Rate limiter avancé avec détection d'attaques"""
    
    def __init__(self):
        self.attempts = defaultdict(list)  # IP -> liste des tentatives
        self.blocked_ips = set()  # IPs bloquées
        self.suspicious_ips = defaultdict(int)  # IPs suspectes
    
    def is_rate_limited(self, ip_address, limit=10, window=300):
        """
        Vérifie si une IP est limitée
        limit: nombre maximum de requêtes
        window: fenêtre de temps en secondes
        """
        now = time.time()
        
        # Nettoyer les anciennes tentatives
        self.attempts[ip_address] = [
            attempt for attempt in self.attempts[ip_address]
            if now - attempt < window
        ]
        
        # Vérifier si l'IP est bloquée
        if ip_address in self.blocked_ips:
            return True
        
        # Vérifier la limite
        if len(self.attempts[ip_address]) >= limit:
            # Marquer comme suspecte
            self.suspicious_ips[ip_address] += 1
            
            # Bloquer temporairement si trop suspecte
            if self.suspicious_ips[ip_address] > 3:
                self.blocked_ips.add(ip_address)
                return True
            
            return True
        
        # Enregistrer la tentative
        self.attempts[ip_address].append(now)
        return False
    
    def unblock_ip(self, ip_address):
        """Débloquer une IP"""
        self.blocked_ips.discard(ip_address)
        self.suspicious_ips[ip_address] = 0
    
    def get_blocked_ips(self):
        """Obtenir la liste des IPs bloquées"""
        return list(self.blocked_ips)
    
    def get_suspicious_ips(self):
        """Obtenir la liste des IPs suspectes"""
        return dict(self.suspicious_ips)

class SecurityRateLimiter:
    """Rate limiter spécialisé pour la sécurité"""
    
    def __init__(self):
        self.login_attempts = defaultdict(list)
        self.failed_logins = defaultdict(int)
        self.lockout_duration = 1800  # 30 minutes
        self.max_attempts = 5
    
    def check_login_rate_limit(self, ip_address, username=None):
        """
        Vérifie la limite de taux pour les connexions
        """
        now = time.time()
        
        # Nettoyer les anciennes tentatives
        self.login_attempts[ip_address] = [
            attempt for attempt in self.login_attempts[ip_address]
            if now - attempt < 300  # 5 minutes
        ]
        
        # Vérifier si l'IP est bloquée
        if len(self.login_attempts[ip_address]) >= self.max_attempts:
            return False, "Trop de tentatives de connexion. Veuillez attendre 5 minutes."
        
        # Enregistrer la tentative
        self.login_attempts[ip_address].append(now)
        return True, None
    
    def record_failed_login(self, ip_address, username=None):
        """Enregistre une connexion échouée"""
        self.failed_logins[ip_address] += 1
        
        # Bloquer l'IP si trop d'échecs
        if self.failed_logins[ip_address] >= self.max_attempts:
            return False, "IP bloquée temporairement"
        
        return True, None
    
    def record_successful_login(self, ip_address, username=None):
        """Enregistre une connexion réussie"""
        self.failed_logins[ip_address] = 0
        self.login_attempts[ip_address] = []
    
    def is_ip_blocked(self, ip_address):
        """Vérifie si une IP est bloquée"""
        return self.failed_logins[ip_address] >= self.max_attempts

# Décorateurs de sécurité
def rate_limit(limit="10 per minute"):
    """Décorateur pour appliquer une limite de taux"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            # Ici on pourrait implémenter la logique de rate limiting
            return f(*args, **kwargs)
        return wrapper
    return decorator

def security_rate_limit(limit=10, window=60):
    """Décorateur pour la limitation de taux sécurisée"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, abort
            
            ip_address = get_remote_address()
            rate_limiter = AdvancedRateLimiter()
            
            if rate_limiter.is_rate_limited(ip_address, limit, window):
                abort(429)  # Too Many Requests
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def login_rate_limit():
    """Décorateur spécialisé pour les connexions"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, abort, jsonify
            
            ip_address = get_remote_address()
            rate_limiter = SecurityRateLimiter()
            
            allowed, message = rate_limiter.check_login_rate_limit(ip_address)
            if not allowed:
                return jsonify({'error': message}), 429
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Configuration des limites par route
RATE_LIMITS = {
    'login': "5 per minute",
    'register': "3 per hour", 
    'password_reset': "3 per hour",
    'api': "100 per hour",
    'upload': "10 per hour",
    'search': "50 per minute",
    'admin': "200 per hour",
    'default': "1000 per hour"
}

def get_rate_limit_for_route(route_name):
    """Obtient la limite de taux pour une route"""
    return RATE_LIMITS.get(route_name, RATE_LIMITS['default'])

def apply_rate_limits_to_app(app, limiter):
    """Applique les limites de taux à l'application"""
    
    # Limites globales
    @app.before_request
    def before_request():
        # Vérifier les limites globales
        pass
    
    # Limites spécifiques par route
    @limiter.limit("5 per minute", methods=["POST"])
    def login_route():
        pass
    
    @limiter.limit("3 per hour", methods=["POST"])
    def register_route():
        pass
    
    @limiter.limit("100 per hour", methods=["GET", "POST"])
    def api_routes():
        pass
    
    @limiter.limit("10 per hour", methods=["POST"])
    def upload_routes():
        pass
    
    @limiter.limit("50 per minute", methods=["GET"])
    def search_routes():
        pass











