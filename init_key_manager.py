#!/usr/bin/env python3
"""
Gestionnaire de clé d'initialisation pour Planify
"""

import os
import json
import hashlib
import secrets
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class InitKeyManager:
    def __init__(self):
        self.key_file = "init_key.json"
        self.key_data = self._load_key_data()
    
    def _load_key_data(self):
        """Charge les données de la clé depuis le fichier"""
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return None
        return None
    
    def _save_key_data(self, data):
        """Sauvegarde les données de la clé dans le fichier"""
        try:
            with open(self.key_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la clé : {e}")
            return False
    
    def is_initialized(self):
        """Vérifie si l'application a été initialisée"""
        return self.key_data is not None and self.key_data.get('initialized', False)
    
    def create_init_key(self, admin_data):
        """Crée une nouvelle clé d'initialisation"""
        # Générer une clé unique
        key = secrets.token_urlsafe(32)
        timestamp = datetime.now().isoformat()
        
        # Créer les données de la clé
        key_data = {
            'initialized': True,
            'key': key,
            'created_at': timestamp,
            'admin_data': {
                'nom': admin_data.get('nom'),
                'prenom': admin_data.get('prenom'),
                'email': admin_data.get('email'),
                'telephone': admin_data.get('telephone'),
                'username': admin_data.get('username')
            },
            'version': '2.1',
            'app_name': 'Planify'
        }
        
        # Sauvegarder la clé
        if self._save_key_data(key_data):
            self.key_data = key_data
            return True
        return False
    
    def get_admin_data(self):
        """Récupère les données de l'administrateur depuis la clé"""
        if self.is_initialized():
            return self.key_data.get('admin_data', {})
        return None
    
    def get_key_info(self):
        """Récupère les informations de la clé"""
        if self.is_initialized():
            return {
                'initialized': True,
                'created_at': self.key_data.get('created_at'),
                'version': self.key_data.get('version'),
                'app_name': self.key_data.get('app_name'),
                'admin_name': f"{self.key_data.get('admin_data', {}).get('prenom', '')} {self.key_data.get('admin_data', {}).get('nom', '')}"
            }
        return {'initialized': False}
    
    def reset_initialization(self):
        """Remet à zéro l'initialisation (supprime la clé)"""
        try:
            if os.path.exists(self.key_file):
                os.remove(self.key_file)
            self.key_data = None
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la clé : {e}")
            return False
    
    def validate_key(self, provided_key):
        """Valide une clé fournie"""
        if not self.is_initialized():
            return False
        
        stored_key = self.key_data.get('key')
        return stored_key == provided_key
    
    def get_status_message(self):
        """Retourne un message de statut"""
        if self.is_initialized():
            admin_data = self.get_admin_data()
            return f"✅ Application initialisée par {admin_data.get('prenom', '')} {admin_data.get('nom', '')} le {self.key_data.get('created_at', '')}"
        else:
            return "⚠️ Application non initialisée - Redirection vers la page d'initialisation"

# Instance globale du gestionnaire de clé
init_key_manager = InitKeyManager()











