#!/usr/bin/env python3
"""
Module de sécurité des mots de passe
"""

import re
import hashlib
import secrets
import string
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import logging
logger = logging.getLogger(__name__)

class PasswordSecurity:
    """Classe pour la sécurité des mots de passe"""
    
    # Mots de passe communs à éviter
    COMMON_PASSWORDS = [
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey',
        'dragon', 'master', 'hello', 'login', 'pass', '1234',
        'test', 'user', 'guest', 'root', 'toor', 'admin123'
    ]
    
    # Patterns de mots de passe faibles
    WEAK_PATTERNS = [
        r'^.{1,7}$',  # Trop court
        r'^[0-9]+$',  # Que des chiffres
        r'^[a-zA-Z]+$',  # Que des lettres
        r'^[a-z]+$',  # Que des minuscules
        r'^[A-Z]+$',  # Que des majuscules
        r'(.)\1{2,}',  # Répétition de caractères
        r'123456',  # Séquences numériques
        r'qwerty',  # Séquences clavier
        r'password',  # Mot "password"
        r'admin',  # Mot "admin"
    ]
    
    def __init__(self):
        self.min_length = 8
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special = True
        self.max_common_ratio = 0.7  # Maximum 70% de similarité avec mots communs
    
    def validate_password_strength(self, password):
        """
        Valide la force d'un mot de passe
        Retourne: (is_valid, score, issues)
        """
        if not password:
            return False, 0, ["Mot de passe requis"]
        
        issues = []
        score = 0
        
        # Vérifier la longueur
        if len(password) < self.min_length:
            issues.append(f"Le mot de passe doit contenir au moins {self.min_length} caractères")
        else:
            score += 1
        
        if len(password) > self.max_length:
            issues.append(f"Le mot de passe ne peut pas dépasser {self.max_length} caractères")
            return False, score, issues
        
        # Vérifier les caractères requis
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            issues.append("Le mot de passe doit contenir au moins une majuscule")
        else:
            score += 1
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            issues.append("Le mot de passe doit contenir au moins une minuscule")
        else:
            score += 1
        
        if self.require_digits and not re.search(r'[0-9]', password):
            issues.append("Le mot de passe doit contenir au moins un chiffre")
        else:
            score += 1
        
        if self.require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            issues.append("Le mot de passe doit contenir au moins un caractère spécial")
        else:
            score += 1
        
        # Vérifier les patterns faibles
        for pattern in self.WEAK_PATTERNS:
            if re.search(pattern, password, re.IGNORECASE):
                issues.append("Le mot de passe contient des patterns faibles")
                score -= 1
                break
        
        # Vérifier les mots de passe communs
        password_lower = password.lower()
        for common in self.COMMON_PASSWORDS:
            if common in password_lower:
                issues.append("Le mot de passe contient des mots communs")
                score -= 2
                break
        
        # Vérifier la similarité avec les mots communs
        similarity = self._calculate_similarity(password)
        if similarity > self.max_common_ratio:
            issues.append("Le mot de passe est trop similaire aux mots communs")
            score -= 1
        
        # Bonus pour la longueur
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        
        # Bonus pour la diversité
        unique_chars = len(set(password))
        if unique_chars >= 8:
            score += 1
        
        is_valid = len(issues) == 0 and score >= 3
        return is_valid, score, issues
    
    def _calculate_similarity(self, password):
        """Calcule la similarité avec les mots de passe communs"""
        password_lower = password.lower()
        max_similarity = 0
        
        for common in self.COMMON_PASSWORDS:
            if common in password_lower:
                similarity = len(common) / len(password_lower)
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def generate_secure_password(self, length=12, include_special=True):
        """
        Génère un mot de passe sécurisé
        """
        characters = string.ascii_letters + string.digits
        if include_special:
            characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # S'assurer qu'on a au moins un caractère de chaque type
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits)
        ]
        
        if include_special:
            password.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))
        
        # Remplir le reste
        for _ in range(length - len(password)):
            password.append(secrets.choice(characters))
        
        # Mélanger
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def hash_password(self, password, method='pbkdf2:sha256'):
        """
        Hash un mot de passe de manière sécurisée
        """
        return generate_password_hash(password, method=method, salt_length=16)
    
    def verify_password(self, password_hash, password):
        """
        Vérifie un mot de passe
        """
        return check_password_hash(password_hash, password)
    
    def check_password_history(self, new_password, password_history, max_history=5):
        """
        Vérifie que le nouveau mot de passe n'est pas dans l'historique
        """
        for old_hash in password_history[-max_history:]:
            if self.verify_password(old_hash, new_password):
                return False, "Le mot de passe a déjà été utilisé récemment"
        
        return True, None
    
    def get_password_strength_level(self, score):
        """
        Retourne le niveau de force du mot de passe
        """
        if score < 2:
            return "Très faible", "red"
        elif score < 4:
            return "Faible", "orange"
        elif score < 6:
            return "Moyen", "yellow"
        elif score < 8:
            return "Fort", "lightgreen"
        else:
            return "Très fort", "green"

class PasswordPolicy:
    """Politique de mots de passe"""
    
    def __init__(self):
        self.min_length = 8
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special = True
        self.max_age_days = 90  # Expiration après 90 jours
        self.history_size = 5  # Garder 5 anciens mots de passe
        self.lockout_attempts = 5  # Blocage après 5 tentatives
        self.lockout_duration = 30  # 30 minutes de blocage
    
    def validate_policy(self, password, user=None):
        """
        Valide un mot de passe selon la politique
        """
        validator = PasswordSecurity()
        is_valid, score, issues = validator.validate_password_strength(password)
        
        # Vérifications supplémentaires
        if user and hasattr(user, 'password_history'):
            history_valid, history_msg = validator.check_password_history(
                password, user.password_history, self.history_size
            )
            if not history_valid:
                issues.append(history_msg)
                is_valid = False
        
        return is_valid, score, issues
    
    def should_expire_password(self, user):
        """
        Vérifie si un mot de passe doit expirer
        """
        if not hasattr(user, 'password_changed_at'):
            return True
        
        if user.password_changed_at is None:
            return True
        
        days_since_change = (datetime.now() - user.password_changed_at).days
        return days_since_change >= self.max_age_days

class PasswordManager:
    """Gestionnaire de mots de passe"""
    
    def __init__(self):
        self.security = PasswordSecurity()
        self.policy = PasswordPolicy()
    
    def create_password(self, password, user=None):
        """
        Crée un nouveau mot de passe avec validation
        """
        # Valider selon la politique
        is_valid, score, issues = self.policy.validate_policy(password, user)
        
        if not is_valid:
            return False, issues
        
        # Hasher le mot de passe
        password_hash = self.security.hash_password(password)
        
        return True, password_hash
    
    def change_password(self, user, old_password, new_password):
        """
        Change le mot de passe d'un utilisateur
        """
        # Vérifier l'ancien mot de passe
        if not self.security.verify_password(user.password_hash, old_password):
            return False, "Ancien mot de passe incorrect"
        
        # Valider le nouveau mot de passe
        is_valid, issues = self.create_password(new_password, user)
        if not is_valid:
            return False, issues
        
        # Mettre à jour
        user.password_hash = is_valid
        user.password_changed_at = datetime.now()
        
        # Ajouter à l'historique
        if not hasattr(user, 'password_history'):
            user.password_history = []
        
        user.password_history.append(user.password_hash)
        if len(user.password_history) > self.policy.history_size:
            user.password_history.pop(0)
        
        return True, "Mot de passe changé avec succès"
    
    def reset_password(self, user, new_password):
        """
        Réinitialise le mot de passe d'un utilisateur
        """
        is_valid, result = self.create_password(new_password, user)
        if not is_valid:
            return False, result
        
        user.password_hash = result
        user.password_changed_at = datetime.now()
        user.password_history = [result]
        
        return True, "Mot de passe réinitialisé avec succès"

# Fonctions utilitaires
def generate_secure_password(length=12):
    """Génère un mot de passe sécurisé"""
    security = PasswordSecurity()
    return security.generate_secure_password(length)

def validate_password_strength(password):
    """Valide la force d'un mot de passe"""
    security = PasswordSecurity()
    return security.validate_password_strength(password)

def hash_password(password):
    """Hash un mot de passe"""
    security = PasswordSecurity()
    return security.hash_password(password)

def verify_password(password_hash, password):
    """Vérifie un mot de passe"""
    security = PasswordSecurity()
    return security.verify_password(password_hash, password)











