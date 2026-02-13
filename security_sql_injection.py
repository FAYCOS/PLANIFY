#!/usr/bin/env python3
"""
Module de protection contre les injections SQL
"""

import re
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
import logging

class SQLInjectionProtection:
    """Classe pour la protection contre les injections SQL"""
    
    # Patterns d'injection SQL courants
    SQL_INJECTION_PATTERNS = [
        # Injection basique
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\'|\"|;|\-\-)",
        r"(\b(script|javascript|vbscript|onload|onerror)\b)",
        
        # Injection avancée
        r"(\bUNION\s+SELECT\b)",
        r"(\bOR\s+1\s*=\s*1\b)",
        r"(\bAND\s+1\s*=\s*1\b)",
        r"(\bOR\s+\'\w+\'\s*=\s*\'\w+\'\b)",
        r"(\bAND\s+\'\w+\'\s*=\s*\'\w+\'\b)",
        
        # Injection de commentaires
        r"(\/\*.*?\*\/)",
        r"(\-\-.*)",
        r"(\#.*)",
        
        # Injection de fonctions
        r"(\b(SUBSTRING|CHAR|ASCII|LENGTH|CONCAT)\b)",
        r"(\b(CAST|CONVERT|ISNULL|COALESCE)\b)",
        r"(\b(WAITFOR|DELAY|BENCHMARK)\b)",
        
        # Injection de base de données
        r"(\b(INFORMATION_SCHEMA|SYSOBJECTS|SYSUSERS)\b)",
        r"(\b(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b)",
        r"(\b(USER|DATABASE|VERSION|CONNECTION_ID)\b)",
        
        # Injection de commandes système
        r"(\b(EXEC|EXECUTE|SP_EXECUTESQL)\b)",
        r"(\b(OPENROWSET|OPENDATASOURCE)\b)",
        r"(\b(BCP|BULK\s+INSERT)\b)",
    ]
    
    # Caractères dangereux
    DANGEROUS_CHARS = [
        "'", '"', ';', '--', '/*', '*/', '\\', '`',
        '(', ')', '[', ']', '{', '}', '<', '>',
        '|', '&', '$', '!', '@', '#', '%', '^'
    ]
    
    # Mots-clés SQL dangereux
    DANGEROUS_KEYWORDS = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'EXEC', 'EXECUTE', 'UNION', 'OR', 'AND', 'WHERE', 'FROM', 'INTO',
        'VALUES', 'SET', 'TABLE', 'DATABASE', 'INDEX', 'VIEW', 'TRIGGER',
        'PROCEDURE', 'FUNCTION', 'CURSOR', 'TRANSACTION', 'COMMIT', 'ROLLBACK'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.blocked_attempts = set()
        self.suspicious_ips = {}
    
    def detect_sql_injection(self, input_string):
        """
        Détecte une tentative d'injection SQL
        Retourne: (is_injection, confidence, details)
        """
        if not input_string:
            return False, 0, []
        
        input_upper = input_string.upper()
        confidence = 0
        details = []
        
        # Vérifier les patterns d'injection
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE):
                confidence += 20
                details.append(f"Pattern d'injection détecté: {pattern}")
        
        # Vérifier les mots-clés dangereux
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in input_upper:
                confidence += 10
                details.append(f"Mot-clé SQL dangereux: {keyword}")
        
        # Vérifier les caractères dangereux
        dangerous_count = sum(1 for char in self.DANGEROUS_CHARS if char in input_string)
        if dangerous_count > 3:
            confidence += 15
            details.append(f"Trop de caractères dangereux: {dangerous_count}")
        
        # Vérifier les tentatives d'échappement
        if '\\' in input_string or '\\x' in input_string:
            confidence += 25
            details.append("Tentative d'échappement détectée")
        
        # Vérifier les commentaires SQL
        if '--' in input_string or '/*' in input_string or '#' in input_string:
            confidence += 30
            details.append("Commentaires SQL détectés")
        
        # Vérifier les tentatives d'union
        if 'UNION' in input_upper and 'SELECT' in input_upper:
            confidence += 40
            details.append("Tentative d'UNION SELECT détectée")
        
        # Vérifier les tentatives d'OR/AND
        if re.search(r'\b(OR|AND)\s+[\w\s=<>]+\b', input_string, re.IGNORECASE):
            confidence += 25
            details.append("Tentative d'injection OR/AND détectée")
        
        is_injection = confidence >= 30
        return is_injection, confidence, details
    
    def sanitize_input(self, input_string, max_length=1000):
        """
        Sanitise une entrée pour éviter les injections SQL
        """
        if not input_string:
            return ""
        
        # Limiter la longueur
        if len(input_string) > max_length:
            input_string = input_string[:max_length]
        
        # Supprimer les caractères dangereux
        for char in self.DANGEROUS_CHARS:
            input_string = input_string.replace(char, '')
        
        # Supprimer les espaces multiples
        input_string = re.sub(r'\s+', ' ', input_string).strip()
        
        # Échapper les caractères spéciaux
        input_string = input_string.replace("'", "''")
        input_string = input_string.replace('"', '""')
        
        return input_string
    
    def validate_sql_query(self, query):
        """
        Valide une requête SQL pour détecter les injections
        """
        if not query:
            return False, "Requête vide"
        
        # Vérifier les patterns d'injection
        is_injection, confidence, details = self.detect_sql_injection(query)
        
        if is_injection:
            return False, f"Injection SQL détectée (confiance: {confidence}%): {', '.join(details)}"
        
        return True, "Requête valide"
    
    def safe_query_execution(self, query, params=None):
        """
        Exécute une requête SQL de manière sécurisée
        """
        try:
            # Valider la requête
            is_valid, message = self.validate_sql_query(query)
            if not is_valid:
                self.logger.warning(f"Requête SQL suspecte bloquée: {message}")
                return False, message
            
            # Utiliser des paramètres liés pour éviter les injections
            if params:
                # Valider les paramètres
                for key, value in params.items():
                    if isinstance(value, str):
                        is_injection, _, _ = self.detect_sql_injection(value)
                        if is_injection:
                            return False, f"Paramètre suspect: {key}"
            
            # Exécuter la requête
            result = current_app.db.session.execute(text(query), params or {})
            return True, result
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erreur SQL: {str(e)}")
            return False, f"Erreur SQL: {str(e)}"
    
    def log_suspicious_activity(self, ip_address, query, details):
        """
        Log une activité suspecte
        """
        self.logger.warning(f"Activité SQL suspecte - IP: {ip_address}, Query: {query}, Details: {details}")
        
        # Ajouter à la liste des IPs suspectes
        if ip_address not in self.suspicious_ips:
            self.suspicious_ips[ip_address] = 0
        self.suspicious_ips[ip_address] += 1
        
        # Bloquer l'IP si trop d'activité suspecte
        if self.suspicious_ips[ip_address] > 5:
            self.blocked_attempts.add(ip_address)
            self.logger.critical(f"IP bloquée pour activité SQL suspecte: {ip_address}")

class SecureDatabaseOperations:
    """Opérations de base de données sécurisées"""
    
    def __init__(self, db):
        self.db = db
        self.protection = SQLInjectionProtection()
    
    def safe_get(self, model, id_value):
        """
        Récupère un enregistrement de manière sécurisée
        """
        try:
            # Valider l'ID
            if not isinstance(id_value, int) or id_value <= 0:
                return None, "ID invalide"
            
            # Utiliser l'ORM pour éviter les injections
            result = self.db.session.get(model, id_value)
            return result, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération: {str(e)}"
    
    def safe_filter(self, model, **filters):
        """
        Filtre des enregistrements de manière sécurisée
        """
        try:
            # Valider les filtres
            for key, value in filters.items():
                if isinstance(value, str):
                    is_injection, _, _ = self.protection.detect_sql_injection(value)
                    if is_injection:
                        return None, f"Valeur de filtre suspecte: {key}"
            
            # Utiliser l'ORM
            query = model.query
            for key, value in filters.items():
                if hasattr(model, key):
                    query = query.filter(getattr(model, key) == value)
                else:
                    return None, f"Champ invalide: {key}"
            
            return query.all(), None
            
        except Exception as e:
            return None, f"Erreur lors du filtrage: {str(e)}"
    
    def safe_create(self, model, data):
        """
        Crée un enregistrement de manière sécurisée
        """
        try:
            # Valider les données
            for key, value in data.items():
                if isinstance(value, str):
                    is_injection, _, _ = self.protection.detect_sql_injection(value)
                    if is_injection:
                        return None, f"Donnée suspecte: {key}"
            
            # Créer l'objet
            obj = model(**data)
            self.db.session.add(obj)
            self.db.session.commit()
            
            return obj, None
            
        except Exception as e:
            self.db.session.rollback()
            return None, f"Erreur lors de la création: {str(e)}"
    
    def safe_update(self, model, id_value, data):
        """
        Met à jour un enregistrement de manière sécurisée
        """
        try:
            # Récupérer l'objet
            obj, error = self.safe_get(model, id_value)
            if error:
                return None, error
            
            if not obj:
                return None, "Enregistrement non trouvé"
            
            # Valider les données
            for key, value in data.items():
                if isinstance(value, str):
                    is_injection, _, _ = self.protection.detect_sql_injection(value)
                    if is_injection:
                        return None, f"Donnée suspecte: {key}"
                
                if hasattr(obj, key):
                    setattr(obj, key, value)
                else:
                    return None, f"Champ invalide: {key}"
            
            self.db.session.commit()
            return obj, None
            
        except Exception as e:
            self.db.session.rollback()
            return None, f"Erreur lors de la mise à jour: {str(e)}"
    
    def safe_delete(self, model, id_value):
        """
        Supprime un enregistrement de manière sécurisée
        """
        try:
            # Récupérer l'objet
            obj, error = self.safe_get(model, id_value)
            if error:
                return False, error
            
            if not obj:
                return False, "Enregistrement non trouvé"
            
            # Supprimer
            self.db.session.delete(obj)
            self.db.session.commit()
            
            return True, None
            
        except Exception as e:
            self.db.session.rollback()
            return False, f"Erreur lors de la suppression: {str(e)}"

# Décorateurs de sécurité
def sql_injection_protection(f):
    """
    Décorateur pour protéger contre les injections SQL
    """
    def wrapper(*args, **kwargs):
        from flask import request, abort
        
        # Vérifier les paramètres de la requête
        for key, value in request.args.items():
            if isinstance(value, str):
                protection = SQLInjectionProtection()
                is_injection, confidence, details = protection.detect_sql_injection(value)
                if is_injection:
                    protection.log_suspicious_activity(
                        request.remote_addr, 
                        f"GET {key}={value}", 
                        details
                    )
                    abort(400)
        
        # Vérifier les données du formulaire
        for key, value in request.form.items():
            if isinstance(value, str):
                protection = SQLInjectionProtection()
                is_injection, confidence, details = protection.detect_sql_injection(value)
                if is_injection:
                    protection.log_suspicious_activity(
                        request.remote_addr, 
                        f"POST {key}={value}", 
                        details
                    )
                    abort(400)
        
        return f(*args, **kwargs)
    return wrapper

def safe_database_operation(f):
    """
    Décorateur pour les opérations de base de données sécurisées
    """
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Erreur de base de données: {str(e)}")
            return {"error": "Erreur de base de données"}, 500
        except Exception as e:
            current_app.logger.error(f"Erreur inattendue: {str(e)}")
            return {"error": "Erreur interne"}, 500
    return wrapper










