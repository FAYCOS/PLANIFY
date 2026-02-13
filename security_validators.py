#!/usr/bin/env python3
"""
Module de validation et sanitisation pour la sécurité
"""

import re
import html
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
import logging
logger = logging.getLogger(__name__)

class SecurityValidator:
    """Classe pour la validation et sanitisation des données"""
    
    # Patterns de validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^[\+]?[0-9\s\-\(\)]{10,20}$')
    ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.]+$')
    SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.\@\(\)\:\/]+$')
    
    # Caractères dangereux à filtrer
    DANGEROUS_CHARS = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`', '$']
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\'|\"|;|\-\-)',
        r'(\b(script|javascript|vbscript|onload|onerror)\b)'
    ]
    
    @staticmethod
    def sanitize_string(text):
        """
        Sanitise une chaîne de caractères pour éviter les attaques XSS
        """
        if not text:
            return ""
        
        # Échapper les caractères HTML
        text = html.escape(str(text), quote=True)
        
        # Supprimer les caractères dangereux
        for char in SecurityValidator.DANGEROUS_CHARS:
            text = text.replace(char, '')
        
        # Vérifier les patterns d'injection SQL
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError("Contenu suspect détecté")
        
        return text.strip()
    
    @staticmethod
    def validate_email(email):
        """
        Valide une adresse email
        """
        if not email:
            return False
        
        email = email.strip().lower()
        if not SecurityValidator.EMAIL_PATTERN.match(email):
            raise ValueError("Format d'email invalide")
        
        # Vérifier la longueur
        if len(email) > 254:
            raise ValueError("Email trop long")
        
        return email
    
    @staticmethod
    def validate_phone(phone):
        """
        Valide un numéro de téléphone
        """
        if not phone:
            return None
        
        phone = phone.strip()
        if not SecurityValidator.PHONE_PATTERN.match(phone):
            raise ValueError("Format de téléphone invalide")
        
        return phone
    
    @staticmethod
    def validate_password(password):
        """
        Valide un mot de passe selon les critères de sécurité
        """
        if not password:
            raise ValueError("Mot de passe requis")
        
        if len(password) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        
        if len(password) > 128:
            raise ValueError("Le mot de passe est trop long")
        
        # Vérifier la complexité
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule, une minuscule et un chiffre")
        
        return password
    
    @staticmethod
    def validate_date(date_str, field_name="date"):
        """
        Valide une date
        """
        if not date_str:
            return None
        
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Vérifier que la date n'est pas trop ancienne ou future
            today = date.today()
            if parsed_date < date(1900, 1, 1):
                raise ValueError(f"{field_name} trop ancienne")
            
            if parsed_date > date(2100, 12, 31):
                raise ValueError(f"{field_name} trop future")
            
            return parsed_date
        except ValueError as e:
            raise ValueError(f"Format de {field_name} invalide: {str(e)}")
    
    @staticmethod
    def validate_time(time_str, field_name="heure"):
        """
        Valide une heure
        """
        if not time_str:
            return None
        
        try:
            parsed_time = datetime.strptime(time_str, '%H:%M').time()
            return parsed_time
        except ValueError:
            raise ValueError(f"Format de {field_name} invalide")
    
    @staticmethod
    def validate_number(value, field_name="nombre", min_val=None, max_val=None):
        """
        Valide un nombre
        """
        if value is None:
            return None
        
        try:
            num = float(value)
            
            if min_val is not None and num < min_val:
                raise ValueError(f"{field_name} doit être >= {min_val}")
            
            if max_val is not None and num > max_val:
                raise ValueError(f"{field_name} doit être <= {max_val}")
            
            return num
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} invalide")
    
    @staticmethod
    def validate_file_upload(filename, allowed_extensions=None, max_size_mb=10):
        """
        Valide un fichier uploadé
        """
        if not filename:
            raise ValueError("Nom de fichier requis")
        
        # Vérifier l'extension
        if allowed_extensions:
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if ext not in allowed_extensions:
                raise ValueError(f"Extension non autorisée. Autorisées: {', '.join(allowed_extensions)}")
        
        # Vérifier la longueur du nom
        if len(filename) > 255:
            raise ValueError("Nom de fichier trop long")
        
        # Vérifier les caractères dangereux
        if any(char in filename for char in ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            raise ValueError("Nom de fichier contient des caractères non autorisés")
        
        return filename
    
    @staticmethod
    def hash_password(password):
        """
        Hash un mot de passe de manière sécurisée
        """
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    @staticmethod
    def verify_password(password_hash, password):
        """
        Vérifie un mot de passe
        """
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def validate_user_input(data, required_fields=None, optional_fields=None):
        """
        Valide les données d'entrée utilisateur de manière globale
        """
        if not isinstance(data, dict):
            raise ValueError("Les données doivent être un dictionnaire")
        
        validated_data = {}
        
        # Vérifier les champs requis
        if required_fields:
            for field in required_fields:
                if field not in data or not data[field]:
                    raise ValueError(f"Le champ '{field}' est requis")
        
        # Valider chaque champ
        for key, value in data.items():
            if value is None or value == '':
                validated_data[key] = None
                continue
            
            # Sanitisation basique
            if isinstance(value, str):
                validated_data[key] = SecurityValidator.sanitize_string(value)
            else:
                validated_data[key] = value
        
        return validated_data

class SecurityLogger:
    """Classe pour logger les événements de sécurité"""
    
    @staticmethod
    def log_security_event(event_type, user_id=None, ip_address=None, details=None):
        """
        Log un événement de sécurité
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] SECURITY: {event_type}"
        
        if user_id:
            log_entry += f" | User: {user_id}"
        
        if ip_address:
            log_entry += f" | IP: {ip_address}"
        
        if details:
            log_entry += f" | Details: {details}"
        
        # Log dans la console (en production, utiliser un vrai système de logs)
        logger.info(log_entry)
        
        # En production, on pourrait aussi logger dans un fichier ou une base de données
        # with open('security.log', 'a') as f:
        #     f.write(log_entry + '\n')
    
    @staticmethod
    def log_failed_login(username, ip_address):
        """Log une tentative de connexion échouée"""
        SecurityLogger.log_security_event(
            "FAILED_LOGIN",
            user_id=username,
            ip_address=ip_address,
            details="Tentative de connexion échouée"
        )
    
    @staticmethod
    def log_successful_login(user_id, ip_address):
        """Log une connexion réussie"""
        SecurityLogger.log_security_event(
            "SUCCESSFUL_LOGIN",
            user_id=user_id,
            ip_address=ip_address,
            details="Connexion réussie"
        )
    
    @staticmethod
    def log_suspicious_activity(activity, user_id=None, ip_address=None, details=None):
        """Log une activité suspecte"""
        SecurityLogger.log_security_event(
            "SUSPICIOUS_ACTIVITY",
            user_id=user_id,
            ip_address=ip_address,
            details=f"{activity}: {details}"
        )











