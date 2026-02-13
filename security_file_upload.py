#!/usr/bin/env python3
"""
Module de sécurité pour les fichiers uploadés
"""

import os
import hashlib
import magic
from PIL import Image
from flask import current_app, request
import secrets
import mimetypes
from werkzeug.utils import secure_filename
import logging
logger = logging.getLogger(__name__)

class FileUploadSecurity:
    """Classe pour la sécurité des fichiers uploadés"""
    
    # Extensions autorisées par type de fichier
    ALLOWED_EXTENSIONS = {
        'images': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'},
        'documents': {'.pdf', '.doc', '.docx', '.txt', '.rtf'},
        'spreadsheets': {'.xls', '.xlsx', '.csv'},
        'presentations': {'.ppt', '.pptx'},
        'archives': {'.zip', '.rar', '.7z', '.tar', '.gz'},
        'audio': {'.mp3', '.wav', '.flac', '.aac', '.ogg'},
        'video': {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
    }
    
    # Types MIME autorisés
    ALLOWED_MIME_TYPES = {
        'images': {
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
        },
        'documents': {
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain', 'application/rtf'
        },
        'spreadsheets': {
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv'
        },
        'presentations': {
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        },
        'archives': {
            'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
            'application/x-tar', 'application/gzip'
        },
        'audio': {
            'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac', 'audio/ogg'
        },
        'video': {
            'video/mp4', 'video/avi', 'video/quicktime', 'video/x-ms-wmv',
            'video/x-flv', 'video/webm'
        }
    }
    
    # Tailles maximales par type (en bytes)
    MAX_FILE_SIZES = {
        'images': 10 * 1024 * 1024,  # 10 MB
        'documents': 50 * 1024 * 1024,  # 50 MB
        'spreadsheets': 20 * 1024 * 1024,  # 20 MB
        'presentations': 100 * 1024 * 1024,  # 100 MB
        'archives': 200 * 1024 * 1024,  # 200 MB
        'audio': 100 * 1024 * 1024,  # 100 MB
        'video': 500 * 1024 * 1024,  # 500 MB
        'default': 10 * 1024 * 1024  # 10 MB
    }
    
    # Signatures de fichiers dangereux
    DANGEROUS_SIGNATURES = [
        b'<script', b'javascript:', b'vbscript:', b'onload=', b'onerror=',
        b'<?php', b'<%', b'<%=', b'<script', b'<iframe', b'<object',
        b'<embed', b'<applet', b'<meta', b'<link', b'<style'
    ]
    
    def __init__(self):
        self.upload_folder = None
        self.max_content_length = 16 * 1024 * 1024  # 16 MB par défaut
    
    def set_upload_folder(self, folder):
        """Définit le dossier d'upload"""
        self.upload_folder = folder
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
    
    def validate_file(self, file, allowed_types=None, max_size=None):
        """
        Valide un fichier uploadé
        Retourne: (is_valid, error_message, file_info)
        """
        if not file or not file.filename:
            return False, "Aucun fichier fourni", None
        
        # Informations du fichier
        filename = secure_filename(file.filename)
        file_size = len(file.read())
        file.seek(0)  # Remettre le curseur au début
        
        file_info = {
            'filename': filename,
            'original_filename': file.filename,
            'size': file_size,
            'content_type': file.content_type
        }
        
        # Vérifier la taille
        if max_size and file_size > max_size:
            return False, f"Fichier trop volumineux (max: {max_size} bytes)", file_info
        
        # Vérifier l'extension
        if not self._is_extension_allowed(filename, allowed_types):
            return False, "Extension de fichier non autorisée", file_info
        
        # Vérifier le type MIME
        if not self._is_mime_type_allowed(file, allowed_types):
            return False, "Type de fichier non autorisé", file_info
        
        # Vérifier le contenu du fichier
        if not self._is_content_safe(file):
            return False, "Contenu de fichier suspect détecté", file_info
        
        # Vérifier les signatures de fichiers
        if not self._verify_file_signature(file):
            return False, "Signature de fichier invalide", file_info
        
        return True, None, file_info
    
    def _is_extension_allowed(self, filename, allowed_types):
        """Vérifie si l'extension est autorisée"""
        if not allowed_types:
            return True
        
        ext = os.path.splitext(filename)[1].lower()
        
        for file_type in allowed_types:
            if ext in self.ALLOWED_EXTENSIONS.get(file_type, set()):
                return True
        
        return False
    
    def _is_mime_type_allowed(self, file, allowed_types):
        """Vérifie si le type MIME est autorisé"""
        if not allowed_types:
            return True
        
        # Détecter le type MIME réel
        file.seek(0)
        file_content = file.read(1024)
        file.seek(0)
        
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
        except:
            mime_type = file.content_type
        
        for file_type in allowed_types:
            if mime_type in self.ALLOWED_MIME_TYPES.get(file_type, set()):
                return True
        
        return False
    
    def _is_content_safe(self, file):
        """Vérifie si le contenu du fichier est sûr"""
        file.seek(0)
        content = file.read(8192)  # Lire les premiers 8KB
        file.seek(0)
        
        # Vérifier les signatures dangereuses
        for signature in self.DANGEROUS_SIGNATURES:
            if signature in content.lower():
                return False
        
        return True
    
    def _verify_file_signature(self, file):
        """Vérifie la signature du fichier"""
        file.seek(0)
        header = file.read(16)
        file.seek(0)
        
        # Vérifier les signatures de fichiers courants
        if header.startswith(b'\x89PNG'):
            return True  # PNG
        elif header.startswith(b'\xff\xd8\xff'):
            return True  # JPEG
        elif header.startswith(b'GIF8'):
            return True  # GIF
        elif header.startswith(b'%PDF'):
            return True  # PDF
        elif header.startswith(b'PK\x03\x04'):
            return True  # ZIP
        elif header.startswith(b'\x50\x4b'):
            return True  # ZIP/Office
        
        # Pour les fichiers texte, vérifier qu'ils ne contiennent pas de code
        if header.startswith(b'<') or header.startswith(b'<?'):
            # Vérifier si c'est du HTML/XML/script
            content = file.read(1024)
            file.seek(0)
            
            if any(tag in content.lower() for tag in [b'<script', b'<?php', b'<%']):
                return False
        
        return True
    
    def generate_secure_filename(self, original_filename):
        """Génère un nom de fichier sécurisé"""
        # Nettoyer le nom de fichier
        filename = secure_filename(original_filename)
        
        # Ajouter un préfixe aléatoire pour éviter les collisions
        prefix = secrets.token_hex(8)
        name, ext = os.path.splitext(filename)
        
        return f"{prefix}_{name}{ext}"
    
    def save_file(self, file, filename=None, subfolder=None):
        """
        Sauvegarde un fichier de manière sécurisée
        """
        if not self.upload_folder:
            raise ValueError("Dossier d'upload non défini")
        
        # Générer un nom de fichier sécurisé
        if not filename:
            filename = self.generate_secure_filename(file.filename)
        
        # Créer le chemin de destination
        if subfolder:
            dest_folder = os.path.join(self.upload_folder, subfolder)
            os.makedirs(dest_folder, exist_ok=True)
        else:
            dest_folder = self.upload_folder
        
        file_path = os.path.join(dest_folder, filename)
        
        # Sauvegarder le fichier
        file.save(file_path)
        
        # Vérifier que le fichier a été sauvegardé correctement
        if not os.path.exists(file_path):
            raise IOError("Erreur lors de la sauvegarde du fichier")
        
        return file_path
    
    def get_file_hash(self, file_path):
        """Calcule le hash d'un fichier"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def scan_file_for_malware(self, file_path):
        """
        Scanne un fichier pour détecter les malwares
        Note: En production, utiliser un vrai antivirus
        """
        # Vérifications basiques
        with open(file_path, 'rb') as f:
            content = f.read(1024)
            
            # Vérifier les signatures de malwares connus
            malware_signatures = [
                b'eicar', b'test', b'virus', b'malware'
            ]
            
            for signature in malware_signatures:
                if signature in content.lower():
                    return False, f"Signature suspecte détectée: {signature}"
        
        return True, "Fichier propre"
    
    def resize_image(self, file_path, max_width=1920, max_height=1080, quality=85):
        """
        Redimensionne une image pour la sécurité
        """
        try:
            with Image.open(file_path) as img:
                # Vérifier que c'est bien une image
                if img.format not in ['JPEG', 'PNG', 'GIF', 'BMP']:
                    return False, "Format d'image non supporté"
                
                # Redimensionner si nécessaire
                if img.width > max_width or img.height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                    
                    # Sauvegarder avec compression
                    img.save(file_path, optimize=True, quality=quality)
                
                return True, "Image redimensionnée"
                
        except Exception as e:
            return False, f"Erreur lors du redimensionnement: {str(e)}"

class SecureFileUpload:
    """Gestionnaire d'upload de fichiers sécurisé"""
    
    def __init__(self, app=None):
        self.app = app
        self.security = FileUploadSecurity()
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le gestionnaire d'upload"""
        self.app = app
        
        # Configuration
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
        self.security.set_upload_folder(app.config.get('UPLOAD_FOLDER', 'uploads'))
    
    def upload_file(self, file, allowed_types=None, max_size=None, subfolder=None):
        """
        Upload un fichier de manière sécurisée
        """
        # Valider le fichier
        is_valid, error, file_info = self.security.validate_file(
            file, allowed_types, max_size
        )
        
        if not is_valid:
            return False, error, None
        
        try:
            # Sauvegarder le fichier
            file_path = self.security.save_file(
                file, 
                subfolder=subfolder
            )
            
            # Scanner le fichier
            is_clean, scan_result = self.security.scan_file_for_malware(file_path)
            if not is_clean:
                os.remove(file_path)
                return False, f"Fichier suspect: {scan_result}", None
            
            # Redimensionner les images
            if file_info['content_type'].startswith('image/'):
                success, result = self.security.resize_image(file_path)
                if not success:
                    current_app.logger.warning(f"Erreur redimensionnement: {result}")
            
            # Calculer le hash
            file_hash = self.security.get_file_hash(file_path)
            
            # Informations finales
            file_info.update({
                'file_path': file_path,
                'file_hash': file_hash,
                'upload_time': datetime.now()
            })
            
            return True, "Fichier uploadé avec succès", file_info
            
        except Exception as e:
            return False, f"Erreur lors de l'upload: {str(e)}", None

# Décorateurs de sécurité
def secure_file_upload(allowed_types=None, max_size=None):
    """
    Décorateur pour sécuriser l'upload de fichiers
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, flash, redirect, url_for
            
            if 'file' not in request.files:
                flash('Aucun fichier sélectionné', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('Aucun fichier sélectionné', 'error')
                return redirect(request.url)
            
            # Valider le fichier
            security = FileUploadSecurity()
            is_valid, error, file_info = security.validate_file(
                file, allowed_types, max_size
            )
            
            if not is_valid:
                flash(f'Fichier invalide: {error}', 'error')
                return redirect(request.url)
            
            # Ajouter les informations du fichier à la requête
            request.secure_file_info = file_info
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def require_file_type(allowed_types):
    """
    Décorateur pour exiger un type de fichier spécifique
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, flash, redirect, url_for

            if 'file' not in request.files:
                flash('Aucun fichier sélectionné', 'error')
                return redirect(request.url)

            file = request.files['file']
            if file.filename == '':
                flash('Aucun fichier sélectionné', 'error')
                return redirect(request.url)

            # Vérifier le type
            security = FileUploadSecurity()
            if not security._is_extension_allowed(file.filename, allowed_types):
                flash('Type de fichier non autorisé', 'error')
                return redirect(request.url)

            return f(*args, **kwargs)

        return wrapper
    return decorator











