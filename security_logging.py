#!/usr/bin/env python3
"""
Module de logs de sécurité
"""

import logging
import json
import os
from datetime import datetime, timedelta
from flask import request, session, current_app
from collections import defaultdict, deque
import hashlib

class SecurityLogger:
    """Classe pour les logs de sécurité"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = None
        self.security_events = deque(maxlen=10000)  # Garder 10000 événements
        self.failed_attempts = defaultdict(list)  # IP -> liste des tentatives
        self.blocked_ips = set()
        self.suspicious_activities = defaultdict(int)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le système de logs"""
        self.app = app
        
        # Configuration du logger
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # Créer le dossier de logs
        log_dir = app.config.get('SECURITY_LOG_DIR', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Handler pour fichier
        file_handler = logging.FileHandler(
            os.path.join(log_dir, 'security.log'),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Handler pour console (développement)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Format des logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Middleware pour logger les requêtes
        @app.before_request
        def log_request():
            self._log_request_start()
        
        @app.after_request
        def log_response(response):
            self._log_request_end(response)
            return response
    
    def _log_request_start(self):
        """Log le début d'une requête"""
        self._log_security_event(
            'REQUEST_START',
            {
                'method': request.method,
                'url': request.url,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'referrer': request.headers.get('Referer', ''),
                'user_id': session.get('user_id'),
                'session_id': session.get('session_token', '')[:8] + '...'
            }
        )
    
    def _log_request_end(self, response):
        """Log la fin d'une requête"""
        self._log_security_event(
            'REQUEST_END',
            {
                'status_code': response.status_code,
                'ip': request.remote_addr,
                'user_id': session.get('user_id'),
                'response_size': len(response.get_data())
            }
        )
    
    def _log_security_event(self, event_type, data):
        """Log un événement de sécurité"""
        timestamp = datetime.now()
        
        event = {
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'data': data,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'session_id': session.get('session_token', '')[:8] + '...' if session.get('session_token') else None
        }
        
        # Ajouter à la liste des événements
        self.security_events.append(event)
        
        # Log selon le niveau
        if event_type in ['LOGIN_SUCCESS', 'LOGOUT', 'PASSWORD_CHANGE']:
            self.logger.info(f"{event_type}: {json.dumps(data)}")
        elif event_type in ['LOGIN_FAILED', 'SUSPICIOUS_ACTIVITY', 'BLOCKED_IP']:
            self.logger.warning(f"{event_type}: {json.dumps(data)}")
        elif event_type in ['SECURITY_VIOLATION', 'MALWARE_DETECTED']:
            self.logger.error(f"{event_type}: {json.dumps(data)}")
        else:
            self.logger.info(f"{event_type}: {json.dumps(data)}")
    
    def log_login_attempt(self, username, success, ip_address=None):
        """Log une tentative de connexion"""
        ip_address = ip_address or request.remote_addr
        
        if success:
            self._log_security_event(
                'LOGIN_SUCCESS',
                {
                    'username': username,
                    'ip': ip_address,
                    'user_agent': request.headers.get('User-Agent', '')
                }
            )
        else:
            self._log_security_event(
                'LOGIN_FAILED',
                {
                    'username': username,
                    'ip': ip_address,
                    'user_agent': request.headers.get('User-Agent', '')
                }
            )
            
            # Enregistrer la tentative échouée
            self.failed_attempts[ip_address].append(datetime.now())
            
            # Vérifier si l'IP doit être bloquée
            if self._should_block_ip(ip_address):
                self.block_ip(ip_address, "Trop de tentatives de connexion échouées")
    
    def log_logout(self, username, ip_address=None):
        """Log une déconnexion"""
        ip_address = ip_address or request.remote_addr
        
        self._log_security_event(
            'LOGOUT',
            {
                'username': username,
                'ip': ip_address
            }
        )
    
    def log_password_change(self, username, success, ip_address=None):
        """Log un changement de mot de passe"""
        ip_address = ip_address or request.remote_addr
        
        event_type = 'PASSWORD_CHANGE_SUCCESS' if success else 'PASSWORD_CHANGE_FAILED'
        
        self._log_security_event(
            event_type,
            {
                'username': username,
                'ip': ip_address
            }
        )
    
    def log_suspicious_activity(self, activity_type, details, ip_address=None):
        """Log une activité suspecte"""
        ip_address = ip_address or request.remote_addr
        
        self._log_security_event(
            'SUSPICIOUS_ACTIVITY',
            {
                'activity_type': activity_type,
                'details': details,
                'ip': ip_address
            }
        )
        
        # Augmenter le compteur d'activités suspectes
        self.suspicious_activities[ip_address] += 1
        
        # Bloquer l'IP si trop d'activités suspectes
        if self.suspicious_activities[ip_address] > 10:
            self.block_ip(ip_address, f"Trop d'activités suspectes: {activity_type}")
    
    def log_security_violation(self, violation_type, details, ip_address=None):
        """Log une violation de sécurité"""
        ip_address = ip_address or request.remote_addr
        
        self._log_security_event(
            'SECURITY_VIOLATION',
            {
                'violation_type': violation_type,
                'details': details,
                'ip': ip_address
            }
        )
    
    def log_file_upload(self, filename, file_size, success, details=None):
        """Log un upload de fichier"""
        self._log_security_event(
            'FILE_UPLOAD',
            {
                'filename': filename,
                'file_size': file_size,
                'success': success,
                'details': details or {},
                'ip': request.remote_addr,
                'user_id': session.get('user_id')
            }
        )
    
    def log_database_operation(self, operation, table, success, details=None):
        """Log une opération de base de données"""
        self._log_security_event(
            'DATABASE_OPERATION',
            {
                'operation': operation,
                'table': table,
                'success': success,
                'details': details or {},
                'ip': request.remote_addr,
                'user_id': session.get('user_id')
            }
        )
    
    def log_api_access(self, endpoint, method, success, response_time=None):
        """Log un accès API"""
        self._log_security_event(
            'API_ACCESS',
            {
                'endpoint': endpoint,
                'method': method,
                'success': success,
                'response_time': response_time,
                'ip': request.remote_addr,
                'user_id': session.get('user_id')
            }
        )
    
    def block_ip(self, ip_address, reason):
        """Bloque une IP"""
        self.blocked_ips.add(ip_address)
        
        self._log_security_event(
            'BLOCKED_IP',
            {
                'ip': ip_address,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def unblock_ip(self, ip_address):
        """Débloque une IP"""
        self.blocked_ips.discard(ip_address)
        
        self._log_security_event(
            'UNBLOCKED_IP',
            {
                'ip': ip_address,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def is_ip_blocked(self, ip_address):
        """Vérifie si une IP est bloquée"""
        return ip_address in self.blocked_ips
    
    def _should_block_ip(self, ip_address):
        """Vérifie si une IP doit être bloquée"""
        if ip_address in self.failed_attempts:
            # Compter les tentatives des dernières 15 minutes
            cutoff = datetime.now() - timedelta(minutes=15)
            recent_attempts = [
                attempt for attempt in self.failed_attempts[ip_address]
                if attempt > cutoff
            ]
            
            return len(recent_attempts) >= 5  # Bloquer après 5 tentatives
    
    def get_security_events(self, event_type=None, limit=100):
        """Récupère les événements de sécurité"""
        events = list(self.security_events)
        
        if event_type:
            events = [e for e in events if e['event_type'] == event_type]
        
        return events[-limit:]
    
    def get_blocked_ips(self):
        """Récupère la liste des IPs bloquées"""
        return list(self.blocked_ips)
    
    def get_suspicious_activities(self):
        """Récupère les activités suspectes"""
        return dict(self.suspicious_activities)
    
    def generate_security_report(self, days=7):
        """Génère un rapport de sécurité"""
        cutoff = datetime.now() - timedelta(days=days)
        
        events = [
            e for e in self.security_events
            if datetime.fromisoformat(e['timestamp']) > cutoff
        ]
        
        report = {
            'period': f"{days} jours",
            'total_events': len(events),
            'login_attempts': len([e for e in events if e['event_type'] == 'LOGIN_ATTEMPT']),
            'failed_logins': len([e for e in events if e['event_type'] == 'LOGIN_FAILED']),
            'suspicious_activities': len([e for e in events if e['event_type'] == 'SUSPICIOUS_ACTIVITY']),
            'security_violations': len([e for e in events if e['event_type'] == 'SECURITY_VIOLATION']),
            'blocked_ips': len(self.blocked_ips),
            'top_ips': self._get_top_ips(events),
            'top_events': self._get_top_events(events)
        }
        
        return report
    
    def _get_top_ips(self, events):
        """Récupère les IPs les plus actives"""
        ip_counts = defaultdict(int)
        for event in events:
            ip_counts[event.get('ip', 'unknown')] += 1
        
        return sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    def _get_top_events(self, events):
        """Récupère les types d'événements les plus fréquents"""
        event_counts = defaultdict(int)
        for event in events:
            event_counts[event['event_type']] += 1
        
        return sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]

class SecurityMonitor:
    """Moniteur de sécurité en temps réel"""
    
    def __init__(self, security_logger):
        self.security_logger = security_logger
        self.alerts = deque(maxlen=1000)
        self.thresholds = {
            'failed_logins_per_hour': 10,
            'suspicious_activities_per_hour': 5,
            'security_violations_per_hour': 3
        }
    
    def check_security_thresholds(self):
        """Vérifie les seuils de sécurité"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Récupérer les événements de la dernière heure
        recent_events = [
            e for e in self.security_logger.security_events
            if datetime.fromisoformat(e['timestamp']) > hour_ago
        ]
        
        # Vérifier les seuils
        self._check_failed_logins(recent_events)
        self._check_suspicious_activities(recent_events)
        self._check_security_violations(recent_events)
    
    def _check_failed_logins(self, events):
        """Vérifie les connexions échouées"""
        failed_logins = [e for e in events if e['event_type'] == 'LOGIN_FAILED']
        
        if len(failed_logins) > self.thresholds['failed_logins_per_hour']:
            self._create_alert(
                'HIGH_FAILED_LOGINS',
                f"Trop de connexions échouées: {len(failed_logins)}"
            )
    
    def _check_suspicious_activities(self, events):
        """Vérifie les activités suspectes"""
        suspicious = [e for e in events if e['event_type'] == 'SUSPICIOUS_ACTIVITY']
        
        if len(suspicious) > self.thresholds['suspicious_activities_per_hour']:
            self._create_alert(
                'HIGH_SUSPICIOUS_ACTIVITY',
                f"Trop d'activités suspectes: {len(suspicious)}"
            )
    
    def _check_security_violations(self, events):
        """Vérifie les violations de sécurité"""
        violations = [e for e in events if e['event_type'] == 'SECURITY_VIOLATION']
        
        if len(violations) > self.thresholds['security_violations_per_hour']:
            self._create_alert(
                'HIGH_SECURITY_VIOLATIONS',
                f"Trop de violations de sécurité: {len(violations)}"
            )
    
    def _create_alert(self, alert_type, message):
        """Crée une alerte de sécurité"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'message': message,
            'severity': 'HIGH'
        }
        
        self.alerts.append(alert)
        
        # Log l'alerte
        self.security_logger.logger.warning(f"ALERT: {alert_type} - {message}")
    
    def get_alerts(self, limit=50):
        """Récupère les alertes"""
        return list(self.alerts)[-limit:]

# Décorateurs de sécurité
def log_security_event(event_type):
    """Décorateur pour logger les événements de sécurité"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                
                # Log l'événement
                if hasattr(current_app, 'security_logger'):
                    current_app.security_logger._log_security_event(
                        event_type,
                        {
                            'function': f.__name__,
                            'success': True,
                            'ip': request.remote_addr,
                            'user_id': session.get('user_id')
                        }
                    )
                
                return result
                
            except Exception as e:
                # Log l'erreur
                if hasattr(current_app, 'security_logger'):
                    current_app.security_logger._log_security_event(
                        f"{event_type}_ERROR",
                        {
                            'function': f.__name__,
                            'error': str(e),
                            'ip': request.remote_addr,
                            'user_id': session.get('user_id')
                        }
                    )
                
                raise
        return wrapper
    return decorator

def monitor_security(f):
    """Décorateur pour surveiller la sécurité"""
    def wrapper(*args, **kwargs):
        from flask import request, session
        
        # Vérifier si l'IP est bloquée
        if hasattr(current_app, 'security_logger'):
            if current_app.security_logger.is_ip_blocked(request.remote_addr):
                return {"error": "IP bloquée"}, 403
        
        # Vérifier les seuils de sécurité
        if hasattr(current_app, 'security_monitor'):
            current_app.security_monitor.check_security_thresholds()
        
        return f(*args, **kwargs)
    return wrapper











