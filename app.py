#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Planify - Application de gestion de missions et services
Version 2.1 - Interface moderne avec Flask
"""

import os
import sqlite3
import smtplib
import csv
import logging
import threading
import uuid
import math
import ssl
import urllib.request
import urllib.parse
import atexit
import base64
from logging.handlers import RotatingFileHandler
import secrets
import time as time_module
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, date, timedelta, time, timezone
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g, make_response, send_from_directory, send_file, has_request_context, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_, event, inspect as sa_inspect, select, text
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import json
import html
import io
from html.parser import HTMLParser
from decimal import Decimal
try:
    from PIL import Image
except Exception:
    Image = None
try:
    import certifi
except Exception:
    certifi = None
try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None
    InvalidToken = Exception
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
# Imports paresseux pour réduire la charge mémoire
from lazy_imports import (
    get_excel_exporter, 
    get_notification_manager,
    get_pdf_generator,
    get_financial_reports,
    lazy_importer
)
from plf_storage import write_plf_from_sqlite, decrypt_plf_to_sqlite, temp_sqlite_path, ensure_dir

# Imports des modules IA et automatisations (v3.0)
from ai_smart_assistant import smart_assistant, init_smart_assistant
from ai_routes import ai_bp
from automation_system import automation_system, init_automation_system
# from google_calendar_config import google_calendar_manager
# from notification_system import notification_manager as notification_system
# from invoice_generator import invoice_generator

# from financial_reports import financial_report_generator

# Configuration du logging (rotation)
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = RotatingFileHandler('planify.log', maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# Horodatage UTC naïf pour compatibilité DB (évite datetime.utcnow déprécié)
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ==================== CHIFFREMENT DONNEES SENSIBLES ====================

def _get_encryption_fernet():
    """Retourne une instance Fernet si la clé d'environnement est valide."""
    if Fernet is None:
        return None
    key = os.environ.get('APP_ENCRYPTION_KEY', '').strip()
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except Exception:
        return None

def encryption_ready():
    return _get_encryption_fernet() is not None

def encrypt_sensitive(value):
    """Chiffre une valeur sensible. Retourne None si vide."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.startswith('enc:'):
        return value
    fernet = _get_encryption_fernet()
    if not fernet:
        raise ValueError("APP_ENCRYPTION_KEY manquante ou invalide")
    token = fernet.encrypt(value.encode('utf-8')).decode('utf-8')
    return f"enc:{token}"

def decrypt_sensitive(value):
    """Déchiffre une valeur sensible si possible."""
    if not value:
        return None
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='ignore')
    value = str(value)
    if not value.startswith('enc:'):
        return value
    fernet = _get_encryption_fernet()
    if not fernet:
        return None
    token = value[4:]
    try:
        return fernet.decrypt(token.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        return None

def mask_sensitive(value, show_last=4):
    if not value:
        return ''
    value = str(value)
    if len(value) <= show_last:
        return '*' * len(value)
    return '*' * (len(value) - show_last) + value[-show_last:]

def get_stripe_secret(parametres):
    if not parametres:
        return None
    return decrypt_sensitive(parametres.stripe_secret_key)

def get_rib_values(parametres):
    if not parametres:
        return {'iban': None, 'bic': None, 'titulaire': None, 'banque': None}
    return {
        'iban': decrypt_sensitive(parametres.rib_iban),
        'bic': decrypt_sensitive(parametres.rib_bic),
        'titulaire': decrypt_sensitive(parametres.rib_titulaire),
        'banque': decrypt_sensitive(parametres.rib_banque),
    }

# ==================== SÉCURITÉ (CSRF + RATE LIMIT) ====================

CSRF_EXEMPT_ENDPOINTS = {
    'scanner_api.scan_material',
    'scanner_api.get_material_by_code',
    'validate_materiel_movement',
    'api_reservation',
    'chat_welcome',
    'chat_message',
    'chat_recommendations',
    'chat_reset',
    'api_signer_devis',
    'rate_prestation',
}

RATE_LIMITS = {
    'login': (10, 60),
    'check_username': (10, 60),
    'chat_welcome': (60, 60),
    'chat_message': (30, 60),
    'chat_recommendations': (30, 60),
    'chat_reset': (10, 60),
    'api_reservation': (20, 60),
    'scanner_api.scan_material': (60, 60),
    'api_signer_devis': (10, 60),
    'stripe_bp.pay_invoice': (30, 60),
    'stripe_bp.pay_quote': (30, 60),
    'stripe_bp.payment_success': (60, 60),
    'stripe_bp.payment_cancel': (60, 60),
    'stripe_bp.stripe_webhook': (120, 60),
}

DEFAULT_API_RATE_LIMIT = (120, 60)

PUBLIC_API_TOKEN_HEADER = 'X-Public-Token'
PUBLIC_API_TOKEN_PARAM = 'public_token'

RESERVATION_STATUTS_BLOQUANTS = {
    'en_attente',
    'en_attente_dj',
    'validee',
    'confirmee'
}

_rate_limit_store = defaultdict(deque)

def _is_rate_limited(endpoint, ip_address, path=None):
    limit_config = RATE_LIMITS.get(endpoint)
    if not limit_config and path and path.startswith('/api/'):
        limit_config = DEFAULT_API_RATE_LIMIT
    if not limit_config:
        return False
    limit, window = limit_config
    key = f"{endpoint}:{ip_address or 'unknown'}"
    now = time_module.time()
    dq = _rate_limit_store[key]
    while dq and now - dq[0] > window:
        dq.popleft()
    if len(dq) >= limit:
        return True
    dq.append(now)
    return False

def _is_same_origin(origin):
    if not origin:
        return True
    try:
        parsed = urllib.parse.urlparse(origin)
        host_origin = urllib.parse.urlparse(request.host_url)
        return parsed.scheme == host_origin.scheme and parsed.netloc == host_origin.netloc
    except Exception:
        return False

def get_public_api_token(parametres=None):
    token = os.environ.get('PUBLIC_API_TOKEN')
    if token:
        return token.strip()
    if not parametres:
        try:
            parametres = ParametresEntreprise.query.first()
        except Exception:
            parametres = None
    if not parametres and app.config.get('DB_READY'):
        try:
            parametres = ParametresEntreprise()
            db.session.add(parametres)
            db.session.commit()
        except Exception:
            db.session.rollback()
            parametres = None
    if not parametres:
        return None
    if ensure_public_api_token(parametres):
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    return (parametres.public_api_token or '').strip() or None

def ensure_public_api_token(parametres):
    if not parametres or parametres.public_api_token:
        return False
    parametres.public_api_token = secrets.token_urlsafe(32)
    return True

def validate_public_api_request():
    if app.config.get('TESTING'):
        return True, None
    origin = request.headers.get('Origin') or request.headers.get('Referer')
    if origin and not _is_same_origin(origin):
        return False, 'Origine non autorisée'
    token = (
        request.headers.get(PUBLIC_API_TOKEN_HEADER)
        or request.args.get(PUBLIC_API_TOKEN_PARAM)
        or request.form.get(PUBLIC_API_TOKEN_PARAM)
    )
    expected = get_public_api_token()
    if not expected:
        return False, 'Token public manquant'
    if not token or not secrets.compare_digest(token, expected):
        return False, 'Token public invalide'
    return True, None

# Configuration de l'application
app = Flask(__name__)

# Configuration pour forcer le rechargement des templates
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configuration des uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB

# Créer le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'profiles'), exist_ok=True)
INSTANCE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(INSTANCE_FOLDER, exist_ok=True)
PLF_FOLDER = os.path.join(INSTANCE_FOLDER, 'databases')
PLF_TEMP_FOLDER = os.path.join(INSTANCE_FOLDER, 'tmp_db')
ensure_dir(PLF_FOLDER)
ensure_dir(PLF_TEMP_FOLDER)

# Identifiant unique de l'appareil (pour la synchronisation offline)
DEVICE_ID_PATH = os.path.join(INSTANCE_FOLDER, 'device_id.txt')

def get_device_id():
    """Retourne un ID unique persistant pour la machine."""
    try:
        if os.path.exists(DEVICE_ID_PATH):
            with open(DEVICE_ID_PATH, 'r', encoding='utf-8') as f:
                device_id = f.read().strip()
                if device_id:
                    return device_id
        device_id = uuid.uuid4().hex
        with open(DEVICE_ID_PATH, 'w', encoding='utf-8') as f:
            f.write(device_id)
        return device_id
    except Exception:
        # Fallback en mémoire si l'écriture échoue
        return uuid.uuid4().hex

DB_READY_DEFAULT = True
# Désactiver la sélection multi-bases (mode mono-base forcé)
PLF_MULTI_DB_ENABLED = False
app.config['PLF_MULTI_DB_ENABLED'] = PLF_MULTI_DB_ENABLED

# Sécurité : Utiliser une variable d'environnement ou générer une clé aléatoire
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Générer une clé aléatoire si aucune n'est définie
    SECRET_KEY = secrets.token_hex(32)
    logger.warning("⚠️  Aucune SECRET_KEY définie dans les variables d'environnement. Une clé temporaire a été générée.")
    logger.info("    Pour la production, définissez la variable d'environnement SECRET_KEY.")

app.config['SECRET_KEY'] = SECRET_KEY
db_path = os.environ.get('PLANIFY_DB_PATH')
if db_path:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(INSTANCE_FOLDER, 'dj_prestations.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DB_READY'] = DB_READY_DEFAULT
app.config['PLF_ACTIVE_PATH'] = None
app.config['PLF_TEMP_PATH'] = None
app.config['PLF_DIRTY'] = False
app.config['PLF_AUTOSAVE_SECONDS'] = 30
app.config['PLF_PASSWORD'] = None

# Configuration de la session pour maintenir la connexion
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 heures
# Sécurité : En production, activer SECURE pour HTTPS uniquement
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Simple API key for external scanner app (override via env var)
app.config['API_KEY'] = os.environ.get('PLANIFY_API_KEY')
if not app.config['API_KEY']:
    logger.warning("⚠️  PLANIFY_API_KEY non défini. L'API scanner est désactivée jusqu'à configuration.")

# Configuration géocodage / cartes
app.config['ADDRESS_VALIDATION_ENABLED'] = os.environ.get('ADDRESS_VALIDATION_ENABLED', '1') == '1'
app.config['GEOCODING_PROVIDER_ENV'] = os.environ.get('GEOCODING_PROVIDER')
app.config['GEOCODING_PROVIDER'] = app.config['GEOCODING_PROVIDER_ENV'] or 'nominatim'  # nominatim | google
app.config['GEOCODING_TIMEOUT'] = float(os.environ.get('GEOCODING_TIMEOUT', '6'))
app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY')
app.config['USE_OSRM_DISTANCE'] = os.environ.get('USE_OSRM_DISTANCE', '1') == '1'

# Synchronisation offline (préparation sync serveur)
app.config['SYNC_ALLOW_INSECURE'] = os.environ.get('SYNC_ALLOW_INSECURE') == '1'
app.config['SYNC_ENABLED_DEFAULT'] = False
app.config['SYNC_INTERVAL_DEFAULT'] = 20
app.config['SYNC_SERVER_MODE'] = os.environ.get('SYNC_SERVER_MODE') == '1'
app.config['SYNC_SERVER_TOKEN'] = os.environ.get('SYNC_SERVER_TOKEN')

# Configuration de la pagination
ITEMS_PER_PAGE = 20  # Nombre d'éléments par page par défaut

# Initialisation de la base de données
db = SQLAlchemy(app)
init_smart_assistant(app, db)


# Les systèmes IA et automatisations sont initialisés plus tard,
# après la création des tables pour éviter les imports/accès précoces aux modèles

# ==================== FONCTIONS DE VALIDATION ====================

import re

def valider_email(email):
    """Valide un format d'email"""
    if not email:
        return False, "L'email est requis"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Format d'email invalide"
    
    if len(email) > 120:
        return False, "L'email est trop long (max 120 caractères)"
    
    return True, "Email valide"

def valider_telephone(telephone):
    """Valide un format de téléphone français"""
    if not telephone:
        return True, "Téléphone optionnel"  # Optionnel
    
    # Nettoyer le numéro
    telephone_clean = re.sub(r'[\s\.\-\(\)]', '', telephone)
    
    # Formats acceptés: 0123456789, +33123456789, 0033123456789
    pattern = r'^(?:(?:\+|00)33|0)[1-9](?:[0-9]{8})$'
    if not re.match(pattern, telephone_clean):
        return False, "Format de téléphone invalide (ex: 0612345678 ou +33612345678)"
    
    return True, "Téléphone valide"

def valider_siret(siret):
    """Valide un numéro SIRET"""
    if not siret:
        return True, "SIRET optionnel"
    
    # Nettoyer le SIRET
    siret_clean = re.sub(r'[\s\.]', '', siret)
    
    if not siret_clean.isdigit() or len(siret_clean) != 14:
        return False, "Le SIRET doit contenir 14 chiffres"
    
    return True, "SIRET valide"

def valider_siren(siren):
    """Valide un numéro SIREN (9 chiffres)."""
    if not siren:
        return False, "SIREN requis"
    siren_clean = re.sub(r'[\s\.]', '', str(siren))
    if not siren_clean.isdigit() or len(siren_clean) != 9:
        return False, "SIREN invalide (9 chiffres requis)"
    return True, "SIREN valide"

def valider_montant(montant, min_value=0, max_value=None):
    """Valide un montant"""
    try:
        montant_float = float(montant)
        
        if montant_float < min_value:
            return False, f"Le montant doit être supérieur ou égal à {min_value}"
        
        if max_value and montant_float > max_value:
            return False, f"Le montant ne peut pas dépasser {max_value}"
        
        return True, "Montant valide"
    except (ValueError, TypeError):
        return False, "Le montant doit être un nombre valide"

def valider_date(date_str, format='%Y-%m-%d'):
    """Valide une date"""
    if not date_str:
        return False, "La date est requise"
    
    try:
        datetime.strptime(date_str, format)
        return True, "Date valide"
    except ValueError:
        return False, f"Format de date invalide (attendu: {format})"

def valider_periode(date_debut_str, date_fin_str):
    """Valide qu'une période est cohérente"""
    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        
        if date_fin < date_debut:
            return False, "La date de fin doit être après la date de début"
        
        return True, "Période valide"
    except ValueError:
        return False, "Dates invalides"

def sanitize_string(text, max_length=None):
    """Nettoie et valide une chaîne de caractères"""
    if not text:
        return ""
    
    # Supprimer les espaces en début/fin
    text = text.strip()
    
    # Limiter la longueur si spécifié
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

class _SafeHTMLSanitizer(HTMLParser):
    """Sanitize limited rich HTML content to reduce XSS risk."""

    _ALLOWED_TAGS = {
        'b', 'strong', 'i', 'em', 'u', 'p', 'br', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a', 'span', 'div'
    }
    _SELF_CLOSING = {'br', 'hr'}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in self._ALLOWED_TAGS:
            return
        if tag in self._SELF_CLOSING:
            self.parts.append(f"<{tag}/>")
            return
        if tag == 'a':
            href = None
            for name, value in attrs:
                if name and name.lower() == 'href':
                    href = value or ''
                    break
            if href and _is_safe_href(href):
                safe_href = html.escape(href.strip(), quote=True)
                self.parts.append(f'<a href="{safe_href}">')
            else:
                self.parts.append('<a>')
            return
        self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self._ALLOWED_TAGS and tag not in self._SELF_CLOSING:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if data:
            self.parts.append(html.escape(data))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

def _is_safe_href(value):
    value = value.strip().lower()
    return value.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', '/'))

def sanitize_rich_html(raw_html):
    """Sanitize limited HTML for rich text fields."""
    if not raw_html:
        return ""
    parser = _SafeHTMLSanitizer()
    parser.feed(str(raw_html))
    parser.close()
    return "".join(parser.parts)

def normalize_whitespace(text):
    """Normalise les espaces sans casser les retours à la ligne."""
    if not text:
        return ""
    # Conserver les retours à la ligne, mais compacter les espaces multiples
    parts = [re.sub(r'[ \t]+', ' ', line.strip()) for line in str(text).splitlines()]
    return "\n".join([p for p in parts if p != ""]).strip()

def normalize_email(email):
    """Normalise un email (lowercase + trim)."""
    if not email:
        return ""
    return str(email).strip().lower()

def normalize_telephone(telephone):
    """Nettoie un numéro de téléphone (supprime espaces/points/parenthèses)."""
    if not telephone:
        return ""
    return re.sub(r'[\s\.\-\(\)]', '', str(telephone))

def parse_date_field(value, label, errors, required=True, fmt='%Y-%m-%d'):
    """Parse une date avec message d'erreur standardisé."""
    if not value:
        if required:
            errors.append(f"{label} est requise")
        return None
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        errors.append(f"{label} invalide (format attendu: {fmt})")
        return None

def parse_time_field(value, label, errors, required=True, fmt='%H:%M'):
    """Parse une heure avec message d'erreur standardisé."""
    if not value:
        if required:
            errors.append(f"{label} est requise")
        return None
    try:
        return datetime.strptime(value, fmt).time()
    except ValueError:
        errors.append(f"{label} invalide (format attendu: {fmt})")
        return None

def parse_float_field(value, label, errors, required=False, min_value=None, max_value=None, default=None):
    """Parse un float avec bornes et erreurs."""
    if value is None or value == "":
        if default is not None:
            return default
        if required:
            errors.append(f"{label} est requis")
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} doit être un nombre valide")
        return None
    if min_value is not None and num < min_value:
        errors.append(f"{label} doit être ≥ {min_value}")
    if max_value is not None and num > max_value:
        errors.append(f"{label} doit être ≤ {max_value}")
    return num

def validate_required_field(value, label, errors):
    """Ajoute une erreur si le champ est vide."""
    if value is None or str(value).strip() == "":
        errors.append(f"{label} est requis")

def validate_date_time_range(date_debut, date_fin, heure_debut, heure_fin, errors):
    """Valide la cohérence date/heure pour une prestation multi-jours."""
    if date_debut and date_fin and date_fin < date_debut:
        errors.append("La date de fin doit être après la date de début")
    if date_debut and date_fin and date_fin == date_debut and heure_debut and heure_fin:
        if heure_fin <= heure_debut:
            errors.append("L'heure de fin doit être après l'heure de début pour une prestation sur la même journée")

def validate_time_range(heure_debut, heure_fin, errors):
    """Valide la cohérence des heures (cross-midnight autorisé)."""
    if heure_debut and heure_fin and heure_debut == heure_fin:
        errors.append("L'heure de fin doit être différente de l'heure de début")

def compute_duration_hours(heure_debut, heure_fin):
    """Calcule la durée en heures en autorisant le passage de minuit."""
    if not heure_debut or not heure_fin:
        return None
    start_minutes = heure_debut.hour * 60 + heure_debut.minute
    end_minutes = heure_fin.hour * 60 + heure_fin.minute
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    return round((end_minutes - start_minutes) / 60, 2)

def compute_reservation_end(date_souhaitee, heure_souhaitee, duree_heures):
    """Calcule la date/heure de fin d'une réservation, en gérant le passage de minuit."""
    if not date_souhaitee or not heure_souhaitee or duree_heures is None:
        return date_souhaitee, heure_souhaitee
    try:
        end_dt = datetime.combine(date_souhaitee, heure_souhaitee) + timedelta(hours=float(duree_heures))
    except Exception:
        return date_souhaitee, heure_souhaitee
    return end_dt.date(), end_dt.time()

DEFAULT_MATERIEL_SORTIE_AVANT_HEURES = 12.0
DEFAULT_MATERIEL_RETOUR_APRES_HEURES = 12.0

RETOUR_MANQUANT_BLOCAGE_JOURS = 7

def _get_materiel_logistique_buffers(parametres=None):
    """Retourne les buffers de logistique (heures avant/après) pour le matériel."""
    sortie_avant = DEFAULT_MATERIEL_SORTIE_AVANT_HEURES
    retour_apres = DEFAULT_MATERIEL_RETOUR_APRES_HEURES
    try:
        if parametres is None:
            parametres = getattr(g, 'parametres', None) or ParametresEntreprise.query.first()
        if parametres:
            if getattr(parametres, 'materiel_sortie_avant_heures', None) is not None:
                sortie_avant = float(parametres.materiel_sortie_avant_heures)
            if getattr(parametres, 'materiel_retour_apres_heures', None) is not None:
                retour_apres = float(parametres.materiel_retour_apres_heures)
    except Exception:
        sortie_avant = DEFAULT_MATERIEL_SORTIE_AVANT_HEURES
        retour_apres = DEFAULT_MATERIEL_RETOUR_APRES_HEURES
    return max(0.0, sortie_avant), max(0.0, retour_apres)

def _build_datetime_range(date_debut, date_fin, heure_debut, heure_fin):
    if not (date_debut and date_fin and heure_debut and heure_fin):
        return None, None
    start_dt = datetime.combine(date_debut, heure_debut)
    end_dt = datetime.combine(date_fin, heure_fin)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return start_dt, end_dt

@contextmanager
def locked_transaction():
    """Verrouille la transaction pour éviter les conflits de stock (SQLite safe)."""
    locked = False
    try:
        if db.engine.dialect.name == 'sqlite':
            db.session.execute(text("BEGIN IMMEDIATE"))
            locked = True
        yield
    except Exception:
        if locked or db.session.in_transaction():
            db.session.rollback()
        raise

def _generate_unique_serial(prefix="AUTO"):
    """Génère un numéro de série unique pour garantir la scannabilité."""
    for _ in range(5):
        candidate = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        if not Materiel.query.filter_by(numero_serie=candidate).first():
            return candidate
    return f"{prefix}-{uuid.uuid4().hex.upper()}"

def _resolve_client_contact(prestation):
    """Tente de retrouver l'email client à partir de la prestation ou des documents liés."""
    if prestation.client_email:
        return prestation.client_email, prestation.client
    devis = Devis.query.filter_by(prestation_id=prestation.id).order_by(Devis.id.desc()).first()
    if devis and devis.client_email:
        return devis.client_email, devis.client_nom or prestation.client
    facture = Facture.query.filter_by(prestation_id=prestation.id).order_by(Facture.id.desc()).first()
    if facture and facture.client_email:
        return facture.client_email, facture.client_nom or prestation.client
    return None, prestation.client

def _client_lookup_key(email, telephone, nom):
    """Construit une clé de déduplication (email > tel > nom)."""
    if email:
        return ('email', email)
    if telephone:
        return ('telephone', telephone)
    if nom:
        return ('nom', nom.lower())
    return None

def get_or_create_client(nom, email=None, telephone=None, categories=None, notes=None):
    """Crée ou retrouve un client (dédoublonnage par email/tel/nom)."""
    nom_clean = normalize_whitespace(nom)
    email_clean = normalize_email(email)
    telephone_clean = normalize_telephone(telephone)
    key = _client_lookup_key(email_clean, telephone_clean, nom_clean)

    client = None
    if email_clean:
        contact = ClientContact.query.filter_by(email=email_clean).first()
        if contact:
            client = contact.client
    if not client and telephone_clean:
        contact = ClientContact.query.filter_by(telephone=telephone_clean).first()
        if contact:
            client = contact.client
    if not client and nom_clean:
        client = Client.query.filter(db.func.lower(Client.nom) == nom_clean.lower()).first()

    if not client:
        client = Client(
            nom=nom_clean or email_clean or telephone_clean or 'Client',
            categories=categories,
            notes=notes
        )
        db.session.add(client)
        db.session.flush()

    if email_clean or telephone_clean:
        contact_filters = []
        if email_clean:
            contact_filters.append(ClientContact.email == email_clean)
        if telephone_clean:
            contact_filters.append(ClientContact.telephone == telephone_clean)
        existing_contact = None
        if contact_filters:
            existing_contact = ClientContact.query.filter(
                ClientContact.client_id == client.id
            ).filter(
                db.or_(*contact_filters)
            ).first()
        if not existing_contact:
            db.session.add(ClientContact(
                client_id=client.id,
                nom=nom_clean,
                email=email_clean or None,
                telephone=telephone_clean or None
            ))

    return client

def backfill_clients():
    """Alimente la table clients depuis devis/factures/prestations (idempotent)."""
    try:
        # Vérifier que la table existe
        db.session.execute(db.text("SELECT 1 FROM clients LIMIT 1"))
    except Exception:
        db.session.rollback()
        return

    try:
        for devis in Devis.query.all():
            if devis.client_id:
                continue
            client = get_or_create_client(devis.client_nom, devis.client_email, devis.client_telephone)
            if client:
                devis.client_id = client.id

        for facture in Facture.query.all():
            if facture.client_id:
                continue
            client = get_or_create_client(facture.client_nom, facture.client_email, facture.client_telephone)
            if client:
                facture.client_id = client.id

        for prestation in Prestation.query.all():
            if prestation.client_id:
                continue
            client = get_or_create_client(prestation.client, prestation.client_email, prestation.client_telephone)
            if client:
                prestation.client_id = client.id

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Backfill clients échoué: {e}")

def _create_or_get_rating_request(prestation, client_email, client_nom):
    """Crée ou réutilise un lien de notation pour une prestation terminée."""
    existing = PrestationRating.query.filter_by(prestation_id=prestation.id).order_by(PrestationRating.created_at.desc()).first()
    now = utcnow()
    if existing and not existing.submitted_at and (not existing.token_expires_at or existing.token_expires_at > now):
        return existing, False
    token = secrets.token_urlsafe(32)
    rating = PrestationRating(
        prestation_id=prestation.id,
        dj_id=prestation.dj_id,
        technicien_id=prestation.technicien_id,
        client_nom=client_nom,
        client_email=client_email,
        token=token,
        token_expires_at=now + timedelta(days=30)
    )
    db.session.add(rating)
    db.session.flush()
    return rating, True

def _send_rating_email(prestation, rating, base_url):
    if not rating or not rating.client_email:
        return False
    try:
        from email_service import EmailService
        email_service = EmailService()
        link = f"{base_url.rstrip('/')}/noter/{rating.token}"
        prestataire_nom = prestation.dj.nom if prestation.dj else "votre prestataire"
        subject = f"Votre avis sur la prestation {prestation.client}"
        body = (
            f"Bonjour {rating.client_nom or ''},\n\n"
            f"Merci pour votre confiance. Nous aimerions recueillir votre avis sur la prestation "
            f"réalisée par {prestataire_nom}.\n\n"
            f"Merci de noter la prestation ici :\n{link}\n\n"
            f"Ce lien est valable 30 jours."
        )
        return email_service.send_email(rating.client_email, subject, body)
    except Exception as e:
        logger.error(f"Erreur envoi email notation: {e}")
        return False

def _get_rating_stats_for_dj(dj_id):
    """Retourne (moyenne, total) des notes DJ."""
    avg = db.session.query(db.func.avg(PrestationRating.rating_dj)).filter(
        PrestationRating.dj_id == dj_id,
        PrestationRating.rating_dj.isnot(None),
        PrestationRating.submitted_at.isnot(None)
    ).scalar()
    count = db.session.query(db.func.count(PrestationRating.id)).filter(
        PrestationRating.dj_id == dj_id,
        PrestationRating.rating_dj.isnot(None),
        PrestationRating.submitted_at.isnot(None)
    ).scalar() or 0
    return (round(float(avg), 2) if avg is not None else None), count

def _get_rating_stats_for_technicien(technicien_id):
    """Retourne (moyenne, total) des notes technicien."""
    avg = db.session.query(db.func.avg(PrestationRating.rating_technicien)).filter(
        PrestationRating.technicien_id == technicien_id,
        PrestationRating.rating_technicien.isnot(None),
        PrestationRating.submitted_at.isnot(None)
    ).scalar()
    count = db.session.query(db.func.count(PrestationRating.id)).filter(
        PrestationRating.technicien_id == technicien_id,
        PrestationRating.rating_technicien.isnot(None),
        PrestationRating.submitted_at.isnot(None)
    ).scalar() or 0
    return (round(float(avg), 2) if avg is not None else None), count

def check_staff_availability(staff_type, staff_id, date_debut, date_fin, heure_debut, heure_fin, exclude_prestation_id=None):
    """Vérifie la disponibilité d'un prestataire (DJ ou technicien) pour une période."""
    if not staff_id:
        return True, "Aucun prestataire sélectionné"

    start_dt, end_dt = _build_datetime_range(date_debut, date_fin, heure_debut, heure_fin)
    if not start_dt or not end_dt:
        return True, "Dates/horaires incomplets"

    query = Prestation.query.filter(Prestation.statut.in_(['planifiee', 'confirmee']))
    if staff_type == 'dj':
        query = query.filter(Prestation.dj_id == staff_id)
    elif staff_type == 'technicien':
        query = query.filter(Prestation.technicien_id == staff_id)
    else:
        return True, "Type de prestataire inconnu"

    if exclude_prestation_id:
        query = query.filter(Prestation.id != exclude_prestation_id)

    conflits = query.all()
    for conflit in conflits:
        conflit_start, conflit_end = _build_datetime_range(
            conflit.date_debut, conflit.date_fin, conflit.heure_debut, conflit.heure_fin
        )
        if not conflit_start or not conflit_end:
            continue
        if not (conflit_end <= start_dt or conflit_start >= end_dt):
            label = "DJ" if staff_type == 'dj' else "technicien"
            return False, f"{label} indisponible (conflit avec {conflit.client} le {conflit.date_debut.strftime('%d/%m/%Y')})"

    return True, "Disponible"

# ==================== GÉOCODAGE & DISTANCES ====================

_geocode_cache = {}
_GEOCODE_CACHE_TTL = 24 * 3600  # 24h

def _cache_get(address):
    entry = _geocode_cache.get(address)
    if not entry:
        return None
    if time_module.time() - entry['ts'] > _GEOCODE_CACHE_TTL:
        _geocode_cache.pop(address, None)
        return None
    return entry['data']

def _cache_set(address, data):
    if len(_geocode_cache) > 500:
        _geocode_cache.clear()
    _geocode_cache[address] = {'ts': time_module.time(), 'data': data}

def build_full_address(adresse, code_postal=None, ville=None):
    parts = [adresse, code_postal, ville]
    return normalize_whitespace(" ".join([p for p in parts if p]))

def geocode_address(address, provider=None, contact_email=None):
    """Retourne dict {lat, lng, formatted, provider} ou (None, error)."""
    address = normalize_whitespace(address)
    if not address:
        return None, "Adresse vide"

    cached = _cache_get(address)
    if cached:
        return cached, None

    provider = provider or app.config.get('GEOCODING_PROVIDER', 'nominatim')
    if provider == 'nominatim' and app.config.get('GEOCODING_PROVIDER_ENV') is None:
        if get_google_maps_api_key():
            provider = 'google'
    timeout = app.config.get('GEOCODING_TIMEOUT', 6)

    def _open_with_context(req):
        ctx = None
        if certifi:
            try:
                ctx = ssl.create_default_context(cafile=certifi.where())
            except Exception:
                ctx = None
        if ctx is None:
            try:
                ctx = ssl.create_default_context()
            except Exception:
                ctx = None
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        except Exception as e:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e):
                logger.warning("Certificat SSL manquant, fallback sur contexte non vérifié pour le géocodage.")
                ctx = ssl._create_unverified_context()
                return urllib.request.urlopen(req, timeout=timeout, context=ctx)
            raise

    try:
        if provider == 'google' and get_google_maps_api_key():
            api_key = get_google_maps_api_key()
            params = {
                'address': address,
                'key': api_key
            }
            url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url)
        else:
            params = {
                'format': 'json',
                'limit': 1,
                'q': address
            }
            url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
            user_agent = f"Planify/2.12 ({contact_email or 'support@planify.local'})"
            req = urllib.request.Request(url, headers={'User-Agent': user_agent})

        with _open_with_context(req) as resp:
            payload = resp.read().decode('utf-8')
        data = json.loads(payload)

        if provider == 'google' and app.config.get('GOOGLE_MAPS_API_KEY'):
            if data.get('status') != 'OK' or not data.get('results'):
                return None, data.get('status') or "Adresse introuvable"
            result = data['results'][0]
            loc = result['geometry']['location']
            geo = {
                'lat': float(loc['lat']),
                'lng': float(loc['lng']),
                'formatted': result.get('formatted_address') or address,
                'provider': 'google'
            }
        else:
            if not data:
                return None, "Adresse introuvable"
            result = data[0]
            geo = {
                'lat': float(result.get('lat')),
                'lng': float(result.get('lon')),
                'formatted': result.get('display_name') or address,
                'provider': 'nominatim'
            }

        _cache_set(address, geo)
        return geo, None
    except Exception as e:
        logger.warning(f"Erreur geocodage: {e}")
        return None, "Impossible de vérifier l'adresse (réseau/API)"

def haversine_km(lat1, lon1, lat2, lon2):
    """Distance à vol d'oiseau en km."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

def route_distance_km(lat1, lon1, lat2, lon2):
    """Distance routière via OSRM (fallback sur vol d'oiseau)."""
    if not app.config.get('USE_OSRM_DISTANCE'):
        return None
    try:
        coords = f"{lon1},{lat1};{lon2},{lat2}"
        url = f"https://router.project-osrm.org/route/v1/driving/{coords}?overview=false"
        req = urllib.request.Request(url, headers={'User-Agent': 'Planify/2.12'})
        timeout = app.config.get('GEOCODING_TIMEOUT', 6)
        def _open_route(req):
            ctx = None
            if certifi:
                try:
                    ctx = ssl.create_default_context(cafile=certifi.where())
                except Exception:
                    ctx = None
            if ctx is None:
                try:
                    ctx = ssl.create_default_context()
                except Exception:
                    ctx = None
            try:
                return urllib.request.urlopen(req, timeout=timeout, context=ctx)
            except Exception as e:
                if 'CERTIFICATE_VERIFY_FAILED' in str(e):
                    logger.warning("Certificat SSL manquant, fallback non vérifié pour OSRM.")
                    ctx = ssl._create_unverified_context()
                    return urllib.request.urlopen(req, timeout=timeout, context=ctx)
                raise
        with _open_route(req) as resp:
            payload = resp.read().decode('utf-8')
        data = json.loads(payload)
        if data.get('code') != 'Ok':
            return None
        routes = data.get('routes') or []
        if not routes:
            return None
        distance_m = routes[0].get('distance')
        if distance_m is None:
            return None
        return distance_m / 1000.0
    except Exception as e:
        logger.warning(f"Erreur OSRM distance: {e}")
        return None

def compute_distance_km(lat1, lon1, lat2, lon2):
    """Distance routière si possible, sinon vol d'oiseau."""
    route_km = route_distance_km(lat1, lon1, lat2, lon2)
    if route_km is not None:
        return round(route_km, 2), 'route'
    return round(haversine_km(lat1, lon1, lat2, lon2), 2), 'air'

def compute_indemnite_km(distance_km, parametres):
    if distance_km is None:
        return None
    distance_gratuite = 30.0
    rate = 0.5
    if parametres:
        if getattr(parametres, 'distance_gratuite_km', None) is not None:
            distance_gratuite = float(parametres.distance_gratuite_km)
        if getattr(parametres, 'frais_deplacement_km', None) is not None:
            rate = float(parametres.frais_deplacement_km)
    km_supp = max(distance_km - distance_gratuite, 0)
    return round(km_supp * rate, 2)

def get_google_maps_api_key():
    """Retourne la clé Google Maps (ENV prioritaire)."""
    key = app.config.get('GOOGLE_MAPS_API_KEY')
    if key:
        return key
    try:
        parametres = ParametresEntreprise.query.first()
        if parametres and parametres.google_maps_api_key:
            return parametres.google_maps_api_key.strip()
    except Exception:
        return None
    return None

def get_company_coordinates(parametres):
    """Retourne (lat, lng) pour l'adresse entreprise. Peut géocoder si besoin."""
    if not parametres:
        return None
    if parametres.adresse_lat and parametres.adresse_lng:
        return float(parametres.adresse_lat), float(parametres.adresse_lng)
    adresse = build_full_address(parametres.adresse, parametres.code_postal, parametres.ville)
    if not adresse:
        return None
    geo, err = geocode_address(adresse, contact_email=parametres.email)
    if geo:
        parametres.adresse_lat = geo['lat']
        parametres.adresse_lng = geo['lng']
        parametres.adresse_formatted = geo['formatted']
        parametres.adresse_geocoded_at = utcnow()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return geo['lat'], geo['lng']
    logger.warning(f"Adresse entreprise non géocodée: {err}")
    return None

def validate_image_upload(file, allowed_extensions):
    """Valide qu'un fichier uploadé est une image conforme."""
    if not file or not file.filename:
        return False, "Fichier invalide"
    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if file_extension not in allowed_extensions:
        return False, "Extension non autorisée"
    if Image:
        try:
            image = Image.open(file.stream)
            image.verify()
            file.stream.seek(0)
            fmt = (image.format or '').lower()
            if fmt == 'jpeg' and file_extension in {'jpg', 'jpeg'}:
                return True, file_extension
            if fmt in allowed_extensions and fmt != 'jpeg':
                return True, file_extension
            return False, "Fichier image invalide"
        except Exception:
            file.stream.seek(0)
            return False, "Fichier image invalide"
    # Fallback si Pillow n'est pas disponible
    return True, file_extension

def validate_document_upload(file, allowed_extensions, max_size_mb=5):
    """Valide un fichier justificatif (PDF/PNG/JPG)."""
    if not file or not file.filename:
        return False, "Fichier invalide"
    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if file_extension not in allowed_extensions:
        return False, "Extension non autorisée"
    try:
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(0)
    except Exception:
        size = 0
        try:
            file.stream.seek(0)
        except Exception:
            pass
    if max_size_mb and size and size > max_size_mb * 1024 * 1024:
        return False, "Fichier trop volumineux"
    if file_extension in {'png', 'jpg', 'jpeg'}:
        return validate_image_upload(file, allowed_extensions)
    if file_extension == 'pdf':
        try:
            header = file.stream.read(4)
            file.stream.seek(0)
            if header != b'%PDF':
                return False, "Fichier PDF invalide"
        except Exception:
            try:
                file.stream.seek(0)
            except Exception:
                pass
            return False, "Fichier PDF invalide"
    return True, file_extension

def valider_formulaire_client(form_data):
    """Valide les données d'un formulaire client"""
    erreurs = []
    
    # Nom (requis)
    if not form_data.get('nom') or not form_data.get('nom').strip():
        erreurs.append("Le nom est requis")
    
    # Email
    if form_data.get('email'):
        valide, message = valider_email(form_data.get('email'))
        if not valide:
            erreurs.append(message)
    
    # Téléphone
    if form_data.get('telephone'):
        valide, message = valider_telephone(form_data.get('telephone'))
        if not valide:
            erreurs.append(message)
    
    return len(erreurs) == 0, erreurs

# Middleware de sécurité global - tous les utilisateurs doivent être connectés
@app.before_request
def require_login():
    """Vérifie que l'utilisateur est connecté pour toutes les routes sauf login, register, first_setup et initialisation"""
    # Routes qui ne nécessitent pas d'authentification
    public_routes = [
        'login', 'register', 'first_setup', 'initialisation', 'verifier_code', 'renvoyer_code',
        'finaliser_initialisation', 'static', 'reservation_client', 'reservation_success',
        'api_reservation', 'zone_clients', 'check_username', 'chat_welcome', 'chat_message',
        'chat_recommendations', 'chat_reset', 'page_signature_devis', 'api_signer_devis',
        'scanner_api.scan_material', 'scanner_api.get_material_by_code',
        'stripe_bp.pay_invoice', 'stripe_bp.pay_quote', 'stripe_bp.payment_success',
        'stripe_bp.payment_cancel', 'stripe_bp.stripe_webhook', 'rate_prestation'
    ]

    # Vérifier si la route actuelle est publique
    if request.endpoint in public_routes:
        # Si c'est une route de réservation et qu'un utilisateur est connecté, le rediriger
        if request.endpoint in ['reservation_client', 'reservation_success'] and 'user_id' in session:
            try:
                user = db.session.get(User, session['user_id'])
            except Exception as e:
                logger.warning(f"Impossible de charger l'utilisateur pour redirection: {e}")
                session.clear()
                return
            if user and user.role in ['admin', 'manager', 'dj', 'technicien']:
                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.role == 'manager':
                    return redirect(url_for('manager_dashboard'))
                elif user.role == 'dj':
                    return redirect(url_for('dj_dashboard'))
                elif user.role == 'technicien':
                    return redirect(url_for('technicien_dashboard'))
        return

    # Vérifier d'abord si l'application a été initialisée
    if app.config.get('DB_READY'):
        try:
            if User.query.count() == 0 and request.endpoint not in public_routes:
                return redirect(url_for('initialisation'))
        except Exception as e:
            logger.warning(f"DB non initialisée (users manquant): {e}")
            try:
                init_db()
            except Exception as init_err:
                logger.warning(f"Init DB échouée: {init_err}")
            try:
                if User.query.count() == 0 and request.endpoint not in public_routes:
                    return redirect(url_for('initialisation'))
            except Exception:
                pass
            return redirect(url_for('login'))
        from init_key_manager import init_key_manager
        if not init_key_manager.is_initialized():
            return redirect(url_for('initialisation'))
    
    # Vérifier si l'utilisateur est connecté
    if 'user_id' not in session:
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Non authentifié'}), 401
        return redirect(url_for('login'))
    
    # Vérifier que l'utilisateur existe toujours en base
    try:
        user = db.session.get(User, session['user_id'])
    except Exception as e:
        logger.warning(f"Impossible de charger l'utilisateur de session: {e}")
        session.clear()
        return redirect(url_for('login'))
    if not user or not user.actif:
        session.clear()
        flash('Votre session a expiré. Veuillez vous reconnecter.', 'error')
        return redirect(url_for('login'))
    
    # Charger l'utilisateur dans g pour l'utiliser dans les templates
    g.user = user
    
    # Initialiser le lazy importer avec les paramètres d'entreprise
    if not hasattr(g, 'parametres_loaded'):
        parametres = ParametresEntreprise.query.first()
        if parametres:
            lazy_importer.set_parametres(parametres)
        g.parametres_loaded = True

@app.before_request
def apply_security_controls():
    """Applique CSRF (pour sessions authentifiées) et rate limiting sur endpoints sensibles."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)

    if app.config.get('TESTING'):
        return None

    endpoint = request.endpoint
    if endpoint:
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        if _is_rate_limited(endpoint, ip_address, request.path):
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': 'Trop de requêtes'}), 429
            flash('Trop de requêtes. Veuillez réessayer plus tard.', 'error')
            return redirect(request.referrer or url_for('login'))

    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        # CSRF uniquement pour les sessions authentifiées
        if session.get('user_id') and endpoint not in CSRF_EXEMPT_ENDPOINTS:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not token or token != session.get('csrf_token'):
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'success': False, 'message': 'CSRF token invalide'}), 400
                return "CSRF token invalide", 400

def is_db_ready():
    return app.config.get('DB_READY') is True and app.config.get('PLF_TEMP_PATH')

def is_devis_locked(devis):
    """Un devis est verrouillé dès qu'il est signé."""
    return bool(getattr(devis, 'est_signe', False))

def is_facture_locked(facture):
    """Une facture est verrouillée dès qu'elle est envoyée ou payée."""
    statut = getattr(facture, 'statut', '') or ''
    return statut in {'envoyee', 'payee', 'partiellement_payee', 'annulee'}

MAX_SIGNATURE_BYTES = 500 * 1024
ALLOWED_SIGNATURE_MIME = {'image/png', 'image/jpeg', 'image/jpg'}

def validate_signature_payload(signature_data):
    """Valide et normalise une signature base64 issue du canvas."""
    if not isinstance(signature_data, str):
        return False, "Signature invalide", None
    signature_data = signature_data.strip()
    if not signature_data:
        return False, "Signature manquante", None

    mime = 'image/png'
    payload = signature_data
    if signature_data.startswith('data:'):
        if ';base64,' not in signature_data:
            return False, "Format de signature invalide", None
        header, payload = signature_data.split(',', 1)
        mime = header.split(';', 1)[0].replace('data:', '', 1).strip().lower()
    if mime not in ALLOWED_SIGNATURE_MIME:
        return False, "Format d’image non autorisé", None
    try:
        decoded = base64.b64decode(payload, validate=True)
    except Exception:
        return False, "Signature illisible", None
    if len(decoded) > MAX_SIGNATURE_BYTES:
        return False, "Signature trop volumineuse", None

    normalized = f"data:{mime};base64,{payload}"
    return True, None, normalized

def generate_document_number(prefix, year=None, width=4):
    """Génère un numéro séquentiel légal par préfixe et année."""
    if year is None:
        year = datetime.now().year
    seq = DocumentSequence.query.filter_by(prefix=prefix, year=year).first()
    if not seq:
        seq = DocumentSequence(prefix=prefix, year=year, last_number=0)
        db.session.add(seq)
        db.session.flush()
    seq.last_number += 1
    return f"{prefix}-{year}-{seq.last_number:0{width}d}"

# Modèles de données
class Local(db.Model):
    __tablename__ = 'locals'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    materiels = db.relationship('Materiel', backref='local', lazy=True)

class AuditLog(db.Model):
    """Journal d'audit pour tracer les modifications importantes"""
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    date_action = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Qui
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user_nom = db.Column(db.String(100))  # Nom complet pour historique
    
    # Quoi
    action = db.Column(db.String(20), nullable=False)  # 'creation', 'modification', 'suppression'
    entite_type = db.Column(db.String(50), nullable=False)  # 'devis', 'facture', 'prestation', etc.
    entite_id = db.Column(db.Integer)  # ID de l'entité modifiée
    entite_nom = db.Column(db.String(200))  # Nom/numéro pour affichage
    
    # Détails
    details = db.Column(db.Text)  # JSON avec les modifications
    ip_address = db.Column(db.String(45))  # IP pour sécurité
    
    # Relation
    user = db.relationship('User', backref='audit_logs')
    
    @staticmethod
    def log_action(action, entite_type, entite_id, entite_nom, details=None, user_id=None):
        """
        Enregistrer une action dans le journal d'audit
        
        Args:
            action: 'creation', 'modification', 'suppression'
            entite_type: 'devis', 'facture', 'prestation', etc.
            entite_id: ID de l'entité
            entite_nom: Nom/numéro pour affichage
            details: Détails supplémentaires (dict ou string)
            user_id: ID de l'utilisateur (si None, prend session)
        """
        try:
            # Récupérer l'utilisateur
            if not user_id and 'user_id' in session:
                user_id = session['user_id']
            
            user_nom = None
            if user_id:
                from flask import current_app
                with current_app.app_context():
                    user = db.session.get(User, user_id)
                    if user:
                        user_nom = f"{user.prenom} {user.nom}"
            
            # Récupérer l'IP
            ip_address = None
            try:
                from flask import request
                ip_address = request.remote_addr
            except:
                pass
            
            # Créer l'entrée d'audit
            audit = AuditLog(
                user_id=user_id,
                user_nom=user_nom,
                action=action,
                entite_type=entite_type,
                entite_id=entite_id,
                entite_nom=entite_nom,
                details=str(details) if details else None,
                ip_address=ip_address
            )
            
            db.session.add(audit)
            db.session.commit()
            
            logger.info(f"📋 Audit: {action} {entite_type} #{entite_id} par {user_nom or 'Système'}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur log audit: {e}")
            # Ne pas faire échouer l'opération principale
            return False

class DocumentSequence(db.Model):
    """Séquence légale pour la numérotation des documents (devis/factures)."""
    __tablename__ = 'document_sequences'

    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(10), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    last_number = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('prefix', 'year', name='uix_document_sequences_prefix_year'),
    )

    def __repr__(self):
        return f'<DocumentSequence {self.prefix}-{self.year}-{self.last_number}>'

class PrestationRating(db.Model):
    """Notation client des prestations (prestataire principal + technicien optionnel)."""
    __tablename__ = 'prestation_ratings'

    id = db.Column(db.Integer, primary_key=True)
    prestation_id = db.Column(db.Integer, db.ForeignKey('prestations.id'), nullable=False)
    dj_id = db.Column(db.Integer, db.ForeignKey('djs.id'), nullable=True)
    technicien_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    client_nom = db.Column(db.String(120))
    client_email = db.Column(db.String(120))

    rating_dj = db.Column(db.Integer)
    rating_technicien = db.Column(db.Integer)
    commentaire = db.Column(db.Text)

    token = db.Column(db.String(128), unique=True, index=True, nullable=False)
    token_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)
    submitted_at = db.Column(db.DateTime)

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    prestation = db.relationship('Prestation', backref='ratings')
    dj = db.relationship('DJ', backref='ratings')
    technicien = db.relationship('User', backref='ratings_technicien')

class GrilleTarifaire(db.Model):
    """Grille tarifaire par type d'événement"""
    __tablename__ = 'grille_tarifaire'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)  # "Mariage", "Anniversaire", etc.
    type_evenement = db.Column(db.String(50), nullable=False, unique=True)  # "mariage", "anniversaire", etc.
    
    # Prix de base
    tarif_horaire_base = db.Column(db.Float, default=100.0)  # Prix par heure de base
    duree_minimum = db.Column(db.Float, default=4.0)  # Durée minimum en heures
    
    # Majorations
    majoration_weekend = db.Column(db.Float, default=0.0)  # % de majoration weekend (ex: 20 = +20%)
    majoration_jour_ferie = db.Column(db.Float, default=0.0)  # % de majoration jour férié
    majoration_nuit = db.Column(db.Float, default=0.0)  # % de majoration après 22h
    
    # Frais fixes
    frais_deplacement_base = db.Column(db.Float, default=50.0)  # Frais de déplacement de base
    frais_deplacement_par_km = db.Column(db.Float, default=0.5)  # €/km au-delà de X km
    distance_gratuite_km = db.Column(db.Float, default=30.0)  # Distance sans frais supplémentaires
    
    # Informations
    description = db.Column(db.Text)  # Description de ce tarif
    actif = db.Column(db.Boolean, default=True)  # Si ce tarif est actif
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_modification = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    def calculer_prix(self, duree_heures, is_weekend=False, is_jour_ferie=False, is_nuit=False, distance_km=0):
        """
        Calculer le prix total basé sur les paramètres
        
        Returns:
            dict: {
                'tarif_horaire': float,
                'cout_horaire': float,
                'frais_deplacement': float,
                'majorations': dict,
                'total': float
            }
        """
        # Durée minimum
        duree_effective = max(duree_heures, self.duree_minimum)
        
        # Tarif horaire de base
        tarif_horaire = self.tarif_horaire_base
        majorations_appliquees = {}
        
        # Appliquer les majorations
        if is_weekend and self.majoration_weekend > 0:
            majoration = tarif_horaire * (self.majoration_weekend / 100)
            tarif_horaire += majoration
            majorations_appliquees['weekend'] = f"+{self.majoration_weekend}%"
        
        if is_jour_ferie and self.majoration_jour_ferie > 0:
            majoration = tarif_horaire * (self.majoration_jour_ferie / 100)
            tarif_horaire += majoration
            majorations_appliquees['jour_ferie'] = f"+{self.majoration_jour_ferie}%"
        
        if is_nuit and self.majoration_nuit > 0:
            majoration = tarif_horaire * (self.majoration_nuit / 100)
            tarif_horaire += majoration
            majorations_appliquees['nuit'] = f"+{self.majoration_nuit}%"
        
        # Coût horaire total
        cout_horaire = tarif_horaire * duree_effective
        
        # Frais de déplacement
        frais_deplacement = self.frais_deplacement_base
        if distance_km > self.distance_gratuite_km:
            km_supplementaires = distance_km - self.distance_gratuite_km
            frais_deplacement += km_supplementaires * self.frais_deplacement_par_km
        
        # Total (sans matériel)
        total = cout_horaire + frais_deplacement
        
        return {
            'tarif_horaire_base': self.tarif_horaire_base,
            'tarif_horaire_final': tarif_horaire,
            'duree_effective': duree_effective,
            'cout_horaire': cout_horaire,
            'frais_deplacement': frais_deplacement,
            'majorations': majorations_appliquees,
            'total_sans_materiel': total
        }

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='dj')  # admin, manager, dj, technicien
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20))
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=utcnow)
    derniere_connexion = db.Column(db.DateTime)
    
    # Nouveaux champs pour le profil
    photo_profil = db.Column(db.String(200))  # Chemin vers la photo
    bio = db.Column(db.Text)  # Biographie/Description
    adresse = db.Column(db.String(200))  # Adresse
    ville = db.Column(db.String(100))  # Ville
    code_postal = db.Column(db.String(10))  # Code postal
    date_naissance = db.Column(db.Date)  # Date de naissance
    
    # Relations
    prestations_crees = db.relationship(
        'Prestation',
        backref='createur_prestation',
        lazy=True,
        foreign_keys='Prestation.createur_id'
    )
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def has_role(self, role):
        """Vérifie si l'utilisateur a un rôle spécifique"""
        return self.role == role
    
    def can_manage_users(self):
        """Peut gérer les utilisateurs (admin uniquement)"""
        return self.role == 'admin'
    
    def can_create_prestations(self):
        """Peut créer des prestations (admin, manager)"""
        return self.role in ['admin', 'manager']
    
    def can_manage_materiel(self):
        """Peut gérer le matériel (admin, manager, technicien)"""
        return self.role in ['admin', 'manager', 'technicien']
    
    def can_view_all_prestations(self):
        """Peut voir toutes les prestations (admin, manager)"""
        return self.role in ['admin', 'manager']
    
    def can_edit_prestations(self):
        """Peut modifier les prestations (admin, manager)"""
        return self.role in ['admin', 'manager']

class DJ(db.Model):
    __tablename__ = 'djs'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(200))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Lien avec l'utilisateur
    
    # Champs pour la synchronisation Google Calendar
    google_calendar_enabled = db.Column(db.Boolean, default=False)
    google_calendar_id = db.Column(db.String(200))  # ID du calendrier Google
    google_access_token = db.Column(db.Text)  # Token d'accès
    google_refresh_token = db.Column(db.Text)  # Token de rafraîchissement
    google_token_expiry = db.Column(db.DateTime)  # Date d'expiration du token
    last_sync = db.Column(db.DateTime)  # Dernière synchronisation
    
    # Relations
    prestations = db.relationship('Prestation', backref='dj', lazy=True)
    user = db.relationship('User', backref='dj_profile', lazy='joined')  # Relation vers User

    @property
    def email(self):
        return self.user.email if self.user and self.user.email else self.contact

    @property
    def telephone(self):
        return self.user.telephone if self.user and self.user.telephone else None

    @property
    def prenom(self):
        if self.user and self.user.prenom:
            return self.user.prenom
        return self.nom.split(' ')[0] if self.nom else ''

    @property
    def specialite_musicale(self):
        return None

    @property
    def specialites(self):
        return None

class ParametresEntreprise(db.Model):
    __tablename__ = 'parametres_entreprise'
    
    id = db.Column(db.Integer, primary_key=True)
    nom_entreprise = db.Column(db.String(200), nullable=False, default='Planify')
    slogan = db.Column(db.String(200))  # Nouveau : slogan/tagline
    adresse = db.Column(db.Text)
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    adresse_lat = db.Column(db.Float)
    adresse_lng = db.Column(db.Float)
    adresse_formatted = db.Column(db.String(255))
    adresse_geocoded_at = db.Column(db.DateTime)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    email_signature = db.Column(db.Text)
    site_web = db.Column(db.String(200))
    google_maps_api_key = db.Column(db.Text)
    siret = db.Column(db.String(20))
    tva_intracommunautaire = db.Column(db.String(20))
    forme_juridique = db.Column(db.String(100))
    capital_social = db.Column(db.String(100))
    rcs_ville = db.Column(db.String(100))
    
    # Google Calendar
    google_calendar_enabled = db.Column(db.Boolean, default=False)
    google_client_id = db.Column(db.String(200))
    google_client_secret = db.Column(db.String(200))
    numero_rcs = db.Column(db.String(100))
    penalites_retard = db.Column(db.String(200))
    escompte = db.Column(db.String(200))
    indemnite_recouvrement = db.Column(db.Float, default=40.0)
    tva_non_applicable = db.Column(db.Boolean, default=False)
    taux_tva_defaut = db.Column(db.Float, default=20.0)
    logo_path = db.Column(db.String(500))  # Chemin vers le logo
    logo_url = db.Column(db.String(500))
    couleur_principale = db.Column(db.String(7), default='#667eea')
    couleur_secondaire = db.Column(db.String(7), default='#764ba2')
    description_courte = db.Column(db.Text)  # Nouveau : description de l'entreprise
    afficher_logo_login = db.Column(db.Boolean, default=True)  # Nouveau : afficher le logo sur l'écran de connexion
    afficher_logo_sidebar = db.Column(db.Boolean, default=True)  # Nouveau : afficher le logo dans la sidebar
    devise = db.Column(db.String(3), default='EUR')
    langue = db.Column(db.String(5), default='fr')
    groq_api_key = db.Column(db.Text)
    terminology_profile = db.Column(db.String(30), default='missions')
    ui_theme = db.Column(db.String(30), default='classic')
    ui_density = db.Column(db.String(30), default='comfortable')
    ui_font = db.Column(db.String(120))
    ui_radius = db.Column(db.Integer, default=14)
    ui_custom_css = db.Column(db.Text)
    show_ai_menu = db.Column(db.Boolean, default=True)
    show_ai_insights = db.Column(db.Boolean, default=True)
    show_quick_actions = db.Column(db.Boolean, default=True)
    show_recent_missions = db.Column(db.Boolean, default=True)
    show_stats_cards = db.Column(db.Boolean, default=True)
    custom_fields_prestation = db.Column(db.Text)
    public_api_token = db.Column(db.String(200))
    signature_entreprise_path = db.Column(db.String(255))
    signature_entreprise_enabled = db.Column(db.Boolean, default=True)
    
    # Modules optionnels - Activation/Désactivation
    module_google_calendar = db.Column(db.Boolean, default=False)
    module_excel_export = db.Column(db.Boolean, default=True)
    module_pdf_generation = db.Column(db.Boolean, default=True)
    module_financial_reports = db.Column(db.Boolean, default=False)
    module_notifications = db.Column(db.Boolean, default=True)
    module_icalendar = db.Column(db.Boolean, default=True)
    distance_gratuite_km = db.Column(db.Float, default=30.0)
    frais_deplacement_km = db.Column(db.Float, default=0.5)
    materiel_sortie_avant_heures = db.Column(db.Float, default=12.0)
    materiel_retour_apres_heures = db.Column(db.Float, default=12.0)

    # Stripe Configuration
    stripe_enabled = db.Column(db.Boolean, default=False)
    stripe_public_key = db.Column(db.String(200))
    stripe_secret_key = db.Column(db.String(200))
    rib_iban = db.Column(db.Text)
    rib_bic = db.Column(db.Text)
    rib_titulaire = db.Column(db.Text)
    rib_banque = db.Column(db.Text)
    
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_modification = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    def __repr__(self):
        return f'<ParametresEntreprise {self.nom_entreprise}>'

class Devis(db.Model):
    __tablename__ = 'devis'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    client_nom = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(100))
    client_telephone = db.Column(db.String(20))
    client_adresse = db.Column(db.Text)
    client_siren = db.Column(db.String(20))
    client_tva = db.Column(db.String(30))
    client_professionnel = db.Column(db.Boolean, default=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    adresse_livraison = db.Column(db.Text)
    nature_operation = db.Column(db.String(120))
    tva_sur_debits = db.Column(db.Boolean, default=False)
    numero_bon_commande = db.Column(db.String(100))
    tva_incluse = db.Column(db.Boolean, default=True)
    
    # Informations de la prestation
    prestation_titre = db.Column(db.String(200), nullable=False)
    prestation_description = db.Column(db.Text)
    date_prestation = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)
    lieu = db.Column(db.String(200), nullable=False)
    
    # Tarification
    tarif_horaire = db.Column(db.Float, nullable=False, default=0.0)
    duree_heures = db.Column(db.Float, nullable=False, default=0.0)
    montant_ht = db.Column(db.Float, nullable=False, default=0.0)
    taux_tva = db.Column(db.Float, default=20.0)
    montant_tva = db.Column(db.Float, default=0.0)
    montant_ttc = db.Column(db.Float, nullable=False, default=0.0)
    
    # Remises et frais
    remise_pourcentage = db.Column(db.Float, default=0.0)
    remise_montant = db.Column(db.Float, default=0.0)
    frais_transport = db.Column(db.Float, default=0.0)
    frais_materiel = db.Column(db.Float, default=0.0)
    
    # Statut et dates
    statut = db.Column(db.String(20), default='brouillon')  # brouillon, envoye, accepte, refuse, expire
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_validite = db.Column(db.Date)
    date_envoi = db.Column(db.DateTime)
    date_acceptation = db.Column(db.DateTime)
    date_annulation = db.Column(db.DateTime)
    
    # Signature électronique
    signature_token = db.Column(db.String(100), unique=True)  # Token unique pour le lien de signature
    signature_image = db.Column(db.Text)  # Signature en base64
    signature_date = db.Column(db.DateTime)  # Date de signature
    signature_ip = db.Column(db.String(50))  # IP du signataire
    est_signe = db.Column(db.Boolean, default=False)  # Statut de signature

    # Contenu personnalisable du devis (éditeur riche)
    contenu_html = db.Column(db.Text)
    
    # Gestion des acomptes
    acompte_requis = db.Column(db.Boolean, default=False)  # Si un acompte est demandé
    acompte_pourcentage = db.Column(db.Float, default=0.0)  # Pourcentage d'acompte (ex: 30.0 pour 30%)
    acompte_montant = db.Column(db.Float, default=0.0)  # Montant d'acompte en euros
    acompte_paye = db.Column(db.Boolean, default=False)  # Si l'acompte a été payé
    date_paiement_acompte = db.Column(db.DateTime)  # Date de paiement de l'acompte
    
    # Stripe
    stripe_payment_intent_id = db.Column(db.String(200))  # ID du Payment Intent Stripe
    stripe_payment_link = db.Column(db.String(500))  # Lien de paiement Stripe
    payment_token = db.Column(db.String(64), unique=True, index=True)
    
    # Relations
    dj_id = db.Column(db.Integer, db.ForeignKey('djs.id'))
    createur_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    prestation_id = db.Column(db.Integer, db.ForeignKey('prestations.id'))
    
    dj = db.relationship('DJ', backref='devis')
    createur = db.relationship('User', backref='devis_crees')
    prestation = db.relationship('Prestation', backref='devis')
    client_ref = db.relationship('Client', backref='devis')
    
    def synchroniser_frais_materiel(self):
        """
        Synchronise le champ frais_materiel avec le coût RÉEL du matériel assigné
        Cette méthode assure la cohérence entre la BDD et le PDF
        """
        if self.prestation_id:
            cout_reel, _ = calculer_cout_materiel_reel(prestation_id=self.prestation_id)
            self.frais_materiel = cout_reel
            return True
        if self.id:
            cout_reel, _ = calculer_cout_materiel_reel(devis_id=self.id)
            self.frais_materiel = cout_reel
            return True
        return False
    
    def calculer_acompte(self):
        """
        Calcule le montant de l'acompte en fonction du pourcentage
        Met à jour acompte_montant automatiquement
        """
        if self.acompte_requis and self.acompte_pourcentage > 0:
            self.acompte_montant = self.montant_ttc * (self.acompte_pourcentage / 100)
        else:
            self.acompte_montant = 0.0
        return self.acompte_montant
    
    def calculer_totaux(self):
        """Calcule automatiquement les totaux du devis"""
        # COHÉRENCE : Synchroniser frais_materiel avec le coût réel
        self.synchroniser_frais_materiel()
        
        # Calcul du montant HT de base
        montant_base = (self.tarif_horaire * self.duree_heures) + self.frais_transport + self.frais_materiel
        
        # Application de la remise (priorité au pourcentage si les deux sont définis)
        remise = 0
        if self.remise_pourcentage and self.remise_pourcentage > 0:
            remise = montant_base * (self.remise_pourcentage / 100)
            # Si pourcentage défini, réinitialiser la remise en montant pour éviter confusion
            self.remise_montant = 0
        elif self.remise_montant and self.remise_montant > 0:
            remise = self.remise_montant
        
        self.montant_ht = max(0, montant_base - remise)
        
        # Calcul de la TVA
        tva_non_applicable = False
        try:
            parametres = ParametresEntreprise.query.first()
            if parametres and parametres.tva_non_applicable:
                tva_non_applicable = True
        except Exception:
            tva_non_applicable = False
        if tva_non_applicable:
            self.taux_tva = 0.0
            self.montant_tva = 0.0
        else:
            self.montant_tva = self.montant_ht * (self.taux_tva / 100)
        
        # Calcul du montant TTC
        self.montant_ttc = self.montant_ht + self.montant_tva
        
        # Calcul de l'acompte si requis
        self.calculer_acompte()

def build_devis_template(devis, parametres):
    """Construit un contenu HTML par défaut pour l'éditeur riche."""
    nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
    description = html.escape(devis.prestation_description or '').replace('\n', '<br/>')
    client_lines = [html.escape(devis.client_nom)]
    if devis.client_adresse:
        client_lines.append(html.escape(devis.client_adresse).replace('\n', '<br/>'))
    if getattr(devis, 'client_siren', None):
        client_lines.append(f"SIREN : {html.escape(devis.client_siren)}")
    if getattr(devis, 'client_tva', None):
        client_lines.append(f"TVA : {html.escape(devis.client_tva)}")
    if getattr(devis, 'adresse_livraison', None):
        client_lines.append(f"Livraison : {html.escape(devis.adresse_livraison).replace(chr(10), '<br/>')}")
    client_block = "<br/>".join([line for line in client_lines if line])
    return f"""
<h2>{html.escape(nom_entreprise)} - Devis {html.escape(devis.numero)}</h2>
<p>Bonjour {html.escape(devis.client_nom)},</p>
<p>Veuillez trouver ci-dessous les details de notre proposition pour la prestation :</p>
<h3>Prestation</h3>
<p><strong>Titre :</strong> {html.escape(devis.prestation_titre)}</p>
<p><strong>Date :</strong> {devis.date_prestation.strftime('%d/%m/%Y')}</p>
<p><strong>Horaire :</strong> {devis.heure_debut.strftime('%H:%M')} - {devis.heure_fin.strftime('%H:%M')}</p>
<p><strong>Lieu :</strong> {html.escape(devis.lieu)}</p>
<h3>Client</h3>
<p>{client_block}</p>
<h3>Description</h3>
<p>{description}</p>
<p>Nous restons a votre disposition pour toute adaptation.</p>
"""

class Facture(db.Model):
    __tablename__ = 'factures'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    client_nom = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(100))
    client_telephone = db.Column(db.String(20))
    client_adresse = db.Column(db.Text)
    client_siren = db.Column(db.String(20))
    client_tva = db.Column(db.String(30))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    adresse_livraison = db.Column(db.Text)
    nature_operation = db.Column(db.String(120))
    tva_sur_debits = db.Column(db.Boolean, default=False)
    numero_bon_commande = db.Column(db.String(100))
    client_professionnel = db.Column(db.Boolean, default=False)

    # Informations de la prestation
    prestation_titre = db.Column(db.String(200), nullable=False)
    prestation_description = db.Column(db.Text)
    date_prestation = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)
    lieu = db.Column(db.String(200), nullable=False)

    # Tarification
    tarif_horaire = db.Column(db.Float, nullable=False, default=0.0)
    duree_heures = db.Column(db.Float, nullable=False, default=0.0)
    montant_ht = db.Column(db.Float, nullable=False, default=0.0)
    taux_tva = db.Column(db.Float, default=20.0)
    montant_tva = db.Column(db.Float, default=0.0)
    montant_ttc = db.Column(db.Float, nullable=False, default=0.0)
    montant_paye = db.Column(db.Float, default=0.0)

    # Remises et frais
    remise_pourcentage = db.Column(db.Float, default=0.0)
    remise_montant = db.Column(db.Float, default=0.0)
    frais_transport = db.Column(db.Float, default=0.0)
    frais_materiel = db.Column(db.Float, default=0.0)

    # Statut et dates
    statut = db.Column(db.String(20), default='brouillon')  # brouillon, envoyee, payee, en_retard, annulee
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_echeance = db.Column(db.Date)
    date_paiement = db.Column(db.Date)
    date_envoi = db.Column(db.DateTime)
    date_annulation = db.Column(db.DateTime)

    # Paiement
    mode_paiement = db.Column(db.String(50))  # virement, cheque, especes, carte, stripe
    mode_paiement_souhaite = db.Column(db.String(50))  # stripe, virement, especes
    reference_paiement = db.Column(db.String(100))
    conditions_paiement = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Gestion des acomptes
    acompte_requis = db.Column(db.Boolean, default=False)  # Si un acompte est demandé
    acompte_pourcentage = db.Column(db.Float, default=0.0)  # Pourcentage d'acompte (ex: 30.0 pour 30%)
    acompte_montant = db.Column(db.Float, default=0.0)  # Montant d'acompte en euros
    acompte_paye = db.Column(db.Boolean, default=False)  # Si l'acompte a été payé
    date_paiement_acompte = db.Column(db.DateTime)  # Date de paiement de l'acompte
    
    # Stripe
    stripe_payment_intent_id = db.Column(db.String(200))  # ID du Payment Intent Stripe
    stripe_payment_link = db.Column(db.String(500))  # Lien de paiement Stripe
    payment_token = db.Column(db.String(64), unique=True, index=True)

    # Relations
    dj_id = db.Column(db.Integer, db.ForeignKey('djs.id'))
    createur_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    prestation_id = db.Column(db.Integer, db.ForeignKey('prestations.id'))
    devis_id = db.Column(db.Integer, db.ForeignKey('devis.id'))

    dj = db.relationship('DJ', backref='factures')
    createur = db.relationship('User', backref='factures_creees')
    prestation = db.relationship('Prestation', backref='factures')
    devis = db.relationship('Devis', backref='factures_issues')
    client_ref = db.relationship('Client', backref='factures')

    @property
    def total_avoirs(self):
        total = 0.0
        for avoir in getattr(self, 'avoirs', []):
            if getattr(avoir, 'statut', '') != 'annule':
                total += avoir.montant_ttc or 0.0
        return total

    @property
    def montant_du_net(self):
        return max(0.0, (self.montant_ttc or 0.0) - self.total_avoirs)

    @property
    def montant_restant(self):
        net = self.montant_du_net
        return max(0.0, net - (self.montant_paye or 0.0))

    @property
    def est_payee(self):
        return (self.montant_paye or 0.0) >= self.montant_du_net

    @property
    def est_en_retard(self):
        if not self.date_echeance or self.est_payee:
            return False
        return date.today() > self.date_echeance
    
    def valider_paiement(self, montant):
        """Valide qu'un montant de paiement est acceptable"""
        if montant < 0:
            return False, "Le montant ne peut pas être négatif"

        net = self.montant_du_net
        if net <= 0:
            return False, "Aucun montant restant à payer (avoirs appliqués)"

        if montant > net:
            return False, f"Le montant ne peut pas dépasser le total net ({net:.2f}€)"

        if (self.montant_paye or 0.0) + montant > net:
            return False, f"Ce paiement dépasserait le montant total. Montant restant: {self.montant_restant:.2f}€"

        return True, "OK"
    
    def ajouter_paiement(self, montant):
        """Ajoute un paiement et met à jour le statut"""
        valide, message = self.valider_paiement(montant)
        if not valide:
            return False, message

        self.montant_paye = (self.montant_paye or 0.0) + montant
        net = self.montant_du_net

        # Mettre à jour le statut automatiquement
        if self.montant_paye >= net:
            self.statut = 'payee'
            self.date_paiement = date.today()
        elif self.montant_paye > 0:
            self.statut = 'partiellement_payee'
        
        return True, f"Paiement de {montant:.2f}€ ajouté. Reste: {self.montant_restant:.2f}€"

    def synchroniser_frais_materiel(self):
        """
        Synchronise le champ frais_materiel avec le coût RÉEL du matériel assigné
        Cette méthode assure la cohérence entre la BDD et le PDF
        """
        if self.prestation_id:
            cout_reel, _ = calculer_cout_materiel_reel(prestation_id=self.prestation_id)
            self.frais_materiel = cout_reel
            return True
        if self.devis_id:
            cout_reel, _ = calculer_cout_materiel_reel(devis_id=self.devis_id)
            self.frais_materiel = cout_reel
            return True
        return False
    
    def calculer_acompte(self):
        """
        Calcule le montant de l'acompte en fonction du pourcentage
        Met à jour acompte_montant automatiquement
        """
        if self.acompte_requis and self.acompte_pourcentage > 0:
            self.acompte_montant = self.montant_ttc * (self.acompte_pourcentage / 100)
        else:
            self.acompte_montant = 0.0
        return self.acompte_montant
    
    @property
    def montant_solde(self):
        """Montant restant à payer après acompte"""
        if self.acompte_paye:
            return self.montant_ttc - self.acompte_montant
        return self.montant_ttc

    def calculer_totaux(self):
        """Calcule automatiquement les totaux de la facture"""
        # COHÉRENCE : Synchroniser frais_materiel avec le coût réel
        self.synchroniser_frais_materiel()
        
        # Calcul du montant HT de base
        montant_base = (self.tarif_horaire * self.duree_heures) + self.frais_transport + self.frais_materiel

        # Application de la remise (priorité au pourcentage si les deux sont définis)
        remise = 0
        if self.remise_pourcentage and self.remise_pourcentage > 0:
            remise = montant_base * (self.remise_pourcentage / 100)
            # Si pourcentage défini, réinitialiser la remise en montant pour éviter confusion
            self.remise_montant = 0
        elif self.remise_montant and self.remise_montant > 0:
            remise = self.remise_montant

        self.montant_ht = max(0, montant_base - remise)

        # Calcul de la TVA
        tva_non_applicable = False
        try:
            parametres = ParametresEntreprise.query.first()
            if parametres and parametres.tva_non_applicable:
                tva_non_applicable = True
        except Exception:
            tva_non_applicable = False
        if tva_non_applicable:
            self.taux_tva = 0.0
            self.montant_tva = 0.0
        else:
            self.montant_tva = self.montant_ht * (self.taux_tva / 100)

        # Calcul du montant TTC
        self.montant_ttc = self.montant_ht + self.montant_tva
        
        # Calcul de l'acompte si requis
        self.calculer_acompte()

    def __repr__(self):
        return f'<Facture {self.numero}>'

class Avoir(db.Model):
    __tablename__ = 'avoirs'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'))
    createur_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_annulation = db.Column(db.DateTime)
    montant_ht = db.Column(db.Float, nullable=False, default=0.0)
    taux_tva = db.Column(db.Float, default=0.0)
    montant_tva = db.Column(db.Float, default=0.0)
    montant_ttc = db.Column(db.Float, nullable=False, default=0.0)
    motif = db.Column(db.Text)
    statut = db.Column(db.String(20), default='emis')  # emis, annule

    facture = db.relationship('Facture', backref='avoirs')
    createur = db.relationship('User', backref='avoirs_crees')

    def __repr__(self):
        return f'<Avoir {self.numero}>'

class Paiement(db.Model):
    """Modèle pour le suivi des paiements sécurisés"""
    __tablename__ = 'paiements'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Informations générales
    numero = db.Column(db.String(50), unique=True, nullable=False)  # Numéro unique de paiement
    montant = db.Column(db.Float, nullable=False)  # Montant du paiement
    devise = db.Column(db.String(10), default='EUR')  # Devise (EUR, USD, etc.)
    type_paiement = db.Column(db.String(20), nullable=False)  # 'facture', 'devis', 'acompte', 'solde'
    mode_paiement = db.Column(db.String(50))  # stripe, virement, especes, cheque, carte
    description = db.Column(db.Text)  # Description du paiement
    
    # Statut
    statut = db.Column(db.String(20), default='en_attente')  # en_attente, traitement, reussi, echoue, rembourse, annule
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_paiement = db.Column(db.DateTime)  # Date effective du paiement
    date_expiration = db.Column(db.DateTime)  # Date d'expiration du lien de paiement
    
    # Stripe
    stripe_payment_intent_id = db.Column(db.String(200), unique=True)  # ID du Payment Intent Stripe
    stripe_checkout_session_id = db.Column(db.String(200))  # ID de la session Checkout Stripe
    stripe_customer_id = db.Column(db.String(200))  # ID du client Stripe
    stripe_payment_method = db.Column(db.String(50))  # card, sepa_debit, etc.
    stripe_charge_id = db.Column(db.String(200))  # ID de la charge Stripe
    
    # Informations client
    client_nom = db.Column(db.String(100))
    client_email = db.Column(db.String(120))
    client_telephone = db.Column(db.String(20))
    client_ip = db.Column(db.String(50))  # IP du client lors du paiement
    
    # Sécurité et audit
    tentatives_paiement = db.Column(db.Integer, default=0)  # Nombre de tentatives
    derniere_erreur = db.Column(db.Text)  # Dernière erreur rencontrée
    payment_metadata = db.Column(db.Text)  # Métadonnées JSON supplémentaires
    
    # Remboursement
    montant_rembourse = db.Column(db.Float, default=0.0)  # Montant remboursé
    date_remboursement = db.Column(db.DateTime)  # Date du remboursement
    raison_remboursement = db.Column(db.Text)  # Raison du remboursement
    
    # Relations
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'))  # Lien vers la facture
    devis_id = db.Column(db.Integer, db.ForeignKey('devis.id'))  # Lien vers le devis
    createur_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Qui a créé le paiement
    justificatif_path = db.Column(db.String(255))
    commentaire = db.Column(db.Text)
    
    facture = db.relationship('Facture', backref='paiements')
    devis = db.relationship('Devis', backref='paiements')
    createur = db.relationship('User', backref='paiements_crees')
    
    @property
    def est_paye(self):
        """Vérifie si le paiement est réussi"""
        return self.statut == 'reussi'
    
    @property
    def est_rembourse(self):
        """Vérifie si le paiement est remboursé"""
        return self.statut == 'rembourse' or self.montant_rembourse > 0
    
    @property
    def montant_net(self):
        """Montant net après remboursement"""
        return self.montant - self.montant_rembourse
    
    def __repr__(self):
        return f'<Paiement {self.numero} - {self.montant}€ - {self.statut}>'

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    categories = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    contacts = db.relationship('ClientContact', backref='client', cascade='all, delete-orphan', lazy='joined')

    def __repr__(self):
        return f'<Client {self.nom}>'

class ClientContact(db.Model):
    __tablename__ = 'client_contacts'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    nom = db.Column(db.String(150))
    email = db.Column(db.String(120))
    telephone = db.Column(db.String(20))
    role = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<ClientContact {self.nom or self.email or self.telephone}>'

class ReservationClient(db.Model):
    """Modèle pour les réservations clients"""
    __tablename__ = 'reservations_client'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    
    # Informations client
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    adresse = db.Column(db.Text, nullable=False)
    nb_invites = db.Column(db.Integer)
    type_lieu = db.Column(db.String(50))
    demandes_speciales = db.Column(db.Text)
    
    # Détails de la prestation
    type_prestation = db.Column(db.String(50), nullable=False)  # mariage, anniversaire, entreprise, prive
    prix_prestation = db.Column(db.Float, nullable=False)
    duree_heures = db.Column(db.Integer, nullable=False)
    date_souhaitee = db.Column(db.Date, nullable=False)
    heure_souhaitee = db.Column(db.Time, nullable=False)
    
    # Statut et validation
    statut = db.Column(db.String(20), default='en_attente')  # en_attente, validee, rejetee, confirmee
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_validation = db.Column(db.DateTime)
    date_confirmation = db.Column(db.DateTime)
    
    # Validation manager/DJ
    validee_par_manager = db.Column(db.Boolean, default=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    manager_notes = db.Column(db.Text)
    
    validee_par_dj = db.Column(db.Boolean, default=False)
    dj_id = db.Column(db.Integer, db.ForeignKey('djs.id'))
    dj_notes = db.Column(db.Text)
    
    # Conversion en prestation
    prestation_id = db.Column(db.Integer, db.ForeignKey('prestations.id'))
    devis_id = db.Column(db.Integer, db.ForeignKey('devis.id'))
    
    # Relations
    manager = db.relationship('User', foreign_keys=[manager_id], backref='reservations_validees')
    dj = db.relationship('DJ', backref='reservations_attribuees')
    prestation = db.relationship('Prestation', backref='reservation_origine')
    devis = db.relationship('Devis', backref=db.backref('reservation_origine', uselist=False))

    @property
    def est_validee(self):
        return self.validee_par_manager and self.validee_par_dj

    @property
    def peut_etre_confirmee(self):
        return self.est_validee and self.statut == 'validee'

    def __repr__(self):
        return f'<ReservationClient {self.numero}>'

class Materiel(db.Model):
    __tablename__ = 'materiels'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    # Code-barre / identifiant externe (ex: EAN, QR) — unique si fourni
    code_barre = db.Column(db.String(128), unique=True, index=True, nullable=True)
    # Numéro de série (utilisé pour code-barres interne)
    numero_serie = db.Column(db.String(128), unique=True, index=True, nullable=True)
    local_id = db.Column(db.Integer, db.ForeignKey('locals.id'), nullable=False)
    quantite = db.Column(db.Integer, default=1)
    categorie = db.Column(db.String(50))
    statut = db.Column(db.String(20), default='disponible')  # disponible, maintenance, hors_service, archive
    prix_location = db.Column(db.Float, default=0.0)  # Prix de location par prestation (€)
    notes_technicien = db.Column(db.Text)
    derniere_maintenance = db.Column(db.DateTime)
    # Relation gérée par MaterielPresta
    
    def est_disponible(self, date_debut=None, date_fin=None, heure_debut=None, heure_fin=None):
        """
        Vérifie si le matériel est disponible pour une période donnée (dates + heures)
        
        Args:
            date_debut: Date de début (date object)
            date_fin: Date de fin (date object)
            heure_debut: Heure de début (time object)
            heure_fin: Heure de fin (time object)
            
        Returns:
            bool: True si disponible, False sinon
        """
        # Si en maintenance, hors service ou archivé, jamais disponible
        if self.statut in ['maintenance', 'hors_service', 'archive']:
            return False
        
        # Si pas de dates fournies, vérifier juste le statut
        if not date_debut or not date_fin:
            return self.statut == 'disponible'
        
        dispo = verifier_disponibilite_materiel(
            materiel_id=self.id,
            quantite_demandee=1,
            date_debut=date_debut,
            date_fin=date_fin,
            heure_debut=heure_debut,
            heure_fin=heure_fin
        )
        return bool(dispo.get('disponible'))
    
    # NOTE: Les méthodes reserver() et liberer() ont été supprimées
    # Le statut 'reserve' n'existe plus !
    # La disponibilité est maintenant gérée UNIQUEMENT via MaterielPresta
    # avec vérification des dates ET heures dans est_disponible()
    
    def generer_qr_code_url(self):
        """Génère l'URL pour le QR code de ce matériel"""
        from flask import url_for
        return url_for('selection_scan_materiel', materiel_id=self.id, _external=True)
    
    def mettre_en_maintenance(self):
        """Met le matériel en maintenance"""
        self.statut = 'maintenance'
        return True
    
    def sortir_de_maintenance(self):
        """Sort le matériel de la maintenance"""
        if self.statut == 'maintenance':
            self.statut = 'disponible'
            return True
        return False
    
    def mettre_a_jour_statut_auto(self):
        """Met à jour automatiquement le statut en fonction des assignations"""
        # Normaliser le statut si des valeurs legacy existent
        statuts_valides = {'disponible', 'maintenance', 'hors_service', 'archive'}
        if self.statut not in statuts_valides:
            self.statut = 'disponible'

class MouvementMateriel(db.Model):
    """Historique des mouvements de matériel (sorties/retours) via QR code"""
    __tablename__ = 'mouvements_materiel'
    
    id = db.Column(db.Integer, primary_key=True)
    materiel_id = db.Column(db.Integer, db.ForeignKey('materiels.id'), nullable=False)
    prestation_id = db.Column(db.Integer, db.ForeignKey('prestations.id'), nullable=True)
    type_mouvement = db.Column(db.String(20), nullable=False)  # 'sortie' ou 'retour'
    quantite = db.Column(db.Integer, default=1)
    local_depart_id = db.Column(db.Integer, db.ForeignKey('locals.id'), nullable=True)
    local_retour_id = db.Column(db.Integer, db.ForeignKey('locals.id'), nullable=True)
    date_mouvement = db.Column(db.DateTime, default=utcnow)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text)
    
    # Relations
    materiel = db.relationship('Materiel', backref='mouvements')
    prestation = db.relationship('Prestation', backref='mouvements_materiel')
    utilisateur = db.relationship('User', backref='mouvements_effectues')
    local_depart = db.relationship('Local', foreign_keys=[local_depart_id], backref='sorties_materiel')
    local_retour = db.relationship('Local', foreign_keys=[local_retour_id], backref='retours_materiel')

class MaterielPresta(db.Model):
    """Modèle pour la relation many-to-many entre matériel et prestations/réservations"""
    __tablename__ = 'materiel_presta'
    
    id = db.Column(db.Integer, primary_key=True)
    materiel_id = db.Column(db.Integer, db.ForeignKey('materiels.id'), nullable=False)
    prestation_id = db.Column(db.Integer, db.ForeignKey('prestations.id'), nullable=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations_client.id'), nullable=True)
    quantite = db.Column(db.Integer, default=1)
    
    # Relations
    materiel = db.relationship('Materiel', backref='assignations')
    prestation = db.relationship('Prestation', backref='materiel_assignations')
    reservation = db.relationship('ReservationClient', backref='materiel_assignations')

@event.listens_for(MaterielPresta, 'before_insert')
@event.listens_for(MaterielPresta, 'before_update')
def _validate_materiel_presta(mapper, connection, target):
    has_prestation = target.prestation_id is not None
    has_reservation = target.reservation_id is not None
    if has_prestation == has_reservation:
        raise ValueError("MaterielPresta doit référencer uniquement une prestation OU une réservation")
    if target.materiel_id is None:
        raise ValueError("Matériel requis pour l'assignation")
    try:
        quantite = int(target.quantite)
    except (TypeError, ValueError):
        raise ValueError("Quantité invalide")
    if quantite <= 0:
        raise ValueError("Quantité invalide")
    target.quantite = quantite
    stmt_materiel = select(Materiel.quantite, Materiel.statut).where(Materiel.id == target.materiel_id)
    materiel_row = connection.execute(stmt_materiel).first()
    if not materiel_row:
        raise ValueError("Matériel introuvable")
    stock_total, statut = materiel_row
    if statut in ['maintenance', 'hors_service', 'archive']:
        raise ValueError("Matériel indisponible")
    if stock_total is not None and quantite > int(stock_total):
        raise ValueError("Quantité assignée supérieure au stock disponible")
    # Empêcher les doublons (même matériel assigné deux fois à la même prestation/réservation)
    if has_prestation:
        stmt = select(MaterielPresta.id).where(
            MaterielPresta.materiel_id == target.materiel_id,
            MaterielPresta.prestation_id == target.prestation_id
        )
    else:
        stmt = select(MaterielPresta.id).where(
            MaterielPresta.materiel_id == target.materiel_id,
            MaterielPresta.reservation_id == target.reservation_id
        )
    existing_id = connection.execute(stmt).scalar()
    if existing_id and existing_id != getattr(target, 'id', None):
        raise ValueError("Matériel déjà assigné à cette mission/réservation")

class Prestation(db.Model):
    __tablename__ = 'prestations'
    id = db.Column(db.Integer, primary_key=True)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.Time, nullable=False, default=time(20, 0))
    heure_fin = db.Column(db.Time, nullable=False, default=time(2, 0))
    client = db.Column(db.String(100), nullable=False)
    client_telephone = db.Column(db.String(20))
    client_email = db.Column(db.String(120))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    lieu = db.Column(db.String(200), nullable=False)
    lieu_lat = db.Column(db.Float)
    lieu_lng = db.Column(db.Float)
    lieu_formatted = db.Column(db.String(255))
    lieu_geocoded_at = db.Column(db.DateTime)
    distance_km = db.Column(db.Float)
    distance_source = db.Column(db.String(20))
    indemnite_km = db.Column(db.Float)
    dj_id = db.Column(db.Integer, db.ForeignKey('djs.id'), nullable=False)
    technicien_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    createur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text)
    custom_fields = db.Column(db.Text)
    statut = db.Column(db.String(20), default='planifiee')  # planifiee, confirmee, en_cours, terminee, annulee
    date_creation = db.Column(db.DateTime, default=utcnow)
    date_modification = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Google Calendar
    google_calendar_event_id = db.Column(db.String(500))  # ID de l'événement Google Calendar
    
    # Relations - dj est défini via le backref dans DJ.prestations
    technicien = db.relationship('User', foreign_keys=[technicien_id], backref='prestations_techniques')
    client_ref = db.relationship('Client', backref='prestations')
    
    @property
    def materiels(self):
        """Propriété pour récupérer les matériels assignés à cette prestation"""
        try:
            # Une seule requête au lieu de N+1
            return Materiel.query.join(MaterielPresta).filter(
                MaterielPresta.prestation_id == self.id
            ).all()
        except Exception:
            return []
    
    def valider_transition_statut(self, nouveau_statut):
        """Valide qu'une transition de statut est autorisée"""
        statuts_valides = ['planifiee', 'confirmee', 'en_cours', 'terminee', 'annulee']
        
        if nouveau_statut not in statuts_valides:
            return False, f"Statut invalide. Statuts autorisés: {', '.join(statuts_valides)}"
        
        # Règles de transition
        transitions_autorisees = {
            'planifiee': ['confirmee', 'annulee'],
            'confirmee': ['en_cours', 'terminee', 'annulee'],
            'en_cours': ['terminee', 'annulee'],
            'terminee': [],  # Une prestation terminée ne peut pas changer de statut
            'annulee': []    # Une prestation annulée ne peut pas changer de statut
        }
        
        if self.statut == nouveau_statut:
            return True, "Aucun changement de statut"
        
        if nouveau_statut not in transitions_autorisees.get(self.statut, []):
            return False, f"Transition de '{self.statut}' vers '{nouveau_statut}' non autorisée"

        if nouveau_statut == 'terminee':
            try:
                assignations = MaterielPresta.query.filter_by(prestation_id=self.id).all()
                for assignation in assignations:
                    total_sortie = db.session.query(
                        db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)
                    ).filter_by(
                        materiel_id=assignation.materiel_id,
                        prestation_id=self.id,
                        type_mouvement='sortie'
                    ).scalar() or 0
                    total_retour = db.session.query(
                        db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)
                    ).filter_by(
                        materiel_id=assignation.materiel_id,
                        prestation_id=self.id,
                        type_mouvement='retour'
                    ).scalar() or 0
                    if total_sortie > total_retour:
                        return False, "Impossible de terminer : retours matériel manquants"
            except Exception:
                return False, "Impossible de vérifier les retours matériel"
        
        return True, "Transition autorisée"
    
    def changer_statut(self, nouveau_statut):
        """Change le statut avec validation"""
        valide, message = self.valider_transition_statut(nouveau_statut)
        if not valide:
            return False, message
        
        ancien_statut = self.statut
        self.statut = nouveau_statut
        self.date_modification = utcnow()
        
        return True, f"Statut changé de '{ancien_statut}' à '{nouveau_statut}'"

# Table de liaison gérée par le modèle MaterielPresta

# ==================== SYNCHRONISATION OFFLINE ====================

class SyncConfig(db.Model):
    __tablename__ = 'sync_config'

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False)
    server_url = db.Column(db.String(255))
    auth_url = db.Column(db.String(255))
    token_url = db.Column(db.String(255))
    client_id = db.Column(db.String(255))
    client_secret = db.Column(db.String(255))
    scopes = db.Column(db.String(500))
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    device_id = db.Column(db.String(64))
    sync_interval_seconds = db.Column(db.Integer, default=20)
    last_sync_at = db.Column(db.DateTime)
    last_success_at = db.Column(db.DateTime)
    last_sync_status = db.Column(db.String(20))
    last_sync_error = db.Column(db.Text)

class SyncChangeLog(db.Model):
    __tablename__ = 'sync_change_log'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(64), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    operation = db.Column(db.String(10), nullable=False)
    changed_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    device_id = db.Column(db.String(64))
    changed_fields = db.Column(db.Text)
    payload = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    sent_at = db.Column(db.DateTime)
    error = db.Column(db.Text)

class SyncConflict(db.Model):
    __tablename__ = 'sync_conflicts'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(64), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    conflict_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    status = db.Column(db.String(20), default='open')
    local_change_id = db.Column(db.Integer)
    remote_version = db.Column(db.String(100))
    details = db.Column(db.Text)

class SyncIncomingLog(db.Model):
    __tablename__ = 'sync_incoming_log'

    id = db.Column(db.Integer, primary_key=True)
    received_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    device_id = db.Column(db.String(64))
    entity_type = db.Column(db.String(64))
    entity_id = db.Column(db.Integer)
    operation = db.Column(db.String(10))
    payload = db.Column(db.Text)
    status = db.Column(db.String(20), default='received')
    error = db.Column(db.Text)

SYNC_EXCLUDED_MODELS = {'AuditLog', 'SyncConfig', 'SyncChangeLog', 'SyncConflict', 'SyncIncomingLog'}
SYNC_EXCLUDED_FIELDS = {'password_hash'}
SYNC_EXCLUDED_FIELD_SUBSTRINGS = ('password', 'token', 'secret')

def _should_exclude_field(field_name):
    if field_name in SYNC_EXCLUDED_FIELDS:
        return True
    return any(part in field_name for part in SYNC_EXCLUDED_FIELD_SUBSTRINGS)

def _serialize_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except Exception:
            return value.hex()
    return value

def _model_to_payload(target):
    payload = {}
    for column in target.__table__.columns:
        name = column.name
        if _should_exclude_field(name):
            continue
        try:
            payload[name] = _serialize_value(getattr(target, name))
        except Exception:
            payload[name] = None
    return payload

def _get_request_user_id():
    if has_request_context() and session.get('user_id'):
        return session.get('user_id')
    return None

def _log_sync_change(connection, target, operation, changed_fields=None):
    if target.__class__.__name__ in SYNC_EXCLUDED_MODELS:
        return
    try:
        payload = _model_to_payload(target)
        payload_json = json.dumps(payload, ensure_ascii=True, default=str)
        fields_json = json.dumps(changed_fields or [], ensure_ascii=True, default=str)
        device_id = get_device_id()
        user_id = _get_request_user_id()
        insert_stmt = SyncChangeLog.__table__.insert().values(
            entity_type=target.__class__.__name__,
            entity_id=getattr(target, 'id', None),
            operation=operation,
            changed_at=utcnow(),
            user_id=user_id,
            device_id=device_id,
            changed_fields=fields_json,
            payload=payload_json,
            status='pending'
        )
        connection.execute(insert_stmt)
    except Exception as e:
        logger.warning(f"Sync log error: {e}")

def _on_after_insert(mapper, connection, target):
    _log_sync_change(connection, target, 'insert')

def _on_after_update(mapper, connection, target):
    try:
        state = sa_inspect(target)
        changed_fields = [
            attr.key for attr in state.attrs
            if attr.history.has_changes()
        ]
    except Exception:
        changed_fields = []
    _log_sync_change(connection, target, 'update', changed_fields=changed_fields)

def _on_after_delete(mapper, connection, target):
    _log_sync_change(connection, target, 'delete')

_sync_listeners_registered = False

def register_sync_listeners():
    global _sync_listeners_registered
    if _sync_listeners_registered:
        return
    models_to_track = [
        Local, GrilleTarifaire, User, DJ, ParametresEntreprise,
        Devis, Facture, Paiement, ReservationClient, Materiel,
        MouvementMateriel, MaterielPresta, Prestation, PrestationRating
    ]
    for model in models_to_track:
        event.listen(model, 'after_insert', _on_after_insert)
        event.listen(model, 'after_update', _on_after_update)
        event.listen(model, 'after_delete', _on_after_delete)
    _sync_listeners_registered = True

register_sync_listeners()

@event.listens_for(db.session, "after_commit")
def _mark_plf_dirty_after_commit(session):
    mark_plf_dirty()

# Fonctions d'authentification et de gestion des rôles
def login_required(f):
    """Décorateur pour les routes nécessitant une authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """Décorateur pour les routes nécessitant des rôles spécifiques"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Vous devez être connecté pour accéder à cette page', 'error')
                return redirect(url_for('login'))
            
            try:
                user = db.session.get(User, session['user_id'])
            except Exception as e:
                logger.warning(f"Impossible de charger l'utilisateur pour role_required: {e}")
                session.clear()
                return redirect(url_for('login'))
            if not user or user.role not in roles:
                flash('Vous n\'avez pas les permissions nécessaires', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Récupère l'utilisateur actuellement connecté"""
    if hasattr(g, 'user'):
        return g.user
    if not app.config.get('DB_READY'):
        return None
    if 'user_id' in session:
        try:
            user = db.session.get(User, session['user_id'])
        except Exception as e:
            logger.warning(f"Impossible de charger l'utilisateur courant: {e}")
            session.clear()
            return None
        if user and user.actif:  # Vérifier que l'utilisateur est toujours actif
            return user
        # Si l'utilisateur n'existe plus ou n'est plus actif, nettoyer la session
        session.clear()
    return None

def get_or_404(model, ident):
    """Récupère un enregistrement ou 404 (SQLAlchemy 2.x compatible)."""
    obj = db.session.get(model, ident)
    if not obj:
        abort(404)
    return obj

TERMINOLOGY_GROUPS = {
    'mission': {
        'singular': ['mission', 'prestation', 'intervention'],
        'plural': ['missions', 'prestations', 'interventions'],
    },
    'prestataire': {
        'singular': ['prestataire', 'dj', 'intervenant'],
        'plural': ['prestataires', 'djs', 'intervenants'],
    },
    'technicien': {
        'singular': ['technicien', 'prestataire technique'],
        'plural': ['techniciens', 'prestataires techniques'],
    },
    'equipement': {
        'singular': ['équipement', 'equipement', 'matériel', 'materiel'],
        'plural': ['équipements', 'equipements', 'matériels', 'materiels'],
    },
    'site': {
        'singular': ['site', 'local'],
        'plural': ['sites', 'locaux'],
    },
    'agenda': {
        'singular': ['agenda', 'calendrier', 'planning'],
        'plural': ['agendas', 'calendriers', 'plannings'],
    },
}

TERMINOLOGY_PROFILES = {
    'missions': {
        'mission': ('mission', 'missions'),
        'prestataire': ('prestataire', 'prestataires'),
        'technicien': ('prestataire technique', 'prestataires techniques'),
        'equipement': ('équipement', 'équipements'),
        'site': ('site', 'sites'),
        'agenda': ('agenda', 'agendas'),
    },
    'prestations': {
        'mission': ('prestation', 'prestations'),
        'prestataire': ('DJ', 'DJs'),
        'technicien': ('technicien', 'techniciens'),
        'equipement': ('matériel', 'matériels'),
        'site': ('local', 'locaux'),
        'agenda': ('calendrier', 'calendriers'),
    },
    'interventions': {
        'mission': ('intervention', 'interventions'),
        'prestataire': ('intervenant', 'intervenants'),
        'technicien': ('technicien', 'techniciens'),
        'equipement': ('matériel', 'matériels'),
        'site': ('site', 'sites'),
        'agenda': ('planning', 'plannings'),
    },
}

def _get_active_terminology_profile():
    try:
        if not app.config.get('DB_READY'):
            return 'missions'
        if hasattr(g, 'parametres'):
            parametres = g.parametres
        else:
            parametres = ParametresEntreprise.query.first()
            g.parametres = parametres
        profile = (parametres.terminology_profile if parametres else '') or 'missions'
        if profile not in TERMINOLOGY_PROFILES:
            return 'missions'
        return profile
    except Exception:
        return 'missions'

def _build_terminology_replacements(profile):
    targets = TERMINOLOGY_PROFILES.get(profile, TERMINOLOGY_PROFILES['missions'])
    replacements = []
    for group, target in targets.items():
        singular_target, plural_target = target
        for variant in TERMINOLOGY_GROUPS.get(group, {}).get('singular', []):
            replacements.append((variant, singular_target))
        for variant in TERMINOLOGY_GROUPS.get(group, {}).get('plural', []):
            replacements.append((variant, plural_target))
    # Longer matches first to avoid partial overlaps
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    return replacements

@app.template_filter('apply_terminology')
def apply_terminology_filter(text):
    if not text:
        return text
    updated = str(text)
    profile = _get_active_terminology_profile()
    replacements = _build_terminology_replacements(profile)
    for source, replacement in replacements:
        pattern = re.compile(rf'\\b{re.escape(source)}\\b', re.IGNORECASE)
        def _repl(match):
            token = match.group(0)
            if replacement.isupper() or any(ch.isupper() for ch in replacement[1:]):
                return replacement
            if token.isupper():
                return replacement.upper()
            if token[0].isupper():
                return replacement.capitalize()
            return replacement.lower() if replacement.islower() else replacement
        updated = pattern.sub(_repl, updated)
    return updated

@app.template_filter('role_label')
def role_label_filter(role):
    mapping = {
        'admin': 'Administrateur',
        'manager': 'Manager',
        'dj': 'Prestataire',
        'technicien': 'Prestataire technique',
    }
    return mapping.get(role, role or '')

def _load_custom_fields_definitions(raw_value):
    if not raw_value:
        return []
    try:
        data = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    normalized = []
    allowed_types = {'text', 'number', 'textarea', 'select', 'date'}
    for field in data:
        if not isinstance(field, dict):
            continue
        key = (field.get('key') or '').strip()
        label = (field.get('label') or '').strip()
        field_type = (field.get('type') or 'text').strip().lower()
        if not key or not label:
            continue
        if field_type not in allowed_types:
            field_type = 'text'
        options = field.get('options') if isinstance(field.get('options'), list) else []
        normalized.append({
            'key': key,
            'label': label,
            'type': field_type,
            'placeholder': (field.get('placeholder') or '').strip(),
            'help': (field.get('help') or '').strip(),
            'required': bool(field.get('required')),
            'options': [str(opt) for opt in options],
            'full_width': bool(field.get('full_width')),
        })
    return normalized

def get_custom_fields_definitions(parametres):
    raw = parametres.custom_fields_prestation if parametres else None
    return _load_custom_fields_definitions(raw)

def extract_custom_fields_from_form(definitions, form_data):
    values = {}
    for field in definitions:
        key = field.get('key')
        if not key:
            continue
        form_key = f"custom_{key}"
        value = form_data.get(form_key)
        if value is None:
            continue
        values[key] = value.strip() if isinstance(value, str) else value
    return values

def parse_custom_fields_values(raw_value):
    if not raw_value:
        return {}
    try:
        data = json.loads(raw_value)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}

def build_custom_fields_display(definitions, values):
    items = []
    for field in definitions:
        key = field.get('key')
        if not key:
            continue
        value = values.get(key)
        if value in (None, '', []):
            continue
        if isinstance(value, list):
            display_value = ', '.join([str(v) for v in value])
        else:
            display_value = str(value)
        items.append({'label': field.get('label', key), 'value': display_value})
    return items

def _apply_terminology_to_payload(payload):
    if isinstance(payload, dict):
        updated = {}
        for key, value in payload.items():
            if key in ('message', 'error') and isinstance(value, str):
                updated[key] = apply_terminology_filter(value)
            else:
                updated[key] = _apply_terminology_to_payload(value)
        return updated
    if isinstance(payload, list):
        return [_apply_terminology_to_payload(item) for item in payload]
    return payload

@app.after_request
def apply_terminology_to_json_response(response):
    try:
        if response.is_json:
            payload = response.get_json(silent=True)
            if payload is not None:
                updated = _apply_terminology_to_payload(payload)
                if updated != payload:
                    response.set_data(json.dumps(updated, ensure_ascii=False))
    except Exception as e:
        logger.debug(f"Impossible d'appliquer la terminologie aux réponses JSON: {e}")
    return response

@app.context_processor
def inject_current_user():
    """Injecte l'utilisateur actuel et les paramètres d'entreprise dans tous les templates"""
    if not app.config.get('DB_READY'):
        return dict(
            current_user=None,
            parametres=None,
            csrf_token=session.get('csrf_token'),
            public_api_token=None
        )
    if hasattr(g, 'parametres'):
        parametres = g.parametres
    else:
        try:
            parametres = ParametresEntreprise.query.first()
        except Exception:
            parametres = None
        g.parametres = parametres
    return dict(
        current_user=get_current_user(),
        parametres=parametres,
        csrf_token=session.get('csrf_token'),
        public_api_token=get_public_api_token(parametres)
    )

def check_materiel_availability(materiel_id, date_debut, date_fin, heure_debut, heure_fin, prestation_id=None):
    """Vérifie la disponibilité d'un matériel pour une période donnée avec logique améliorée"""
    dispo = verifier_disponibilite_materiel(
        materiel_id=materiel_id,
        quantite_demandee=1,
        date_debut=date_debut,
        date_fin=date_fin,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        exclure_prestation_id=prestation_id
    )
    if dispo.get('disponible'):
        return True, "Disponible"
    if dispo.get('erreur'):
        return False, dispo.get('erreur')
    return False, f"Indisponible ({dispo.get('quantite_disponible', 0)}/{dispo.get('quantite_totale', 0)})"

def update_materiel_status(materiel_id, commit=True):
    """Met à jour le statut d'un matériel en fonction de ses prestations"""
    materiel = db.session.get(Materiel, materiel_id)
    if not materiel:
        return

    # Utiliser la méthode du modèle pour mettre à jour automatiquement
    materiel.mettre_a_jour_statut_auto()
    if commit:
        db.session.commit()

def is_materiel_available_at_time(materiel_id, date, heure_debut, heure_fin):
    """Vérifie si un matériel est disponible à une date et heure spécifiques"""
    materiel = db.session.get(Materiel, materiel_id)
    if not materiel:
        return False
    if materiel.statut in {'maintenance', 'hors_service', 'archive'}:
        return False
    dispo = verifier_disponibilite_materiel(
        materiel_id=materiel_id,
        quantite_demandee=1,
        date_debut=date,
        date_fin=date,
        heure_debut=heure_debut,
        heure_fin=heure_fin
    )
    return bool(dispo.get('disponible'))

def update_all_materiels_status():
    """Met à jour le statut de tous les matériels en fonction des créneaux horaires actuels"""
    materiels = Materiel.query.all()
    for materiel in materiels:
        update_materiel_status(materiel.id)

def get_materiel_status_at_time(materiel_id, date, heure_debut, heure_fin):
    """Détermine le statut d'un matériel à une date et heure spécifiques"""
    materiel = db.session.get(Materiel, materiel_id)
    if not materiel:
        return 'indisponible'
    
    # Si le matériel est en maintenance, hors service ou archivé
    if materiel.statut == 'maintenance':
        return 'maintenance'
    if materiel.statut == 'hors_service':
        return 'hors_service'
    if materiel.statut == 'archive':
        return 'archive'

    dispo = verifier_disponibilite_materiel(
        materiel_id=materiel_id,
        quantite_demandee=1,
        date_debut=date,
        date_fin=date,
        heure_debut=heure_debut,
        heure_fin=heure_fin
    )
    if not dispo.get('disponible'):
        return 'occupe'
    quantite_dispo = dispo.get('quantite_disponible', materiel.quantite)
    quantite_totale = dispo.get('quantite_totale', materiel.quantite)
    if quantite_dispo < quantite_totale:
        return 'partiel'
    return 'disponible'

def verifier_disponibilite_materiel(materiel_id, quantite_demandee, date_debut, date_fin, 
                                    heure_debut=None, heure_fin=None, 
                                    exclure_prestation_id=None, exclure_reservation_id=None):
    """
    Vérifie si une quantité de matériel est disponible sur une période donnée
    
    Args:
        materiel_id: ID du matériel
        quantite_demandee: Quantité souhaitée
        date_debut: Date de début de la prestation
        date_fin: Date de fin de la prestation
        heure_debut: Heure de début (optionnel)
        heure_fin: Heure de fin (optionnel)
        exclure_prestation_id: ID de prestation à exclure (pour édition)
        exclure_reservation_id: ID de réservation à exclure (pour édition)
    
    Returns:
        dict: {
            'disponible': bool,
            'quantite_disponible': int,
            'quantite_totale': int,
            'quantite_utilisee': int,
            'conflits': list  # Liste des prestations en conflit
        }
    """
    materiel = db.session.get(Materiel, materiel_id)
    if not materiel:
        return {
            'disponible': False,
            'quantite_disponible': 0,
            'quantite_totale': 0,
            'quantite_utilisee': 0,
            'conflits': [],
            'erreur': 'Matériel introuvable'
        }
    
    # Si le matériel est en maintenance ou hors service, non disponible
    if materiel.statut in {'maintenance', 'hors_service', 'archive'}:
        return {
            'disponible': False,
            'quantite_disponible': 0,
            'quantite_totale': materiel.quantite,
            'quantite_utilisee': materiel.quantite,
            'conflits': [],
            'erreur': f"Matériel en {materiel.statut.replace('_', ' ')}"
        }
    
    try:
        if not date_debut or not date_fin:
            return {
                'disponible': False,
                'quantite_disponible': 0,
                'quantite_totale': materiel.quantite,
                'quantite_utilisee': 0,
                'conflits': [],
                'erreur': 'Dates manquantes'
            }

        # Si aucune heure fournie, considérer la journée entière
        heure_debut_effective = heure_debut or time(0, 0)
        heure_fin_effective = heure_fin or time(23, 59)
        req_start, req_end = _build_datetime_range(
            date_debut, date_fin, heure_debut_effective, heure_fin_effective
        )
        if not req_start or not req_end:
            return {
                'disponible': False,
                'quantite_disponible': 0,
                'quantite_totale': materiel.quantite,
                'quantite_utilisee': 0,
                'conflits': [],
                'erreur': 'Période invalide'
            }

        sortie_avant_h, retour_apres_h = _get_materiel_logistique_buffers()

        # Chercher toutes les assignations qui se chevauchent avec cette période
        # 1. Assignations à des PRESTATIONS actives
        active_statuses = ['planifiee', 'confirmee', 'en_cours']
        ended_statuses = ['terminee', 'annulee']
        query_prestations = db.session.query(MaterielPresta).join(Prestation).filter(
            MaterielPresta.materiel_id == materiel_id,
            MaterielPresta.prestation_id.isnot(None),
            Prestation.statut.in_(active_statuses),
            # Chevauchement de dates
            Prestation.date_debut <= date_fin,
            Prestation.date_fin >= date_debut
        )
        
        if exclure_prestation_id:
            query_prestations = query_prestations.filter(MaterielPresta.prestation_id != exclure_prestation_id)
        
        assignations_prestations = query_prestations.all()

        # 1bis. Prestations terminées/annulées avec retours manquants
        query_prestations_ended = db.session.query(MaterielPresta).join(Prestation).filter(
            MaterielPresta.materiel_id == materiel_id,
            MaterielPresta.prestation_id.isnot(None),
            Prestation.statut.in_(ended_statuses)
        )
        if exclure_prestation_id:
            query_prestations_ended = query_prestations_ended.filter(MaterielPresta.prestation_id != exclure_prestation_id)
        assignations_prestations_ended = query_prestations_ended.all()
        
        # 2. Assignations à des RÉSERVATIONS en attente de validation DJ
        query_reservations = db.session.query(MaterielPresta).join(ReservationClient).filter(
            MaterielPresta.materiel_id == materiel_id,
            MaterielPresta.reservation_id.isnot(None),
            ReservationClient.statut.in_(list(RESERVATION_STATUTS_BLOQUANTS))
        )
        
        if exclure_reservation_id:
            query_reservations = query_reservations.filter(MaterielPresta.reservation_id != exclure_reservation_id)
        
        assignations_reservations = query_reservations.all()
        
        # Calculer la quantité maximale utilisée sur la période (concurrence)
        events = []
        conflits = []
        
        for assignation in assignations_prestations:
            prestation = assignation.prestation
            start_dt, end_dt = _build_datetime_range(
                prestation.date_debut,
                prestation.date_fin,
                prestation.heure_debut or time(0, 0),
                prestation.heure_fin or time(23, 59)
            )
            if not start_dt or not end_dt:
                continue
            buffer_start = start_dt - timedelta(hours=sortie_avant_h)
            buffer_end = end_dt + timedelta(hours=retour_apres_h)
            if buffer_end <= req_start or buffer_start >= req_end:
                continue

            overlap_start = max(buffer_start, req_start)
            overlap_end = min(buffer_end, req_end)
            if overlap_end <= overlap_start:
                continue
            events.append((overlap_start, assignation.quantite))
            events.append((overlap_end, -assignation.quantite))
            conflits.append({
                'type': 'prestation',
                'id': prestation.id,
                'nom': prestation.client,
                'date': prestation.date_debut,
                'heure': f"{prestation.heure_debut} - {prestation.heure_fin}",
                'quantite': assignation.quantite
            })
        
        # Ajouter les retours manquants pour prestations terminées/annulées
        for assignation in assignations_prestations_ended:
            prestation = assignation.prestation
            if not prestation:
                continue
            total_sortie = db.session.query(
                db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)
            ).filter_by(
                materiel_id=materiel_id,
                prestation_id=prestation.id,
                type_mouvement='sortie'
            ).scalar() or 0
            total_retour = db.session.query(
                db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)
            ).filter_by(
                materiel_id=materiel_id,
                prestation_id=prestation.id,
                type_mouvement='retour'
            ).scalar() or 0
            quantite_restante = total_sortie - total_retour
            if quantite_restante <= 0:
                continue
            start_dt, end_dt = _build_datetime_range(
                prestation.date_debut,
                prestation.date_fin,
                prestation.heure_debut or time(0, 0),
                prestation.heure_fin or time(23, 59)
            )
            if not end_dt:
                continue
            block_start = end_dt
            block_end = end_dt + timedelta(days=RETOUR_MANQUANT_BLOCAGE_JOURS)
            if block_end <= req_start or block_start >= req_end:
                continue
            overlap_start = max(block_start, req_start)
            overlap_end = min(block_end, req_end)
            if overlap_end <= overlap_start:
                continue
            events.append((overlap_start, quantite_restante))
            events.append((overlap_end, -quantite_restante))
            conflits.append({
                'type': 'retour_manquant',
                'id': prestation.id,
                'nom': prestation.client,
                'date': prestation.date_debut,
                'heure': f"{prestation.heure_debut} - {prestation.heure_fin}",
                'quantite': quantite_restante
            })

        # Ajouter les réservations en attente
        for assignation in assignations_reservations:
            reservation = assignation.reservation
            if not reservation or not reservation.date_souhaitee:
                continue
            date_fin_res, heure_fin_res = compute_reservation_end(
                reservation.date_souhaitee,
                reservation.heure_souhaitee,
                reservation.duree_heures
            )
            start_dt, end_dt = _build_datetime_range(
                reservation.date_souhaitee,
                date_fin_res,
                reservation.heure_souhaitee or time(0, 0),
                heure_fin_res or time(23, 59)
            )
            if not start_dt or not end_dt:
                continue
            buffer_start = start_dt - timedelta(hours=sortie_avant_h)
            buffer_end = end_dt + timedelta(hours=retour_apres_h)
            if buffer_end <= req_start or buffer_start >= req_end:
                continue

            overlap_start = max(buffer_start, req_start)
            overlap_end = min(buffer_end, req_end)
            if overlap_end <= overlap_start:
                continue
            events.append((overlap_start, assignation.quantite))
            events.append((overlap_end, -assignation.quantite))
            conflits.append({
                'type': 'reservation',
                'id': reservation.id,
                'nom': reservation.nom,
                'date': reservation.date_souhaitee,
                'heure': reservation.heure_souhaitee.strftime('%H:%M') if reservation.heure_souhaitee else 'Non précisée',
                'quantite': assignation.quantite
            })
        
        # Calculer le pic de concurrence
        events.sort(key=lambda item: (item[0], 0 if item[1] < 0 else 1))
        quantite_utilisee = 0
        quantite_max = 0
        for _, delta in events:
            quantite_utilisee += delta
            if quantite_utilisee > quantite_max:
                quantite_max = quantite_utilisee
        quantite_disponible = max(0, materiel.quantite - quantite_max)
        
        return {
            'disponible': quantite_disponible >= quantite_demandee,
            'quantite_disponible': quantite_disponible,
            'quantite_totale': materiel.quantite,
            'quantite_utilisee': quantite_max,
            'conflits': conflits
        }
        
    except Exception as e:
        logger.error(f"Erreur vérification disponibilité matériel: {e}")
        import traceback
        traceback.print_exc()
        return {
            'disponible': False,
            'quantite_disponible': 0,
            'quantite_totale': materiel.quantite if materiel else 0,
            'quantite_utilisee': 0,
            'conflits': [],
            'erreur': str(e)
        }

def calculer_cout_materiel_reel(prestation_id=None, devis_id=None, reservation_id=None):
    """
    Calcule le coût RÉEL du matériel assigné à une prestation ou un devis
    
    Args:
        prestation_id: ID de la prestation
        devis_id: ID du devis (utilise prestation_id du devis)
        reservation_id: ID de la réservation (si devis sans prestation)
    
    Returns:
        tuple: (cout_total, liste_details)
            - cout_total (float): Montant total du matériel
            - liste_details (list): Liste de dict avec details par materiel
    """
    cout_total = 0.0
    details = []
    
    try:
        # Si devis_id fourni, récupérer prestation_id ou reservation_id du devis
        if devis_id and not prestation_id and not reservation_id:
            devis = db.session.get(Devis, devis_id)
            if devis and devis.prestation_id:
                prestation_id = devis.prestation_id
            elif devis and getattr(devis, 'reservation_origine', None):
                reservation_id = devis.reservation_origine.id

        if not prestation_id and not reservation_id:
            return 0.0, []
        
        # Récupérer tous les matériels assignés à cette prestation ou réservation
        if prestation_id:
            assignations = MaterielPresta.query.filter_by(prestation_id=prestation_id).all()
        else:
            assignations = MaterielPresta.query.filter_by(reservation_id=reservation_id).all()
        
        for assignation in assignations:
            materiel = db.session.get(Materiel, assignation.materiel_id)
            if materiel:
                # Calcul : prix_location * quantité
                cout_item = materiel.prix_location * assignation.quantite
                cout_total += cout_item
                
                details.append({
                    'nom': materiel.nom,
                    'prix_unitaire': materiel.prix_location,
                    'quantite': assignation.quantite,
                    'cout_total': cout_item
                })
        
        return cout_total, details
        
    except Exception as e:
        logger.error(f"Erreur calcul coût matériel: {e}")
        return 0.0, []

def sync_documents_for_prestation(prestation_id):
    """Synchronise devis/factures non verrouillés après modification du matériel."""
    try:
        devis_list = Devis.query.filter_by(prestation_id=prestation_id).all()
        for devis in devis_list:
            if not is_devis_locked(devis):
                devis.calculer_totaux()

        factures_list = Facture.query.filter_by(prestation_id=prestation_id).all()
        for facture in factures_list:
            if not is_facture_locked(facture):
                facture.calculer_totaux()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur synchronisation docs prestation {prestation_id}: {e}")

# Routes principales
@app.route('/', methods=['GET', 'POST'])
def index():
    """Page d'accueil - redirection selon le rôle"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Interface selon le rôle
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user.role == 'manager':
        return redirect(url_for('manager_dashboard'))
    elif user.role == 'dj':
        return redirect(url_for('dj_dashboard'))
    elif user.role == 'technicien':
        return redirect(url_for('technicien_dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/api/check-username', methods=['POST'])
def check_username():
    """API pour vérifier si un username existe et retourner les infos utilisateur"""
    ok, error = validate_public_api_request()
    if not ok:
        return jsonify({'exists': False, 'message': error}), 401
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    
    if not username:
        return jsonify({'exists': False})

    # Ne pas exposer d'informations sur l'existence d'un compte
    return jsonify({
        'exists': True,
        'prenom': None,
        'nom': None,
        'photo_profil': None
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if User.query.count() == 0:
        return redirect(url_for('initialisation'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, actif=True).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session.permanent = True  # Rendre la session permanente
            
            # Mettre à jour la dernière connexion
            user.derniere_connexion = utcnow()
            db.session.commit()
            
            flash(f'Bienvenue {user.nom} !', 'success')
            
            # Redirection selon le rôle
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif user.role == 'dj':
                return redirect(url_for('dj_dashboard'))
            elif user.role == 'technicien':
                return redirect(url_for('technicien_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    
    # Récupérer les paramètres d'entreprise pour l'affichage
    parametres = ParametresEntreprise.query.first()
    return render_template('login.html', parametres=parametres)

@app.route('/initialisation', methods=['GET', 'POST'])
def initialisation():
    """Page d'initialisation pour créer l'administrateur"""
    # Importer le gestionnaire de clé
    from init_key_manager import init_key_manager
    
    # Vérifier si l'application a déjà été initialisée
    if init_key_manager.is_initialized():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            nom = request.form['nom']
            prenom = request.form['prenom']
            email = request.form['email']
            telephone = request.form['telephone']
            
            # Validation basique
            if not nom or not prenom or not email or not telephone:
                flash('Tous les champs sont obligatoires', 'error')
                return render_template('initialisation.html')
            
            # Importer le service email
            from email_service import email_service
            
            # Générer et envoyer le code de vérification
            code = email_service.generate_verification_code()
            if email_service.send_verification_email(email, f"{prenom} {nom}", code):
                # Stocker les données temporairement en session
                session['init_data'] = {
                    'nom': nom,
                    'prenom': prenom,
                    'email': email,
                    'telephone': telephone
                }
                flash('Code de vérification envoyé par email !', 'success')
                return render_template('initialisation.html', email_sent=True)
            else:
                flash('Erreur lors de l\'envoi de l\'email', 'error')
                return render_template('initialisation.html')
            
        except Exception as e:
            flash(f'Erreur lors de l\'envoi : {str(e)}', 'error')
            return render_template('initialisation.html')
    
    return render_template('initialisation.html')

@app.route('/verifier-code', methods=['POST'])
def verifier_code():
    """Vérifier le code de vérification"""
    try:
        # Récupérer les données de session
        init_data = session.get('init_data')
        if not init_data:
            flash('Session expirée, veuillez recommencer', 'error')
            return redirect(url_for('initialisation'))
        
        # Récupérer le code saisi
        code = ''.join([
            request.form.get('code1', ''),
            request.form.get('code2', ''),
            request.form.get('code3', ''),
            request.form.get('code4', ''),
            request.form.get('code5', ''),
            request.form.get('code6', '')
        ])
        
        if len(code) != 6:
            flash('Code invalide', 'error')
            return render_template('initialisation.html')
        
        # Importer le service email
        from email_service import email_service
        
        # Vérifier le code
        if email_service.verify_code(init_data['email'], code):
            session['email_verified'] = True
            flash('Email vérifié avec succès !', 'success')
            return render_template('initialisation.html', email_verified=True)
        else:
            flash('Code incorrect ou expiré', 'error')
            return render_template('initialisation.html')
            
    except Exception as e:
        flash(f'Erreur lors de la vérification : {str(e)}', 'error')
        return render_template('initialisation.html')

@app.route('/renvoyer-code', methods=['POST'])
def renvoyer_code():
    """Renvoyer le code de vérification"""
    try:
        init_data = session.get('init_data')
        if not init_data:
            return jsonify({'success': False, 'message': 'Session expirée'})
        
        # Importer le service email
        from email_service import email_service
        
        # Générer un nouveau code
        code = email_service.generate_verification_code()
        if email_service.send_verification_email(init_data['email'], f"{init_data['prenom']} {init_data['nom']}", code):
            return jsonify({'success': True, 'message': 'Code renvoyé avec succès'})
        else:
            return jsonify({'success': False, 'message': 'Erreur lors de l\'envoi'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/finaliser-initialisation', methods=['POST'])
def finaliser_initialisation():
    """Finaliser l'initialisation du compte administrateur"""
    try:
        # Vérifier que l'email a été vérifié
        if not session.get('email_verified'):
            flash('Veuillez d\'abord vérifier votre email', 'error')
            return redirect(url_for('initialisation'))
        
        init_data = session.get('init_data')
        if not init_data:
            flash('Session expirée, veuillez recommencer', 'error')
            return redirect(url_for('initialisation'))
        
        # Récupérer les données du formulaire
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('initialisation.html')
        
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères', 'error')
            return render_template('initialisation.html')
        
        # Vérifier si le nom d'utilisateur ou l'email existe déjà
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur existe déjà', 'error')
            return render_template('initialisation.html')

        if User.query.filter_by(email=init_data['email']).first():
            flash('Un compte avec cet email existe déjà. Si c\'est vous, connectez-vous ou utilisez un autre email.', 'error')
            return render_template('initialisation.html')
        
        # Créer l'utilisateur administrateur
        admin_user = User(
            username=username,
            email=init_data['email'],
            password_hash=generate_password_hash(password),
            role='admin',
            nom=init_data['nom'],
            prenom=init_data['prenom'],
            telephone=init_data['telephone'],
            actif=True,
            date_creation=utcnow()
        )
        
        db.session.add(admin_user)
        try:
            db.session.commit()
        except Exception as e:
            # Si commit échoue (ex: contrainte unique), rollback et informer l'utilisateur
            from sqlalchemy.exc import IntegrityError
            db.session.rollback()
            if isinstance(e, IntegrityError) or isinstance(e.__cause__, IntegrityError):
                flash('Impossible de créer le compte : un utilisateur avec cet email existe déjà.', 'error')
            else:
                flash(f'Erreur lors de la création de l\'utilisateur : {str(e)}', 'error')
            return render_template('initialisation.html')
        
        # Créer les paramètres d'entreprise avec les informations du formulaire
        parametres = ParametresEntreprise(
            nom_entreprise=request.form.get('nom_entreprise', 'Mon Entreprise'),
            adresse=request.form.get('adresse', ''),
            code_postal=request.form.get('code_postal', ''),
            ville=request.form.get('ville', ''),
            telephone=init_data['telephone'],
            email=init_data['email'],
            site_web=request.form.get('site_web', ''),
            siret=request.form.get('siret', ''),
            tva_intracommunautaire=request.form.get('tva_intracommunautaire', ''),
            couleur_principale=request.form.get('couleur_principale', '#667eea'),
            couleur_secondaire=request.form.get('couleur_secondaire', '#764ba2'),
            devise="EUR",
            langue="fr"
        )
        db.session.add(parametres)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création des paramètres d'entreprise: {e}")
            flash('Erreur lors de la création des paramètres d\'entreprise', 'error')
            return render_template('initialisation.html')
        
        # Créer la clé d'initialisation
        from init_key_manager import init_key_manager
        
        admin_data = {
            'nom': init_data['nom'],
            'prenom': init_data['prenom'],
            'email': init_data['email'],
            'telephone': init_data['telephone'],
            'username': username
        }
        
        if init_key_manager.create_init_key(admin_data):
            # Nettoyer la session
            session.pop('init_data', None)
            session.pop('email_verified', None)
            
            flash('🎉 Initialisation terminée avec succès ! Votre compte administrateur a été créé.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Erreur lors de la création de la clé d\'initialisation', 'error')
            return render_template('initialisation.html')
        
    except Exception as e:
        flash(f'Erreur lors de la finalisation : {str(e)}', 'error')
        return render_template('initialisation.html')

@app.route('/first-setup', methods=['GET', 'POST'])
def first_setup():
    """Redirection vers le système d'initialisation moderne avec clé"""
    # Cette route est conservée pour compatibilité mais redirige vers le nouveau système
    logger.info("Redirection de first-setup vers initialisation (système unifié)")
    return redirect(url_for('initialisation'))

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    """Page de profil utilisateur"""
    user = get_current_user()
    rating_avg = None
    rating_count = 0
    if user and user.role == 'technicien':
        rating_avg, rating_count = _get_rating_stats_for_technicien(user.id)
    
    if request.method == 'POST':
        try:
            # Mise à jour des informations personnelles
            user.nom = request.form.get('nom', user.nom)
            user.prenom = request.form.get('prenom', user.prenom)
            user.email = request.form.get('email', user.email)
            user.telephone = request.form.get('telephone', user.telephone)
            user.bio = request.form.get('bio', '')
            user.adresse = request.form.get('adresse', '')
            user.ville = request.form.get('ville', '')
            user.code_postal = request.form.get('code_postal', '')
            
            # Date de naissance
            date_naissance_str = request.form.get('date_naissance')
            if date_naissance_str:
                user.date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
            
            # Changement de mot de passe (optionnel)
            nouveau_mdp = request.form.get('nouveau_mdp')
            if nouveau_mdp:
                ancien_mdp = request.form.get('ancien_mdp')
                if ancien_mdp and check_password_hash(user.password_hash, ancien_mdp):
                    user.password_hash = generate_password_hash(nouveau_mdp)
                    flash('Mot de passe modifié avec succès !', 'success')
                elif ancien_mdp:
                    flash('Ancien mot de passe incorrect', 'error')
                    return redirect(url_for('profil'))
            
            # Upload de photo
            if 'photo_profil' in request.files:
                file = request.files['photo_profil']
                if file and file.filename:
                    # Sécuriser le nom de fichier
                    from werkzeug.utils import secure_filename
                    import uuid
                    
                    filename = secure_filename(file.filename)
                    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
                    valid, result = validate_image_upload(file, allowed_extensions)
                    if valid:
                        ext = result
                        # Créer un nom unique
                        unique_filename = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles')
                        
                        # Créer le dossier s'il n'existe pas
                        os.makedirs(upload_path, exist_ok=True)
                        
                        # Supprimer l'ancienne photo si elle existe
                        if user.photo_profil:
                            old_photo_path = os.path.join(app.root_path, 'static', user.photo_profil)
                            if os.path.exists(old_photo_path):
                                os.remove(old_photo_path)
                        
                        # Sauvegarder la nouvelle photo
                        file_path = os.path.join(upload_path, unique_filename)
                        file.save(file_path)
                        
                        # Stocker le chemin relatif
                        user.photo_profil = f'uploads/profiles/{unique_filename}'
                    else:
                        flash('Format de fichier non autorisé. Utilisez JPG, PNG ou GIF.', 'error')
                        return redirect(url_for('profil'))
            
            db.session.commit()
            flash('Profil mis à jour avec succès !', 'success')
            return redirect(url_for('profil'))
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du profil: {str(e)}")
            flash(f'Erreur lors de la mise à jour : {str(e)}', 'error')
            return redirect(url_for('profil'))
    
    return render_template('profil.html', user=user, current_user=user, rating_avg=rating_avg, rating_count=rating_count)

@app.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def register():
    """Création d'un nouvel utilisateur (admin uniquement)"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        nom = request.form['nom']
        prenom = request.form['prenom']
        telephone = request.form.get('telephone', '')
        
        # Vérifier si l'utilisateur existe déjà
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur existe déjà', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Cette adresse email existe déjà', 'error')
            return redirect(url_for('register'))
        
        # Créer l'utilisateur
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            nom=nom,
            prenom=prenom,
            telephone=telephone
        )
        
        db.session.add(user)
        db.session.flush()  # Pour obtenir l'ID de l'utilisateur
        
        # Si l'utilisateur a le rôle "dj", créer automatiquement un DJ
        if role == 'dj':
            dj = DJ(
                nom=f"{prenom} {nom}".strip(),
                contact=telephone or email,
                user_id=user.id
            )
            db.session.add(dj)
        
        db.session.commit()
        
        flash('Utilisateur créé avec succès !', 'success')
        return redirect(url_for('users'))
    
    return render_template('register.html')

def _get_groq_status():
    from ai_assistant import GROQ_AVAILABLE, ai_assistant
    parametres = ParametresEntreprise.query.first()
    db_groq_key = (parametres.groq_api_key or '').strip() if parametres else ''
    env_groq_key = (os.environ.get('GROQ_API_KEY') or '').strip()
    groq_configured = bool(env_groq_key or db_groq_key)
    try:
        ai_assistant.refresh_api_key()
    except Exception as e:
        logger.warning(f"Impossible de rafraîchir la clé Groq: {e}")
    loaded_key = (getattr(ai_assistant, 'api_key', '') or '').strip()
    client_ready = bool(getattr(ai_assistant, 'client', None))
    last_error = getattr(ai_assistant, 'last_error', None)
    last_error_at = getattr(ai_assistant, 'last_error_at', None)
    last_ok_at = getattr(ai_assistant, 'last_ok_at', None)
    error_is_recent = False
    if last_error:
        if not last_ok_at:
            error_is_recent = True
        elif last_error_at and last_ok_at and last_error_at >= last_ok_at:
            error_is_recent = True
    groq_active = bool(GROQ_AVAILABLE and loaded_key and client_ready and not error_is_recent)
    if not GROQ_AVAILABLE:
        groq_message = "SDK manquant"
    elif not groq_configured:
        groq_message = "Clé manquante"
    elif not loaded_key:
        groq_message = "Clé non chargée"
    elif not client_ready:
        groq_message = "Init échouée"
    elif error_is_recent:
        groq_message = "Erreur API récente"
    else:
        source_label = "env" if env_groq_key else "base"
        if last_ok_at:
            groq_message = f"OK ({source_label}, testé)"
        else:
            groq_message = f"OK ({source_label}, non testé)"
    return {
        'available': GROQ_AVAILABLE,
        'configured': groq_configured,
        'active': groq_active,
        'source': 'env' if env_groq_key else ('base' if db_groq_key else None),
        'message': groq_message,
        'error': last_error if error_is_recent else None,
    }

@app.route('/admin')
@login_required
@role_required(['admin'])
def admin_dashboard():
    """Tableau de bord administrateur"""
    user = get_current_user()
    groq_status = _get_groq_status()
    
    # Statistiques complètes
    stats = {
        'total_prestations': Prestation.query.count(),
        'prestations_planifiees': Prestation.query.filter_by(statut='planifiee').count(),
        'prestations_confirmees': Prestation.query.filter_by(statut='confirmee').count(),
        'total_materiels': Materiel.query.count(),
        'materiels_disponibles': Materiel.query.filter_by(statut='disponible').count(),
        'materiels_maintenance': Materiel.query.filter_by(statut='maintenance').count(),
        'total_djs': DJ.query.count(),
        'total_locals': Local.query.count(),
        'total_users': User.query.count(),
        'total_devis': Devis.query.count()
    }
    
    # Prestations récentes
    prestations_recentes = Prestation.query.order_by(Prestation.date_debut.desc()).limit(5).all()
    
    # Prestations à venir
    prestations_a_venir = Prestation.query.filter(
        Prestation.date_debut >= date.today()
    ).order_by(Prestation.date_debut).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                         stats=stats,
                         prestations_recentes=prestations_recentes,
                         prestations_a_venir=prestations_a_venir,
                         groq_status=groq_status,
                         current_user=user)

@app.route('/ia')
@login_required
@role_required(['admin', 'manager'])
def ia_hub():
    """Page centrale des fonctionnalités IA"""
    user = get_current_user()
    groq_status = _get_groq_status()
    parametres = ParametresEntreprise.query.first()
    djs = DJ.query.order_by(DJ.nom).all()
    materiels = Materiel.query.order_by(Materiel.nom).all()
    return render_template('ia_hub.html',
                           groq_status=groq_status,
                           parametres=parametres,
                           djs=djs,
                           materiels=materiels,
                           current_user=user)

@app.route('/ia/update-key', methods=['POST'])
@login_required
@role_required(['admin'])
def ia_update_key():
    """Met à jour la clé Groq depuis la page IA"""
    try:
        parametres = ParametresEntreprise.query.first()
        if not parametres:
            parametres = ParametresEntreprise()
            db.session.add(parametres)

        old_groq_key = (parametres.groq_api_key or '').strip()
        groq_api_key = request.form.get('groq_api_key', '').strip()
        if request.form.get('clear_groq_api_key'):
            parametres.groq_api_key = None
        elif groq_api_key:
            parametres.groq_api_key = groq_api_key

        db.session.commit()

        try:
            from ai_assistant import ai_assistant
            ai_assistant.refresh_api_key()
            new_groq_key = (parametres.groq_api_key or '').strip()
            groq_key_changed = old_groq_key != new_groq_key
            if groq_key_changed and new_groq_key:
                source_label = "env" if os.environ.get('GROQ_API_KEY') else "base"
                ok, msg = ai_assistant.test_connection()
                if ok:
                    flash(f'Clé Groq validée ({source_label})', 'success')
                else:
                    flash(f'Verification Groq ({source_label}) échouée: {msg}', 'error')
        except Exception as e:
            logger.warning(f"Impossible de recharger la clé Groq: {e}")

        flash('Clé Groq mise à jour', 'success')
    except Exception as e:
        logger.error(f"Erreur mise à jour clé Groq: {e}")
        flash('Erreur lors de la mise à jour de la clé Groq', 'error')

    return redirect(url_for('ia_hub'))

@app.route('/manager')
@login_required
@role_required(['manager'])
def manager_dashboard():
    """Tableau de bord manager"""
    user = get_current_user()
    
    # Statistiques pour manager
    stats = {
        'total_prestations': Prestation.query.count(),
        'prestations_planifiees': Prestation.query.filter_by(statut='planifiee').count(),
        'prestations_confirmees': Prestation.query.filter_by(statut='confirmee').count(),
        'total_materiels': Materiel.query.count(),
        'materiels_disponibles': Materiel.query.filter_by(statut='disponible').count(),
        'materiels_maintenance': Materiel.query.filter_by(statut='maintenance').count()
    }
    
    # Prestations récentes
    prestations_recentes = Prestation.query.order_by(Prestation.date_debut.desc()).limit(5).all()
    
    return render_template('manager_dashboard.html', 
                         stats=stats,
                         prestations_recentes=prestations_recentes,
                         current_user=user)

@app.route('/dj')
@login_required
@role_required(['dj'])
def dj_dashboard():
    """Tableau de bord DJ"""
    user = get_current_user()
    
    # Trouver le DJ lié à cet utilisateur
    dj = DJ.query.filter_by(user_id=user.id).first()
    
    if not dj:
        flash('Aucun profil DJ trouvé pour votre compte. Contactez un administrateur.', 'error')
        return redirect(url_for('login'))
    
    # Prestations du DJ
    prestations_dj = Prestation.query.filter_by(dj_id=dj.id).order_by(Prestation.date_debut.desc()).all()
    
    # Prestations à venir
    prestations_a_venir = Prestation.query.filter(
        Prestation.dj_id == dj.id,
        Prestation.date_debut >= date.today()
    ).order_by(Prestation.date_debut).all()
    
    return render_template('dj_dashboard.html', 
                         prestations_dj=prestations_dj,
                         prestations_a_venir=prestations_a_venir,
                         dj=dj,
                         current_user=user)

@app.route('/technicien')
@login_required
@role_required(['technicien'])
def technicien_dashboard():
    """Tableau de bord technicien"""
    user = get_current_user()
    
    # Matériel en maintenance
    materiels_maintenance = Materiel.query.filter_by(statut='maintenance').all()
    
    # Statistiques matériel
    stats = {
        'total_materiels': Materiel.query.count(),
        'materiels_disponibles': Materiel.query.filter_by(statut='disponible').count(),
        'materiels_maintenance': Materiel.query.filter_by(statut='maintenance').count()
    }

    return render_template('technicien_dashboard.html', 
                         materiels_maintenance=materiels_maintenance,
                         stats=stats,
                         current_user=user)

@app.route('/users')
@login_required
@role_required(['admin'])
def users():
    """Liste des utilisateurs (admin uniquement)"""
    users = User.query.all()
    return render_template('users.html', users=users, current_user=get_current_user())

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_user(user_id):
    """Modifier un utilisateur (admin uniquement)"""
    user = get_or_404(User, user_id)
    
    if request.method == 'POST':
        try:
            old_role = user.role
            user.nom = request.form['nom']
            user.prenom = request.form['prenom']
            user.email = request.form['email']
            user.telephone = request.form.get('telephone', '')
            user.role = request.form['role']
            user.actif = 'actif' in request.form
            
            # Si un nouveau mot de passe est fourni
            new_password = request.form.get('password')
            if new_password:
                user.password_hash = generate_password_hash(new_password)
            
            # Gérer les changements de rôle pour les DJs
            if old_role != 'dj' and user.role == 'dj':
                # L'utilisateur devient DJ, créer un DJ
                dj = DJ(
                    nom=f"{user.prenom} {user.nom}".strip(),
                    contact=user.telephone or user.email,
                    user_id=user.id
                )
                db.session.add(dj)
            elif old_role == 'dj' and user.role != 'dj':
                # L'utilisateur n'est plus DJ, supprimer le DJ associé
                dj_to_delete = DJ.query.filter_by(user_id=user.id).first()
                if dj_to_delete:
                    db.session.delete(dj_to_delete)
            
            db.session.commit()
            flash('Utilisateur modifié avec succès !', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    return render_template('edit_user.html', user=user, current_user=get_current_user())

@app.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_user(user_id):
    """Activer/Désactiver un utilisateur (admin uniquement)"""
    user = get_or_404(User, user_id)
    
    # Ne pas permettre de désactiver son propre compte
    if user.id == session.get('user_id'):
        flash('Vous ne pouvez pas désactiver votre propre compte', 'error')
        return redirect(url_for('users'))
    
    try:
        user.actif = not user.actif
        db.session.commit()
        
        status = "activé" if user.actif else "désactivé"
        flash(f'Utilisateur {user.nom} {status} avec succès !', 'success')
    except Exception as e:
        flash(f'Erreur lors du changement de statut : {str(e)}', 'error')
    
    return redirect(url_for('users'))

# Routes pour les devis
@app.route('/devis')
@login_required
@role_required(['admin', 'manager'])
def devis():
    """Page devis supprimée : rediriger vers la facturation."""
    return redirect(url_for('facturation'))

@app.route('/devis/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def nouveau_devis():
    """Créer un nouveau devis"""
    # Récupérer les prestations actives pour la sélection
    prestations_actives = Prestation.query.filter(
        Prestation.statut.in_(['planifiee', 'confirmee'])
    ).order_by(Prestation.date_debut.desc()).all()
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            erreurs = []
            prestation_id = request.form.get('prestation_id')
            prestation_selectionnee = None
            
            if prestation_id and prestation_id != '':
                # Si une prestation est sélectionnée, récupérer ses données
                try:
                    prestation_selectionnee = db.session.get(Prestation, int(prestation_id))
                except (TypeError, ValueError):
                    prestation_selectionnee = None
                if prestation_selectionnee:
                    # Auto-remplissage depuis la prestation
                    client_nom = normalize_whitespace(prestation_selectionnee.client)
                    client_email = ''  # Pas d'email dans Prestation
                    client_telephone = ''  # Pas de téléphone dans Prestation
                    client_adresse = ''
                    prestation_titre = normalize_whitespace(f"Mission Prestataire - {prestation_selectionnee.client}")
                    prestation_description = prestation_selectionnee.notes or ''
                    date_prestation = prestation_selectionnee.date_debut
                    heure_debut = prestation_selectionnee.heure_debut
                    heure_fin = prestation_selectionnee.heure_fin
                    lieu = normalize_whitespace(prestation_selectionnee.lieu)
                    dj_id = prestation_selectionnee.dj_id
                else:
                    erreurs.append('Prestation sélectionnée introuvable')
            else:
                # Création manuelle
                client_nom = normalize_whitespace(request.form.get('client_nom', ''))
                client_email = normalize_email(request.form.get('client_email', ''))
                client_telephone = normalize_telephone(request.form.get('client_telephone', ''))
                client_adresse = normalize_whitespace(request.form.get('client_adresse', ''))
                prestation_titre = normalize_whitespace(request.form.get('prestation_titre', ''))
                prestation_description = request.form.get('prestation_description', '')
                date_prestation = parse_date_field(request.form.get('date_prestation'), "Date de prestation", erreurs)
                heure_debut = parse_time_field(request.form.get('heure_debut'), "Heure de début", erreurs)
                heure_fin = parse_time_field(request.form.get('heure_fin'), "Heure de fin", erreurs)
                lieu = normalize_whitespace(request.form.get('lieu', ''))
                dj_id = request.form.get('dj_id')

            client_siren = normalize_whitespace(request.form.get('client_siren', ''))
            client_tva = normalize_whitespace(request.form.get('client_tva', ''))
            adresse_livraison = normalize_whitespace(request.form.get('adresse_livraison', ''))
            nature_operation = normalize_whitespace(request.form.get('nature_operation', ''))
            numero_bon_commande = normalize_whitespace(request.form.get('numero_bon_commande', ''))
            client_professionnel = 'client_professionnel' in request.form
            tva_sur_debits = 'tva_sur_debits' in request.form

            validate_required_field(client_nom, "Nom client", erreurs)
            validate_required_field(prestation_titre, "Titre de prestation", erreurs)
            validate_required_field(lieu, "Lieu", erreurs)

            if client_email:
                valide, message = valider_email(client_email)
                if not valide:
                    erreurs.append(message)
            if client_telephone:
                valide, message = valider_telephone(client_telephone)
                if not valide:
                    erreurs.append(message)
            if client_professionnel:
                valide, message = valider_siren(client_siren)
                if not valide:
                    erreurs.append(message)
                if not nature_operation:
                    erreurs.append("La nature de l’opération est requise pour un client professionnel")

            validate_time_range(heure_debut, heure_fin, erreurs)
            
            # Tarification
            tarif_horaire = parse_float_field(request.form.get('tarif_horaire', 0), "Tarif horaire", erreurs, min_value=0, default=0)
            duree_heures = parse_float_field(request.form.get('duree_heures', 0), "Durée (heures)", erreurs, min_value=0, default=0)
            taux_tva = parse_float_field(request.form.get('taux_tva', 20), "TVA", erreurs, min_value=0, max_value=100, default=20)
            remise_pourcentage = parse_float_field(request.form.get('remise_pourcentage', 0), "Remise (%)", erreurs, min_value=0, max_value=100, default=0)
            remise_montant = parse_float_field(request.form.get('remise_montant', 0), "Remise (€)", erreurs, min_value=0, default=0)
            frais_transport = parse_float_field(request.form.get('frais_transport', 0), "Frais transport", erreurs, min_value=0, default=0)
            frais_materiel = parse_float_field(request.form.get('frais_materiel', 0), "Frais matériel", erreurs, min_value=0, default=0)
            
            # Acompte
            acompte_requis = 'acompte_requis' in request.form
            acompte_pourcentage = parse_float_field(request.form.get('acompte_pourcentage', 0) or 0, "Acompte (%)", erreurs, min_value=0, max_value=100, default=0)

            # Date de validité
            date_validite = None
            if request.form.get('date_validite'):
                date_validite = parse_date_field(request.form.get('date_validite'), "Date de validité", erreurs, required=False)

            # Vérifier cohérence durée / horaires
            duree_calc = compute_duration_hours(heure_debut, heure_fin)
            if duree_calc is not None:
                if duree_heures is not None and duree_heures <= 0:
                    duree_heures = duree_calc
                elif duree_heures is not None and abs(duree_heures - duree_calc) > 0.5:
                    erreurs.append("La durée ne correspond pas aux horaires indiqués")

            if date_validite and date_prestation and date_validite < date_prestation:
                erreurs.append("La date de validité doit être postérieure à la date de prestation")

            dj_id_value = None
            if dj_id not in (None, "", "None"):
                try:
                    dj_id_value = int(dj_id)
                    if not db.session.get(DJ, dj_id_value):
                        erreurs.append("DJ sélectionné introuvable")
                except (TypeError, ValueError):
                    erreurs.append("DJ invalide")

            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('nouveau_devis'))
            
            # Créer le devis
            client_ref = get_or_create_client(client_nom, client_email, client_telephone)
            numero_devis = generate_document_number('DEV')
            devis = Devis(
                numero=numero_devis,
                client_nom=client_nom,
                client_email=client_email,
                client_telephone=client_telephone,
                client_adresse=client_adresse,
                client_siren=client_siren,
                client_tva=client_tva,
                adresse_livraison=adresse_livraison,
                nature_operation=nature_operation,
                tva_sur_debits=tva_sur_debits,
                numero_bon_commande=numero_bon_commande,
                client_professionnel=client_professionnel,
                client_id=client_ref.id if client_ref else None,
                prestation_titre=prestation_titre,
                prestation_description=prestation_description,
                date_prestation=date_prestation,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                lieu=lieu,
                tarif_horaire=tarif_horaire,
                duree_heures=duree_heures,
                taux_tva=taux_tva,
                remise_pourcentage=remise_pourcentage,
                remise_montant=remise_montant,
                frais_transport=frais_transport,
                frais_materiel=frais_materiel,
                acompte_requis=acompte_requis,
                acompte_pourcentage=acompte_pourcentage,
                date_validite=date_validite,
                dj_id=dj_id_value,
                prestation_id=prestation_id if prestation_id else None,
                createur_id=session['user_id']
            )
            
            # Calculer les totaux
            devis.calculer_totaux()

            if not devis.contenu_html:
                parametres = ParametresEntreprise.query.first()
                devis.contenu_html = build_devis_template(devis, parametres)
            
            db.session.add(devis)
            db.session.commit()
            AuditLog.log_action(
                action='creation',
                entite_type='devis',
                entite_id=devis.id,
                entite_nom=devis.numero,
                details={'montant_ttc': devis.montant_ttc}
            )
            flash('Devis créé avec succès !', 'success')
            return redirect(url_for('detail_devis', devis_id=devis.id))
            
        except Exception as e:
            flash(f'Erreur lors de la création du devis : {str(e)}', 'error')
    
    # Récupérer les DJs pour le formulaire
    djs = DJ.query.all()
    techniciens = User.query.filter_by(role='technicien', actif=True).all()
    techniciens = User.query.filter_by(role='technicien', actif=True).all()
    techniciens = User.query.filter_by(role='technicien', actif=True).all()
    techniciens = User.query.filter_by(role='technicien', actif=True).all()
    techniciens = User.query.filter_by(role='technicien', actif=True).all()
    return render_template('nouveau_devis.html', 
                         djs=djs, 
                         prestations_actives=prestations_actives,
                         current_user=get_current_user())

@app.route('/devis/<int:devis_id>')
@login_required
@role_required(['admin', 'manager'])
def detail_devis(devis_id):
    """Détail d'un devis"""
    devis = get_or_404(Devis, devis_id)
    parametres = ParametresEntreprise.query.first()
    devis_content_raw = devis.contenu_html or build_devis_template(devis, parametres)
    devis_content = sanitize_rich_html(devis_content_raw)
    return render_template(
        'detail_devis.html',
        devis=devis,
        devis_content=devis_content,
        current_user=get_current_user(),
        parametres=parametres
    )

@app.route('/devis/<int:devis_id>/contenu', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def mettre_a_jour_contenu_devis(devis_id):
    """Mettre a jour le contenu riche d'un devis"""
    devis = get_or_404(Devis, devis_id)
    if is_devis_locked(devis):
        flash('Ce devis est signé et ne peut plus être modifié.', 'error')
        return redirect(url_for('detail_devis', devis_id=devis.id))
    contenu_html = request.form.get('contenu_html', '').strip()
    devis.contenu_html = sanitize_rich_html(contenu_html)
    db.session.commit()
    flash('Contenu du devis mis a jour.', 'success')
    return redirect(url_for('detail_devis', devis_id=devis.id))

@app.route('/devis/<int:devis_id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def modifier_devis(devis_id):
    """Modifier un devis"""
    devis = get_or_404(Devis, devis_id)
    if is_devis_locked(devis):
        flash('Ce devis est signé et ne peut plus être modifié.', 'error')
        return redirect(url_for('detail_devis', devis_id=devis.id))
    
    if request.method == 'POST':
        try:
            # Mettre à jour les données
            erreurs = []
            client_nom = normalize_whitespace(request.form.get('client_nom', ''))
            client_email = normalize_email(request.form.get('client_email', ''))
            client_telephone = normalize_telephone(request.form.get('client_telephone', ''))
            client_adresse = normalize_whitespace(request.form.get('client_adresse', ''))
            client_siren = normalize_whitespace(request.form.get('client_siren', ''))
            client_tva = normalize_whitespace(request.form.get('client_tva', ''))
            adresse_livraison = normalize_whitespace(request.form.get('adresse_livraison', ''))
            nature_operation = normalize_whitespace(request.form.get('nature_operation', ''))
            tva_sur_debits = 'tva_sur_debits' in request.form
            numero_bon_commande = normalize_whitespace(request.form.get('numero_bon_commande', ''))
            client_professionnel = 'client_professionnel' in request.form

            prestation_titre = normalize_whitespace(request.form.get('prestation_titre', ''))
            prestation_description = request.form.get('prestation_description', '')
            date_prestation = parse_date_field(request.form.get('date_prestation'), "Date de prestation", erreurs)
            heure_debut = parse_time_field(request.form.get('heure_debut'), "Heure de début", erreurs)
            heure_fin = parse_time_field(request.form.get('heure_fin'), "Heure de fin", erreurs)
            lieu = normalize_whitespace(request.form.get('lieu', ''))

            validate_required_field(client_nom, "Nom client", erreurs)
            validate_required_field(prestation_titre, "Titre de prestation", erreurs)
            validate_required_field(lieu, "Lieu", erreurs)
            validate_time_range(heure_debut, heure_fin, erreurs)

            if client_email:
                valide, message = valider_email(client_email)
                if not valide:
                    erreurs.append(message)
            if client_telephone:
                valide, message = valider_telephone(client_telephone)
                if not valide:
                    erreurs.append(message)
            if client_professionnel:
                valide, message = valider_siren(client_siren)
                if not valide:
                    erreurs.append(message)
                if not nature_operation:
                    erreurs.append("La nature de l’opération est requise pour un client professionnel")

            # Tarification
            tarif_horaire = parse_float_field(request.form.get('tarif_horaire', 0), "Tarif horaire", erreurs, min_value=0, default=0)
            duree_heures = parse_float_field(request.form.get('duree_heures', 0), "Durée (heures)", erreurs, min_value=0, default=0)
            taux_tva = parse_float_field(request.form.get('taux_tva', 20), "TVA", erreurs, min_value=0, max_value=100, default=20)
            remise_pourcentage = parse_float_field(request.form.get('remise_pourcentage', 0), "Remise (%)", erreurs, min_value=0, max_value=100, default=0)
            remise_montant = parse_float_field(request.form.get('remise_montant', 0), "Remise (€)", erreurs, min_value=0, default=0)
            frais_transport = parse_float_field(request.form.get('frais_transport', 0), "Frais transport", erreurs, min_value=0, default=0)
            frais_materiel = parse_float_field(request.form.get('frais_materiel', 0), "Frais matériel", erreurs, min_value=0, default=0)

            # Acompte
            acompte_requis = 'acompte_requis' in request.form
            acompte_pourcentage = parse_float_field(request.form.get('acompte_pourcentage', 0) or 0, "Acompte (%)", erreurs, min_value=0, max_value=100, default=0)

            # Date de validité
            date_validite = None
            if request.form.get('date_validite'):
                date_validite = parse_date_field(request.form.get('date_validite'), "Date de validité", erreurs, required=False)

            duree_calc = compute_duration_hours(heure_debut, heure_fin)
            if duree_calc is not None:
                if duree_heures is not None and duree_heures <= 0:
                    duree_heures = duree_calc
                elif duree_heures is not None and abs(duree_heures - duree_calc) > 0.5:
                    erreurs.append("La durée ne correspond pas aux horaires indiqués")

            if date_validite and date_prestation and date_validite < date_prestation:
                erreurs.append("La date de validité doit être postérieure à la date de prestation")

            dj_id_value = None
            dj_id_raw = request.form.get('dj_id')
            if dj_id_raw not in (None, "", "None"):
                try:
                    dj_id_value = int(dj_id_raw)
                    if not db.session.get(DJ, dj_id_value):
                        erreurs.append("DJ sélectionné introuvable")
                except (TypeError, ValueError):
                    erreurs.append("DJ invalide")

            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('modifier_devis', devis_id=devis.id))

            devis.client_nom = client_nom
            devis.client_email = client_email
            devis.client_telephone = client_telephone
            devis.client_adresse = client_adresse
            devis.client_siren = client_siren
            devis.client_tva = client_tva
            devis.adresse_livraison = adresse_livraison
            devis.nature_operation = nature_operation
            devis.tva_sur_debits = tva_sur_debits
            devis.numero_bon_commande = numero_bon_commande
            devis.client_professionnel = client_professionnel
            
            devis.prestation_titre = prestation_titre
            devis.prestation_description = prestation_description
            devis.date_prestation = date_prestation
            devis.heure_debut = heure_debut
            devis.heure_fin = heure_fin
            devis.lieu = lieu
            
            # Tarification
            devis.tarif_horaire = tarif_horaire
            devis.duree_heures = duree_heures
            devis.taux_tva = taux_tva
            devis.remise_pourcentage = remise_pourcentage
            devis.remise_montant = remise_montant
            devis.frais_transport = frais_transport
            devis.frais_materiel = frais_materiel
            
            # Acompte
            devis.acompte_requis = acompte_requis
            devis.acompte_pourcentage = acompte_pourcentage

            # Date de validité
            devis.date_validite = date_validite
            
            devis.dj_id = dj_id_value
            
            # Recalculer les totaux
            devis.calculer_totaux()
            
            db.session.commit()
            AuditLog.log_action(
                action='modification',
                entite_type='devis',
                entite_id=devis.id,
                entite_nom=devis.numero,
                details={'statut': devis.statut}
            )
            flash('Devis modifié avec succès !', 'success')
            return redirect(url_for('detail_devis', devis_id=devis.id))
            
        except Exception as e:
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    # Récupérer les DJs pour le formulaire
    djs = DJ.query.all()
    return render_template('modifier_devis.html', devis=devis, djs=djs, current_user=get_current_user())

@app.route('/devis/<int:devis_id>/supprimer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def supprimer_devis(devis_id):
    """Supprimer un devis"""
    devis = get_or_404(Devis, devis_id)
    try:
        if is_devis_locked(devis):
            flash('Ce devis est signé et ne peut pas être supprimé. Utilisez une annulation.', 'error')
            return redirect(url_for('detail_devis', devis_id=devis.id))
        devis.statut = 'annule'
        devis.date_annulation = utcnow()
        db.session.commit()
        AuditLog.log_action(
            action='annulation',
            entite_type='devis',
            entite_id=devis.id,
            entite_nom=devis.numero
        )
        flash('Devis annulé avec succès !', 'success')
    except Exception as e:
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
    
    return redirect(url_for('facturation'))

@app.route('/devis/<int:devis_id>/changer-statut', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def changer_statut_devis(devis_id):
    """Changer le statut d'un devis"""
    devis = get_or_404(Devis, devis_id)
    nouveau_statut = request.form['statut']

    if is_devis_locked(devis):
        flash('Ce devis est signé et son statut ne peut plus être modifié.', 'error')
        return redirect(url_for('detail_devis', devis_id=devis_id))
    
    try:
        devis.statut = nouveau_statut
        
        if nouveau_statut == 'envoye':
            devis.date_envoi = utcnow()
        elif nouveau_statut == 'accepte':
            devis.date_acceptation = utcnow()
        
        db.session.commit()
        flash(f'Statut du devis changé en "{nouveau_statut}"', 'success')
    except Exception as e:
        flash(f'Erreur lors du changement de statut : {str(e)}', 'error')
    
    return redirect(url_for('detail_devis', devis_id=devis_id))

# Routes pour les paramètres d'entreprise
@app.route('/parametres')
@login_required
@role_required(['admin'])
def parametres():
    """Page des paramètres d'entreprise"""
    # Récupérer ou créer les paramètres
    parametres = ParametresEntreprise.query.first()
    if not parametres:
        parametres = ParametresEntreprise()
        db.session.add(parametres)
        db.session.commit()
    rib_values = get_rib_values(parametres)
    rib_masked = {
        'iban': mask_sensitive(rib_values.get('iban')),
        'bic': mask_sensitive(rib_values.get('bic')),
        'titulaire': mask_sensitive(rib_values.get('titulaire')),
        'banque': mask_sensitive(rib_values.get('banque')),
    }
    return render_template(
        'parametres.html',
        parametres=parametres,
        current_user=get_current_user(),
        rib_masked=rib_masked,
        encryption_ready=encryption_ready()
    )

@app.route('/personnalisation')
@login_required
@role_required(['admin'])
def personnalisation():
    """Page de personnalisation et données entreprise"""
    parametres = ParametresEntreprise.query.first()
    if not parametres:
        parametres = ParametresEntreprise()
        db.session.add(parametres)
        db.session.commit()
    return render_template('personnalisation.html', parametres=parametres, current_user=get_current_user())

@app.route('/parametres/modifier', methods=['POST'])
@login_required
@role_required(['admin'])
def modifier_parametres():
    """Modifier les paramètres d'entreprise"""
    try:
        parametres = ParametresEntreprise.query.first()
        if not parametres:
            parametres = ParametresEntreprise()
            db.session.add(parametres)
        erreurs = []
        old_address = build_full_address(parametres.adresse, parametres.code_postal, parametres.ville)
        old_groq_key = (parametres.groq_api_key or '').strip()

        # Mise à jour des données
        parametres.nom_entreprise = request.form['nom_entreprise']
        parametres.slogan = request.form.get('slogan', '')
        parametres.description_courte = request.form.get('description_courte', '')
        parametres.adresse = normalize_whitespace(request.form.get('adresse', ''))
        parametres.code_postal = normalize_whitespace(request.form.get('code_postal', ''))
        parametres.ville = normalize_whitespace(request.form.get('ville', ''))
        parametres.telephone = request.form.get('telephone', '')
        parametres.email = normalize_email(request.form.get('email', ''))
        parametres.email_signature = request.form.get('email_signature', '')
        parametres.site_web = request.form.get('site_web', '')
        google_maps_api_key = request.form.get('google_maps_api_key', '').strip()
        if request.form.get('clear_google_maps_api_key'):
            parametres.google_maps_api_key = None
        elif google_maps_api_key:
            parametres.google_maps_api_key = google_maps_api_key
        parametres.siret = request.form.get('siret', '')
        parametres.tva_intracommunautaire = request.form.get('tva_intracommunautaire', '')
        parametres.forme_juridique = request.form.get('forme_juridique', '').strip()
        parametres.capital_social = request.form.get('capital_social', '').strip()
        parametres.rcs_ville = request.form.get('rcs_ville', '').strip()
        parametres.numero_rcs = request.form.get('numero_rcs', '').strip()
        parametres.penalites_retard = request.form.get('penalites_retard', '').strip()
        parametres.escompte = request.form.get('escompte', '').strip()
        if 'indemnite_recouvrement' in request.form:
            parametres.indemnite_recouvrement = parse_float_field(
                request.form.get('indemnite_recouvrement', 40),
                "Indemnité forfaitaire",
                erreurs,
                min_value=0,
                default=40.0
            )
        parametres.tva_non_applicable = 'tva_non_applicable' in request.form
        if 'taux_tva_defaut' in request.form:
            parametres.taux_tva_defaut = parse_float_field(
                request.form.get('taux_tva_defaut', 20),
                "Taux TVA par défaut",
                erreurs,
                min_value=0,
                max_value=100,
                default=20.0
            )
        parametres.couleur_principale = request.form.get('couleur_principale', '#667eea')
        parametres.couleur_secondaire = request.form.get('couleur_secondaire', '#764ba2')
        parametres.devise = request.form.get('devise', 'EUR')
        if 'distance_gratuite_km' in request.form:
            parametres.distance_gratuite_km = parse_float_field(
                request.form.get('distance_gratuite_km', 30),
                "Distance gratuite (km)",
                erreurs,
                min_value=0,
                default=30.0
            )
        if 'frais_deplacement_km' in request.form:
            parametres.frais_deplacement_km = parse_float_field(
                request.form.get('frais_deplacement_km', 0.5),
                "Indemnité kilométrique",
                erreurs,
                min_value=0,
                default=0.5
            )
        if 'materiel_sortie_avant_heures' in request.form:
            parametres.materiel_sortie_avant_heures = parse_float_field(
                request.form.get('materiel_sortie_avant_heures', DEFAULT_MATERIEL_SORTIE_AVANT_HEURES),
                "Sortie matériel avant (heures)",
                erreurs,
                min_value=0,
                default=DEFAULT_MATERIEL_SORTIE_AVANT_HEURES
            )
        if 'materiel_retour_apres_heures' in request.form:
            parametres.materiel_retour_apres_heures = parse_float_field(
                request.form.get('materiel_retour_apres_heures', DEFAULT_MATERIEL_RETOUR_APRES_HEURES),
                "Retour matériel après (heures)",
                erreurs,
                min_value=0,
                default=DEFAULT_MATERIEL_RETOUR_APRES_HEURES
            )
        parametres.afficher_logo_login = 'afficher_logo_login' in request.form
        parametres.afficher_logo_sidebar = 'afficher_logo_sidebar' in request.form
        parametres.signature_entreprise_enabled = 'signature_entreprise_enabled' in request.form
        groq_api_key = request.form.get('groq_api_key', '').strip()
        if request.form.get('clear_groq_api_key'):
            parametres.groq_api_key = None
        elif groq_api_key:
            parametres.groq_api_key = groq_api_key
        new_groq_key = (parametres.groq_api_key or '').strip()
        groq_key_changed = old_groq_key != new_groq_key

        # Stripe
        parametres.stripe_enabled = 'stripe_enabled' in request.form
        stripe_public_key = request.form.get('stripe_public_key', '').strip()
        parametres.stripe_public_key = stripe_public_key or None
        stripe_secret_key = request.form.get('stripe_secret_key', '').strip()
        if stripe_secret_key:
            if not encryption_ready():
                erreurs.append("APP_ENCRYPTION_KEY requise pour enregistrer la clé Stripe.")
            else:
                parametres.stripe_secret_key = encrypt_sensitive(stripe_secret_key)

        # Coordonnées bancaires (RIB) - chiffrées
        clear_rib = 'clear_rib' in request.form
        rib_iban_input = normalize_whitespace(request.form.get('rib_iban', ''))
        rib_bic_input = normalize_whitespace(request.form.get('rib_bic', ''))
        rib_titulaire_input = normalize_whitespace(request.form.get('rib_titulaire', ''))
        rib_banque_input = normalize_whitespace(request.form.get('rib_banque', ''))
        if clear_rib:
            parametres.rib_iban = None
            parametres.rib_bic = None
            parametres.rib_titulaire = None
            parametres.rib_banque = None
        else:
            rib_inputs = [rib_iban_input, rib_bic_input, rib_titulaire_input, rib_banque_input]
            if any(rib_inputs):
                if not encryption_ready():
                    erreurs.append("APP_ENCRYPTION_KEY requise pour enregistrer le RIB.")
                else:
                    if rib_iban_input:
                        parametres.rib_iban = encrypt_sensitive(rib_iban_input)
                    if rib_bic_input:
                        parametres.rib_bic = encrypt_sensitive(rib_bic_input)
                    if rib_titulaire_input:
                        parametres.rib_titulaire = encrypt_sensitive(rib_titulaire_input)
                    if rib_banque_input:
                        parametres.rib_banque = encrypt_sensitive(rib_banque_input)

        # Ré-encrypter les valeurs sensibles existantes si besoin
        if encryption_ready():
            if parametres.stripe_secret_key and not str(parametres.stripe_secret_key).startswith('enc:'):
                parametres.stripe_secret_key = encrypt_sensitive(parametres.stripe_secret_key)
            if parametres.rib_iban and not str(parametres.rib_iban).startswith('enc:'):
                parametres.rib_iban = encrypt_sensitive(parametres.rib_iban)
            if parametres.rib_bic and not str(parametres.rib_bic).startswith('enc:'):
                parametres.rib_bic = encrypt_sensitive(parametres.rib_bic)
            if parametres.rib_titulaire and not str(parametres.rib_titulaire).startswith('enc:'):
                parametres.rib_titulaire = encrypt_sensitive(parametres.rib_titulaire)
            if parametres.rib_banque and not str(parametres.rib_banque).startswith('enc:'):
                parametres.rib_banque = encrypt_sensitive(parametres.rib_banque)
        
        # Gestion des modules optionnels
        parametres.module_excel_export = 'module_excel_export' in request.form
        parametres.module_pdf_generation = 'module_pdf_generation' in request.form
        parametres.module_financial_reports = 'module_financial_reports' in request.form
        parametres.module_notifications = 'module_notifications' in request.form
        
        # Gestion du logo
        logger.info(f"Fichiers reçus: {list(request.files.keys())}")
        if 'logo' in request.files:
            logo_file = request.files['logo']
            logger.info(f"Logo file: {logo_file}, filename: {logo_file.filename}")
            if logo_file and logo_file.filename:
                # Vérifier l'extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                valid, result = validate_image_upload(logo_file, allowed_extensions)
                file_extension = result if valid else ''
                logger.info(f"Extension du fichier: {file_extension}")
                if valid:
                    # Générer un nom unique
                    import uuid
                    filename = f"logo_{uuid.uuid4().hex[:8]}.{file_extension}"
                    
                    # Créer le dossier uploads s'il n'existe pas
                    uploads_dir = 'static/uploads'
                    os.makedirs(uploads_dir, exist_ok=True)
                    
                    logo_path = os.path.join(uploads_dir, filename)
                    logger.info(f"Sauvegarde du logo vers: {logo_path}")
                    logo_file.save(logo_path)
                    parametres.logo_path = filename
                    logger.info(f"Logo sauvegardé avec succès: {filename}")
                else:
                    logger.warning(f"Extension non autorisée: {file_extension}")
                    flash(f'Extension de fichier non autorisée. Extensions autorisées: {", ".join(allowed_extensions)}', 'error')
            else:
                logger.debug("Aucun fichier logo ou nom de fichier vide")
        else:
            logger.debug("Pas de champ 'logo' dans les fichiers")

        # Gestion de la signature entreprise
        if request.form.get('clear_signature_entreprise'):
            parametres.signature_entreprise_path = None
        if 'signature_entreprise' in request.files:
            signature_file = request.files['signature_entreprise']
            if signature_file and signature_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg'}
                valid, result = validate_image_upload(signature_file, allowed_extensions)
                file_extension = result if valid else ''
                if valid:
                    import uuid
                    filename = f"signature_{uuid.uuid4().hex[:8]}.{file_extension}"
                    uploads_dir = 'static/uploads'
                    os.makedirs(uploads_dir, exist_ok=True)
                    signature_path = os.path.join(uploads_dir, filename)
                    signature_file.save(signature_path)
                    parametres.signature_entreprise_path = filename
                else:
                    flash(f'Extension de fichier non autorisée pour la signature. Extensions autorisées: {", ".join(allowed_extensions)}', 'error')
        parametres.langue = request.form.get('langue', 'fr')
        parametres.date_modification = utcnow()

        if erreurs:
            for err in erreurs:
                flash(err, 'error')
            return redirect(url_for('parametres'))

        # Géocodage adresse entreprise si modifiée
        new_address = build_full_address(parametres.adresse, parametres.code_postal, parametres.ville)
        if new_address != old_address:
            parametres.adresse_lat = None
            parametres.adresse_lng = None
            parametres.adresse_formatted = None
            parametres.adresse_geocoded_at = None
            if new_address:
                geo, err = geocode_address(new_address, contact_email=parametres.email)
                if geo:
                    parametres.adresse_lat = geo['lat']
                    parametres.adresse_lng = geo['lng']
                    parametres.adresse_formatted = geo['formatted']
                    parametres.adresse_geocoded_at = utcnow()
                elif app.config.get('ADDRESS_VALIDATION_ENABLED'):
                    flash(f"Adresse entreprise non reconnue sur la carte: {err}", 'warning')
        
        db.session.commit()

        if not os.environ.get('GOOGLE_MAPS_API_KEY'):
            app.config['GOOGLE_MAPS_API_KEY'] = parametres.google_maps_api_key
        stripe_secret = get_stripe_secret(parametres)
        if stripe_secret:
            app.config['STRIPE_SECRET_KEY'] = stripe_secret
            try:
                from stripe_service import stripe_service
                stripe_service.init_app(app)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Stripe: {e}")
        else:
            app.config.pop('STRIPE_SECRET_KEY', None)
            if parametres.stripe_enabled:
                flash('Stripe activé sans clé secrète : les paiements en ligne resteront désactivés.', 'warning')

        try:
            from ai_assistant import ai_assistant
            ai_assistant.refresh_api_key()
            if groq_key_changed and new_groq_key:
                source_label = "env" if os.environ.get('GROQ_API_KEY') else "base"
                ok, msg = ai_assistant.test_connection()
                if ok:
                    flash(f'Clé Groq validée ({source_label})', 'success')
                else:
                    flash(f'Verification Groq ({source_label}) échouée: {msg}', 'error')
        except Exception as e:
            logger.warning(f"Impossible de recharger la clé Groq: {e}")
        
        # Mettre à jour le lazy importer avec les nouveaux paramètres
        lazy_importer.set_parametres(parametres)
        
        flash('Paramètres mis à jour avec succès !', 'success')
        
    except Exception as e:
        flash(f'Erreur lors de la mise à jour : {str(e)}', 'error')
    
    return redirect(url_for('parametres'))

@app.route('/personnalisation/modifier', methods=['POST'])
@login_required
@role_required(['admin'])
def modifier_personnalisation():
    """Met à jour uniquement la personnalisation de l'interface (sans modules)."""
    try:
        parametres = ParametresEntreprise.query.first()
        if not parametres:
            parametres = ParametresEntreprise()
            db.session.add(parametres)

        erreurs = []
        terminology_profile = request.form.get('terminology_profile', 'missions')
        if terminology_profile not in TERMINOLOGY_PROFILES:
            erreurs.append("Profil de terminologie invalide")
        parametres.terminology_profile = terminology_profile
        parametres.ui_theme = request.form.get('ui_theme', 'classic')
        parametres.ui_density = request.form.get('ui_density', 'comfortable')
        parametres.ui_font = normalize_whitespace(request.form.get('ui_font', ''))
        ui_radius_raw = request.form.get('ui_radius', '')
        if ui_radius_raw:
            try:
                ui_radius_val = int(float(ui_radius_raw))
                if ui_radius_val < 4 or ui_radius_val > 28:
                    erreurs.append("Le rayon des angles doit être entre 4 et 28")
                else:
                    parametres.ui_radius = ui_radius_val
            except ValueError:
                erreurs.append("Rayon des angles invalide")
        parametres.ui_custom_css = request.form.get('ui_custom_css', '').strip() or None
        parametres.show_ai_menu = 'show_ai_menu' in request.form
        parametres.show_ai_insights = 'show_ai_insights' in request.form
        parametres.show_quick_actions = 'show_quick_actions' in request.form
        parametres.show_recent_missions = 'show_recent_missions' in request.form
        parametres.show_stats_cards = 'show_stats_cards' in request.form
        custom_fields_raw = request.form.get('custom_fields_prestation', '').strip()
        if custom_fields_raw:
            try:
                parsed = _load_custom_fields_definitions(custom_fields_raw)
                if not parsed:
                    erreurs.append("Définition des champs personnalisés invalide")
                else:
                    parametres.custom_fields_prestation = json.dumps(parsed, ensure_ascii=False)
            except Exception:
                erreurs.append("Définition des champs personnalisés invalide")
        else:
            parametres.custom_fields_prestation = None

        parametres.date_modification = utcnow()

        if erreurs:
            for err in erreurs:
                flash(err, 'error')
            return redirect(url_for('personnalisation'))

        db.session.commit()
        lazy_importer.set_parametres(parametres)
        flash('Personnalisation mise à jour avec succès !', 'success')
    except Exception as e:
        flash(f'Erreur lors de la mise à jour : {str(e)}', 'error')

    return redirect(url_for('personnalisation'))

# ==================== ROUTES DE BACKUP ====================
@app.route('/backup')
@login_required
@role_required(['admin'])
def backup_page():
    """Page de gestion des backups"""
    from backup_manager import backup_manager
    backups = backup_manager.list_backups()
    return render_template('backup.html', backups=backups, current_user=get_current_user())

@app.route('/backup/create', methods=['POST'])
@login_required
@role_required(['admin'])
def create_backup():
    """Créer un backup manuel de la base de données"""
    from backup_manager import backup_manager
    
    compress = request.form.get('compress', 'true') == 'true'
    result = backup_manager.create_backup(compress=compress)
    
    if result['success']:
        flash(f'✅ Backup créé avec succès! ({result["size_mb"]:.2f} MB)', 'success')
    else:
        flash(f'❌ Erreur lors du backup: {result.get("error")}', 'error')
    
    return redirect(url_for('backup_page'))

@app.route('/backup/download/<filename>')
@login_required
@role_required(['admin'])
def download_backup(filename):
    """Télécharger un backup"""
    from backup_manager import backup_manager
    from flask import send_from_directory
    
    try:
        return send_from_directory(
            backup_manager.backup_dir,
            filename,
            as_attachment=True
        )
    except Exception as e:
        flash(f'Erreur lors du téléchargement: {str(e)}', 'error')
        return redirect(url_for('backup_page'))

@app.route('/backup/delete/<filename>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_backup(filename):
    """Supprimer un backup"""
    from backup_manager import backup_manager
    
    result = backup_manager.delete_backup(filename)
    
    if result['success']:
        flash(f'🗑️ Backup supprimé: {filename}', 'success')
    else:
        flash(f'❌ Erreur: {result.get("error")}', 'error')
    
    return redirect(url_for('backup_page'))

@app.route('/backup/restore/<filename>', methods=['POST'])
@login_required
@role_required(['admin'])
def restore_backup(filename):
    """Restaurer un backup (ATTENTION: écrase la base actuelle)"""
    from backup_manager import backup_manager
    
    # Vérifier confirmation
    confirm = request.form.get('confirm')
    if confirm != 'RESTORE':
        flash('❌ Confirmation incorrecte. Veuillez taper "RESTORE" pour confirmer.', 'error')
        return redirect(url_for('backup_page'))
    
    result = backup_manager.restore_backup(filename)
    
    if result['success']:
        flash(f'✅ Backup restauré: {filename} (Sauvegarde de sécurité: {result["security_backup"]})', 'success')
        # Redirection vers login car la session peut être invalidée
        return redirect(url_for('login'))
    else:
        flash(f'❌ Erreur: {result.get("error")}', 'error')
        return redirect(url_for('backup_page'))

# Routes d'export des données
@app.route('/export/parametres')
@login_required
@role_required(['admin'])
def export_parametres():
    """Exporter les paramètres d'entreprise"""
    try:
        from client_export import ClientExport
        exporter = ClientExport()
        
        # Export des paramètres uniquement
        parametres = ParametresEntreprise.query.first()
        if not parametres:
            flash('Aucun paramètre d\'entreprise trouvé', 'warning')
            return redirect(url_for('parametres'))
        
        data = {
            'nom_entreprise': parametres.nom_entreprise,
            'adresse': parametres.adresse,
            'code_postal': parametres.code_postal,
            'ville': parametres.ville,
            'adresse_lat': parametres.adresse_lat,
            'adresse_lng': parametres.adresse_lng,
            'telephone': parametres.telephone,
            'email': parametres.email,
            'email_signature': parametres.email_signature,
            'site_web': parametres.site_web,
            'siret': parametres.siret,
            'tva_intracommunautaire': parametres.tva_intracommunautaire,
            'forme_juridique': parametres.forme_juridique,
            'capital_social': parametres.capital_social,
            'rcs_ville': parametres.rcs_ville,
            'numero_rcs': parametres.numero_rcs,
            'penalites_retard': parametres.penalites_retard,
            'escompte': parametres.escompte,
            'indemnite_recouvrement': parametres.indemnite_recouvrement,
            'tva_non_applicable': parametres.tva_non_applicable,
            'couleur_principale': parametres.couleur_principale,
            'couleur_secondaire': parametres.couleur_secondaire,
            'devise': parametres.devise,
            'langue': parametres.langue,
            'distance_gratuite_km': parametres.distance_gratuite_km,
            'frais_deplacement_km': parametres.frais_deplacement_km,
            'signature_entreprise_path': parametres.signature_entreprise_path,
            'signature_entreprise_enabled': parametres.signature_entreprise_enabled
        }
        
        # Créer le fichier JSON
        import json
        from flask import make_response
        
        response = make_response(json.dumps(data, indent=2, ensure_ascii=False))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename="parametres_entreprise_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
        
    except Exception as e:
        flash(f'Erreur lors de l\'export : {str(e)}', 'error')
        return redirect(url_for('parametres'))

@app.route('/export/complet')
@login_required
@role_required(['admin'])
def export_complet():
    """Export complet de toutes les données"""
    try:
        from client_export import ClientExport
        exporter = ClientExport()
        
        # Export en JSON par défaut
        export_file = exporter.export_all_data('json')
        
        # Lire le fichier et le renvoyer
        with open(export_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        response = make_response(content)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename="export_complet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
        
    except Exception as e:
        flash(f'Erreur lors de l\'export complet : {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/export/statistiques')
@login_required
@role_required(['admin'])
def export_statistiques():
    """Export des statistiques"""
    try:
        from client_export import ClientExport
        exporter = ClientExport()
        
        stats_file = exporter.export_statistics()
        
        # Lire le fichier et le renvoyer
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        response = make_response(content)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename="statistiques_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
        
    except Exception as e:
        flash(f'Erreur lors de l\'export des statistiques : {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/devis/<int:devis_id>/pdf', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def devis_pdf(devis_id):
    """Générer le PDF d'un devis"""
    devis = get_or_404(Devis, devis_id)
    
    # Récupérer les paramètres d'entreprise
    parametres_entreprise = ParametresEntreprise.query.first()
    if not devis.contenu_html:
        devis.contenu_html = build_devis_template(devis, parametres_entreprise)
        db.session.commit()
    
    # TVA : valeur par défaut depuis le devis
    include_tva = True if devis.tva_incluse is None else bool(devis.tva_incluse)
    taux_tva = float(devis.taux_tva or 0.0)
    if parametres_entreprise and parametres_entreprise.tva_non_applicable:
        include_tva = False
        taux_tva = 0.0
    elif request.method == 'POST':
        if devis.est_signe:
            flash('Ce devis est signé et ne peut plus être modifié.', 'error')
        else:
            include_tva = str(request.form.get('include_tva', '1')).lower() in ('1', 'true', 'on', 'yes')
            devis.tva_incluse = include_tva
            db.session.commit()

    include_company_signature = None
    if parametres_entreprise and getattr(parametres_entreprise, 'signature_entreprise_path', None):
        include_company_signature = str(request.form.get('include_company_signature', '')).lower() in ('1', 'true', 'on', 'yes')
    
    try:
        from pdf_generator import generate_devis_pdf
        
        # Générer le PDF avec les paramètres d'entreprise et TVA
        pdf_bytes = generate_devis_pdf(
            devis,
            parametres_entreprise,
            include_tva,
            taux_tva,
            include_company_signature=include_company_signature
        )
        
        # Créer la réponse
        from flask import make_response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="devis_{devis.numero}.pdf"'
        
        return response
        
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF : {str(e)}', 'error')
        return redirect(url_for('facturation'))

@app.route('/devis/<int:devis_id>/choix-tva')
@login_required
@role_required(['admin', 'manager'])
def devis_choix_tva(devis_id):
    """Page de choix de TVA pour un devis"""
    devis = get_or_404(Devis, devis_id)
    parametres = ParametresEntreprise.query.first()
    return render_template('devis_choix_tva.html', devis=devis, parametres=parametres)

# Routes d'export Excel
@app.route('/export/prestations')
@login_required
def export_prestations():
    """Export des prestations en Excel"""
    prestations = Prestation.query.all()
    excel_exporter_module = get_excel_exporter()
    if not excel_exporter_module:
        flash('Module Excel non disponible', 'error')
        return redirect(url_for('prestations'))
    excel_data, filename = excel_exporter_module.export_prestations(prestations)
    
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/export/prestations-csv')
@login_required
def export_prestations_csv():
    """Export des prestations en CSV"""
    prestations = Prestation.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'id', 'client', 'lieu', 'date_debut', 'date_fin', 'heure_debut', 'heure_fin',
        'dj_id', 'statut', 'distance_km', 'indemnite_km'
    ])
    for p in prestations:
        writer.writerow([
            p.id,
            p.client,
            p.lieu,
            p.date_debut.strftime('%Y-%m-%d') if p.date_debut else '',
            p.date_fin.strftime('%Y-%m-%d') if p.date_fin else '',
            p.heure_debut.strftime('%H:%M') if p.heure_debut else '',
            p.heure_fin.strftime('%H:%M') if p.heure_fin else '',
            p.dj_id,
            p.statut,
            p.distance_km if p.distance_km is not None else '',
            p.indemnite_km if p.indemnite_km is not None else ''
        ])
    csv_data = output.getvalue()
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="prestations_{datetime.now().strftime("%Y%m%d")}.csv"'
    return response

@app.route('/export/materiels')
@login_required
def export_materiels():
    """Export du matériel en Excel"""
    materiels = Materiel.query.all()
    excel_exporter_module = get_excel_exporter()
    if not excel_exporter_module:
        flash('Module Excel non disponible', 'error')
        return redirect(url_for('materiels'))
    excel_data, filename = excel_exporter_module.export_materiels(materiels)
    
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/export/djs')
@login_required
def export_djs():
    """Export des DJs en Excel"""
    djs = DJ.query.all()
    excel_exporter_module = get_excel_exporter()
    if not excel_exporter_module:
        flash('Module Excel non disponible', 'error')
        return redirect(url_for('djs'))
    excel_data, filename = excel_exporter_module.export_djs(djs)
    
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/export/devis')
@login_required
@role_required(['admin', 'manager'])
def export_devis():
    """Export des devis en Excel"""
    devis = Devis.query.all()
    excel_exporter_module = get_excel_exporter()
    if not excel_exporter_module:
        flash('Module Excel non disponible', 'error')
        return redirect(url_for('facturation'))
    excel_data, filename = excel_exporter_module.export_devis(devis)
    
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# ==================== ROUTES RÉSERVATION CLIENT ====================

@app.route('/reservation')
def reservation_client():
    """Page de réservation pour les clients"""
    return render_template('reservation_client.html')

@app.route('/zone-clients')
def zone_clients():
    """Page vitrine publique Karano Event"""
    return render_template('zone_clients.html')

@app.route('/reservation/success')
def reservation_success():
    """Page de succès après réservation"""
    return render_template('reservation_success.html')

# ==================== FONCTIONS EMAIL RÉSERVATION ====================

def send_reservation_confirmation_email(reservation):
    """Envoie un email de confirmation de réservation au client"""
    try:
        from email_service import EmailService
        email_service = EmailService()
        
        parametres = ParametresEntreprise.query.first()
        nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
        
        subject = f"Confirmation de réservation {reservation.numero}"
        body = f"""Bonjour {reservation.nom},

Votre réservation a bien été reçue !

Détails de votre réservation :
- Numéro : {reservation.numero}
- Type : {reservation.type_prestation.title()}
- Date : {reservation.date_souhaitee.strftime('%d/%m/%Y')}
- Heure : {reservation.heure_souhaitee.strftime('%H:%M')}
- Durée : {reservation.duree_heures} heures
- Lieu : {reservation.adresse}

Votre réservation sera traitée dans les plus brefs délais.
Vous recevrez un devis détaillé une fois validée par notre équipe.

Merci pour votre confiance !
L'équipe {nom_entreprise}
"""
        
        email_service.send_email(
            to_email=reservation.email,
            subject=subject,
            body=body
        )
        
        logger.info(f"Email de confirmation envoyé à {reservation.email}")
        
    except Exception as e:
        logger.error(f"Erreur envoi email confirmation réservation : {e}")

def notify_managers_new_reservation(reservation):
    """Notifie les managers d'une nouvelle réservation"""
    try:
        from email_service import EmailService
        email_service = EmailService()
        
        # Récupérer tous les managers et admins
        managers = User.query.filter(User.role.in_(['admin', 'manager'])).all()
        
        subject = f"Nouvelle réservation {reservation.numero}"
        body = f"""Nouvelle réservation reçue :

CLIENT :
- Nom : {reservation.nom}
- Email : {reservation.email}
- Téléphone : {reservation.telephone}

PRESTATION :
- Type : {reservation.type_prestation.title()}
- Date : {reservation.date_souhaitee.strftime('%d/%m/%Y')}
- Heure : {reservation.heure_souhaitee.strftime('%H:%M')}
- Durée : {reservation.duree_heures} heures
- Lieu : {reservation.adresse}
- Invités : {reservation.nb_invites or 'Non spécifié'}

DEMANDES SPÉCIALES :
{reservation.demandes_speciales or 'Aucune'}

Connectez-vous pour valider cette réservation.
"""
        
        for manager in managers:
            if manager.email:
                email_service.send_email(
                    to_email=manager.email,
                    subject=subject,
                    body=body
                )
        
        logger.info(f"Notification envoyée à {len(managers)} manager(s)")
        
    except Exception as e:
        logger.error(f"Erreur notification managers : {e}")

def notify_dj_new_reservation(reservation):
    """Notifie le prestataire d'une nouvelle réservation assignée"""
    try:
        from email_service import EmailService
        email_service = EmailService()
        
        if not reservation.dj:
            logger.info("Pas de DJ assigné pour cette réservation")
            return
        
        # Vérifier si le DJ a un utilisateur associé avec un email
        dj_email = None
        if reservation.dj.user_id:
            dj_user = db.session.get(User, reservation.dj.user_id)
            if dj_user and dj_user.email:
                dj_email = dj_user.email
        
        if not dj_email:
            logger.info(f"DJ {reservation.dj.nom} n'a pas d'utilisateur associé avec email")
            return
        
        parametres = ParametresEntreprise.query.first()
        nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
        
        subject = f"Nouvelle réservation assignée {reservation.numero}"
        body = f"""Bonjour {reservation.dj.nom},

Une nouvelle réservation vous a été assignée !

CLIENT :
- Nom : {reservation.nom}
- Email : {reservation.email}
- Téléphone : {reservation.telephone}

MISSION :
- Type : {reservation.type_prestation.title()}
- Date : {reservation.date_souhaitee.strftime('%d/%m/%Y')}
- Heure : {reservation.heure_souhaitee.strftime('%H:%M')}
- Durée : {reservation.duree_heures} heures
- Prix : {reservation.prix_prestation}€
- Lieu : {reservation.adresse}
- Participants : {reservation.nb_invites or 'Non spécifié'}

DEMANDES SPÉCIALES :
{reservation.demandes_speciales or 'Aucune'}

Connectez-vous pour plus de détails.

L'équipe {nom_entreprise}
"""
        
        email_service.send_email(
            to_email=dj_email,
            subject=subject,
            body=body
        )
        
        logger.info(f"Notification envoyée au DJ {reservation.dj.nom}")
        
    except Exception as e:
        logger.error(f"Erreur notification DJ : {e}")

def send_dj_notification_for_devis(devis, dj, prestation, parametres):
    """Envoie un email au prestataire pour le notifier de sa mission à venir"""
    try:
        from email_service import EmailService
        email_service = EmailService()
        
        # Vérifier si le DJ a un utilisateur associé avec un email
        dj_email = None
        if dj.user_id:
            dj_user = db.session.get(User, dj.user_id)
            if dj_user and dj_user.email:
                dj_email = dj_user.email
        
        # Si pas d'email, on ne peut pas envoyer
        if not dj_email:
            logger.info(f"DJ {dj.nom} n'a pas d'utilisateur associé avec email, notification ignorée")
            return
        
        # Préparer les informations
        nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
        date_prestation_str = devis.date_prestation.strftime('%d/%m/%Y') if devis.date_prestation else 'Non spécifiée'
        
        # Email au DJ
        subject = f"Nouvelle mission confirmée - {devis.numero}"
        body = f"""Bonjour {dj.nom},

Une nouvelle mission vous a été assignée !

DÉTAILS DE LA MISSION :
• Devis n° : {devis.numero}
• Date : {date_prestation_str}
• Heure : {devis.heure_debut} - {devis.heure_fin}
• Lieu : {devis.lieu}
• Type : {devis.prestation_titre}
• Montant : {devis.montant_ttc:.2f}€

COORDONNÉES DU CLIENT :
• Nom : {devis.client_nom}
• Téléphone : {devis.client_telephone if devis.client_telephone else 'Non renseigné'}
• Email : {devis.client_email if devis.client_email else 'Non renseigné'}

Le devis a été envoyé au client. N'hésitez pas à le contacter pour finaliser les détails de la mission.

Cordialement,
{nom_entreprise}
"""
        
        email_service.send_email(
            to_email=dj_email,
            subject=subject,
            body=body
        )
        
        logger.info(f"Email de notification envoyé au DJ {dj.nom} pour le devis {devis.numero}")
        
    except Exception as e:
        logger.error(f"Erreur notification DJ pour devis : {e}")

def build_signature_url(signature_token):
    """Construit un lien de signature base sur l'hote courant."""
    if has_request_context():
        return url_for('page_signature_devis', token=signature_token, _external=True)
    return f"/signer-devis/{signature_token}"

def ensure_facture_payment_token(facture):
    """Assure un token de paiement unique pour la facture."""
    if not facture:
        return None
    if not getattr(facture, 'payment_token', None):
        facture.payment_token = secrets.token_urlsafe(32)
        db.session.commit()
    return facture.payment_token

def send_devis_to_client(devis, include_tva=None):
    """Envoie un devis par email au client avec copie au manager et au DJ"""
    try:
        from email_service import EmailService
        email_service = EmailService()
        import secrets
        
        # Générer un token de signature unique si pas déjà existant
        if not devis.signature_token:
            devis.signature_token = secrets.token_urlsafe(32)
            db.session.commit()
        
        # Générer le PDF du devis
        from pdf_generator import generate_devis_pdf
        parametres = ParametresEntreprise.query.first()
        nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
        if include_tva is None:
            include_tva = True if devis.tva_incluse is None else bool(devis.tva_incluse)
        if parametres and parametres.tva_non_applicable:
            include_tva = False
        taux_tva = float(devis.taux_tva or 0.0)
        if not devis.contenu_html:
            devis.contenu_html = build_devis_template(devis, parametres)
            db.session.commit()
        devis.tva_incluse = include_tva
        pdf_data = generate_devis_pdf(devis, parametres, include_tva, taux_tva)
        
        # Récupérer la prestation associée pour obtenir le DJ
        prestation = None
        dj = None
        if devis.prestation_id:
            prestation = db.session.get(Prestation, devis.prestation_id)
            if prestation and prestation.dj_id:
                dj = db.session.get(DJ, prestation.dj_id)
        
        # Préparer la liste des destinataires en copie cachée (BCC)
        bcc_list = []
        
        # Ajouter le manager/admin qui a validé (utilisateur connecté)
        current_user_obj = get_current_user()
        if current_user_obj and current_user_obj.email:
            bcc_list.append(current_user_obj.email)
        
        # Ajouter le DJ en copie cachée (via son utilisateur associé)
        if dj and dj.user_id:
            dj_user = db.session.get(User, dj.user_id)
            if dj_user and dj_user.email:
                bcc_list.append(dj_user.email)
        
        # Générer le lien de signature
        signature_url = build_signature_url(devis.signature_token)
        
        # Envoyer l'email avec le PDF en pièce jointe
        subject = f"Devis {devis.numero} - {devis.prestation_titre}"
        body = f"""Bonjour {devis.client_nom},

Veuillez trouver ci-joint votre devis pour la mission du {devis.date_prestation.strftime('%d/%m/%Y')}.

DETAILS :
• Mission : {devis.prestation_titre}
• Date : {devis.date_prestation.strftime('%d/%m/%Y')}
• Horaires : {devis.heure_debut.strftime('%H:%M')} - {devis.heure_fin.strftime('%H:%M')}
• Lieu : {devis.lieu}

SIGNATURE ELECTRONIQUE :
Pour valider ce devis, cliquez sur le lien ci-dessous et signez electroniquement :

{signature_url}

Cette signature electronique a la meme valeur legale qu'une signature manuscrite.

Cordialement,
L'equipe {nom_entreprise}
"""
        
        # Envoyer avec BCC
        email_service.send_email_with_attachment(
            to_email=devis.client_email,
            subject=subject,
            body=body,
            attachment_data=pdf_data,
            attachment_filename=f"devis_{devis.numero}.pdf",
            bcc=bcc_list
        )
        
        # Envoyer un email séparé au DJ avec les informations du client
        if dj:
            send_dj_notification_for_devis(devis, dj, prestation, parametres)
        
        # Mettre à jour le statut
        devis.date_envoi = utcnow()
        db.session.commit()
        
        logger.info(f"Devis {devis.numero} envoyé à {devis.client_email}")
        
    except Exception as e:
        logger.error(f"Erreur envoi email devis : {e}")
        raise

def _envoyer_devis_email(devis, include_tva=True):
    """Envoie un devis par email au client et met a jour le statut."""
    if not devis.client_email:
        raise ValueError("Aucune adresse email renseignee pour ce client.")

    from pdf_generator import generate_devis_pdf
    from email_service import EmailService
    import secrets

    parametres = ParametresEntreprise.query.first()
    if parametres and parametres.tva_non_applicable:
        include_tva = False
    if devis.est_signe:
        include_tva = False if (parametres and parametres.tva_non_applicable) else (True if devis.tva_incluse is None else bool(devis.tva_incluse))

    original_contenu = devis.contenu_html
    if not devis.contenu_html:
        devis.contenu_html = build_devis_template(devis, parametres)
        if not devis.est_signe:
            db.session.commit()

    # Generer un token de signature si necessaire (uniquement si non signe)
    if (not devis.est_signe) and (not devis.signature_token):
        devis.signature_token = secrets.token_urlsafe(32)
        db.session.commit()

    if not devis.est_signe:
        devis.tva_incluse = include_tva
        db.session.commit()
    taux_tva = float(devis.taux_tva or 0.0)
    pdf_data = generate_devis_pdf(devis, parametres, include_tva, taux_tva)

    # Recuperer la prestation associee pour obtenir le DJ
    prestation = None
    dj = None
    if devis.prestation_id:
        prestation = db.session.get(Prestation, devis.prestation_id)
        if prestation and prestation.dj_id:
            dj = db.session.get(DJ, prestation.dj_id)

    # Liste des destinataires en copie cachee (BCC)
    bcc_list = []
    current_user_obj = get_current_user()
    if current_user_obj and current_user_obj.email:
        bcc_list.append(current_user_obj.email)
    if dj and dj.user_id:
        dj_user = db.session.get(User, dj.user_id)
        if dj_user and dj_user.email:
            bcc_list.append(dj_user.email)

    date_prestation_str = devis.date_prestation.strftime('%d/%m/%Y') if devis.date_prestation else 'Non specifiee'
    date_validite_str = devis.date_validite.strftime('%d/%m/%Y') if devis.date_validite else None
    signature_url = build_signature_url(devis.signature_token) if devis.signature_token and not devis.est_signe else None
    signature_block = "Ce devis est déjà signé et ne peut plus être modifié." if devis.est_signe else f"Lien de signature : {signature_url}"

    body = f"""Bonjour {devis.client_nom},

Veuillez trouver en piece jointe votre devis {devis.numero}.

Details de la prestation :
- Date : {date_prestation_str}
- Heure : {devis.heure_debut} - {devis.heure_fin}
- Lieu : {devis.lieu}

{('Validite du devis : ' + date_validite_str) if date_validite_str else ''}

Ce devis est valable 30 jours a compter de sa date d'emission.

    {signature_block}

Merci pour votre confiance."""

    subject = f"Devis {devis.numero} - {parametres.nom_entreprise if parametres else 'Planify'}"
    email_service = EmailService()
    email_service.send_email_with_attachment(
        to_email=devis.client_email,
        subject=subject,
        body=body,
        attachment_data=pdf_data,
        attachment_filename=f'devis_{devis.numero}.pdf',
        bcc=bcc_list
    )

    if dj:
        send_dj_notification_for_devis(devis, dj, prestation, parametres)

    if not devis.est_signe:
        devis.statut = 'envoye'
        devis.date_envoi = utcnow()
        db.session.commit()
    elif original_contenu is None:
        devis.contenu_html = original_contenu

# ==================== ROUTES SIGNATURE ÉLECTRONIQUE ====================

@app.route('/signer-devis/<token>')
def page_signature_devis(token):
    """Page de signature électronique pour le client (PUBLIC)"""
    devis = Devis.query.filter_by(signature_token=token).first()
    
    if not devis:
        return "Devis introuvable ou lien invalide", 404
    
    if devis.est_signe:
        return render_template('devis_deja_signe.html', devis=devis)
    
    parametres = ParametresEntreprise.query.first()
    return render_template('signer_devis.html', devis=devis, parametres=parametres)

@app.route('/api/signer-devis/<token>', methods=['POST'])
def api_signer_devis(token):
    """API pour enregistrer la signature d'un devis (PUBLIC)"""
    try:
        ok, error = validate_public_api_request()
        if not ok:
            return jsonify({'success': False, 'message': error}), 401
        devis = Devis.query.filter_by(signature_token=token).first()
        
        if not devis:
            return jsonify({
                'success': False,
                'message': 'Devis introuvable'
            }), 404
        
        if devis.est_signe:
            return jsonify({
                'success': False,
                'message': 'Ce devis a déjà été signé'
            }), 400
        
        data = request.get_json(silent=True) or {}
        signature_data = data.get('signature')
        valide, message, normalized = validate_signature_payload(signature_data)
        if not valide:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Enregistrer la signature
        devis.signature_image = normalized
        devis.signature_date = utcnow()
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        devis.signature_ip = client_ip
        devis.est_signe = True
        devis.statut = 'accepte'
        devis.date_acceptation = utcnow()
        
        db.session.commit()
        
        # Envoyer des notifications
        notifier_signature_devis(devis)
        
        logger.info(f"Devis {devis.numero} signé par {devis.client_nom}")
        
        return jsonify({
            'success': True,
            'message': 'Signature enregistrée avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur signature devis : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Erreur lors de l\'enregistrement de la signature'
        }), 500

def notifier_signature_devis(devis):
    """Envoie des notifications après signature du devis"""
    try:
        from email_service import EmailService
        email_service = EmailService()
        
        parametres = ParametresEntreprise.query.first()
        nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
        
        # Email au client
        client_subject = f"Confirmation de signature - Devis {devis.numero}"
        client_body = f"""Bonjour {devis.client_nom},

Nous vous confirmons la réception de votre signature électronique pour le devis {devis.numero}.

DÉTAILS :
• Date de signature : {devis.signature_date.strftime('%d/%m/%Y à %H:%M')}
• Mission : {devis.prestation_titre}
• Date : {devis.date_prestation.strftime('%d/%m/%Y')}
• Montant : {devis.montant_ttc:.2f}€

Vous recevrez prochainement une copie du devis signé.

Merci pour votre confiance !
L'équipe {nom_entreprise}
"""
        
        email_service.send_email(
            to_email=devis.client_email,
            subject=client_subject,
            body=client_body
        )
        
        # Email aux managers
        managers = User.query.filter(User.role.in_(['admin', 'manager'])).all()
        manager_subject = f"Devis signé - {devis.numero}"
        manager_body = f"""Le devis {devis.numero} a été signé électroniquement !

CLIENT :
• Nom : {devis.client_nom}
• Email : {devis.client_email}
• Téléphone : {devis.client_telephone}

MISSION :
• Titre : {devis.prestation_titre}
• Date : {devis.date_prestation.strftime('%d/%m/%Y')}
• Montant : {devis.montant_ttc:.2f}€

SIGNATURE :
• Date : {devis.signature_date.strftime('%d/%m/%Y à %H:%M')}
• IP : {devis.signature_ip}

Connectez-vous pour voir le devis signé.
"""
        
        for manager in managers:
            if manager.email:
                email_service.send_email(
                    to_email=manager.email,
                    subject=manager_subject,
                    body=manager_body
                )
        
        logger.info(f"Notifications de signature envoyées pour le devis {devis.numero}")
        
    except Exception as e:
        logger.error(f"Erreur notification signature : {e}")

# ==================== ROUTES NOTATION PRESTATION (PUBLIC) ====================

@app.route('/noter/<token>', methods=['GET', 'POST'])
def rate_prestation(token):
    rating = PrestationRating.query.filter_by(token=token).first()
    csrf_token = session.get('csrf_token')
    if not rating:
        return render_template('rating_prestation.html', invalid=True, csrf_token=csrf_token), 404

    now = utcnow()
    if rating.token_expires_at and rating.token_expires_at < now:
        return render_template('rating_prestation.html', expired=True, csrf_token=csrf_token), 410

    prestation = db.session.get(Prestation, rating.prestation_id)
    dj = db.session.get(DJ, rating.dj_id) if rating.dj_id else None
    technicien = db.session.get(User, rating.technicien_id) if rating.technicien_id else None

    if rating.submitted_at:
        return render_template(
            'rating_prestation.html',
            submitted=True,
            prestation=prestation,
            dj=dj,
            technicien=technicien,
            csrf_token=csrf_token
        )

    if request.method == 'POST':
        try:
            rating_dj = int(request.form.get('rating_dj', 0))
        except (TypeError, ValueError):
            rating_dj = 0
        rating_technicien = None
        if technicien:
            try:
                rating_technicien = int(request.form.get('rating_technicien', 0))
                if rating_technicien not in [1, 2, 3, 4, 5]:
                    rating_technicien = None
            except (TypeError, ValueError):
                rating_technicien = None

        if rating_dj not in [1, 2, 3, 4, 5]:
            return render_template(
                'rating_prestation.html',
                prestation=prestation,
                dj=dj,
                technicien=technicien,
                error="Veuillez sélectionner une note pour le prestataire.",
                csrf_token=csrf_token
            ), 400

        rating.rating_dj = rating_dj
        rating.rating_technicien = rating_technicien
        rating.commentaire = (request.form.get('commentaire') or '').strip()
        rating.submitted_at = now
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        rating.ip_address = client_ip
        rating.user_agent = request.headers.get('User-Agent', '')[:255]

        db.session.commit()
        AuditLog.log_action(
            action='creation',
            entite_type='notation',
            entite_id=prestation.id if prestation else None,
            entite_nom=prestation.client if prestation else 'prestation',
            details={'rating_dj': rating_dj, 'rating_technicien': rating_technicien}
        )
        return render_template(
            'rating_prestation.html',
            submitted=True,
            prestation=prestation,
            dj=dj,
            technicien=technicien,
            csrf_token=csrf_token
        )

    return render_template(
        'rating_prestation.html',
        prestation=prestation,
        dj=dj,
        technicien=technicien,
        csrf_token=csrf_token
    )

# ==================== ROUTES API CHATBOT IA ====================
# Note: Ces routes sont publiques pour permettre aux clients d'utiliser le chatbot

@app.route('/api/chat/welcome', methods=['GET'])
def chat_welcome():
    """API pour obtenir le message de bienvenue avec le nom de l'entreprise (PUBLIC)"""
    try:
        ok, error = validate_public_api_request()
        if not ok:
            return jsonify({'success': False, 'message': error}), 401
        from ai_assistant import ai_assistant
        
        nom_entreprise = ai_assistant.nom_entreprise
        message = f"Bonjour ! Je suis votre assistant {nom_entreprise}. Je vais vous aider à définir la mission idéale. Pour commencer, quel type de mission ou service souhaitez-vous ?"
        
        return jsonify({
            'success': True,
            'message': message,
            'nom_entreprise': nom_entreprise
        })
        
    except Exception as e:
        logger.error(f"Erreur message de bienvenue : {e}")
        return jsonify({
            'success': True,
            'message': "Bonjour ! Je suis votre assistant. Quel type de mission ou service souhaitez-vous ?",
            'nom_entreprise': 'Planify'
        })

@app.route('/api/chat/message', methods=['POST'])
def chat_message():
    """API pour envoyer un message au chatbot IA (PUBLIC)"""
    try:
        ok, error = validate_public_api_request()
        if not ok:
            return jsonify({'success': False, 'message': error}), 401
        from ai_assistant import ai_assistant
        
        data = request.get_json(silent=True) or {}
        user_message = (data.get('message') or '').strip()
        conversation_id = (data.get('conversation_id') or 'default').strip()
        if len(conversation_id) > 64:
            return jsonify({'success': False, 'message': 'conversation_id invalide'}), 400
        
        if not user_message:
            return jsonify({
                'success': False,
                'message': 'Message vide'
            }), 400
        if len(user_message) > 2000:
            return jsonify({'success': False, 'message': 'Message trop long'}), 400
        
        # Obtenir la réponse de l'IA
        ai_response = ai_assistant.get_response(user_message, conversation_id)
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
        
    except Exception as e:
        logger.error(f"Erreur chatbot IA : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erreur lors du traitement de votre message: {str(e)}'
        }), 500

@app.route('/api/chat/recommendations/<conversation_id>', methods=['GET'])
def chat_recommendations(conversation_id):
    """API pour obtenir les recommandations basées sur la conversation (PUBLIC)"""
    try:
        ok, error = validate_public_api_request()
        if not ok:
            return jsonify({'success': False, 'message': error}), 401
        from ai_assistant import ai_assistant
        conversation_id = (conversation_id or '').strip()
        if not conversation_id or len(conversation_id) > 64:
            return jsonify({'success': False, 'message': 'conversation_id invalide'}), 400
        recommendations = ai_assistant.get_recommendations(conversation_id)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
        
    except Exception as e:
        logger.error(f"Erreur recommandations IA : {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la récupération des recommandations'
        }), 500

@app.route('/api/chat/reset/<conversation_id>', methods=['POST'])
def chat_reset(conversation_id):
    """API pour réinitialiser une conversation (PUBLIC)"""
    try:
        ok, error = validate_public_api_request()
        if not ok:
            return jsonify({'success': False, 'message': error}), 401
        from ai_assistant import ai_assistant
        conversation_id = (conversation_id or '').strip()
        if not conversation_id or len(conversation_id) > 64:
            return jsonify({'success': False, 'message': 'conversation_id invalide'}), 400
        ai_assistant.reset_conversation(conversation_id)
        
        return jsonify({
            'success': True,
            'message': 'Conversation réinitialisée'
        })
        
    except Exception as e:
        logger.error(f"Erreur reset conversation : {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la réinitialisation'
        }), 500

# ==================== FIN ROUTES CHATBOT ====================

@app.route('/api/reservation', methods=['POST'])
def api_reservation():
    """API pour créer une réservation client"""
    try:
        ok, error = validate_public_api_request()
        if not ok:
            return jsonify({'success': False, 'message': error}), 401
        # Récupérer les données du formulaire (FormData)
        data = request.form.to_dict()
        data.pop(PUBLIC_API_TOKEN_PARAM, None)
        
        # Récupérer aussi les checkboxes (services)
        services = request.form.getlist('services')
        
        # Validation des données
        erreurs_validation = []
        
        # Valider nom
        if not data.get('nom') or not data.get('nom').strip():
            erreurs_validation.append("Le nom est requis")
        
        # Valider email
        if data.get('email'):
            valide, message = valider_email(data.get('email'))
            if not valide:
                erreurs_validation.append(message)
        else:
            erreurs_validation.append("L'email est requis")
        
        # Valider téléphone
        if data.get('telephone'):
            valide, message = valider_telephone(data.get('telephone'))
            if not valide:
                erreurs_validation.append(message)
        else:
            erreurs_validation.append("Le téléphone est requis")
        
        # Valider lieu
        if not data.get('lieu') or not data.get('lieu').strip():
            erreurs_validation.append("Le lieu est requis")
        
        # Valider date
        if data.get('date'):
            valide, message = valider_date(data.get('date'))
            if not valide:
                erreurs_validation.append(message)
        else:
            erreurs_validation.append("La date est requise")
        
        # Valider heures et calculer la durée
        duree_heures = 0
        heure_debut = None
        heure_fin = None
        
        if data.get('heure_debut') and data.get('heure_fin'):
            try:
                heure_debut = datetime.strptime(data['heure_debut'], '%H:%M').time()
                heure_fin = datetime.strptime(data['heure_fin'], '%H:%M').time()
                
                # Calculer la durée
                debut_minutes = heure_debut.hour * 60 + heure_debut.minute
                fin_minutes = heure_fin.hour * 60 + heure_fin.minute
                
                # Si heure_fin < heure_debut, on passe au jour suivant (après minuit)
                if fin_minutes <= debut_minutes:
                    # Événement qui se termine le lendemain
                    fin_minutes += 24 * 60
                    logger.info(f"Événement sur 2 jours : {data['heure_debut']} → {data['heure_fin']} (lendemain)")
                
                duree_heures = (fin_minutes - debut_minutes) / 60
                
                if duree_heures < 1:
                    erreurs_validation.append("La durée doit être d'au moins 1 heure")
                elif duree_heures > 24:
                    erreurs_validation.append("La durée ne peut pas dépasser 24 heures")
                    
                logger.info(f"Durée calculée : {duree_heures}h (début: {data['heure_debut']}, fin: {data['heure_fin']})")
            except ValueError as e:
                logger.error(f"Erreur parsing heures : {e}")
                erreurs_validation.append("Format d'heure invalide")
        else:
            erreurs_validation.append("Les heures de début et de fin sont requises")
        
        # Si des erreurs, les retourner
        if erreurs_validation:
            return jsonify({
                'success': False,
                'message': 'Données invalides',
                'erreurs': erreurs_validation
            }), 400
        
        # Générer un numéro de réservation
        numero_reservation = f"RES-{datetime.now().strftime('%Y%m%d')}-{ReservationClient.query.count() + 1:03d}"
        
        # Préparer les demandes spéciales (combiner services + préférences + message)
        demandes_parts = []
        if services:
            demandes_parts.append(f"Services: {', '.join(services)}")
        if data.get('preferences'):
            demandes_parts.append(f"Préférences musicales: {data['preferences']}")
        if data.get('message'):
            demandes_parts.append(f"Message: {data['message']}")
        
        demandes_speciales = " | ".join(demandes_parts)
        
        # Créer la réservation avec données nettoyées
        reservation = ReservationClient(
            numero=numero_reservation,
            nom=sanitize_string(data['nom'], 100),
            email=sanitize_string(data['email'], 100),
            telephone=sanitize_string(data['telephone'], 20),
            adresse=sanitize_string(data.get('lieu', ''), 500),
            nb_invites=int(data.get('nb_invites', 0)) if data.get('nb_invites') else None,
            type_lieu=sanitize_string(data.get('type_evenement', ''), 50),
            demandes_speciales=sanitize_string(demandes_speciales, 1000),
            type_prestation=data.get('type_evenement', 'personnalisee'),
            prix_prestation=0,  # Prix défini lors de la validation par le manager
            duree_heures=round(duree_heures, 2),  # Garder 2 décimales pour la précision
            date_souhaitee=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            heure_souhaitee=heure_debut
        )
        
        logger.info(f"Réservation créée : {numero_reservation} - {data['nom']} - {duree_heures}h")
        
        db.session.add(reservation)
        db.session.commit()
        
        # Envoyer email de confirmation au client
        send_reservation_confirmation_email(reservation)
        
        # Notifier les managers
        notify_managers_new_reservation(reservation)
        
        return jsonify({
            'success': True,
            'message': 'Réservation créée avec succès',
            'numero': numero_reservation
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur création réservation : {e}")
        import traceback
        traceback.print_exc()
        
        # Message d'erreur plus détaillé pour le debug
        error_msg = str(e)
        if 'duree_heures' in error_msg:
            error_msg = "Erreur dans le calcul de la durée. Vérifiez les heures de début et de fin."
        elif 'sanitize' in error_msg:
            error_msg = "Erreur dans le traitement des données. Vérifiez que tous les champs sont correctement remplis."
        
        return jsonify({
            'success': False,
            'message': f'Erreur lors de la création de la réservation',
            'details': error_msg
        }), 500

@app.route('/reservations')
@login_required
@role_required(['admin', 'manager'])
def reservations():
    """Liste des réservations clients"""
    page = request.args.get('page', 1, type=int)
    statut_filter = request.args.get('statut', '')
    
    reservations_query = ReservationClient.query
    if statut_filter:
        reservations_query = reservations_query.filter_by(statut=statut_filter)
    
    reservations = reservations_query.order_by(ReservationClient.date_creation.desc()).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False
    )
    
    return render_template('reservations.html', 
                         reservations=reservations, 
                         current_user=get_current_user())

@app.route('/reservations/<int:reservation_id>')
@login_required
@role_required(['admin', 'manager'])
def detail_reservation(reservation_id):
    """
    Détail d'une réservation
    Note: Le matériel n'est plus listé automatiquement pour des raisons de performance.
    Il sera chargé à la demande via l'API /api/check-materiel-disponibilite
    """
    reservation = get_or_404(ReservationClient, reservation_id)
    djs = DJ.query.all()
    
    return render_template('detail_reservation.html', 
                         reservation=reservation, 
                         djs=djs,
                         current_user=get_current_user())

@app.route('/reservations/<int:reservation_id>/valider', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def valider_reservation(reservation_id):
    """
    PRÉ-VALIDATION Manager (Étape 1/2)
    Le manager définit le prix et assigne le matériel + DJ
    RIEN n'est créé ici, on attend l'acceptation du DJ
    """
    reservation = get_or_404(ReservationClient, reservation_id)
    
    try:
        # Récupérer les données du formulaire
        prix_prestation = float(request.form.get('prix_prestation', 0))
        materiels_ids = request.form.getlist('materiels')
        notes = request.form.get('notes', '')
        dj_id = request.form.get('dj_id')
        
        # Valider que le DJ est assigné
        if not dj_id:
            flash('Vous devez assigner un DJ avant de valider', 'error')
            return redirect(url_for('detail_reservation', reservation_id=reservation_id))
        
        # Pré-validation du manager
        reservation.validee_par_manager = True
        reservation.manager_id = session['user_id']
        reservation.manager_notes = notes
        reservation.date_validation = utcnow()
        reservation.prix_prestation = prix_prestation
        reservation.dj_id = int(dj_id)
        reservation.statut = 'en_attente_dj'  # Nouveau statut : attend validation DJ
        
        # Stocker les matériels à assigner (via la table de liaison temporaire)
        # On les stockera dans la prestation seulement quand le DJ accepte
        # Pour l'instant, on les lie à la réservation
        date_fin_res, heure_fin_res = compute_reservation_end(
            reservation.date_souhaitee,
            reservation.heure_souhaitee,
            reservation.duree_heures
        )
        
        # ✅ NOUVEAU: Vérifier disponibilité AVANT d'assigner
        erreurs_materiel = []
        for materiel_id in materiels_ids:
            if materiel_id:
                materiel = db.session.get(Materiel, int(materiel_id))
                if not materiel:
                    continue
                
                # Vérifier disponibilité
                dispo = verifier_disponibilite_materiel(
                    materiel_id=int(materiel_id),
                    quantite_demandee=1,  # Par défaut 1 unité
                    date_debut=reservation.date_souhaitee,
                    date_fin=date_fin_res,
                    heure_debut=reservation.heure_souhaitee,
                    heure_fin=heure_fin_res,
                    exclure_reservation_id=reservation.id
                )
                
                if not dispo['disponible']:
                    erreurs_materiel.append(f"{materiel.nom}: non disponible ({dispo['quantite_disponible']}/{dispo['quantite_totale']})")
        
        # Si des erreurs, BLOQUER la validation
        if erreurs_materiel:
            for erreur in erreurs_materiel:
                flash(f'❌ Matériel: {erreur}', 'error')
            db.session.rollback()
            return redirect(url_for('detail_reservation', reservation_id=reservation_id))
        
        # Tout est OK : assigner les matériels
        for materiel_id in materiels_ids:
            if materiel_id:
                # Vérifier si déjà assigné
                existant = MaterielPresta.query.filter_by(
                    reservation_id=reservation.id,
                    materiel_id=int(materiel_id)
                ).first()
                
                if not existant:
                    materiel_presta = MaterielPresta(
                        reservation_id=reservation.id,
                        materiel_id=int(materiel_id),
                        quantite=1
                    )
                    db.session.add(materiel_presta)
        
        db.session.commit()
        
        # Notifier le DJ qu'une réservation l'attend
        dj = db.session.get(DJ, dj_id)
        if dj and dj.user_id:
            dj_user = db.session.get(User, dj.user_id)
            if dj_user and dj_user.email:
                try:
                    from email_service import EmailService
                    email_service = EmailService()
                    
                    subject = f"Nouvelle réservation à valider - {reservation.nom}"
                    body = f"""Bonjour {dj.nom},

Une nouvelle réservation client nécessite votre validation :

CLIENT : {reservation.nom}
DATE : {reservation.date_souhaitee.strftime('%d/%m/%Y')} à {reservation.heure_souhaitee.strftime('%H:%M')}
DURÉE : {reservation.duree_heures}h
LIEU : {reservation.adresse}
TYPE : {reservation.type_prestation.title()}
MONTANT : {prix_prestation:.2f}€

Connectez-vous pour accepter ou refuser cette prestation.

Cordialement,
L'équipe Planify
"""
                    email_service.send_email(dj_user.email, subject, body)
                    logger.info(f"Email de notification envoyé au DJ {dj.nom}")
                except Exception as e:
                    logger.error(f"Erreur envoi email DJ : {e}")
        
        flash(f'Pré-validation effectuée ! En attente de la validation du DJ {dj.nom if dj else ""}', 'success')
        logger.info(f"Réservation {reservation.id} pré-validée par manager {session['user_id']}, en attente DJ {dj_id}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la validation : {str(e)}', 'error')
        logger.error(f"Erreur validation réservation : {e}")
    
    return redirect(url_for('detail_reservation', reservation_id=reservation_id))

# ANCIENNE LOGIQUE SUPPRIMÉE : Plus de création prématurée de prestation/devis
# La création se fait maintenant dans valider_reservation_dj() quand le DJ accepte

@app.route('/reservations/<int:reservation_id>/assigner-dj', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def assigner_dj_reservation(reservation_id):
    """Assigner un DJ à une réservation"""
    reservation = get_or_404(ReservationClient, reservation_id)
    
    try:
        dj_id = request.form.get('dj_id')
        if dj_id:
            reservation.dj_id = dj_id
            db.session.commit()
            
            # Notifier le DJ
            notify_dj_new_reservation(reservation)
            
            flash('DJ assigné avec succès !', 'success')
        else:
            flash('Veuillez sélectionner un DJ', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'assignation : {str(e)}', 'error')
    
    return redirect(url_for('detail_reservation', reservation_id=reservation_id))

@app.route('/reservations/<int:reservation_id>/assigner-materiel', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def assigner_materiel_reservation(reservation_id):
    """Assigner du matériel à une réservation avec vérification de disponibilité ET quantités"""
    reservation = get_or_404(ReservationClient, reservation_id)
    
    try:
        materiel_ids = request.form.getlist('materiel_ids')
        
        if not materiel_ids:
            flash('⚠️ Aucun matériel sélectionné', 'warning')
            return redirect(url_for('detail_reservation', reservation_id=reservation_id))
        
        # Vérifier la disponibilité AVANT toute modification
        erreurs = []
        materiels_a_assigner = []  # Liste des (materiel_id, quantite) valides
        date_fin_res, heure_fin_res = compute_reservation_end(
            reservation.date_souhaitee,
            reservation.heure_souhaitee,
            reservation.duree_heures
        )
        
        for materiel_id in materiel_ids:
            if not materiel_id:
                continue
            
            # Récupérer la quantité depuis le champ nommé "quantite_{materiel_id}"
            quantite_str = request.form.get(f'quantite_{materiel_id}', '1')
            try:
                quantite_demandee = int(quantite_str)
            except ValueError:
                quantite_demandee = 1
            
            # Validation: quantité minimum 1
            if quantite_demandee < 1:
                quantite_demandee = 1
            
            materiel = db.session.get(Materiel, int(materiel_id))
            
            if not materiel:
                erreurs.append(f"Matériel #{materiel_id} introuvable")
                continue
            
            # Vérifier disponibilité avec la quantité demandée
            dispo = verifier_disponibilite_materiel(
                materiel_id=int(materiel_id),
                quantite_demandee=quantite_demandee,
                date_debut=reservation.date_souhaitee,
                date_fin=date_fin_res,
                heure_debut=reservation.heure_souhaitee,
                heure_fin=heure_fin_res,
                exclure_reservation_id=reservation_id  # Exclure cette réservation si déjà assignée
            )
            
            if not dispo['disponible']:
                erreur_msg = f"❌ {materiel.nom}: {quantite_demandee} demandé(s), seulement {dispo['quantite_disponible']}/{dispo['quantite_totale']} disponible(s)"
                if dispo['conflits']:
                    conflits_str = ", ".join([f"{c['nom']} ({c['quantite']})" for c in dispo['conflits'][:3]])
                    erreur_msg += f" - Conflit: {conflits_str}"
                erreurs.append(erreur_msg)
            else:
                # OK, on peut l'assigner
                materiels_a_assigner.append((int(materiel_id), quantite_demandee))
        
        # Si des erreurs, BLOQUER l'assignation
        if erreurs:
            for erreur in erreurs:
                flash(erreur, 'error')
            return redirect(url_for('detail_reservation', reservation_id=reservation_id))
        
        # Tout est OK : supprimer les anciennes assignations
        MaterielPresta.query.filter_by(prestation_id=None, reservation_id=reservation_id).delete()
        
        # Ajouter les nouvelles assignations avec les quantités
        count = 0
        total_quantite = 0
        for materiel_id, quantite in materiels_a_assigner:
            materiel_presta = MaterielPresta(
                materiel_id=materiel_id,
                reservation_id=reservation_id,
                quantite=quantite
            )
            db.session.add(materiel_presta)
            count += 1
            total_quantite += quantite
        
        db.session.commit()
        flash(f'✅ {count} matériel(s) assigné(s) ({total_quantite} unité(s) au total) !', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'assignation du matériel : {str(e)}', 'error')
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('detail_reservation', reservation_id=reservation_id))

@app.route('/reservations/<int:reservation_id>/valider-dj', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'dj'])
def valider_reservation_dj(reservation_id):
    """
    VALIDATION DJ (Étape 2/2) - ACCEPTER
    Quand le DJ accepte : création prestation + devis + envoi email au client
    """
    reservation = get_or_404(ReservationClient, reservation_id)
    
    if not reservation.validee_par_manager:
        flash('La réservation doit d\'abord être pré-validée par un manager', 'error')
        return redirect(url_for('detail_reservation', reservation_id=reservation_id))
    
    try:
        action = request.form.get('action', 'accepter')
        notes_dj = request.form.get('notes', '')
        
        if action == 'refuser':
            # DJ REFUSE : Retour en attente, réassignation possible
            reservation.validee_par_dj = False
            reservation.dj_notes = notes_dj
            reservation.statut = 'en_attente'  # Retour en attente
            reservation.dj_id = None  # Libérer le DJ
            
            # Supprimer le matériel pré-assigné
            MaterielPresta.query.filter_by(reservation_id=reservation.id).delete()
            
            db.session.commit()
            
            flash(f'Vous avez refusé cette réservation. Elle a été remise en attente de réassignation.', 'info')
            logger.info(f"Réservation {reservation.id} refusée par DJ {session.get('user_id')}")
            
            return redirect(url_for('dj_dashboard'))
        
        # DJ ACCEPTE : Créer la prestation + devis + envoi
        reservation.validee_par_dj = True
        reservation.dj_notes = notes_dj
        reservation.statut = 'confirmee'
        date_fin_res, heure_fin_res = compute_reservation_end(
            reservation.date_souhaitee,
            reservation.heure_souhaitee,
            reservation.duree_heures
        )
        
        # Créer la PRESTATION
        client_ref = get_or_create_client(reservation.nom, reservation.email, reservation.telephone)
        prestation = Prestation(
            client=reservation.nom,
            client_email=reservation.email,
            client_telephone=reservation.telephone,
            lieu=reservation.adresse,
            date_debut=reservation.date_souhaitee,
            date_fin=date_fin_res,
            heure_debut=reservation.heure_souhaitee,
            heure_fin=heure_fin_res,
            client_id=client_ref.id if client_ref else None,
            dj_id=reservation.dj_id,
            createur_id=reservation.manager_id,  # Le manager qui a pré-validé
            notes=f"Réservation client - {reservation.demandes_speciales or ''} - Type: {reservation.type_prestation}",
            statut='confirmee'  # Directement confirmée
        )
        
        db.session.add(prestation)
        db.session.flush()  # Pour obtenir l'ID
        
        # Transférer le matériel de la réservation vers la prestation
        materiels_reservation = MaterielPresta.query.filter_by(reservation_id=reservation.id).all()
        for mat_res in materiels_reservation:
            mat_prest = MaterielPresta(
                prestation_id=prestation.id,
                materiel_id=mat_res.materiel_id,
                quantite=mat_res.quantite
            )
            db.session.add(mat_prest)
        
        # Supprimer les assignations temporaires de la réservation
        MaterielPresta.query.filter_by(reservation_id=reservation.id).delete()
        
        # Lier la réservation à la prestation
        reservation.prestation_id = prestation.id
        
        # Calculer les montants avec le coût RÉEL du matériel
        cout_materiel, _ = calculer_cout_materiel_reel(prestation_id=prestation.id)
        tarif_horaire = 0
        if reservation.duree_heures > 0:
            tarif_horaire_raw = (reservation.prix_prestation - cout_materiel) / reservation.duree_heures
            if tarif_horaire_raw < 0:
                logger.warning(
                    f"Tarif horaire négatif évité (prix {reservation.prix_prestation} < coût matériel {cout_materiel})"
                )
                flash("⚠️ Le coût matériel dépasse le prix. Tarif horaire mis à 0.", 'warning')
                tarif_horaire = 0
            else:
                tarif_horaire = tarif_horaire_raw
        
        # Générer un numéro de devis unique et séquentiel
        numero_devis = generate_document_number('DEV')
        
        # Créer le DEVIS
        devis = Devis(
            numero=numero_devis,
            prestation_id=prestation.id,
            client_nom=reservation.nom,
            client_email=reservation.email,
            client_telephone=reservation.telephone,
            client_adresse=reservation.adresse,
            client_id=client_ref.id if client_ref else None,
            prestation_titre=f"Mission Prestataire - {reservation.type_prestation.title()}",
            prestation_description=reservation.demandes_speciales or f"Prestation {reservation.type_prestation}",
            date_prestation=reservation.date_souhaitee,
            heure_debut=reservation.heure_souhaitee,
            heure_fin=heure_fin_res,
            lieu=reservation.adresse,
            tarif_horaire=tarif_horaire,
            duree_heures=reservation.duree_heures,
            frais_materiel=cout_materiel,  # Coût RÉEL
            frais_transport=0.0,
            montant_ht=reservation.prix_prestation,
            taux_tva=20.0,
            montant_tva=reservation.prix_prestation * 0.2,
            montant_ttc=reservation.prix_prestation * 1.2,
            statut='brouillon',
            dj_id=reservation.dj_id,
            createur_id=reservation.manager_id,
            date_creation=utcnow()
        )
        
        # Générer token de signature électronique
        import secrets
        devis.signature_token = secrets.token_urlsafe(32)
        
        db.session.add(devis)
        db.session.flush()  # Pour obtenir l'ID et pouvoir appeler les méthodes
        
        # Synchroniser les coûts RÉELS du matériel et recalculer les totaux
        devis.synchroniser_frais_materiel()
        devis.calculer_totaux()
        if not devis.contenu_html:
            parametres = ParametresEntreprise.query.first()
            devis.contenu_html = build_devis_template(devis, parametres)
        
        reservation.devis_id = devis.id
        
        db.session.commit()
        
        flash('Réservation acceptée ! Prestation créée et devis prêt pour validation.', 'success')
        logger.info(f"Réservation {reservation.id} acceptée par DJ, prestation {prestation.id} créée, devis {devis.numero} en brouillon")
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la validation : {str(e)}', 'error')
        logger.error(f"Erreur validation DJ : {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('detail_reservation', reservation_id=reservation_id))

@app.route('/reservations/<int:reservation_id>/confirmer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def confirmer_reservation(reservation_id):
    """
    OBSOLÈTE - Route de confirmation finale
    Cette route n'est plus nécessaire avec le nouveau workflow en 2 étapes
    La confirmation se fait automatiquement quand le DJ accepte
    Conservée pour compatibilité avec les anciennes réservations
    """
    reservation = get_or_404(ReservationClient, reservation_id)
    
    # Si déjà confirmée, rediriger
    if reservation.statut == 'confirmee':
        flash('Cette réservation est déjà confirmée', 'info')
        return redirect(url_for('detail_reservation', reservation_id=reservation_id))
    
    if not reservation.peut_etre_confirmee:
        flash('La réservation doit être validée par le manager et le DJ', 'error')
        return redirect(url_for('detail_reservation', reservation_id=reservation_id))
    
    try:
        # La prestation existe déjà, créer seulement le devis
        if not reservation.devis_id and reservation.prestation_id:
            date_fin_res, heure_fin_res = compute_reservation_end(
                reservation.date_souhaitee,
                reservation.heure_souhaitee,
                reservation.duree_heures
            )
            client_ref = get_or_create_client(reservation.nom, reservation.email, reservation.telephone)
            devis = Devis(
                numero=generate_document_number('DEV'),
                client_nom=reservation.nom,
                client_email=reservation.email,
                client_telephone=reservation.telephone,
                client_adresse=reservation.adresse,
                client_id=client_ref.id if client_ref else None,
                prestation_titre=f"Prestation {reservation.type_prestation.title()}",
                prestation_description=reservation.demandes_speciales or f"Prestation {reservation.type_prestation}",
                date_prestation=reservation.date_souhaitee,
                heure_debut=reservation.heure_souhaitee,
                heure_fin=heure_fin_res,
                lieu=reservation.adresse,
                tarif_horaire=reservation.prix_prestation / reservation.duree_heures,
                duree_heures=reservation.duree_heures,
                montant_ht=reservation.prix_prestation,
                taux_tva=20.0,
                montant_tva=reservation.prix_prestation * 0.2,
                montant_ttc=reservation.prix_prestation * 1.2,
                statut='brouillon',
                dj_id=reservation.dj_id,
                createur_id=session['user_id'],
                prestation_id=reservation.prestation_id
            )
            
            db.session.add(devis)
            db.session.flush()  # Pour obtenir l'ID
            
            # Mettre à jour la réservation
            reservation.devis_id = devis.id
            reservation.statut = 'confirmee'
            reservation.date_confirmation = utcnow()

            if not devis.contenu_html:
                parametres = ParametresEntreprise.query.first()
                devis.contenu_html = build_devis_template(devis, parametres)
            
            db.session.commit()
            
            flash('Devis créé. Vous pouvez le vérifier avant envoi.', 'success')
        else:
            flash('Le devis existe déjà ou la prestation n\'est pas créée', 'error')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la confirmation : {str(e)}', 'error')
    
    return redirect(url_for('detail_reservation', reservation_id=reservation_id))

# ==================== ROUTES FACTURATION ====================

@app.route('/facturation')
@login_required
@role_required(['admin', 'manager'])
def facturation():
    """Page principale de facturation - liste des factures, devis, paiements"""
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'factures')

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    statut_filter = request.args.get('statut', '')
    mode_filter = request.args.get('mode', '')
    montant_min = request.args.get('montant_min', type=float)
    montant_max = request.args.get('montant_max', type=float)

    def _apply_date_range(query, field):
        if date_from:
            query = query.filter(field >= datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            query = query.filter(field <= datetime.strptime(date_to, '%Y-%m-%d').date())
        return query

    factures_query = Facture.query.options(
        joinedload(Facture.dj),
        joinedload(Facture.createur),
        joinedload(Facture.prestation),
        joinedload(Facture.devis)
    )
    devis_query = Devis.query.options(
        joinedload(Devis.dj),
        joinedload(Devis.createur),
        joinedload(Devis.prestation)
    )
    paiements_query = Paiement.query.options(joinedload(Paiement.facture))

    if statut_filter:
        if view == 'factures':
            if statut_filter == 'en_retard':
                factures_query = factures_query.filter(
                    Facture.date_echeance < date.today(),
                    Facture.statut.in_(['envoyee', 'brouillon', 'partiellement_payee'])
                )
            else:
                factures_query = factures_query.filter_by(statut=statut_filter)
        elif view == 'devis':
            devis_query = devis_query.filter_by(statut=statut_filter)
        elif view == 'paiements':
            paiements_query = paiements_query.filter(Paiement.statut == statut_filter)

    if mode_filter and view == 'paiements':
        paiements_query = paiements_query.filter(Paiement.mode_paiement == mode_filter)

    if view == 'factures':
        factures_query = _apply_date_range(factures_query, Facture.date_prestation)
        if montant_min is not None:
            factures_query = factures_query.filter(Facture.montant_ttc >= montant_min)
        if montant_max is not None:
            factures_query = factures_query.filter(Facture.montant_ttc <= montant_max)
        pagination = factures_query.order_by(Facture.date_creation.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    elif view == 'devis':
        devis_query = _apply_date_range(devis_query, Devis.date_prestation)
        if montant_min is not None:
            devis_query = devis_query.filter(Devis.montant_ttc >= montant_min)
        if montant_max is not None:
            devis_query = devis_query.filter(Devis.montant_ttc <= montant_max)
        pagination = devis_query.order_by(Devis.date_creation.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    else:
        if date_from:
            paiements_query = paiements_query.filter(Paiement.date_creation >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            paiements_query = paiements_query.filter(Paiement.date_creation <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        if montant_min is not None:
            paiements_query = paiements_query.filter(Paiement.montant >= montant_min)
        if montant_max is not None:
            paiements_query = paiements_query.filter(Paiement.montant <= montant_max)
        pagination = paiements_query.order_by(Paiement.date_creation.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)

    total_factures = Facture.query.count()
    factures_payees = Facture.query.filter_by(statut='payee').count()
    factures_en_attente = Facture.query.filter(Facture.statut.in_(['envoyee', 'partiellement_payee'])).count()
    factures_en_retard = Facture.query.filter(
        Facture.date_echeance < date.today(),
        Facture.statut.in_(['envoyee', 'brouillon', 'partiellement_payee'])
    ).count()
    total_devis = Devis.query.count()
    devis_acceptes = Devis.query.filter_by(statut='accepte').count()
    devis_en_attente = Devis.query.filter_by(statut='envoye').count()

    labels = []
    encaissements = []
    decaissements = []
    solde = []
    cumul = 0.0
    for i in range(11, -1, -1):
        month_start = (date.today().replace(day=1) - timedelta(days=30*i))
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        labels.append(month_start.strftime('%b %Y'))
        total_in = db.session.query(db.func.sum(Paiement.montant)).filter(
            Paiement.statut == 'reussi',
            Paiement.date_paiement >= month_start,
            Paiement.date_paiement <= month_end
        ).scalar() or 0
        total_out = 0
        cumul += (total_in - total_out)
        encaissements.append(float(total_in))
        decaissements.append(float(total_out))
        solde.append(float(cumul))

    chart_data = {
        'labels': labels,
        'encaissements': encaissements,
        'decaissements': decaissements,
        'solde': solde,
    }

    filters = {
        'date_from': date_from,
        'date_to': date_to,
        'statut': statut_filter,
        'mode': mode_filter,
        'montant_min': montant_min,
        'montant_max': montant_max,
    }

    return render_template(
        'facturation.html',
        factures=pagination if view == 'factures' else Facture.query.order_by(Facture.date_creation.desc()).paginate(page=1, per_page=ITEMS_PER_PAGE, error_out=False),
        devis=pagination if view == 'devis' else Devis.query.order_by(Devis.date_creation.desc()).paginate(page=1, per_page=ITEMS_PER_PAGE, error_out=False),
        paiements=pagination if view == 'paiements' else Paiement.query.order_by(Paiement.date_creation.desc()).paginate(page=1, per_page=ITEMS_PER_PAGE, error_out=False),
        pagination=pagination,
        view=view,
        filters=filters,
        total_factures=total_factures,
        factures_payees=factures_payees,
        factures_en_attente=factures_en_attente,
        factures_en_retard=factures_en_retard,
        total_devis=total_devis,
        devis_acceptes=devis_acceptes,
        devis_en_attente=devis_en_attente,
        chart_data=chart_data,
        now=datetime.now(),
        current_user=get_current_user()
    )

@app.route('/factures')
@login_required
@role_required(['admin', 'manager'])
def factures():
    """Liste des factures"""
    page = request.args.get('page', 1, type=int)
    statut_filter = request.args.get('statut', '')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    montant_min = request.args.get('montant_min', type=float)
    montant_max = request.args.get('montant_max', type=float)

    factures_query = Facture.query.options(
        joinedload(Facture.dj),
        joinedload(Facture.createur),
        joinedload(Facture.prestation),
        joinedload(Facture.devis)
    )
    if statut_filter:
        if statut_filter == 'en_retard':
            factures_query = factures_query.filter(
                Facture.date_echeance < date.today(),
                Facture.statut.in_(['envoyee', 'brouillon', 'partiellement_payee'])
            )
        else:
            factures_query = factures_query.filter_by(statut=statut_filter)

    if date_from:
        factures_query = factures_query.filter(Facture.date_prestation >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        factures_query = factures_query.filter(Facture.date_prestation <= datetime.strptime(date_to, '%Y-%m-%d').date())
    if montant_min is not None:
        factures_query = factures_query.filter(Facture.montant_ttc >= montant_min)
    if montant_max is not None:
        factures_query = factures_query.filter(Facture.montant_ttc <= montant_max)

    factures = factures_query.order_by(Facture.date_creation.desc()).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False
    )

    filters = {
        'statut': statut_filter,
        'date_from': date_from,
        'date_to': date_to,
        'montant_min': montant_min,
        'montant_max': montant_max,
    }

    return render_template('factures.html', factures=factures, filters=filters, current_user=get_current_user())

@app.route('/paiements')
@login_required
@role_required(['admin', 'manager'])
def paiements():
    """Liste des transactions de paiement"""
    page = request.args.get('page', 1, type=int)
    selected_id = request.args.get('selected', type=int)
    statut_filter = request.args.get('statut', '')
    mode_filter = request.args.get('mode', '')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    montant_min = request.args.get('montant_min', type=float)
    montant_max = request.args.get('montant_max', type=float)

    query = Paiement.query.options(joinedload(Paiement.facture)).order_by(Paiement.date_creation.desc())
    if statut_filter:
        query = query.filter(Paiement.statut == statut_filter)
    if mode_filter:
        query = query.filter(Paiement.mode_paiement == mode_filter)
    if date_from:
        query = query.filter(Paiement.date_creation >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Paiement.date_creation <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    if montant_min is not None:
        query = query.filter(Paiement.montant >= montant_min)
    if montant_max is not None:
        query = query.filter(Paiement.montant <= montant_max)

    paiements = query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    selected_paiement = None
    if selected_id:
        selected_paiement = db.session.get(Paiement, selected_id)
    if not selected_paiement and paiements.items:
        selected_paiement = paiements.items[0]

    filters = {
        'statut': statut_filter,
        'mode': mode_filter,
        'date_from': date_from,
        'date_to': date_to,
        'montant_min': montant_min,
        'montant_max': montant_max,
    }

    return render_template(
        'paiements.html',
        paiements=paiements,
        selected_paiement=selected_paiement,
        statut_filter=statut_filter,
        mode_filter=mode_filter,
        filters=filters,
        current_user=get_current_user()
    )

@app.route('/paiements/<int:paiement_id>/justificatif', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def upload_paiement_justificatif(paiement_id):
    """Upload justificatif + commentaire pour un paiement."""
    paiement = get_or_404(Paiement, paiement_id)
    commentaire = (request.form.get('commentaire') or '').strip()
    justificatif_file = request.files.get('justificatif_file')

    if not justificatif_file and not commentaire:
        flash('Ajoutez un justificatif ou un commentaire.', 'error')
        return redirect(request.referrer or url_for('paiements', selected=paiement.id))

    if justificatif_file and justificatif_file.filename:
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        valid, message = validate_document_upload(justificatif_file, allowed_extensions, max_size_mb=8)
        if not valid:
            flash(f'Justificatif invalide : {message}', 'error')
            return redirect(request.referrer or url_for('paiements', selected=paiement.id))
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'justificatifs')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = secure_filename(justificatif_file.filename)
        unique_name = f"justif_{uuid.uuid4().hex[:8]}_{safe_name}"
        file_path = os.path.join(upload_dir, unique_name)
        justificatif_file.save(file_path)
        paiement.justificatif_path = f'uploads/justificatifs/{unique_name}'

    if commentaire:
        paiement.commentaire = commentaire

    db.session.commit()
    flash('Justificatif mis à jour.', 'success')
    return redirect(request.referrer or url_for('paiements', selected=paiement.id))

@app.route('/produits')
@login_required
@role_required(['admin', 'manager'])
def produits():
    """Liste des produits (matériel) façon PennyLane."""
    page = request.args.get('page', 1, type=int)
    query_str = (request.args.get('q') or '').strip()

    query = Materiel.query
    if query_str:
        like = f"%{query_str}%"
        query = query.filter(
            db.or_(
                Materiel.nom.ilike(like),
                Materiel.code_barre.ilike(like),
                Materiel.numero_serie.ilike(like)
            )
        )
    materiels = query.order_by(Materiel.nom.asc()).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False
    )
    parametres = ParametresEntreprise.query.first()
    tva_rate = 20.0
    if parametres:
        tva_rate = parametres.taux_tva_defaut if parametres.taux_tva_defaut is not None else 20.0
        if parametres.tva_non_applicable:
            tva_rate = 0.0

    return render_template(
        'produits.html',
        materiels=materiels,
        tva_rate=tva_rate,
        filters={'q': query_str},
        current_user=get_current_user()
    )

@app.route('/clients')
@login_required
@role_required(['admin', 'manager'])
def clients():
    """Liste des clients."""
    page = request.args.get('page', 1, type=int)
    query_str = (request.args.get('q') or '').strip()

    factures_counts = db.session.query(
        Facture.client_id, db.func.count(Facture.id).label('factures_count')
    ).group_by(Facture.client_id).subquery()
    devis_counts = db.session.query(
        Devis.client_id, db.func.count(Devis.id).label('devis_count')
    ).group_by(Devis.client_id).subquery()

    query = db.session.query(
        Client,
        factures_counts.c.factures_count,
        devis_counts.c.devis_count
    ).outerjoin(
        factures_counts, Client.id == factures_counts.c.client_id
    ).outerjoin(
        devis_counts, Client.id == devis_counts.c.client_id
    )

    if query_str:
        query = query.filter(Client.nom.ilike(f"%{query_str}%"))

    clients_page = query.order_by(Client.nom.asc()).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False
    )

    return render_template(
        'clients.html',
        clients=clients_page,
        filters={'q': query_str},
        current_user=get_current_user()
    )

@app.route('/clients/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def nouveau_client():
    """Créer un client."""
    if request.method == 'POST':
        nom = normalize_whitespace(request.form.get('nom', ''))
        categories = normalize_whitespace(request.form.get('categories', ''))
        notes = normalize_whitespace(request.form.get('notes', ''))
        if not nom:
            flash("Le nom du client est requis.", 'error')
            return redirect(url_for('nouveau_client'))

        client = Client(nom=nom, categories=categories, notes=notes)
        db.session.add(client)
        db.session.flush()

        contact_noms = request.form.getlist('contact_nom')
        contact_emails = request.form.getlist('contact_email')
        contact_telephones = request.form.getlist('contact_telephone')
        contact_roles = request.form.getlist('contact_role')

        for idx, contact_nom in enumerate(contact_noms):
            email = normalize_email(contact_emails[idx]) if idx < len(contact_emails) else ''
            telephone = normalize_telephone(contact_telephones[idx]) if idx < len(contact_telephones) else ''
            role = normalize_whitespace(contact_roles[idx]) if idx < len(contact_roles) else ''
            nom_contact = normalize_whitespace(contact_nom)
            if not (nom_contact or email or telephone):
                continue
            db.session.add(ClientContact(
                client_id=client.id,
                nom=nom_contact,
                email=email or None,
                telephone=telephone or None,
                role=role or None
            ))

        db.session.commit()
        flash('Client créé avec succès.', 'success')
        return redirect(url_for('clients'))

    return render_template('client_form.html', client=None, current_user=get_current_user())

@app.route('/clients/<int:client_id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def modifier_client(client_id):
    """Modifier un client."""
    client = get_or_404(Client, client_id)
    if request.method == 'POST':
        nom = normalize_whitespace(request.form.get('nom', ''))
        categories = normalize_whitespace(request.form.get('categories', ''))
        notes = normalize_whitespace(request.form.get('notes', ''))
        if not nom:
            flash("Le nom du client est requis.", 'error')
            return redirect(url_for('modifier_client', client_id=client_id))
        client.nom = nom
        client.categories = categories
        client.notes = notes

        ClientContact.query.filter_by(client_id=client.id).delete()

        contact_noms = request.form.getlist('contact_nom')
        contact_emails = request.form.getlist('contact_email')
        contact_telephones = request.form.getlist('contact_telephone')
        contact_roles = request.form.getlist('contact_role')
        for idx, contact_nom in enumerate(contact_noms):
            email = normalize_email(contact_emails[idx]) if idx < len(contact_emails) else ''
            telephone = normalize_telephone(contact_telephones[idx]) if idx < len(contact_telephones) else ''
            role = normalize_whitespace(contact_roles[idx]) if idx < len(contact_roles) else ''
            nom_contact = normalize_whitespace(contact_nom)
            if not (nom_contact or email or telephone):
                continue
            db.session.add(ClientContact(
                client_id=client.id,
                nom=nom_contact,
                email=email or None,
                telephone=telephone or None,
                role=role or None
            ))

        db.session.commit()
        flash('Client mis à jour.', 'success')
        return redirect(url_for('client_detail', client_id=client.id))

    return render_template('client_form.html', client=client, current_user=get_current_user())

@app.route('/clients/<int:client_id>')
@login_required
@role_required(['admin', 'manager'])
def client_detail(client_id):
    """Détail client."""
    client = get_or_404(Client, client_id)
    factures = Facture.query.filter_by(client_id=client.id).order_by(Facture.date_creation.desc()).limit(10).all()
    devis_list = Devis.query.filter_by(client_id=client.id).order_by(Devis.date_creation.desc()).limit(10).all()
    return render_template(
        'client_detail.html',
        client=client,
        factures=factures,
        devis_list=devis_list,
        current_user=get_current_user()
    )

@app.route('/factures/nouvelle', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def nouvelle_facture():
    """Créer une nouvelle facture"""
    if request.method == 'POST':
        try:
            devis_id = request.form.get('devis_id')
            
            # ✅ VÉRIFICATION : Empêcher création multiple de factures pour le même devis
            if devis_id:
                facture_existante = Facture.query.filter_by(devis_id=int(devis_id)).first()
                if facture_existante:
                    devis = db.session.get(Devis, int(devis_id))
                    flash(f'❌ Une facture existe déjà pour le devis {devis.numero if devis else devis_id} (Facture #{facture_existante.numero}). Impossible de créer une 2ème facture.', 'error')
                    return redirect(url_for('detail_facture', facture_id=facture_existante.id))
            
            erreurs = []
            client_nom = normalize_whitespace(request.form.get('client_nom', ''))
            client_email = normalize_email(request.form.get('client_email', ''))
            client_telephone = normalize_telephone(request.form.get('client_telephone', ''))
            client_adresse = normalize_whitespace(request.form.get('client_adresse', ''))
            client_siren = normalize_whitespace(request.form.get('client_siren', ''))
            client_tva = normalize_whitespace(request.form.get('client_tva', ''))
            adresse_livraison = normalize_whitespace(request.form.get('adresse_livraison', ''))
            nature_operation = normalize_whitespace(request.form.get('nature_operation', ''))
            tva_sur_debits = 'tva_sur_debits' in request.form
            numero_bon_commande = normalize_whitespace(request.form.get('numero_bon_commande', ''))
            client_professionnel = 'client_professionnel' in request.form
            prestation_titre = normalize_whitespace(request.form.get('prestation_titre', ''))
            prestation_description = request.form.get('prestation_description', '')
            date_prestation = parse_date_field(request.form.get('date_prestation'), "Date de prestation", erreurs)
            heure_debut = parse_time_field(request.form.get('heure_debut'), "Heure de début", erreurs)
            heure_fin = parse_time_field(request.form.get('heure_fin'), "Heure de fin", erreurs)
            lieu = normalize_whitespace(request.form.get('lieu', ''))

            validate_required_field(client_nom, "Nom client", erreurs)
            validate_required_field(prestation_titre, "Titre de prestation", erreurs)
            validate_required_field(lieu, "Lieu", erreurs)
            validate_time_range(heure_debut, heure_fin, erreurs)

            if client_email:
                valide, message = valider_email(client_email)
                if not valide:
                    erreurs.append(message)
            if client_telephone:
                valide, message = valider_telephone(client_telephone)
                if not valide:
                    erreurs.append(message)
            if client_professionnel:
                valide, message = valider_siren(client_siren)
                if not valide:
                    erreurs.append(message)
                if not nature_operation:
                    erreurs.append("La nature de l’opération est requise pour un client professionnel")

            tarif_horaire = parse_float_field(request.form.get('tarif_horaire'), "Tarif horaire", erreurs, min_value=0, required=True)
            duree_heures = parse_float_field(request.form.get('duree_heures'), "Durée (heures)", erreurs, min_value=0, required=True)
            taux_tva = parse_float_field(request.form.get('taux_tva', 20.0), "TVA", erreurs, min_value=0, max_value=100, default=20.0)
            remise_pourcentage = parse_float_field(request.form.get('remise_pourcentage', 0.0), "Remise (%)", erreurs, min_value=0, max_value=100, default=0.0)
            remise_montant = parse_float_field(request.form.get('remise_montant', 0.0), "Remise (€)", erreurs, min_value=0, default=0.0)
            frais_transport = parse_float_field(request.form.get('frais_transport', 0.0), "Frais transport", erreurs, min_value=0, default=0.0)
            frais_materiel = parse_float_field(request.form.get('frais_materiel', 0.0), "Frais matériel", erreurs, min_value=0, default=0.0)

            date_echeance = None
            if request.form.get('date_echeance'):
                date_echeance = parse_date_field(request.form.get('date_echeance'), "Date d'échéance", erreurs, required=False)

            duree_calc = compute_duration_hours(heure_debut, heure_fin)
            if duree_calc is not None and duree_heures is not None:
                if abs(duree_heures - duree_calc) > 0.5:
                    erreurs.append("La durée ne correspond pas aux horaires indiqués")

            if date_echeance and date_prestation and date_echeance < date_prestation:
                erreurs.append("La date d'échéance doit être postérieure à la date de prestation")

            dj_id_value = None
            dj_id_raw = request.form.get('dj_id')
            if dj_id_raw not in (None, "", "None"):
                try:
                    dj_id_value = int(dj_id_raw)
                    if not db.session.get(DJ, dj_id_value):
                        erreurs.append("DJ sélectionné introuvable")
                except (TypeError, ValueError):
                    erreurs.append("DJ invalide")

            prestation_id_value = None
            prestation_id_raw = request.form.get('prestation_id')
            if prestation_id_raw not in (None, "", "None"):
                try:
                    prestation_id_value = int(prestation_id_raw)
                    if not db.session.get(Prestation, prestation_id_value):
                        erreurs.append("Prestation sélectionnée introuvable")
                except (TypeError, ValueError):
                    erreurs.append("Prestation invalide")

            # Cohérence devis ↔ prestation
            if devis_id:
                try:
                    devis_obj = db.session.get(Devis, int(devis_id))
                except Exception:
                    devis_obj = None
                if not devis_obj:
                    erreurs.append("Devis sélectionné introuvable")
                else:
                    if devis_obj.prestation_id:
                        if prestation_id_value and prestation_id_value != devis_obj.prestation_id:
                            erreurs.append("La prestation sélectionnée ne correspond pas au devis")
                        else:
                            prestation_id_value = devis_obj.prestation_id

            if not devis_id and not prestation_id_value:
                erreurs.append("La facture doit être liée à un devis ou une prestation")

            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('nouvelle_facture'))
            
            client_ref = get_or_create_client(client_nom, client_email, client_telephone)
            numero_facture = generate_document_number('FAC')
            facture = Facture(
                numero=numero_facture,
                client_nom=client_nom,
                client_email=client_email,
                client_telephone=client_telephone,
                client_adresse=client_adresse,
                client_siren=client_siren,
                client_tva=client_tva,
                adresse_livraison=adresse_livraison,
                nature_operation=nature_operation,
                tva_sur_debits=tva_sur_debits,
                numero_bon_commande=numero_bon_commande,
                client_professionnel=client_professionnel,
                client_id=client_ref.id if client_ref else None,
                prestation_titre=prestation_titre,
                prestation_description=prestation_description,
                date_prestation=date_prestation,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                lieu=lieu,
                tarif_horaire=tarif_horaire,
                duree_heures=duree_heures,
                taux_tva=taux_tva,
                remise_pourcentage=remise_pourcentage,
                remise_montant=remise_montant,
                frais_transport=frais_transport,
                frais_materiel=frais_materiel,
                date_echeance=date_echeance,
                conditions_paiement=request.form.get('conditions_paiement', ''),
                notes=request.form.get('notes', ''),
                statut=request.form.get('statut', 'brouillon'),
                dj_id=dj_id_value,
                createur_id=session['user_id'],
                prestation_id=prestation_id_value,
                devis_id=devis_id
            )
            
            # Calculer les totaux
            facture.calculer_totaux()
            
            db.session.add(facture)
            db.session.commit()
            AuditLog.log_action(
                action='creation',
                entite_type='facture',
                entite_id=facture.id,
                entite_nom=facture.numero,
                details={'montant_ttc': facture.montant_ttc}
            )
            flash('✅ Facture créée avec succès !', 'success')
            return redirect(url_for('detail_facture', facture_id=facture.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création de la facture : {str(e)}', 'error')
    
    # Récupérer les données pour les listes déroulantes
    djs = DJ.query.all()
    prestations = Prestation.query.filter_by(statut='confirmee').all()
    devis = Devis.query.filter_by(statut='accepte').all()
    
    return render_template('nouvelle_facture.html', 
                         djs=djs, 
                         prestations=prestations, 
                         devis=devis,
                         current_user=get_current_user())

@app.route('/factures/<int:facture_id>')
@login_required
@role_required(['admin', 'manager'])
def detail_facture(facture_id):
    """Détail d'une facture"""
    facture = get_or_404(Facture, facture_id)
    parametres = ParametresEntreprise.query.first()
    if parametres and parametres.stripe_enabled and parametres.stripe_secret_key:
        if facture.montant_restant > 0 and facture.statut not in ['annulee']:
            ensure_facture_payment_token(facture)
    return render_template('detail_facture.html', facture=facture, current_user=get_current_user(), parametres=parametres)

@app.route('/factures/<int:facture_id>/avoir', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def creer_avoir(facture_id):
    """Créer un avoir sur une facture"""
    facture = get_or_404(Facture, facture_id)
    if facture.statut == 'annulee':
        flash('Impossible de créer un avoir sur une facture annulée.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    if facture.statut == 'brouillon':
        flash('La facture doit être envoyée avant d’émettre un avoir.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))

    montant_max = max(0.0, (facture.montant_ttc or 0.0) - facture.total_avoirs)
    if montant_max <= 0:
        flash('Aucun montant disponible pour un avoir.', 'info')
        return redirect(url_for('detail_facture', facture_id=facture.id))

    if request.method == 'POST':
        try:
            erreurs = []
            montant_ttc = parse_float_field(request.form.get('montant_ttc'), "Montant TTC", erreurs, min_value=0.01, required=True)
            motif = normalize_whitespace(request.form.get('motif', ''))
            if not motif:
                erreurs.append("Motif requis")
            if montant_ttc is not None and montant_ttc > montant_max:
                erreurs.append(f"Le montant ne peut pas dépasser {montant_max:.2f}€")
            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('creer_avoir', facture_id=facture.id))

            taux_tva = facture.taux_tva or 0.0
            if taux_tva > 0:
                montant_ht = round(montant_ttc / (1 + (taux_tva / 100)), 2)
                montant_tva = round(montant_ttc - montant_ht, 2)
            else:
                montant_ht = montant_ttc
                montant_tva = 0.0

            avoir = Avoir(
                numero=generate_document_number('AV'),
                facture=facture,
                createur_id=session.get('user_id'),
                date_creation=utcnow(),
                montant_ht=montant_ht,
                taux_tva=taux_tva,
                montant_tva=montant_tva,
                montant_ttc=montant_ttc,
                motif=motif,
                statut='emis'
            )
            db.session.add(avoir)

            net_due = max(0.0, montant_max - montant_ttc)
            if net_due <= 0:
                facture.statut = 'payee'
                if not facture.date_paiement:
                    facture.date_paiement = date.today()
            elif facture.montant_paye > 0 and facture.statut != 'payee':
                facture.statut = 'partiellement_payee'

            db.session.commit()
            AuditLog.log_action(
                action='avoir',
                entite_type='facture',
                entite_id=facture.id,
                entite_nom=facture.numero,
                details={'montant': montant_ttc, 'motif': motif, 'numero': avoir.numero}
            )
            flash('Avoir émis avec succès !', 'success')
            return redirect(url_for('detail_facture', facture_id=facture.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création de l’avoir : {str(e)}', 'error')
            return redirect(url_for('creer_avoir', facture_id=facture.id))

    return render_template('creer_avoir.html', facture=facture, montant_max=montant_max, current_user=get_current_user())

@app.route('/factures/<int:facture_id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def modifier_facture(facture_id):
    """Modifier une facture"""
    facture = get_or_404(Facture, facture_id)
    if is_facture_locked(facture):
        flash('Cette facture est envoyée ou payée et ne peut plus être modifiée.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    
    if request.method == 'POST':
        try:
            erreurs = []
            client_nom = normalize_whitespace(request.form.get('client_nom', ''))
            client_email = normalize_email(request.form.get('client_email', ''))
            client_telephone = normalize_telephone(request.form.get('client_telephone', ''))
            client_adresse = normalize_whitespace(request.form.get('client_adresse', ''))
            client_siren = normalize_whitespace(request.form.get('client_siren', ''))
            client_tva = normalize_whitespace(request.form.get('client_tva', ''))
            adresse_livraison = normalize_whitespace(request.form.get('adresse_livraison', ''))
            nature_operation = normalize_whitespace(request.form.get('nature_operation', ''))
            tva_sur_debits = 'tva_sur_debits' in request.form
            numero_bon_commande = normalize_whitespace(request.form.get('numero_bon_commande', ''))
            client_professionnel = 'client_professionnel' in request.form
            prestation_titre = normalize_whitespace(request.form.get('prestation_titre', ''))
            prestation_description = request.form.get('prestation_description', '')
            date_prestation = parse_date_field(request.form.get('date_prestation'), "Date de prestation", erreurs)
            heure_debut = parse_time_field(request.form.get('heure_debut'), "Heure de début", erreurs)
            heure_fin = parse_time_field(request.form.get('heure_fin'), "Heure de fin", erreurs)
            lieu = normalize_whitespace(request.form.get('lieu', ''))

            validate_required_field(client_nom, "Nom client", erreurs)
            validate_required_field(prestation_titre, "Titre de prestation", erreurs)
            validate_required_field(lieu, "Lieu", erreurs)
            validate_time_range(heure_debut, heure_fin, erreurs)

            if client_email:
                valide, message = valider_email(client_email)
                if not valide:
                    erreurs.append(message)
            if client_telephone:
                valide, message = valider_telephone(client_telephone)
                if not valide:
                    erreurs.append(message)
            if client_professionnel:
                valide, message = valider_siren(client_siren)
                if not valide:
                    erreurs.append(message)
                if not nature_operation:
                    erreurs.append("La nature de l’opération est requise pour un client professionnel")

            tarif_horaire = parse_float_field(request.form.get('tarif_horaire'), "Tarif horaire", erreurs, min_value=0, required=True)
            duree_heures = parse_float_field(request.form.get('duree_heures'), "Durée (heures)", erreurs, min_value=0, required=True)
            taux_tva = parse_float_field(request.form.get('taux_tva', 20.0), "TVA", erreurs, min_value=0, max_value=100, default=20.0)
            remise_pourcentage = parse_float_field(request.form.get('remise_pourcentage', 0.0), "Remise (%)", erreurs, min_value=0, max_value=100, default=0.0)
            remise_montant = parse_float_field(request.form.get('remise_montant', 0.0), "Remise (€)", erreurs, min_value=0, default=0.0)
            frais_transport = parse_float_field(request.form.get('frais_transport', 0.0), "Frais transport", erreurs, min_value=0, default=0.0)
            frais_materiel = parse_float_field(request.form.get('frais_materiel', 0.0), "Frais matériel", erreurs, min_value=0, default=0.0)

            date_echeance = None
            if request.form.get('date_echeance'):
                date_echeance = parse_date_field(request.form.get('date_echeance'), "Date d'échéance", erreurs, required=False)

            duree_calc = compute_duration_hours(heure_debut, heure_fin)
            if duree_calc is not None and duree_heures is not None:
                if abs(duree_heures - duree_calc) > 0.5:
                    erreurs.append("La durée ne correspond pas aux horaires indiqués")

            if date_echeance and date_prestation and date_echeance < date_prestation:
                erreurs.append("La date d'échéance doit être postérieure à la date de prestation")

            dj_id_value = None
            dj_id_raw = request.form.get('dj_id')
            if dj_id_raw not in (None, "", "None"):
                try:
                    dj_id_value = int(dj_id_raw)
                    if not db.session.get(DJ, dj_id_value):
                        erreurs.append("DJ sélectionné introuvable")
                except (TypeError, ValueError):
                    erreurs.append("DJ invalide")

            prestation_id_value = None
            prestation_id_raw = request.form.get('prestation_id')
            if prestation_id_raw not in (None, "", "None"):
                try:
                    prestation_id_value = int(prestation_id_raw)
                    if not db.session.get(Prestation, prestation_id_value):
                        erreurs.append("Prestation sélectionnée introuvable")
                except (TypeError, ValueError):
                    erreurs.append("Prestation invalide")

            devis_id_value = None
            devis_id_raw = request.form.get('devis_id')
            if devis_id_raw not in (None, "", "None"):
                try:
                    devis_id_value = int(devis_id_raw)
                    if not db.session.get(Devis, devis_id_value):
                        erreurs.append("Devis sélectionné introuvable")
                except (TypeError, ValueError):
                    erreurs.append("Devis invalide")
            if devis_id_value:
                facture_existante = Facture.query.filter_by(devis_id=devis_id_value).first()
                if facture_existante and facture_existante.id != facture.id:
                    erreurs.append("Une autre facture est déjà liée à ce devis")
                devis_obj = db.session.get(Devis, devis_id_value)
                if devis_obj and devis_obj.prestation_id:
                    if prestation_id_value and prestation_id_value != devis_obj.prestation_id:
                        erreurs.append("La prestation sélectionnée ne correspond pas au devis")
                    else:
                        prestation_id_value = devis_obj.prestation_id

            if not devis_id_value and not prestation_id_value:
                erreurs.append("La facture doit être liée à un devis ou une prestation")

            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('modifier_facture', facture_id=facture.id))

            facture.client_nom = client_nom
            facture.client_email = client_email
            facture.client_telephone = client_telephone
            facture.client_adresse = client_adresse
            facture.client_siren = client_siren
            facture.client_tva = client_tva
            facture.adresse_livraison = adresse_livraison
            facture.nature_operation = nature_operation
            facture.tva_sur_debits = tva_sur_debits
            facture.numero_bon_commande = numero_bon_commande
            facture.client_professionnel = client_professionnel
            facture.prestation_titre = prestation_titre
            facture.prestation_description = prestation_description
            facture.date_prestation = date_prestation
            facture.heure_debut = heure_debut
            facture.heure_fin = heure_fin
            facture.lieu = lieu
            facture.tarif_horaire = tarif_horaire
            facture.duree_heures = duree_heures
            facture.taux_tva = taux_tva
            facture.remise_pourcentage = remise_pourcentage
            facture.remise_montant = remise_montant
            facture.frais_transport = frais_transport
            facture.frais_materiel = frais_materiel
            facture.date_echeance = date_echeance
            facture.conditions_paiement = request.form.get('conditions_paiement', '')
            facture.notes = request.form.get('notes', '')
            facture.statut = request.form.get('statut', 'brouillon')
            facture.dj_id = dj_id_value
            facture.prestation_id = prestation_id_value
            facture.devis_id = devis_id_value

            if facture.statut == 'annulee' and facture.montant_paye > 0:
                flash('Impossible d’annuler une facture avec un paiement enregistré.', 'error')
                return redirect(url_for('modifier_facture', facture_id=facture.id))
            
            # Recalculer les totaux
            facture.calculer_totaux()

            if facture.statut == 'payee':
                facture.montant_paye = facture.montant_du_net
                facture.date_paiement = date.today()
            elif facture.statut in {'brouillon', 'envoyee', 'en_retard'} and facture.montant_paye > facture.montant_du_net:
                facture.montant_paye = facture.montant_du_net
            
            db.session.commit()
            AuditLog.log_action(
                action='modification',
                entite_type='facture',
                entite_id=facture.id,
                entite_nom=facture.numero,
                details={'statut': facture.statut}
            )
            flash('Facture modifiée avec succès !', 'success')
            return redirect(url_for('detail_facture', facture_id=facture.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification de la facture : {str(e)}', 'error')
    
    # Récupérer les données pour les listes déroulantes
    djs = DJ.query.all()
    prestations = Prestation.query.filter_by(statut='confirmee').all()
    devis = Devis.query.filter_by(statut='accepte').all()
    
    return render_template('modifier_facture.html', 
                         facture=facture, 
                         djs=djs, 
                         prestations=prestations, 
                         devis=devis,
                         current_user=get_current_user())

@app.route('/factures/<int:facture_id>/supprimer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def supprimer_facture(facture_id):
    """Supprimer une facture"""
    facture = get_or_404(Facture, facture_id)
    if facture.est_payee:
        flash('Impossible d’annuler une facture payée. Émettre un avoir.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    facture.statut = 'annulee'
    facture.date_annulation = utcnow()
    db.session.commit()
    AuditLog.log_action(
        action='annulation',
        entite_type='facture',
        entite_id=facture.id,
        entite_nom=facture.numero
    )
    flash('Facture annulée avec succès !', 'success')
    return redirect(url_for('factures'))

@app.route('/factures/<int:facture_id>/changer-statut', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def changer_statut_facture(facture_id):
    """Changer le statut d'une facture"""
    facture = get_or_404(Facture, facture_id)
    nouveau_statut = request.form['statut']

    if facture.statut == 'annulee':
        flash('Cette facture est annulée et ne peut plus changer de statut.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture_id))
    if is_facture_locked(facture) and nouveau_statut != facture.statut:
        flash('Cette facture est verrouillée et son statut ne peut plus être modifié.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture_id))
    if facture.est_payee and nouveau_statut == 'annulee':
        flash('Impossible d’annuler une facture payée. Émettre un avoir.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture_id))
    
    facture.statut = nouveau_statut
    
    if nouveau_statut == 'envoyee':
        facture.date_envoi = utcnow()
    elif nouveau_statut == 'payee':
        facture.date_paiement = date.today()
        facture.montant_paye = facture.montant_du_net
    
    db.session.commit()
    flash(f'Statut de la facture changé en "{nouveau_statut}"', 'success')
    return redirect(url_for('detail_facture', facture_id=facture_id))

@app.route('/factures/<int:facture_id>/enregistrer-paiement', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def enregistrer_paiement(facture_id):
    """Enregistrer un paiement pour une facture"""
    facture = get_or_404(Facture, facture_id)

    if facture.statut == 'annulee':
        flash('Impossible d’enregistrer un paiement sur une facture annulée.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    if facture.statut in ['brouillon']:
        flash('La facture doit être envoyée avant d’enregistrer un paiement.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    if facture.montant_restant <= 0:
        flash('Aucun montant restant à payer sur cette facture.', 'info')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    
    try:
        erreurs = []
        montant_paye = parse_float_field(request.form.get('montant_paye'), "Montant payé", erreurs, min_value=0.01, required=True)
        if erreurs:
            for err in erreurs:
                flash(err, 'error')
            return redirect(url_for('detail_facture', facture_id=facture.id))
        mode_paiement = (request.form.get('mode_paiement') or '').strip()
        reference_paiement = (request.form.get('reference_paiement') or '').strip()
        justificatif = (request.form.get('justificatif') or '').strip()
        confirm_numero = (request.form.get('confirm_numero') or '').strip()

        if not mode_paiement:
            flash('Le mode de paiement est obligatoire.', 'error')
            return redirect(url_for('detail_facture', facture_id=facture.id))
        if facture.mode_paiement_souhaite and facture.mode_paiement_souhaite != mode_paiement:
            flash('Le mode de paiement doit correspondre au mode demandé sur la facture.', 'error')
            return redirect(url_for('detail_facture', facture_id=facture.id))
        if mode_paiement in ['virement', 'cheque', 'carte'] and not reference_paiement:
            flash('La référence est obligatoire pour ce mode de paiement.', 'error')
            return redirect(url_for('detail_facture', facture_id=facture.id))
        if not justificatif:
            flash('Un justificatif est obligatoire pour enregistrer un paiement manuel.', 'error')
            return redirect(url_for('detail_facture', facture_id=facture.id))
        if confirm_numero != facture.numero:
            flash('Le numéro de facture saisi ne correspond pas.', 'error')
            return redirect(url_for('detail_facture', facture_id=facture.id))

        valide, message = facture.valider_paiement(montant_paye)
        if not valide:
            flash(message, 'error')
            return redirect(url_for('detail_facture', facture_id=facture.id))

        parametres = ParametresEntreprise.query.first()
        paiement = Paiement(
            numero=generate_document_number('PAY'),
            montant=montant_paye,
            devise=(parametres.devise if parametres else 'EUR'),
            type_paiement='facture',
            mode_paiement=mode_paiement or None,
            description=f"Paiement facture {facture.numero} (en attente de validation)",
            statut='en_attente',
            date_paiement=None,
            facture_id=facture.id,
            createur_id=session.get('user_id'),
            client_nom=facture.client_nom,
            client_email=facture.client_email,
            client_telephone=facture.client_telephone,
            client_ip=request.remote_addr,
            payment_metadata=json.dumps({
                'reference': reference_paiement,
                'justificatif': justificatif,
                'saisi_par': session.get('user_id')
            }, ensure_ascii=False)
        )
        db.session.add(paiement)

        db.session.commit()
        AuditLog.log_action(
            action='paiement',
            entite_type='facture',
            entite_id=facture.id,
            entite_nom=facture.numero,
            details={'montant': montant_paye, 'mode': mode_paiement, 'statut': 'en_attente'}
        )
        flash('Paiement enregistré et en attente de validation.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'enregistrement du paiement : {str(e)}', 'error')
    
    return redirect(url_for('detail_facture', facture_id=facture_id))

@app.route('/factures/<int:facture_id>/paiements/<int:paiement_id>/valider', methods=['POST'])
@login_required
@role_required(['admin'])
def valider_paiement_facture(facture_id, paiement_id):
    facture = get_or_404(Facture, facture_id)
    paiement = get_or_404(Paiement, paiement_id)
    if paiement.facture_id != facture.id:
        flash('Paiement invalide pour cette facture.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    if paiement.statut != 'en_attente':
        flash('Ce paiement a déjà été traité.', 'info')
        return redirect(url_for('detail_facture', facture_id=facture.id))

    valide, message = facture.valider_paiement(paiement.montant)
    if not valide:
        flash(message, 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))

    ok, msg = facture.ajouter_paiement(paiement.montant)
    if not ok:
        flash(msg, 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))

    paiement.statut = 'reussi'
    paiement.date_paiement = utcnow()
    try:
        metadata = json.loads(paiement.payment_metadata or '{}')
    except Exception:
        metadata = {}
    facture.mode_paiement = paiement.mode_paiement
    if metadata.get('reference'):
        facture.reference_paiement = metadata['reference']
    metadata['valide_par'] = session.get('user_id')
    paiement.payment_metadata = json.dumps(metadata, ensure_ascii=False)

    db.session.commit()
    AuditLog.log_action(
        action='paiement',
        entite_type='facture',
        entite_id=facture.id,
        entite_nom=facture.numero,
        details={'montant': paiement.montant, 'mode': paiement.mode_paiement, 'statut': 'reussi'}
    )
    flash('Paiement validé.', 'success')
    return redirect(url_for('detail_facture', facture_id=facture.id))

@app.route('/factures/<int:facture_id>/paiements/<int:paiement_id>/rejeter', methods=['POST'])
@login_required
@role_required(['admin'])
def rejeter_paiement_facture(facture_id, paiement_id):
    facture = get_or_404(Facture, facture_id)
    paiement = get_or_404(Paiement, paiement_id)
    if paiement.facture_id != facture.id:
        flash('Paiement invalide pour cette facture.', 'error')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    if paiement.statut != 'en_attente':
        flash('Ce paiement a déjà été traité.', 'info')
        return redirect(url_for('detail_facture', facture_id=facture.id))
    raison = (request.form.get('raison') or '').strip()
    paiement.statut = 'annule'
    paiement.derniere_erreur = raison or 'Rejeté par un administrateur'
    try:
        metadata = json.loads(paiement.payment_metadata or '{}')
    except Exception:
        metadata = {}
    metadata['rejete_par'] = session.get('user_id')
    paiement.payment_metadata = json.dumps(metadata, ensure_ascii=False)
    db.session.commit()
    AuditLog.log_action(
        action='paiement',
        entite_type='facture',
        entite_id=facture.id,
        entite_nom=facture.numero,
        details={'montant': paiement.montant, 'mode': paiement.mode_paiement, 'statut': 'annule'}
    )
    flash('Paiement rejeté.', 'warning')
    return redirect(url_for('detail_facture', facture_id=facture.id))

@app.route('/factures/<int:facture_id>/pdf')
@login_required
@role_required(['admin', 'manager'])
def facture_pdf(facture_id):
    """Générer le PDF d'une facture"""
    facture = get_or_404(Facture, facture_id)
    
    # Récupérer les paramètres de l'entreprise
    parametres = ParametresEntreprise.query.first()
    include_company_signature = None
    if parametres and getattr(parametres, 'signature_entreprise_path', None):
        if 'signature' in request.args:
            include_company_signature = str(request.args.get('signature', '')).lower() in ('1', 'true', 'on', 'yes')
    
    # Générer le PDF
    from pdf_generator import generate_facture_pdf
    pdf_data = generate_facture_pdf(facture, parametres, include_company_signature=include_company_signature)
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="facture_{facture.numero}.pdf"'
    return response

@app.route('/export/factures')
@login_required
@role_required(['admin', 'manager'])
def export_factures():
    """Export des factures en Excel"""
    factures = Facture.query.all()
    excel_exporter_module = get_excel_exporter()
    if not excel_exporter_module:
        flash('Module Excel non disponible', 'error')
        return redirect(url_for('factures'))
    excel_data, filename = excel_exporter_module.export_factures(factures)
    
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/factures/creer-depuis-prestation')
@login_required
@role_required(['admin', 'manager'])
def creer_facture_depuis_prestation():
    """Page pour créer une facture à partir d'une prestation avec devis"""
    # Récupérer les prestations qui ont un devis associé
    prestations = Prestation.query.join(Devis, Prestation.id == Devis.prestation_id).all()
    
    return render_template('creer_facture_prestation.html', prestations=prestations)

@app.route('/factures/envoyer-email/<int:facture_id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def envoyer_facture_email(facture_id):
    """Envoyer une facture par email au client"""
    facture = get_or_404(Facture, facture_id)
    
    if facture.statut == 'annulee':
        flash('Impossible d’envoyer une facture annulée.', 'error')
        return redirect(url_for('facturation'))
    if not facture.client_email:
        flash('Aucune adresse email renseignée pour ce client.', 'error')
        return redirect(url_for('facturation'))
    
    try:
        # Générer le PDF de la facture
        from pdf_generator import generate_facture_pdf
        from email_service import EmailService
        parametres = ParametresEntreprise.query.first()
        pdf_data = generate_facture_pdf(facture, parametres)

        payment_option = (request.form.get('payment_option') or '').strip().lower()
        if payment_option not in {'stripe', 'virement', 'especes', ''}:
            payment_option = ''
        if not payment_option:
            if parametres and parametres.stripe_enabled and get_stripe_secret(parametres):
                payment_option = 'stripe'
            elif parametres:
                rib_values = get_rib_values(parametres)
                if rib_values.get('iban'):
                    payment_option = 'virement'
                else:
                    payment_option = 'especes'
            else:
                payment_option = 'especes'

        date_prestation_str = facture.date_prestation.strftime('%d/%m/%Y') if facture.date_prestation else 'Non spécifiée'
        date_echeance_str = facture.date_echeance.strftime('%d/%m/%Y') if facture.date_echeance else None
        body = f"""Bonjour {facture.client_nom},

Voici votre facture {facture.numero} d'un montant de {facture.montant_ttc:.2f}€.

Détails de la prestation :
- Date : {date_prestation_str}
- Heure : {facture.heure_debut} - {facture.heure_fin}
- Lieu : {facture.lieu}

{('Date d\'échéance : ' + date_echeance_str) if date_echeance_str else ''}

{('Conditions de paiement : ' + facture.conditions_paiement) if facture.conditions_paiement else ''}

Merci pour votre confiance."""

        if payment_option == 'stripe':
            if not parametres or not parametres.stripe_enabled or not get_stripe_secret(parametres):
                flash('Stripe n’est pas configuré. Activez-le ou choisissez un autre mode.', 'error')
                return redirect(url_for('facturation'))
            token = ensure_facture_payment_token(facture)
            payment_link = url_for('stripe_bp.pay_invoice', invoice_id=facture.id, token=token, _external=True)
            body += f"\n\nVous pouvez régler cette facture en ligne via notre plateforme sécurisée :\n{payment_link}"
        elif payment_option == 'virement':
            rib_values = get_rib_values(parametres)
            iban = rib_values.get('iban')
            titulaire = rib_values.get('titulaire')
            bic = rib_values.get('bic')
            banque = rib_values.get('banque')
            if not iban or not titulaire:
                flash('RIB incomplet. Renseignez IBAN et titulaire dans les paramètres.', 'error')
                return redirect(url_for('facturation'))
            rib_lines = [
                f"TITULAIRE : {titulaire}",
                f"IBAN : {iban}",
            ]
            if bic:
                rib_lines.append(f"BIC : {bic}")
            if banque:
                rib_lines.append(f"BANQUE : {banque}")
            body += "\n\nRèglement par virement bancaire :\n" + "\n".join(rib_lines)
        elif payment_option == 'especes':
            body += "\n\nRèglement en espèces : merci de prévoir le paiement le jour de la prestation."

        facture.mode_paiement_souhaite = payment_option

        subject = f"Facture {facture.numero} - {parametres.nom_entreprise if parametres else 'Planify'}"
        email_service = EmailService()
        email_service.send_email_with_attachment(
            to_email=facture.client_email,
            subject=subject,
            body=body,
            attachment_data=pdf_data,
            attachment_filename=f'facture_{facture.numero}.pdf'
        )

        # Mettre à jour le statut de la facture (ne pas écraser un paiement)
        if facture.statut not in ('payee', 'partiellement_payee'):
            facture.statut = 'envoyee'
        facture.date_envoi = utcnow()
        db.session.commit()

        AuditLog.log_action(
            action='envoi',
            entite_type='facture',
            entite_id=facture.id,
            entite_nom=facture.numero
        )
        flash(f'Facture {facture.numero} envoyée avec succès à {facture.client_email} !', 'success')

    except Exception as e:
        flash(f'Erreur lors de l\'envoi de l\'email : {str(e)}', 'error')
    
    return redirect(url_for('facturation'))

@app.route('/devis/envoyer-email/<int:devis_id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def envoyer_devis_email(devis_id):
    """Envoyer un devis par email au client"""
    devis = get_or_404(Devis, devis_id)
    include_tva_raw = request.form.get('include_tva')
    if include_tva_raw is None:
        include_tva = True if devis.tva_incluse is None else bool(devis.tva_incluse)
    else:
        include_tva = str(include_tva_raw).lower() in ('1', 'true', 'on', 'yes')
    parametres = ParametresEntreprise.query.first()
    if parametres and parametres.tva_non_applicable:
        include_tva = False
    
    if not devis.client_email:
        flash('Aucune adresse email renseignée pour ce client.', 'error')
        return redirect(url_for('facturation'))
    
    try:
        _envoyer_devis_email(devis, include_tva=include_tva)

        AuditLog.log_action(
            action='envoi',
            entite_type='devis',
            entite_id=devis.id,
            entite_nom=devis.numero
        )
        flash(f'Devis {devis.numero} envoyé avec succès à {devis.client_email} !', 'success')

    except Exception as e:
        flash(f'Erreur lors de l\'envoi de l\'email : {str(e)}', 'error')
    
    return redirect(url_for('facturation'))

@app.route('/devis/<int:devis_id>/envoyer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def envoyer_devis_apres_edition(devis_id):
    """Met a jour le contenu du devis puis envoie l'email au client."""
    devis = get_or_404(Devis, devis_id)
    contenu_html = request.form.get('contenu_html', '').strip()
    if not is_devis_locked(devis) and contenu_html:
        devis.contenu_html = sanitize_rich_html(contenu_html)
        db.session.commit()

    if not devis.client_email:
        flash('Aucune adresse email renseignée pour ce client.', 'error')
        return redirect(url_for('detail_devis', devis_id=devis.id))

    try:
        include_tva_raw = request.form.get('include_tva')
        if devis.est_signe:
            include_tva = True if devis.tva_incluse is None else bool(devis.tva_incluse)
        elif include_tva_raw is None:
            include_tva = True if devis.tva_incluse is None else bool(devis.tva_incluse)
        else:
            include_tva = str(include_tva_raw).lower() in ('1', 'true', 'on', 'yes')
        parametres = ParametresEntreprise.query.first()
        if parametres and parametres.tva_non_applicable:
            include_tva = False
        _envoyer_devis_email(devis, include_tva=include_tva)
        AuditLog.log_action(
            action='envoi',
            entite_type='devis',
            entite_id=devis.id,
            entite_nom=devis.numero
        )
        flash(f'Devis {devis.numero} envoyé avec succès à {devis.client_email} !', 'success')
    except Exception as e:
        flash(f'Erreur lors de l\'envoi de l\'email : {str(e)}', 'error')

    return redirect(url_for('detail_devis', devis_id=devis.id))

@app.route('/factures/creer-depuis-prestation/<int:prestation_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def creer_facture_depuis_prestation_id(prestation_id):
    """Créer une facture à partir d'une prestation spécifique"""
    prestation = get_or_404(Prestation, prestation_id)
    devis = Devis.query.filter_by(prestation_id=prestation_id).first()
    
    if not devis:
        flash('Cette prestation n\'a pas de devis associé.', 'error')
        return redirect(url_for('creer_facture_depuis_prestation'))
    
    # ✅ VÉRIFICATION : Empêcher création multiple de factures pour le même devis
    facture_existante = Facture.query.filter_by(devis_id=devis.id).first()
    if facture_existante:
        flash(f'❌ Une facture existe déjà pour le devis {devis.numero} (Facture #{facture_existante.numero}). Impossible de créer une 2ème facture.', 'warning')
        return redirect(url_for('detail_facture', facture_id=facture_existante.id))
    
    if request.method == 'POST':
        try:
            # Générer un numéro de facture unique et séquentiel
            numero_facture = generate_document_number('FAC')
            parametres = ParametresEntreprise.query.first()
            include_tva = True if devis.tva_incluse is None else bool(devis.tva_incluse)
            if parametres and parametres.tva_non_applicable:
                include_tva = False
            montant_tva = devis.montant_tva if include_tva else 0.0
            montant_ttc = devis.montant_ttc if include_tva else devis.montant_ht
            taux_tva = devis.taux_tva if include_tva else 0.0
            client_professionnel = 'client_professionnel' in request.form
            client_siren = normalize_whitespace(request.form.get('client_siren', ''))
            client_tva = normalize_whitespace(request.form.get('client_tva', ''))
            adresse_livraison = normalize_whitespace(request.form.get('adresse_livraison', ''))
            nature_operation = normalize_whitespace(request.form.get('nature_operation', ''))
            tva_sur_debits = 'tva_sur_debits' in request.form
            numero_bon_commande = normalize_whitespace(request.form.get('numero_bon_commande', ''))

            erreurs = []
            if client_professionnel:
                valide, message = valider_siren(client_siren)
                if not valide:
                    erreurs.append(message)
                if not nature_operation:
                    erreurs.append("La nature de l’opération est requise pour un client professionnel")
            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('creer_facture_depuis_prestation_id', prestation_id=prestation_id))
            
            # Créer la facture à partir des données de la prestation (priorité) et du devis
            client_nom = prestation.client
            client_email = prestation.client_email or devis.client_email
            client_telephone = prestation.client_telephone or devis.client_telephone
            client_ref = get_or_create_client(client_nom, client_email, client_telephone)
            facture = Facture(
                numero=numero_facture,
                client_nom=client_nom,  # Utiliser les données de la prestation
                client_email=client_email,  # Prestation en priorité
                client_telephone=client_telephone,  # Prestation en priorité
                client_adresse=devis.client_adresse,  # Garder l'adresse du devis si pas dans prestation
                client_siren=client_siren,
                client_tva=client_tva,
                client_id=client_ref.id if client_ref else None,
                adresse_livraison=adresse_livraison,
                nature_operation=nature_operation,
                tva_sur_debits=tva_sur_debits,
                numero_bon_commande=numero_bon_commande,
                client_professionnel=client_professionnel,
                
                # Informations de la prestation
                prestation_titre=devis.prestation_titre,
                prestation_description=devis.prestation_description,
                date_prestation=devis.date_prestation,
                heure_debut=devis.heure_debut,
                heure_fin=devis.heure_fin,
                lieu=devis.lieu,
                
                # Tarification (copiée du devis)
                tarif_horaire=devis.tarif_horaire,
                duree_heures=devis.duree_heures,
                montant_ht=devis.montant_ht,
                taux_tva=taux_tva,
                montant_tva=montant_tva,
                montant_ttc=montant_ttc,
                
                # Remises et frais
                remise_pourcentage=devis.remise_pourcentage,
                remise_montant=devis.remise_montant,
                frais_transport=devis.frais_transport,
                frais_materiel=devis.frais_materiel,
                
                # Statut et dates
                statut='brouillon',
                date_creation=utcnow(),
                date_echeance=utcnow() + timedelta(days=30),
                
                # Relations
                dj_id=prestation.dj_id,
                createur_id=session['user_id'],
                prestation_id=prestation.id,
                devis_id=devis.id,
                
                # Notes personnalisées
                notes=request.form.get('notes', ''),
                conditions_paiement=request.form.get('conditions_paiement', 'Paiement à réception de facture')
            )
            
            db.session.add(facture)
            db.session.commit()
            
            flash(f'Facture {numero_facture} créée avec succès à partir de la prestation !', 'success')
            return redirect(url_for('detail_facture', facture_id=facture.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création de la facture : {str(e)}', 'error')
    
    return render_template('creer_facture_prestation_detail.html', prestation=prestation, devis=devis)

@app.route('/export/rapport-complet')
@login_required
def export_rapport_complet():
    """Export d'un rapport complet"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    excel_exporter_module = get_excel_exporter()
    if not excel_exporter_module:
        flash('Module Excel non disponible', 'error')
        return redirect(url_for('rapports_avances'))
    excel_data, filename = excel_exporter_module.export_rapport_complet(start_date, end_date)
    
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/rapports-avances')
@login_required
def rapports_avances():
    """Rapports avancés avec exports"""
    # Récupération des paramètres de filtre
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = date.today() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = date.today()
    
    # Statistiques sur la période - Calculs basés sur les vraies données
    prestations_periode = Prestation.query.filter(
        Prestation.date_debut.between(start_date, end_date)
    ).count()
    
    # Calcul des revenus estimés basé sur les devis réels
    devis_periode = Devis.query.filter(
        Devis.date_creation.between(start_date, end_date)
    ).all()
    revenus_estimes = sum(devis.montant_ttc for devis in devis_periode if devis.montant_ttc) if devis_periode else 0
    
    # Matériel utilisé sur la période (matériels associés aux prestations de la période)
    materiel_utilise = db.session.query(Materiel).join(MaterielPresta).join(Prestation).filter(
        Prestation.date_debut.between(start_date, end_date)
    ).distinct().count()
    
    # DJs actifs sur la période
    djs_actifs = db.session.query(DJ).join(Prestation).filter(
        Prestation.date_debut.between(start_date, end_date)
    ).distinct().count()
    
    # Calcul des pourcentages d'augmentation par rapport à la période précédente
    periode_duree = (end_date - start_date).days
    periode_precedente_start = start_date - timedelta(days=periode_duree)
    periode_precedente_end = start_date - timedelta(days=1)
    
    # Statistiques de la période précédente
    prestations_periode_precedente = Prestation.query.filter(
        Prestation.date_debut.between(periode_precedente_start, periode_precedente_end)
    ).count()
    
    devis_periode_precedente = Devis.query.filter(
        Devis.date_creation.between(periode_precedente_start, periode_precedente_end)
    ).all()
    revenus_periode_precedente = sum(devis.montant_ttc for devis in devis_periode_precedente if devis.montant_ttc) if devis_periode_precedente else 0
    
    materiel_utilise_precedente = db.session.query(Materiel).join(MaterielPresta).join(Prestation).filter(
        Prestation.date_debut.between(periode_precedente_start, periode_precedente_end)
    ).distinct().count()
    
    djs_actifs_precedente = db.session.query(DJ).join(Prestation).filter(
        Prestation.date_debut.between(periode_precedente_start, periode_precedente_end)
    ).distinct().count()
    
    # Calcul des pourcentages d'augmentation
    def calculer_pourcentage_evolution(actuel, precedent):
        if precedent == 0:
            return 100 if actuel > 0 else 0
        return round(((actuel - precedent) / precedent) * 100, 1)
    
    pourcentage_prestations = calculer_pourcentage_evolution(prestations_periode, prestations_periode_precedente)
    pourcentage_revenus = calculer_pourcentage_evolution(revenus_estimes, revenus_periode_precedente)
    pourcentage_materiel = calculer_pourcentage_evolution(materiel_utilise, materiel_utilise_precedente)
    pourcentage_djs = calculer_pourcentage_evolution(djs_actifs, djs_actifs_precedente)
    
    # Données réelles pour les graphiques - Évolution des prestations par semaine
    prestations_par_semaine = []
    prestations_labels = []
    
    # Calculer les semaines dans la période
    current_date = start_date
    while current_date <= end_date:
        semaine_fin = min(current_date + timedelta(days=6), end_date)
        count = Prestation.query.filter(
            Prestation.date_debut.between(current_date, semaine_fin)
        ).count()
        prestations_par_semaine.append(count)
        prestations_labels.append(f"Sem {len(prestations_labels) + 1}")
        current_date = semaine_fin + timedelta(days=1)
    
    prestations_data = prestations_par_semaine if prestations_par_semaine else [0]
    
    # Répartition par statut des prestations
    prestations_par_statut = db.session.query(
        Prestation.statut, 
        db.func.count(Prestation.id)
    ).filter(
        Prestation.date_debut.between(start_date, end_date)
    ).group_by(Prestation.statut).all()
    
    repartition_labels = [statut.title() for statut, _ in prestations_par_statut]
    repartition_data = [count for _, count in prestations_par_statut]
    
    stats = {
        'prestations_periode': prestations_periode,
        'revenus_estimes': revenus_estimes,
        'materiel_utilise': materiel_utilise,
        'djs_actifs': djs_actifs,
        'pourcentage_prestations': pourcentage_prestations,
        'pourcentage_revenus': pourcentage_revenus,
        'pourcentage_materiel': pourcentage_materiel,
        'pourcentage_djs': pourcentage_djs,
        'prestations_periode_precedente': prestations_periode_precedente,
        'revenus_periode_precedente': revenus_periode_precedente,
        'materiel_utilise_precedente': materiel_utilise_precedente,
        'djs_actifs_precedente': djs_actifs_precedente
    }
    
    return render_template('rapports_avances.html',
                         stats=stats,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         prestations_labels=prestations_labels,
                         prestations_data=prestations_data,
                         repartition_labels=repartition_labels,
                         repartition_data=repartition_data,
                         current_user=get_current_user())

@app.route('/materiels/<int:materiel_id>/calendrier')
@login_required
def materiel_calendrier(materiel_id):
    """Calendrier d'un matériel spécifique"""
    materiel = get_or_404(Materiel, materiel_id)
    
    # Récupérer les prestations qui utilisent ce matériel
    prestations = Prestation.query.join(MaterielPresta).filter(
        MaterielPresta.materiel_id == materiel_id,
        Prestation.statut.in_(['planifiee', 'confirmee', 'terminee'])
    ).order_by(Prestation.date_debut, Prestation.heure_debut).all()
    
    # Organiser les prestations par date
    prestations_par_date = {}
    for prestation in prestations:
        date_key = prestation.date_debut.strftime('%Y-%m-%d')
        if date_key not in prestations_par_date:
            prestations_par_date[date_key] = []
        prestations_par_date[date_key].append(prestation)
    
    return render_template('materiel_calendrier.html', 
                         materiel=materiel, 
                         prestations_par_date=prestations_par_date,
                         current_user=get_current_user())

@app.route('/materiels/update-status')
@login_required
@role_required(['admin', 'manager'])
def update_all_materiel_status():
    """Met à jour le statut de tous les matériels (admin/manager uniquement)"""
    materiels = Materiel.query.all()
    for materiel in materiels:
        update_materiel_status(materiel.id, commit=False)
    db.session.commit()
    
    flash('Statuts des matériels mis à jour', 'success')
    return redirect(url_for('materiels'))

@app.route('/prestations')
@login_required
def prestations():
    """Liste des prestations"""
    page = request.args.get('page', 1, type=int)
    statut = (request.args.get('statut') or '').strip()
    date_from_str = request.args.get('date_from') or ''
    date_to_str = request.args.get('date_to') or ''
    date_from = None
    date_to = None
    try:
        if date_from_str:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        date_from = None
    try:
        if date_to_str:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        date_to = None
    current_user = get_current_user()
    prestations_query = Prestation.query.options(
        joinedload(Prestation.dj),
        selectinload(Prestation.materiel_assignations).joinedload(MaterielPresta.materiel)
    )
    if statut:
        prestations_query = prestations_query.filter(Prestation.statut == statut)
    if date_from and date_to:
        prestations_query = prestations_query.filter(
            Prestation.date_debut <= date_to,
            Prestation.date_fin >= date_from
        )
    elif date_from:
        prestations_query = prestations_query.filter(Prestation.date_fin >= date_from)
    elif date_to:
        prestations_query = prestations_query.filter(Prestation.date_debut <= date_to)
    if current_user and current_user.role == 'dj':
        dj_profile = DJ.query.filter_by(user_id=current_user.id).first()
        if dj_profile:
            prestations_query = prestations_query.filter(Prestation.dj_id == dj_profile.id)
        else:
            prestations_query = prestations_query.filter(Prestation.id == 0)
    elif current_user and current_user.role == 'technicien':
        prestations_query = prestations_query.filter(Prestation.technicien_id == current_user.id)

    prestations = prestations_query.order_by(Prestation.date_debut.desc()).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    return render_template(
        'prestations.html',
        prestations=prestations,
        filters={
            'statut': statut,
            'date_from': date_from_str,
            'date_to': date_to_str
        }
    )

@app.route('/prestations/<int:prestation_id>')
@login_required
def detail_prestation(prestation_id):
    """Détail d'une prestation"""
    prestation = get_or_404(Prestation, prestation_id)
    current_user = get_current_user()
    if current_user:
        if current_user.role == 'dj':
            dj_profile = DJ.query.filter_by(user_id=current_user.id).first()
            if not dj_profile or prestation.dj_id != dj_profile.id:
                abort(404)
        elif current_user.role == 'technicien':
            if prestation.technicien_id != current_user.id:
                abort(404)
    parametres = ParametresEntreprise.query.first()
    company_coords = None
    if parametres:
        company_coords = get_company_coordinates(parametres)
    if app.config.get('ADDRESS_VALIDATION_ENABLED') and prestation.lieu and (not prestation.lieu_lat or not prestation.lieu_lng):
        try:
            geo, err = geocode_address(prestation.lieu, contact_email=parametres.email if parametres else None)
            if geo:
                prestation.lieu_lat = geo['lat']
                prestation.lieu_lng = geo['lng']
                prestation.lieu_formatted = geo.get('formatted') or prestation.lieu
                prestation.lieu_geocoded_at = utcnow()
                if company_coords:
                    distance_km, distance_source = compute_distance_km(
                        company_coords[0], company_coords[1], geo['lat'], geo['lng']
                    )
                    prestation.distance_km = distance_km
                    prestation.distance_source = distance_source
                    prestation.indemnite_km = compute_indemnite_km(distance_km, parametres)
                db.session.commit()
        except Exception as e:
            logger.warning(f"Impossible de géocoder la mission #{prestation.id}: {e}")
    custom_definitions = get_custom_fields_definitions(parametres)
    custom_values = parse_custom_fields_values(prestation.custom_fields)
    custom_fields_display = build_custom_fields_display(custom_definitions, custom_values)
    return render_template(
        'detail_prestation.html',
        prestation=prestation,
        maps_api_key=get_google_maps_api_key(),
        custom_fields_display=custom_fields_display,
        company_coords=company_coords
    )

@app.route('/prestations/<int:prestation_id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def modifier_prestation(prestation_id):
    """Modifier une prestation"""
    prestation = get_or_404(Prestation, prestation_id)
    parametres = ParametresEntreprise.query.first()
    custom_definitions = get_custom_fields_definitions(parametres)
    custom_values_existing = parse_custom_fields_values(prestation.custom_fields)
    
    if request.method == 'POST':
        try:
            old_lieu = prestation.lieu
            ancien_statut = prestation.statut
            erreurs = []
            date_debut = parse_date_field(request.form.get('date_debut'), "Date de début", erreurs)
            date_fin = parse_date_field(request.form.get('date_fin'), "Date de fin", erreurs)
            heure_debut = parse_time_field(request.form.get('heure_debut') or '20:00', "Heure de début", erreurs)
            heure_fin = parse_time_field(request.form.get('heure_fin') or '02:00', "Heure de fin", erreurs)

            client = normalize_whitespace(request.form.get('client', ''))
            lieu = normalize_whitespace(request.form.get('lieu', ''))
            validate_required_field(client, "Client", erreurs)
            validate_required_field(lieu, "Lieu", erreurs)

            dj_id = None
            dj_id_raw = request.form.get('dj_id')
            if not dj_id_raw:
                erreurs.append("DJ est requis")
            else:
                try:
                    dj_id = int(dj_id_raw)
                    if not db.session.get(DJ, dj_id):
                        erreurs.append("DJ sélectionné introuvable")
                except (TypeError, ValueError):
                    erreurs.append("DJ invalide")

            technicien_id = None
            technicien_raw = request.form.get('technicien_id')
            if technicien_raw:
                try:
                    technicien_id = int(technicien_raw)
                    technicien = db.session.get(User, technicien_id)
                    if not technicien or technicien.role != 'technicien':
                        erreurs.append("Prestataire technique sélectionné introuvable")
                        technicien_id = None
                except (TypeError, ValueError):
                    erreurs.append("Prestataire technique invalide")

            client_telephone = normalize_telephone(request.form.get('client_telephone', prestation.client_telephone or ''))
            client_email = normalize_email(request.form.get('client_email', prestation.client_email or ''))
            if client_email:
                valide, message = valider_email(client_email)
                if not valide:
                    erreurs.append(message)
            if client_telephone:
                valide, message = valider_telephone(client_telephone)
                if not valide:
                    erreurs.append(message)

            validate_date_time_range(date_debut, date_fin, heure_debut, heure_fin, erreurs)

            # Disponibilite des prestataires
            dj_ok, dj_msg = check_staff_availability('dj', dj_id, date_debut, date_fin, heure_debut, heure_fin, prestation.id)
            if not dj_ok:
                erreurs.append(dj_msg)
            tech_ok, tech_msg = check_staff_availability('technicien', technicien_id, date_debut, date_fin, heure_debut, heure_fin, prestation.id)
            if not tech_ok:
                erreurs.append(tech_msg)

            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('modifier_prestation', prestation_id=prestation.id))

            # Validation adresse + géocodage si nécessaire
            geo = None
            if app.config.get('ADDRESS_VALIDATION_ENABLED'):
                needs_geocode = (lieu != old_lieu) or not prestation.lieu_lat or not prestation.lieu_lng
                if needs_geocode:
                    geo, err = geocode_address(lieu, contact_email=parametres.email if parametres else None)
                    if not geo:
                        flash(f"Adresse introuvable sur la carte : {err}", 'error')
                        return redirect(url_for('modifier_prestation', prestation_id=prestation.id))
                else:
                    geo = {
                        'lat': prestation.lieu_lat,
                        'lng': prestation.lieu_lng,
                        'formatted': prestation.lieu_formatted or lieu
                    }
            else:
                if lieu != old_lieu:
                    prestation.lieu_lat = None
                    prestation.lieu_lng = None
                    prestation.lieu_formatted = None
                    prestation.lieu_geocoded_at = None
                    prestation.distance_km = None
                    prestation.distance_source = None
                    prestation.indemnite_km = None

            distance_km = None
            distance_source = None
            indemnite_km = None
            if geo:
                company_coords = get_company_coordinates(parametres)
                if company_coords:
                    distance_km, distance_source = compute_distance_km(
                        company_coords[0], company_coords[1], geo['lat'], geo['lng']
                    )
                    indemnite_km = compute_indemnite_km(distance_km, parametres)

            prestation.date_debut = date_debut
            prestation.date_fin = date_fin
            prestation.heure_debut = heure_debut
            prestation.heure_fin = heure_fin
            prestation.client = client
            prestation.client_telephone = client_telephone
            prestation.client_email = client_email
            prestation.lieu = lieu
            if geo:
                prestation.lieu_lat = geo['lat']
                prestation.lieu_lng = geo['lng']
                prestation.lieu_formatted = geo['formatted']
                prestation.lieu_geocoded_at = utcnow()
                prestation.distance_km = distance_km
                prestation.distance_source = distance_source
                prestation.indemnite_km = indemnite_km
            prestation.dj_id = dj_id
            prestation.technicien_id = technicien_id
            prestation.notes = request.form.get('notes', '')
            nouveau_statut = request.form.get('statut', 'planifiee')
            statut_ok, statut_msg = prestation.valider_transition_statut(nouveau_statut)
            if not statut_ok:
                erreurs.append(statut_msg)
            else:
                prestation.statut = nouveau_statut
            send_rating = (ancien_statut != 'terminee' and nouveau_statut == 'terminee')
            custom_values = extract_custom_fields_from_form(custom_definitions, request.form)
            for field in custom_definitions:
                if field.get('required'):
                    key = field.get('key')
                    if key and not custom_values.get(key):
                        erreurs.append(f"{field.get('label', key)} est requis")
            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('modifier_prestation', prestation_id=prestation.id))
            prestation.custom_fields = json.dumps(custom_values, ensure_ascii=False) if custom_values else None
            
            # Gestion des matériels avec vérification des conflits
            nouveaux_materiels_ids = request.form.getlist('materiels')
            materiel_quantites = {}
            for materiel_id in nouveaux_materiels_ids:
                try:
                    materiel_id_int = int(materiel_id)
                except (TypeError, ValueError):
                    erreurs.append("Matériel invalide")
                    continue
                qty_raw = request.form.get(f'quantite_{materiel_id_int}', '1')
                try:
                    quantite = int(qty_raw)
                except (TypeError, ValueError):
                    quantite = 1
                if quantite < 1:
                    quantite = 1
                materiel_quantites[materiel_id_int] = quantite

            if not nouveaux_materiels_ids:
                erreurs.append("Sélectionnez au moins un équipement pour cette mission")

            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('modifier_prestation', prestation_id=prestation.id))

            # Interdire la modification du matériel si mouvements existants ou documents verrouillés
            assignations_existantes = MaterielPresta.query.filter_by(prestation_id=prestation.id).all()
            map_existante = {a.materiel_id: a.quantite for a in assignations_existantes}
            map_nouvelle = {mid: qty for mid, qty in materiel_quantites.items()}
            materiel_change = map_existante != map_nouvelle
            if materiel_change:
                mouvement_existe = MouvementMateriel.query.filter_by(prestation_id=prestation.id).first()
                devis_verrouille = Devis.query.filter_by(prestation_id=prestation.id, est_signe=True).first()
                facture_verrouillee = Facture.query.filter(
                    Facture.prestation_id == prestation.id,
                    Facture.statut.in_({'envoyee', 'payee', 'partiellement_payee', 'annulee'})
                ).first()
                if mouvement_existe or devis_verrouille or facture_verrouillee:
                    flash(
                        "Modification du matériel impossible : des sorties/retours existent ou des documents sont verrouillés.",
                        'error'
                    )
                    return redirect(url_for('modifier_prestation', prestation_id=prestation.id))
            
            # Vérifier les conflits avant d'assigner
            conflits_detectes = []
            for materiel_id_int, quantite in materiel_quantites.items():
                materiel = db.session.get(Materiel, materiel_id_int)
                if not materiel:
                    conflits_detectes.append("Matériel introuvable")
                    continue
                if materiel.statut in {'maintenance', 'hors_service', 'archive'}:
                    conflits_detectes.append(
                        f"{materiel.nom}: matériel en {materiel.statut.replace('_', ' ')}"
                    )
                    continue
                dispo = verifier_disponibilite_materiel(
                    materiel_id=materiel_id_int,
                    quantite_demandee=quantite,
                    date_debut=prestation.date_debut,
                    date_fin=prestation.date_fin,
                    heure_debut=prestation.heure_debut,
                    heure_fin=prestation.heure_fin,
                    exclure_prestation_id=prestation.id
                )
                
                if not dispo.get('disponible'):
                    conflits_detectes.append(
                        f"{materiel.nom}: {quantite} demandé(s), seulement {dispo.get('quantite_disponible', 0)}/{dispo.get('quantite_totale', 0)} disponible(s)"
                    )
            
            # Si des conflits sont détectés, annuler la modification
            if conflits_detectes:
                for conflit in conflits_detectes:
                    flash(conflit, 'error')
                return redirect(url_for('modifier_prestation', prestation_id=prestation.id))
            
            # Supprimer les assignations existantes
            MaterielPresta.query.filter_by(prestation_id=prestation.id).delete()
            
            for materiel_id_int, quantite in materiel_quantites.items():
                materiel = db.session.get(Materiel, materiel_id_int)
                if materiel:
                    # Créer une nouvelle assignation
                    materiel_presta = MaterielPresta(
                        materiel_id=materiel.id,
                        prestation_id=prestation.id,
                        quantite=quantite
                    )
                    db.session.add(materiel_presta)
                    # Ne pas changer le statut ici, il sera géré dynamiquement
            
            db.session.commit()

            if send_rating:
                try:
                    client_email, client_nom = _resolve_client_contact(prestation)
                    if client_email:
                        rating, _ = _create_or_get_rating_request(prestation, client_email, client_nom)
                        db.session.commit()
                        _send_rating_email(prestation, rating, request.host_url)
                except Exception as e:
                    logger.warning(f"Envoi notation échoué: {e}")

            # Mettre à jour devis/factures non verrouillés après changement matériel
            if materiel_change:
                sync_documents_for_prestation(prestation.id)
            
            flash('Prestation modifiée avec succès !', 'success')
            return redirect(url_for('prestations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    djs = DJ.query.all()
    
    # Filtrer les matériels disponibles pour la date/heure de la prestation
    materiels_disponibles = []
    materiels_en_maintenance = Materiel.query.filter_by(statut='maintenance').all()
    materiels_autres = Materiel.query.filter(~Materiel.statut.in_(['maintenance', 'archive'])).all()
    
    for materiel in materiels_autres:
        # Vérifier la disponibilité pour la date/heure de la prestation
        disponible, message = check_materiel_availability(
            materiel.id, 
            prestation.date_debut, 
            prestation.date_fin, 
            prestation.heure_debut, 
            prestation.heure_fin,
            prestation.id  # Exclure la prestation actuelle
        )
        
        if disponible or materiel in prestation.materiels:
            # Inclure les matériels disponibles ET ceux déjà assignés à cette prestation
            materiels_disponibles.append(materiel)
    
    # Ajouter les matériels en maintenance pour information
    materiels_disponibles.extend(materiels_en_maintenance)

    # Toujours inclure les matériels déjà assignés (même archivés) pour éviter les pertes de sélection
    materiels_assignes = Materiel.query.join(MaterielPresta).filter(
        MaterielPresta.prestation_id == prestation.id
    ).all()
    for materiel in materiels_assignes:
        if materiel not in materiels_disponibles:
            materiels_disponibles.append(materiel)
    
    assignations = MaterielPresta.query.filter_by(prestation_id=prestation.id).all()
    prestation_materiel_ids = [assignation.materiel_id for assignation in assignations]
    prestation_materiel_quantities = {
        assignation.materiel_id: assignation.quantite for assignation in assignations
    }
    return render_template(
        'modifier_prestation.html',
        prestation=prestation,
        djs=djs,
        techniciens=techniciens,
        materiels=materiels_disponibles,
        custom_fields_definitions=custom_definitions,
        custom_fields_values=custom_values_existing,
        prestation_materiel_ids=prestation_materiel_ids,
        prestation_materiel_quantities=prestation_materiel_quantities
    )

@app.route('/prestations/<int:prestation_id>/annuler', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def annuler_prestation(prestation_id):
    """Annuler une prestation (garde l'historique, supprime les documents associés)"""
    prestation = get_or_404(Prestation, prestation_id)
    
    try:
        logger.info(f"🚫 Début de l'annulation de la prestation {prestation.id}")
        
        # 1. Récupérer les infos avant modification
        client_email = None
        dj_email = None
        
        # Email du client (depuis le devis/facture)
        devis_lies = Devis.query.filter_by(prestation_id=prestation.id).all()
        if devis_lies:
            client_email = devis_lies[0].client_email
        
        # Email du DJ
        if prestation.dj_id:
            dj = db.session.get(DJ, prestation.dj_id)
            if dj and dj.user_id:
                dj_user = db.session.get(User, dj.user_id)
                if dj_user:
                    dj_email = dj_user.email
        
        # 2. Annuler les DEVIS liés (sans suppression)
        devis_count = 0
        devis_verrouilles = 0
        for devis in devis_lies:
            if devis.est_signe:
                devis_verrouilles += 1
                continue
            devis.statut = 'annule'
            devis.date_annulation = utcnow()
            devis_count += 1
        logger.info(f"   ✓ {devis_count} devis annulés (verrouillés: {devis_verrouilles})")
        
        # 3. Annuler les FACTURES liées (sans suppression)
        factures_liees = Facture.query.filter_by(prestation_id=prestation.id).all()
        factures_count = 0
        factures_verrouillees = 0
        for facture in factures_liees:
            if facture.statut in ['payee', 'partiellement_payee']:
                factures_verrouillees += 1
                continue
            facture.statut = 'annulee'
            facture.date_annulation = utcnow()
            factures_count += 1
        logger.info(f"   ✓ {factures_count} factures annulées (verrouillées: {factures_verrouillees})")
        
        # 4. Libérer les MATÉRIELS assignés (conserver ceux avec retours manquants)
        materiels_assignations = MaterielPresta.query.filter_by(prestation_id=prestation.id).all()
        materiels_count = 0
        materiels_retour_en_attente = 0
        for ma in materiels_assignations:
            if db.session.get(Materiel, ma.materiel_id):
                total_sortie = db.session.query(
                    db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)
                ).filter_by(
                    materiel_id=ma.materiel_id,
                    prestation_id=prestation.id,
                    type_mouvement='sortie'
                ).scalar() or 0
                total_retour = db.session.query(
                    db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)
                ).filter_by(
                    materiel_id=ma.materiel_id,
                    prestation_id=prestation.id,
                    type_mouvement='retour'
                ).scalar() or 0
                if total_sortie > total_retour:
                    materiels_retour_en_attente += 1
                    continue
                materiels_count += 1
            db.session.delete(ma)
        logger.info(f"   ✓ {materiels_count} matériels libérés (retours en attente: {materiels_retour_en_attente})")
        
        # 5. Mettre le statut de la prestation à "annulé"
        prestation.statut = 'annulee'
        
        # 6. Sauvegarder tout
        db.session.commit()
        
        # 7. Envoyer des notifications d'annulation
        try:
            envoyer_notifications_annulation(prestation, client_email, dj_email, devis_count, factures_count)
        except Exception as e:
            logger.error(f"   ⚠️ Erreur envoi notifications : {e}")
        
        logger.info(f"✅ Mission {prestation.id} annulée avec succès")
        message = f"Mission annulée avec succès ! ({devis_count} devis, {factures_count} factures, {materiels_count} équipements libérés)"
        if materiels_retour_en_attente:
            message += f" - {materiels_retour_en_attente} équipement(s) en attente de retour."
        if devis_verrouilles or factures_verrouillees:
            message += " - Certains documents verrouillés n'ont pas été modifiés."
        flash(message, 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erreur lors de l'annulation : {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erreur lors de l\'annulation : {str(e)}', 'error')
    
    return redirect(url_for('detail_prestation', prestation_id=prestation.id))

def envoyer_notifications_annulation(prestation, client_email, dj_email, nb_devis, nb_factures):
    """Envoie des notifications d'annulation à toutes les parties"""
    try:
        from email_service import EmailService
        email_service = EmailService()
        
        parametres = ParametresEntreprise.query.first()
        nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
        
        mission_titre = prestation.client or "Mission"
        if prestation.date_debut and prestation.date_fin and prestation.date_fin != prestation.date_debut:
            date_str = f"{prestation.date_debut.strftime('%d/%m/%Y')} → {prestation.date_fin.strftime('%d/%m/%Y')}"
        else:
            date_str = prestation.date_debut.strftime('%d/%m/%Y') if prestation.date_debut else "Non spécifiée"
        heure_str = ""
        if prestation.heure_debut and prestation.heure_fin:
            heure_str = f"{prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}"

        # Email au CLIENT
        if client_email:
            subject_client = f"Annulation de mission - {mission_titre}"
            body_client = f"""Bonjour,

Nous vous informons que la mission suivante a été annulée :

MISSION :
• Titre : {mission_titre}
• Date : {date_str}
• Heure : {heure_str or 'Non spécifiée'}
• Lieu : {prestation.lieu or 'Non spécifié'}

Les documents associés ({nb_devis} devis, {nb_factures} factures) ont été annulés.

Si vous avez des questions, n'hésitez pas à nous contacter.

Cordialement,
L'équipe {nom_entreprise}
"""
            email_service.send_email(client_email, subject_client, body_client)
            logger.info(f"   ✓ Email envoyé au client : {client_email}")
        
        # Email au prestataire
        if dj_email:
            subject_dj = f"Mission annulée - {mission_titre}"
            body_dj = f"""Bonjour,

La mission suivante a été annulée :

• Titre : {mission_titre}
• Date : {date_str}
• Heure : {heure_str or 'Non spécifiée'}
• Lieu : {prestation.lieu or 'Non spécifié'}

Documents annulés : {nb_devis} devis, {nb_factures} factures

Cordialement,
{nom_entreprise}
"""
            email_service.send_email(dj_email, subject_dj, body_dj)
            logger.info(f"   ✓ Email envoyé au DJ : {dj_email}")
        
        # Email aux MANAGERS
        managers = User.query.filter(User.role.in_(['admin', 'manager'])).all()
        if managers:
            subject_managers = f"Mission annulée - {mission_titre}"
            body_managers = f"""Une mission a été annulée dans le système.

MISSION :
• ID : {prestation.id}
• Titre : {mission_titre}
• Date : {date_str}

SUPPRESSION EN CASCADE :
• Devis annulés : {nb_devis}
• Factures annulées : {nb_factures}
• Matériels libérés

Connectez-vous pour plus de détails.
"""
            for manager in managers:
                if manager.email:
                    email_service.send_email(manager.email, subject_managers, body_managers)
            logger.info(f"   ✓ Email envoyé à {len(managers)} managers")
    
    except Exception as e:
        logger.error(f"Erreur envoi notifications annulation : {e}")

@app.route('/prestations/<int:prestation_id>/supprimer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def supprimer_prestation(prestation_id):
    """Supprimer une prestation"""
    prestation = get_or_404(Prestation, prestation_id)

    devis_lies = Devis.query.filter_by(prestation_id=prestation.id).all()
    factures_liees = Facture.query.filter_by(prestation_id=prestation.id).all()
    if devis_lies or factures_liees:
        flash("Impossible de supprimer une mission avec des devis/factures. Utilisez l'annulation.", 'error')
        return redirect(url_for('detail_prestation', prestation_id=prestation.id))
    
    try:
        # Les matériels sont automatiquement libérés via cascade delete de MaterielPresta
        # Plus besoin de changer le statut !
        
        db.session.delete(prestation)
        db.session.commit()
        flash('Prestation supprimée avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
    
    return redirect(url_for('prestations'))

@app.route('/prestations/nouvelle', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def nouvelle_prestation():
    """Créer une nouvelle prestation"""
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            erreurs = []
            parametres = ParametresEntreprise.query.first()
            custom_definitions = get_custom_fields_definitions(parametres)
            date_debut = parse_date_field(request.form.get('date_debut'), "Date de début", erreurs)
            date_fin = parse_date_field(request.form.get('date_fin'), "Date de fin", erreurs)
            heure_debut = parse_time_field(request.form.get('heure_debut') or '20:00', "Heure de début", erreurs)
            heure_fin = parse_time_field(request.form.get('heure_fin') or '02:00', "Heure de fin", erreurs)

            client = normalize_whitespace(request.form.get('client', ''))
            lieu = normalize_whitespace(request.form.get('lieu', ''))
            validate_required_field(client, "Client", erreurs)
            validate_required_field(lieu, "Lieu", erreurs)

            client_telephone = normalize_telephone(request.form.get('client_telephone', ''))
            client_email = normalize_email(request.form.get('client_email', ''))
            if client_email:
                valide, message = valider_email(client_email)
                if not valide:
                    erreurs.append(message)
            if client_telephone:
                valide, message = valider_telephone(client_telephone)
                if not valide:
                    erreurs.append(message)

            dj_id = None
            dj_id_raw = request.form.get('dj_id')
            if not dj_id_raw:
                erreurs.append("DJ est requis")
            else:
                try:
                    dj_id = int(dj_id_raw)
                    if not db.session.get(DJ, dj_id):
                        erreurs.append("DJ sélectionné introuvable")
                except (TypeError, ValueError):
                    erreurs.append("DJ invalide")

            technicien_id = None
            technicien_raw = request.form.get('technicien_id')
            if technicien_raw:
                try:
                    technicien_id = int(technicien_raw)
                    technicien = db.session.get(User, technicien_id)
                    if not technicien or technicien.role != 'technicien':
                        erreurs.append("Prestataire technique sélectionné introuvable")
                        technicien_id = None
                except (TypeError, ValueError):
                    erreurs.append("Prestataire technique invalide")

            notes = request.form.get('notes', '')
            materiels_ids = request.form.getlist('materiels')
            materiel_quantites = {}
            for materiel_id in materiels_ids:
                try:
                    materiel_id_int = int(materiel_id)
                except (TypeError, ValueError):
                    erreurs.append("Matériel invalide")
                    continue
                qty_raw = request.form.get(f'quantite_{materiel_id_int}', '1')
                try:
                    quantite = int(qty_raw)
                except (TypeError, ValueError):
                    quantite = 1
                if quantite < 1:
                    quantite = 1
                materiel_quantites[materiel_id_int] = quantite

            validate_date_time_range(date_debut, date_fin, heure_debut, heure_fin, erreurs)

            # Disponibilite des prestataires
            dj_ok, dj_msg = check_staff_availability('dj', dj_id, date_debut, date_fin, heure_debut, heure_fin)
            if not dj_ok:
                erreurs.append(dj_msg)
            tech_ok, tech_msg = check_staff_availability('technicien', technicien_id, date_debut, date_fin, heure_debut, heure_fin)
            if not tech_ok:
                erreurs.append(tech_msg)

            custom_values = extract_custom_fields_from_form(custom_definitions, request.form)
            for field in custom_definitions:
                if field.get('required'):
                    key = field.get('key')
                    if key and not custom_values.get(key):
                        erreurs.append(f"{field.get('label', key)} est requis")
            
            if not materiels_ids:
                erreurs.append("Sélectionnez au moins un équipement pour cette mission")

            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('nouvelle_prestation'))

            # Validation adresse + géocodage
            geo = None
            if app.config.get('ADDRESS_VALIDATION_ENABLED'):
                geo, err = geocode_address(lieu, contact_email=parametres.email if parametres else None)
                if not geo:
                    flash(f"Adresse introuvable sur la carte : {err}", 'error')
                    return redirect(url_for('nouvelle_prestation'))

            distance_km = None
            distance_source = None
            indemnite_km = None
            if geo:
                company_coords = get_company_coordinates(parametres)
                if company_coords:
                    distance_km, distance_source = compute_distance_km(
                        company_coords[0], company_coords[1], geo['lat'], geo['lng']
                    )
                    indemnite_km = compute_indemnite_km(distance_km, parametres)
            
            # Vérification de la disponibilité des matériels avec la nouvelle logique
            materiels_disponibles = []
            conflits_detectes = []
            
            for materiel_id_int, quantite in materiel_quantites.items():
                materiel = db.session.get(Materiel, materiel_id_int)
                if materiel:
                    dispo = verifier_disponibilite_materiel(
                        materiel_id=materiel.id,
                        quantite_demandee=quantite,
                        date_debut=date_debut,
                        date_fin=date_fin,
                        heure_debut=heure_debut,
                        heure_fin=heure_fin
                    )

                    if dispo.get('disponible'):
                        materiels_disponibles.append((materiel, quantite))
                    else:
                        conflits_detectes.append(
                            f"{materiel.nom}: {quantite} demandé(s), seulement {dispo.get('quantite_disponible', 0)}/{dispo.get('quantite_totale', 0)} disponible(s)"
                        )
                else:
                    conflits_detectes.append("Matériel introuvable")
            
            # Si des conflits sont détectés, afficher les erreurs
            if conflits_detectes:
                for conflit in conflits_detectes:
                    flash(conflit, 'error')
                return redirect(url_for('nouvelle_prestation'))
            
            # Si aucun matériel disponible, empêcher la création
            if not materiels_disponibles:
                flash('Aucun matériel disponible pour cette période', 'error')
                return redirect(url_for('nouvelle_prestation'))
            
            # Création de la prestation
            client_ref = get_or_create_client(client, client_email, client_telephone)
            prestation = Prestation(
                date_debut=date_debut,
                date_fin=date_fin,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                client=client,
                client_telephone=client_telephone,
                client_email=client_email,
                client_id=client_ref.id if client_ref else None,
                lieu=lieu,
                lieu_lat=geo['lat'] if geo else None,
                lieu_lng=geo['lng'] if geo else None,
                lieu_formatted=geo['formatted'] if geo else None,
                lieu_geocoded_at=utcnow() if geo else None,
                distance_km=distance_km,
                distance_source=distance_source,
                indemnite_km=indemnite_km,
                dj_id=dj_id,
                technicien_id=technicien_id,
                notes=notes,
                custom_fields=json.dumps(custom_values, ensure_ascii=False) if custom_values else None,
                createur_id=session.get('user_id')
            )
            
            db.session.add(prestation)
            db.session.flush()  # Pour obtenir l'ID de la prestation
            
            # Association des matériels et mise à jour de leur statut
            for materiel, quantite in materiels_disponibles:
                # Créer une assignation via MaterielPresta
                materiel_presta = MaterielPresta(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id,
                    quantite=quantite
                )
                db.session.add(materiel_presta)
            
            db.session.commit()
            
            # Les matériels ne changent plus de statut !
            # La disponibilité est gérée via MaterielPresta uniquement
            db.session.commit()
            
             # Envoi de notification de confirmation au client
             # try:
             #     if prestation.client_email:
             #         notification_system.send_prestation_confirmation(prestation)
             # except Exception as e:
             #     logger.error(f'Erreur lors de l\'envoi de la confirmation client : {e}')
            
            flash('Prestation créée avec succès !', 'success')
            return redirect(url_for('prestations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création de la prestation : {str(e)}', 'error')
            return redirect(url_for('nouvelle_prestation'))
    
    # GET - Affichage du formulaire
    djs = DJ.query.all()
    techniciens = User.query.filter_by(role='technicien', actif=True).all()
    parametres = ParametresEntreprise.query.first()
    custom_fields_definitions = get_custom_fields_definitions(parametres)
    return render_template(
        'nouvelle_prestation.html',
        djs=djs,
        techniciens=techniciens,
        custom_fields_definitions=custom_fields_definitions
    )

@app.route('/materiels')
def materiels():
    """Liste du matériel avec consultation par date/heure"""
    # Récupérer les paramètres de date/heure
    date_consultation = request.args.get('date_consultation')
    heure_debut_consultation = request.args.get('heure_debut_consultation')
    heure_fin_consultation = request.args.get('heure_fin_consultation')

    local_id = request.args.get('local_id', type=int)
    statut = request.args.get('statut', '')
    
    query = Materiel.query.options(joinedload(Materiel.local))
    if statut != 'archive':
        query = query.filter(Materiel.statut != 'archive')
    if local_id:
        query = query.filter_by(local_id=local_id)
    
    materiels = query.all()
    
    # Si une date est spécifiée, calculer les statuts pour cette date/heure
    if date_consultation and heure_debut_consultation and heure_fin_consultation:
        try:
            date_consultation_dt = datetime.strptime(date_consultation, '%Y-%m-%d').date()
            heure_debut_dt = datetime.strptime(heure_debut_consultation, '%H:%M').time()
            heure_fin_dt = datetime.strptime(heure_fin_consultation, '%H:%M').time()
            for materiel in materiels:
                materiel.statut_consultation = get_materiel_status_at_time(
                    materiel.id, date_consultation_dt, heure_debut_dt, heure_fin_dt
                )
            if statut:
                materiels = [m for m in materiels if (m.statut_consultation or m.statut) == statut]
        except ValueError:
            for materiel in materiels:
                materiel.statut_consultation = materiel.statut
            if statut:
                materiels = [m for m in materiels if m.statut == statut]
    else:
        if statut:
            materiels = [m for m in materiels if m.statut == statut]
        for materiel in materiels:
            materiel.statut_consultation = materiel.statut

    locals = Local.query.options(joinedload(Local.materiels)).all()
    return render_template('materiels.html', materiels=materiels, locals=locals, 
                         selected_local=local_id, selected_statut=statut,
                         date_consultation=request.args.get('date_consultation'),
                         heure_debut_consultation=request.args.get('heure_debut_consultation'),
                         heure_fin_consultation=request.args.get('heure_fin_consultation'))

@app.route('/materiels/disponibilites')
@login_required
@role_required(['admin', 'manager'])
def materiels_disponibilites():
    """Écran de monitoring en temps réel de la disponibilité du matériel par local"""
    return render_template('materiels_disponibilites.html')

@app.route('/api/materiels/disponibilites')
@login_required
@role_required(['admin', 'manager'])
def api_materiels_disponibilites():
    """
    API pour récupérer l'état de disponibilité du matériel en temps réel
    Retourne pour chaque local : disponible / en prestation / maintenance
    """
    try:
        locaux = Local.query.all()
        resultats = []
        
        # Récupérer toutes les prestations actives (filtrées ensuite par fenêtre logistique)
        prestations_actives = Prestation.query.filter(
            Prestation.statut.in_(['planifiee', 'confirmee', 'en_cours'])
        ).all()
        
        # Créer un dictionnaire materiel_id -> quantité en prestation
        materiel_en_prestation = {}
        now_dt = datetime.now()
        sortie_avant_h, retour_apres_h = _get_materiel_logistique_buffers()
        for prestation in prestations_actives:
            start_dt, end_dt = _build_datetime_range(
                prestation.date_debut,
                prestation.date_fin,
                prestation.heure_debut or time(0, 0),
                prestation.heure_fin or time(23, 59)
            )
            if not start_dt or not end_dt:
                continue
            window_start = start_dt - timedelta(hours=sortie_avant_h)
            window_end = end_dt + timedelta(hours=retour_apres_h)
            if not (window_start <= now_dt <= window_end):
                continue
            materiels_presta = MaterielPresta.query.filter_by(prestation_id=prestation.id).all()
            for mp in materiels_presta:
                if mp.materiel_id not in materiel_en_prestation:
                    materiel_en_prestation[mp.materiel_id] = 0
                materiel_en_prestation[mp.materiel_id] += mp.quantite

        # Ajouter les réservations bloquantes (filtrées par fenêtre logistique)
        reservations_actives = ReservationClient.query.filter(
            ReservationClient.statut.in_(list(RESERVATION_STATUTS_BLOQUANTS))
        ).all()
        for reservation in reservations_actives:
            if not reservation.date_souhaitee:
                continue
            date_fin_res, heure_fin_res = compute_reservation_end(
                reservation.date_souhaitee,
                reservation.heure_souhaitee,
                reservation.duree_heures
            )
            start_dt, end_dt = _build_datetime_range(
                reservation.date_souhaitee,
                date_fin_res,
                reservation.heure_souhaitee or time(0, 0),
                heure_fin_res or time(23, 59)
            )
            if not start_dt or not end_dt:
                continue
            window_start = start_dt - timedelta(hours=sortie_avant_h)
            window_end = end_dt + timedelta(hours=retour_apres_h)
            if not (window_start <= now_dt <= window_end):
                continue
            materiels_resa = MaterielPresta.query.filter_by(reservation_id=reservation.id).all()
            for mp in materiels_resa:
                if mp.materiel_id not in materiel_en_prestation:
                    materiel_en_prestation[mp.materiel_id] = 0
                materiel_en_prestation[mp.materiel_id] += mp.quantite
        
        # Pour chaque local, calculer les dispos
        for local in locaux:
            materiels = Materiel.query.filter_by(local_id=local.id).all()
            
            materiels_data = []
            for materiel in materiels:
                if materiel.statut == 'archive':
                    continue
                quantite_en_prestation = materiel_en_prestation.get(materiel.id, 0)
                quantite_maintenance = materiel.quantite if materiel.statut == 'maintenance' else 0
                quantite_hors_service = materiel.quantite if materiel.statut == 'hors_service' else 0
                
                # Quantité disponible = total - en prestation - maintenance - hors service
                quantite_disponible = max(0, materiel.quantite - quantite_en_prestation - quantite_maintenance - quantite_hors_service)
                
                materiels_data.append({
                    'id': materiel.id,
                    'nom': materiel.nom,
                    'categorie': materiel.categorie,
                    'quantite_totale': materiel.quantite,
                    'disponible': quantite_disponible,
                    'en_prestation': quantite_en_prestation,
                    'maintenance': quantite_maintenance,
                    'hors_service': quantite_hors_service,
                    'statut': materiel.statut
                })
            
            # Trier par catégorie puis par nom (gérer les valeurs nulles)
            materiels_data.sort(key=lambda x: ((x.get('categorie') or ''), (x.get('nom') or '')))
            
            resultats.append({
                'local_id': local.id,
                'local_nom': local.nom,
                'local_adresse': local.adresse or '',
                'materiels': materiels_data,
                'stats': {
                    'total_materiels': len(materiels_data),
                    'total_disponible': sum(m['disponible'] for m in materiels_data),
                    'total_en_prestation': sum(m['en_prestation'] for m in materiels_data),
                    'total_maintenance': sum(m['maintenance'] for m in materiels_data),
                    'total_hors_service': sum(m['hors_service'] for m in materiels_data)
                }
            })
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'locaux': resultats
        })
        
    except Exception as e:
        logger.error(f"Erreur API disponibilités matériel: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/materiels/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def nouveau_materiel():
    """Créer un nouveau matériel"""
    if request.method == 'POST':
        try:
            erreurs = []
            numero_serie = normalize_whitespace(request.form.get('numero_serie', '')) or None
            auto_sn = False
            if not numero_serie:
                numero_serie = _generate_unique_serial()
                auto_sn = True
            if numero_serie:
                existing = Materiel.query.filter_by(numero_serie=numero_serie).first()
                if existing:
                    flash('Ce numéro de série existe déjà. Sélectionnez une action.', 'info')
                    return redirect(url_for('selection_scan_materiel', materiel_id=existing.id))
            quantite_raw = request.form.get('quantite', '')
            try:
                quantite = int(quantite_raw)
            except (TypeError, ValueError):
                erreurs.append("Quantité invalide")
                quantite = 0
            if quantite < 1:
                erreurs.append("La quantité doit être ≥ 1")
            prix_location = parse_float_field(
                request.form.get('prix_location', 0),
                "Prix de location",
                erreurs,
                min_value=0,
                default=0
            )
            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('nouveau_materiel'))
            materiel = Materiel(
                nom=request.form['nom'],
                local_id=int(request.form['local_id']),
                quantite=quantite,
                categorie=request.form.get('categorie', ''),
                statut=request.form.get('statut', 'disponible'),
                prix_location=prix_location,
                numero_serie=numero_serie,
                notes_technicien=request.form.get('notes_technicien', '')
            )
            db.session.add(materiel)
            db.session.commit()
            if auto_sn:
                flash(f'Numéro de série généré automatiquement : {numero_serie}', 'info')
            flash('Matériel créé avec succès !', 'success')
            return redirect(url_for('materiels'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du matériel : {str(e)}', 'error')
            return redirect(url_for('nouveau_materiel'))
    
    locals = Local.query.all()
    return render_template('nouveau_materiel.html', locals=locals)

@app.route('/materiels/<int:materiel_id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def modifier_materiel(materiel_id):
    """Modifier un matériel"""
    materiel = get_or_404(Materiel, materiel_id)
    
    if request.method == 'POST':
        try:
            erreurs = []
            materiel.nom = request.form['nom']
            materiel.local_id = int(request.form['local_id'])
            quantite_raw = request.form.get('quantite', '')
            try:
                quantite = int(quantite_raw)
            except (TypeError, ValueError):
                erreurs.append("Quantité invalide")
                quantite = 0
            if quantite < 1:
                erreurs.append("La quantité doit être ≥ 1")
            prix_location = parse_float_field(
                request.form.get('prix_location', 0),
                "Prix de location",
                erreurs,
                min_value=0,
                default=0
            )
            if erreurs:
                for err in erreurs:
                    flash(err, 'error')
                return redirect(url_for('modifier_materiel', materiel_id=materiel.id))
            materiel.quantite = quantite
            materiel.prix_location = prix_location
            materiel.categorie = request.form.get('categorie', '')
            nouveau_sn = normalize_whitespace(request.form.get('numero_serie', '')) or None
            auto_sn = False
            if not nouveau_sn:
                nouveau_sn = _generate_unique_serial()
                auto_sn = True
            if nouveau_sn and nouveau_sn != materiel.numero_serie:
                existing = Materiel.query.filter_by(numero_serie=nouveau_sn).first()
                if existing and existing.id != materiel.id:
                    flash('Ce numéro de série est déjà assigné à un autre matériel.', 'error')
                    return redirect(url_for('modifier_materiel', materiel_id=materiel.id))
            materiel.numero_serie = nouveau_sn
            materiel.notes_technicien = request.form.get('notes_technicien', '')
            
            # Gestion intelligente du changement de statut
            nouveau_statut = request.form.get('statut', 'disponible')
            if nouveau_statut != materiel.statut:
                if nouveau_statut == 'maintenance':
                    materiel.mettre_en_maintenance()
                    materiel.derniere_maintenance = utcnow()
                elif nouveau_statut == 'disponible' and materiel.statut == 'maintenance':
                    materiel.sortir_de_maintenance()
                else:
                    materiel.statut = nouveau_statut
            
            db.session.commit()
            if auto_sn:
                flash(f'Numéro de série généré automatiquement : {nouveau_sn}', 'info')
            flash('Matériel modifié avec succès !', 'success')
            return redirect(url_for('materiels'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    locals = Local.query.all()
    return render_template('modifier_materiel.html', materiel=materiel, locals=locals)

@app.route('/materiels/<int:materiel_id>/supprimer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def supprimer_materiel(materiel_id):
    """Supprimer un matériel"""
    materiel = get_or_404(Materiel, materiel_id)
    
    try:
        # Vérifier s'il est utilisé dans des prestations actives ou des réservations bloquantes
        active_presta = MaterielPresta.query.join(Prestation).filter(
            MaterielPresta.materiel_id == materiel_id,
            MaterielPresta.prestation_id.isnot(None),
            Prestation.statut.in_(['planifiee', 'confirmee', 'en_cours'])
        ).first()
        active_resa = MaterielPresta.query.join(ReservationClient).filter(
            MaterielPresta.materiel_id == materiel_id,
            MaterielPresta.reservation_id.isnot(None),
            ReservationClient.statut.in_(list(RESERVATION_STATUTS_BLOQUANTS))
        ).first()

        mouvements_existants = MouvementMateriel.query.filter_by(materiel_id=materiel_id).first()
        assignations_existantes = MaterielPresta.query.filter_by(materiel_id=materiel_id).first()

        if active_presta or active_resa:
            flash('Impossible de supprimer ce matériel car il est utilisé dans des missions actives', 'error')
        elif mouvements_existants:
            flash('Impossible de supprimer ce matériel car des mouvements existent. Passez-le en hors service ou archivez-le.', 'error')
        elif assignations_existantes:
            flash('Impossible de supprimer ce matériel car il a été utilisé. Archivez-le ou passez-le en hors service.', 'error')
        else:
            MaterielPresta.query.filter_by(materiel_id=materiel_id).delete()
            db.session.delete(materiel)
            db.session.commit()
            flash('Matériel supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
    
    return redirect(url_for('materiels'))

@app.route('/materiels/<int:materiel_id>/changer-statut', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def changer_statut_materiel(materiel_id):
    """Changer le statut d'un matériel"""
    materiel = get_or_404(Materiel, materiel_id)
    nouveau_statut = request.form.get('statut')
    
    try:
        if nouveau_statut == 'maintenance' and materiel.statut != 'maintenance':
            materiel.statut = 'maintenance'
            materiel.derniere_maintenance = utcnow()
        else:
            materiel.statut = nouveau_statut
        db.session.commit()
        flash(f'Statut du matériel changé en {nouveau_statut}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors du changement de statut : {str(e)}', 'error')
    
    return redirect(url_for('materiels'))

# ==================== ROUTES QR CODE MATÉRIEL ====================

@app.route('/materiels/qrcode/scan/<int:materiel_id>')
@login_required
def scan_materiel(materiel_id):
    """Page d'action après scan QR code"""
    materiel = get_or_404(Materiel, materiel_id)
    prestations_assignees = Prestation.query.join(MaterielPresta).filter(
        MaterielPresta.materiel_id == materiel_id,
        Prestation.statut.in_(['planifiee', 'confirmee', 'en_cours', 'terminee', 'annulee'])
    ).order_by(Prestation.date_debut.desc()).all()

    now_dt = datetime.now()
    sortie_avant_h, _ = _get_materiel_logistique_buffers()
    prestations_sortie = []
    prestations_retour = []
    for p in prestations_assignees:
        start_dt, end_dt = _build_datetime_range(
            p.date_debut,
            p.date_fin,
            p.heure_debut or time(0, 0),
            p.heure_fin or time(23, 59)
        )
        if start_dt and end_dt:
            window_start = start_dt - timedelta(hours=sortie_avant_h)
            if p.statut in ['confirmee', 'en_cours'] and window_start <= now_dt <= end_dt:
                prestations_sortie.append(p)
            if p.statut in ['terminee', 'annulee'] or (end_dt <= now_dt):
                prestations_retour.append(p)

    locaux = Local.query.all()
    
    return render_template('scan_materiel.html', 
                         materiel=materiel,
                         prestations_sortie=prestations_sortie,
                         prestations_retour=prestations_retour,
                         locaux=locaux)

@app.route('/materiels/scan/selection/<int:materiel_id>')
@login_required
def selection_scan_materiel(materiel_id):
    """Page de choix après scan (fiche ou sortie/retour)"""
    materiel = get_or_404(Materiel, materiel_id)
    return render_template('scan_materiel_selection.html', materiel=materiel)

@app.route('/materiels/<int:materiel_id>')
@login_required
def fiche_materiel(materiel_id):
    """Fiche détaillée d'un matériel"""
    materiel = get_or_404(Materiel, materiel_id)
    dernier_mouvement = MouvementMateriel.query.filter_by(
        materiel_id=materiel_id
    ).order_by(MouvementMateriel.date_mouvement.desc()).first()
    return render_template(
        'detail_materiel.html',
        materiel=materiel,
        dernier_mouvement=dernier_mouvement
    )

@app.route('/api/materiels/lookup-serial/<string:serial>')
@login_required
def api_materiel_lookup_serial(serial):
    """Lookup matériel par numéro de série ou code-barres."""
    cleaned = (serial or '').strip()
    materiel = Materiel.query.filter(
        (Materiel.numero_serie == cleaned) | (Materiel.code_barre == cleaned)
    ).first()
    if not materiel:
        return jsonify({'success': False, 'message': 'Not found'}), 404
    return jsonify({
        'success': True,
        'materiel_id': materiel.id,
        'materiel': {
            'id': materiel.id,
            'nom': materiel.nom,
            'categorie': materiel.categorie,
            'statut': materiel.statut,
            'local': materiel.local.nom if materiel.local else None,
            'local_id': materiel.local_id,
            'numero_serie': materiel.numero_serie,
            'code_barre': materiel.code_barre
        }
    })

@app.route('/api/materiel/sortie', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def sortie_materiel_api():
    """API pour enregistrer une sortie de matériel vers une prestation"""
    try:
        data = request.get_json()
        materiel_id = data.get('materiel_id')
        prestation_id = data.get('prestation_id')
        quantite = data.get('quantite', 1)
        try:
            quantite = int(quantite)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Quantité invalide'}), 400
        if quantite <= 0:
            return jsonify({'success': False, 'error': 'Quantité invalide'}), 400
        
        # VALIDATIONS STRICTES
        materiel = db.session.get(Materiel, materiel_id)
        if not materiel:
            return jsonify({'success': False, 'error': 'Matériel introuvable'}), 404
        
        prestation = db.session.get(Prestation, prestation_id)
        if not prestation:
            return jsonify({'success': False, 'error': 'Prestation introuvable'}), 404
        
        current_user = get_current_user()
        if current_user and current_user.role == 'technicien':
            if not prestation.technicien_id or prestation.technicien_id != current_user.id:
                return jsonify({'success': False, 'error': '❌ Vous n’êtes pas assigné à cette prestation'}), 403
        
        # 1. Prestation pas confirmée
        if prestation.statut not in ['confirmee', 'en_cours']:
            return jsonify({'success': False, 'error': f'❌ Prestation pas confirmée (statut: {prestation.statut})'}), 400
        
        # 2. Prestation déjà terminée
        if prestation.statut == 'terminee':
            return jsonify({'success': False, 'error': '❌ Prestation déjà terminée'}), 400
        
        # 3. Prestation en dehors de la fenêtre logistique
        start_dt, end_dt = _build_datetime_range(
            prestation.date_debut,
            prestation.date_fin,
            prestation.heure_debut or time(0, 0),
            prestation.heure_fin or time(23, 59)
        )
        now_dt = datetime.now()
        if not start_dt or not end_dt:
            return jsonify({'success': False, 'error': '❌ Créneau prestation invalide'}), 400
        sortie_avant_h, _ = _get_materiel_logistique_buffers()
        window_start = start_dt - timedelta(hours=sortie_avant_h)
        if now_dt < window_start:
            return jsonify({'success': False, 'error': '❌ Sortie trop tôt (fenêtre logistique)'}), 400
        if now_dt > end_dt:
            return jsonify({'success': False, 'error': '❌ Prestation terminée'}), 400
        
        # 4. Matériel en maintenance/hors service
        if materiel.statut != 'disponible':
            return jsonify({'success': False, 'error': f'❌ Matériel en {materiel.statut}'}), 400
        
        # 5. Quantité disponible
        dispo = verifier_disponibilite_materiel(
            materiel_id=materiel_id,
            quantite_demandee=quantite,
            date_debut=prestation.date_debut,
            date_fin=prestation.date_fin,
            heure_debut=prestation.heure_debut,
            heure_fin=prestation.heure_fin,
            exclure_prestation_id=prestation_id
        )
        
        if not dispo['disponible']:
            return jsonify({'success': False, 'error': f'❌ Seulement {dispo["quantite_disponible"]}/{materiel.quantite} disponible(s)'}), 400
        
        # 6. Doit être assigné à cette prestation
        assignation = MaterielPresta.query.filter_by(
            materiel_id=materiel_id,
            prestation_id=prestation_id
        ).first()
        
        if not assignation:
            return jsonify({'success': False, 'error': '❌ Matériel non assigné à cette prestation'}), 400
        
        total_sortie = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
            materiel_id=materiel_id,
            prestation_id=prestation_id,
            type_mouvement='sortie'
        ).scalar() or 0
        quantite_restante = assignation.quantite - total_sortie
        if quantite_restante <= 0:
            return jsonify({'success': False, 'error': '❌ Tout le matériel est déjà sorti pour cette prestation'}), 400
        if quantite > quantite_restante:
            return jsonify({'success': False, 'error': f'❌ Quantité max restante à sortir: {quantite_restante}'}), 400
        
        # OK : Enregistrer la sortie
        mouvement = MouvementMateriel(
            materiel_id=materiel_id,
            prestation_id=prestation_id,
            type_mouvement='sortie',
            quantite=quantite,
            local_depart_id=materiel.local_id,
            utilisateur_id=session.get('user_id'),
            notes=f"Sortie QR code pour {prestation.client}"
        )
        db.session.add(mouvement)
        db.session.flush()
        total_sortie_check = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
            materiel_id=materiel_id,
            prestation_id=prestation_id,
            type_mouvement='sortie'
        ).scalar() or 0
        if total_sortie_check > assignation.quantite:
            db.session.rollback()
            return jsonify({'success': False, 'error': '❌ Conflit de stock, réessayez'}), 409
        
        db.session.commit()
        
        logger.info(f"✅ Sortie matériel #{materiel_id} ({quantite}x) pour prestation #{prestation_id}")
        
        return jsonify({
            'success': True,
            'message': f'✅ {quantite}x {materiel.nom} sorti(s) pour {prestation.client}'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur sortie matériel: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/materiel/retour', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def retour_materiel_api():
    """API pour enregistrer un retour de matériel vers un local"""
    try:
        data = request.get_json()
        materiel_id = data.get('materiel_id')
        prestation_id = data.get('prestation_id')
        local_retour_id = data.get('local_retour_id')
        quantite = data.get('quantite', 1)
        try:
            quantite = int(quantite)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Quantité invalide'}), 400
        if quantite <= 0:
            return jsonify({'success': False, 'error': 'Quantité invalide'}), 400
        
        # VALIDATIONS STRICTES
        materiel = db.session.get(Materiel, materiel_id)
        if not materiel:
            return jsonify({'success': False, 'error': 'Matériel introuvable'}), 404
        
        prestation = db.session.get(Prestation, prestation_id)
        if not prestation:
            return jsonify({'success': False, 'error': 'Prestation introuvable'}), 404
        
        current_user = get_current_user()
        if current_user and current_user.role == 'technicien':
            if not prestation.technicien_id or prestation.technicien_id != current_user.id:
                return jsonify({'success': False, 'error': '❌ Vous n’êtes pas assigné à cette prestation'}), 403

        local_retour = db.session.get(Local, local_retour_id)
        if not local_retour:
            return jsonify({'success': False, 'error': 'Local introuvable'}), 404
        
        # 7. Prestation pas terminée (statut ou date/heure)
        start_dt, end_dt = _build_datetime_range(
            prestation.date_debut,
            prestation.date_fin,
            prestation.heure_debut or time(0, 0),
            prestation.heure_fin or time(23, 59)
        )
        now_dt = datetime.now()
        if prestation.statut not in ['terminee', 'annulee'] and (not end_dt or now_dt < end_dt):
            return jsonify({'success': False, 'error': f'❌ Prestation pas terminée (statut: {prestation.statut})'}), 400
        
        # 8. Matériel pas dans cette prestation
        mp = MaterielPresta.query.filter_by(
            materiel_id=materiel_id,
            prestation_id=prestation_id
        ).first()
        
        if not mp:
            return jsonify({'success': False, 'error': '❌ Ce matériel n\'est pas assigné à cette prestation'}), 400

        # 9. Quantité retournée > quantité sortie
        total_sortie = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
            materiel_id=materiel_id,
            prestation_id=prestation_id,
            type_mouvement='sortie'
        ).scalar() or 0
        total_retour = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
            materiel_id=materiel_id,
            prestation_id=prestation_id,
            type_mouvement='retour'
        ).scalar() or 0
        quantite_sortie_restante = total_sortie - total_retour
        if quantite_sortie_restante <= 0:
            return jsonify({'success': False, 'error': '❌ Aucun matériel sorti à retourner'}), 400
        if quantite > quantite_sortie_restante:
            return jsonify({'success': False, 'error': f'❌ Impossible de retourner {quantite}x, seulement {quantite_sortie_restante}x sorti(s)'}), 400

        if quantite < quantite_sortie_restante and materiel.local_id and materiel.local_id != local_retour_id:
            return jsonify({'success': False, 'error': '❌ Retour partiel vers un autre local non autorisé'}), 400
        
        # OK : Enregistrer le retour
        mouvement = MouvementMateriel(
            materiel_id=materiel_id,
            prestation_id=prestation_id,
            type_mouvement='retour',
            quantite=quantite,
            local_retour_id=local_retour_id,
            utilisateur_id=session.get('user_id'),
            notes=f"Retour QR code de {prestation.client}"
        )
        db.session.add(mouvement)
        db.session.flush()
        total_retour_check = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
            materiel_id=materiel_id,
            prestation_id=prestation_id,
            type_mouvement='retour'
        ).scalar() or 0
        total_sortie_check = total_sortie
        if total_retour_check > total_sortie:
            db.session.rollback()
            return jsonify({'success': False, 'error': '❌ Conflit de stock, réessayez'}), 409
        
        # Si tout est revenu ET que tout le stock a été déplacé, mettre à jour le local de référence
        all_returned = total_retour_check >= total_sortie_check and total_sortie_check > 0
        if all_returned and total_sortie_check >= materiel.quantite:
            materiel.local_id = local_retour_id
        
        db.session.commit()
        
        logger.info(f"✅ Retour matériel #{materiel_id} ({quantite}x) de prestation #{prestation_id} vers {local_retour.nom}")
        
        return jsonify({
            'success': True,
            'message': f'✅ {quantite}x {materiel.nom} retourné(s) au {local_retour.nom}'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur retour matériel: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def _valider_sortie_materiel(materiel, prestation, quantite):
    if not prestation:
        return "Prestation introuvable"
    if prestation.statut not in ['confirmee', 'en_cours']:
        return f"Prestation pas confirmée (statut: {prestation.statut})"
    if prestation.statut == 'terminee':
        return "Prestation déjà terminée"
    start_dt, end_dt = _build_datetime_range(
        prestation.date_debut,
        prestation.date_fin,
        prestation.heure_debut or time(0, 0),
        prestation.heure_fin or time(23, 59)
    )
    now_dt = datetime.now()
    if not start_dt or not end_dt:
        return "Créneau prestation invalide"
    sortie_avant_h, _ = _get_materiel_logistique_buffers()
    window_start = start_dt - timedelta(hours=sortie_avant_h)
    if now_dt < window_start:
        return "Sortie trop tôt (fenêtre logistique)"
    if now_dt > end_dt:
        return "Prestation terminée"
    if materiel.statut != 'disponible':
        return f"Matériel en {materiel.statut}"
    dispo = verifier_disponibilite_materiel(
        materiel_id=materiel.id,
        quantite_demandee=quantite,
        date_debut=prestation.date_debut,
        date_fin=prestation.date_fin,
        heure_debut=prestation.heure_debut,
        heure_fin=prestation.heure_fin,
        exclure_prestation_id=prestation.id
    )
    if not dispo['disponible']:
        return f"Seulement {dispo['quantite_disponible']}/{materiel.quantite} disponible(s)"
    assignation = MaterielPresta.query.filter_by(
        materiel_id=materiel.id,
        prestation_id=prestation.id
    ).first()
    if not assignation:
        return "Matériel non assigné à cette prestation"
    total_sortie = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
        materiel_id=materiel.id,
        prestation_id=prestation.id,
        type_mouvement='sortie'
    ).scalar() or 0
    quantite_restante = assignation.quantite - total_sortie
    if quantite_restante <= 0:
        return "Tout le matériel est déjà sorti pour cette prestation"
    if quantite > quantite_restante:
        return f"Quantité max restante à sortir: {quantite_restante}"
    return None

def _valider_retour_materiel(materiel, prestation, quantite):
    if not prestation:
        return "Prestation introuvable"
    start_dt, end_dt = _build_datetime_range(
        prestation.date_debut,
        prestation.date_fin,
        prestation.heure_debut or time(0, 0),
        prestation.heure_fin or time(23, 59)
    )
    if prestation.statut not in ['terminee', 'annulee'] and (not end_dt or datetime.now() < end_dt):
        return f"Prestation pas terminée (statut: {prestation.statut})"
    mp = MaterielPresta.query.filter_by(
        materiel_id=materiel.id,
        prestation_id=prestation.id
    ).first()
    if not mp:
        return "Ce matériel n'est pas assigné à cette prestation"
    total_sortie = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
        materiel_id=materiel.id,
        prestation_id=prestation.id,
        type_mouvement='sortie'
    ).scalar() or 0
    total_retour = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
        materiel_id=materiel.id,
        prestation_id=prestation.id,
        type_mouvement='retour'
    ).scalar() or 0
    quantite_sortie_restante = total_sortie - total_retour
    if quantite_sortie_restante <= 0:
        return "Aucun matériel sorti à retourner"
    if quantite > quantite_sortie_restante:
        return f"Impossible de retourner {quantite}x, seulement {quantite_sortie_restante}x sorti(s)"
    return None

@app.route('/api/materiel/validate-movement', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def validate_materiel_movement():
    """Validation temps réel d'un mouvement (sortie/retour) sans modification."""
    try:
        data = request.get_json() or {}
        mode = data.get('mode')
        materiel_id = data.get('materiel_id')
        prestation_id = data.get('prestation_id')
        local_retour_id = data.get('local_retour_id')
        quantite = data.get('quantite', 1)
        try:
            quantite = int(quantite)
        except (TypeError, ValueError):
            return jsonify({'success': True, 'ok': False, 'message': 'Quantité invalide'}), 200
        if quantite <= 0:
            return jsonify({'success': True, 'ok': False, 'message': 'Quantité invalide'}), 200

        if mode not in {'sortie', 'retour'}:
            return jsonify({'success': True, 'ok': False, 'message': 'Mode invalide'}), 200

        materiel = db.session.get(Materiel, materiel_id)
        if not materiel:
            return jsonify({'success': True, 'ok': False, 'message': 'Matériel introuvable'}), 200
        prestation = db.session.get(Prestation, prestation_id)
        if not prestation:
            return jsonify({'success': True, 'ok': False, 'message': 'Prestation introuvable'}), 200

        current_user = get_current_user()
        if current_user and current_user.role == 'technicien':
            if not prestation.technicien_id or prestation.technicien_id != current_user.id:
                return jsonify({'success': True, 'ok': False, 'message': 'Vous n’êtes pas assigné à cette prestation'}), 200

        if mode == 'sortie':
            error = _valider_sortie_materiel(materiel, prestation, quantite)
            if error:
                return jsonify({'success': True, 'ok': False, 'message': error}), 200
            assignation = MaterielPresta.query.filter_by(
                materiel_id=materiel.id,
                prestation_id=prestation.id
            ).first()
            total_sortie = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
                materiel_id=materiel.id,
                prestation_id=prestation.id,
                type_mouvement='sortie'
            ).scalar() or 0
            restante = max(0, (assignation.quantite if assignation else 0) - total_sortie)
            return jsonify({'success': True, 'ok': True, 'message': f'OK · reste {restante} dispo'}), 200

        # retour
        if not local_retour_id:
            return jsonify({'success': True, 'ok': False, 'message': 'Site de retour requis'}), 200
        local_retour = db.session.get(Local, local_retour_id)
        if not local_retour:
            return jsonify({'success': True, 'ok': False, 'message': 'Site de retour introuvable'}), 200
        error = _valider_retour_materiel(materiel, prestation, quantite)
        if error:
            return jsonify({'success': True, 'ok': False, 'message': error}), 200
        total_sortie = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
            materiel_id=materiel.id,
            prestation_id=prestation.id,
            type_mouvement='sortie'
        ).scalar() or 0
        total_retour = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
            materiel_id=materiel.id,
            prestation_id=prestation.id,
            type_mouvement='retour'
        ).scalar() or 0
        quantite_sortie_restante = total_sortie - total_retour
        if quantite < quantite_sortie_restante and materiel.local_id and materiel.local_id != local_retour.id:
            return jsonify({'success': True, 'ok': False, 'message': 'Retour partiel vers un autre local non autorisé'}), 200
        restante = max(0, quantite_sortie_restante)
        return jsonify({'success': True, 'ok': True, 'message': f'OK · reste {restante} à retourner'}), 200

    except Exception as e:
        logger.error(f"Validation mouvement matériel: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _normalize_movement_items(items):
    """Normalise et dé-duplique les items d'un batch matériel."""
    normalized = {}
    results = []
    for item in items:
        materiel_id_raw = item.get('materiel_id')
        try:
            materiel_id = int(materiel_id_raw)
        except (TypeError, ValueError):
            results.append({'materiel_id': materiel_id_raw, 'success': False, 'message': 'Matériel invalide'})
            continue
        try:
            quantite = int(item.get('quantite', 1))
        except (TypeError, ValueError):
            results.append({'materiel_id': materiel_id, 'success': False, 'message': 'Quantité invalide'})
            continue
        if quantite <= 0:
            results.append({'materiel_id': materiel_id, 'success': False, 'message': 'Quantité invalide'})
            continue
        normalized[materiel_id] = normalized.get(materiel_id, 0) + quantite
    return normalized, results

@app.route('/api/materiel/sortie-batch', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def sortie_materiel_batch_api():
    """API batch pour sortie de matériel"""
    try:
        data = request.get_json() or {}
        prestation_id = data.get('prestation_id')
        items = data.get('items') or []
        if not items:
            return jsonify({'success': False, 'error': 'Aucun matériel fourni'}), 400
        normalized_items, results = _normalize_movement_items(items)
        if not normalized_items:
            return jsonify({'success': False, 'error': 'Aucun matériel valide', 'results': results}), 400
        success_count = 0

        with locked_transaction():
            prestation = db.session.get(Prestation, prestation_id)
            if not prestation:
                return jsonify({'success': False, 'error': 'Prestation introuvable'}), 404
            current_user = get_current_user()
            if current_user and current_user.role == 'technicien':
                if not prestation.technicien_id or prestation.technicien_id != current_user.id:
                    return jsonify({'success': False, 'error': '❌ Vous n’êtes pas assigné à cette prestation'}), 403

            for materiel_id, quantite in normalized_items.items():
                materiel = db.session.get(Materiel, materiel_id)
                if not materiel:
                    results.append({'materiel_id': materiel_id, 'success': False, 'message': 'Matériel introuvable'})
                    continue
                error = _valider_sortie_materiel(materiel, prestation, quantite)
                if error:
                    results.append({'materiel_id': materiel.id, 'success': False, 'message': error})
                    continue
                mouvement = MouvementMateriel(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id if prestation else None,
                    type_mouvement='sortie',
                    quantite=quantite,
                    local_depart_id=materiel.local_id,
                    utilisateur_id=session.get('user_id'),
                    notes=f"Sortie batch pour {prestation.client if prestation else ''}"
                )
                db.session.add(mouvement)
                db.session.flush()
                assignation = MaterielPresta.query.filter_by(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id
                ).first()
                total_sortie_check = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id,
                    type_mouvement='sortie'
                ).scalar() or 0
                if assignation and total_sortie_check > assignation.quantite:
                    db.session.rollback()
                    return jsonify({'success': False, 'error': 'Conflit de stock, réessayez'}), 409
                success_count += 1
                results.append({'materiel_id': materiel.id, 'success': True, 'message': f"{quantite}x {materiel.nom} sorti(s)"})

            db.session.commit()
        AuditLog.log_action(
            action='creation',
            entite_type='mouvement',
            entite_id=prestation.id if prestation else None,
            entite_nom=f"Sortie batch {prestation.client if prestation else ''}",
            details={'mode': 'sortie', 'prestation_id': prestation.id if prestation else None, 'items': len(normalized_items), 'success': success_count}
        )
        return jsonify({
            'success': True,
            'success_count': success_count,
            'error_count': len(results) - success_count,
            'results': results
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/materiel/retour-batch', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def retour_materiel_batch_api():
    """API batch pour retour de matériel"""
    try:
        data = request.get_json() or {}
        prestation_id = data.get('prestation_id')
        local_retour_id = data.get('local_retour_id')
        items = data.get('items') or []
        if not items:
            return jsonify({'success': False, 'error': 'Aucun matériel fourni'}), 400
        normalized_items, results = _normalize_movement_items(items)
        if not normalized_items:
            return jsonify({'success': False, 'error': 'Aucun matériel valide', 'results': results}), 400
        success_count = 0

        with locked_transaction():
            prestation = db.session.get(Prestation, prestation_id)
            if not prestation:
                return jsonify({'success': False, 'error': 'Prestation introuvable'}), 404
            current_user = get_current_user()
            if current_user and current_user.role == 'technicien':
                if not prestation.technicien_id or prestation.technicien_id != current_user.id:
                    return jsonify({'success': False, 'error': '❌ Vous n’êtes pas assigné à cette prestation'}), 403
            local_retour = db.session.get(Local, local_retour_id) if local_retour_id else None
            if not local_retour:
                return jsonify({'success': False, 'error': 'Local introuvable'}), 400

            for materiel_id, quantite in normalized_items.items():
                materiel = db.session.get(Materiel, materiel_id)
                if not materiel:
                    results.append({'materiel_id': materiel_id, 'success': False, 'message': 'Matériel introuvable'})
                    continue
                error = _valider_retour_materiel(materiel, prestation, quantite)
                if error:
                    results.append({'materiel_id': materiel.id, 'success': False, 'message': error})
                    continue
                total_sortie = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id,
                    type_mouvement='sortie'
                ).scalar() or 0
                total_retour = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id,
                    type_mouvement='retour'
                ).scalar() or 0
                quantite_sortie_restante = total_sortie - total_retour
                if quantite < quantite_sortie_restante and materiel.local_id and materiel.local_id != local_retour.id:
                    results.append({'materiel_id': materiel.id, 'success': False, 'message': 'Retour partiel vers un autre local non autorisé'})
                    continue
                mouvement = MouvementMateriel(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id if prestation else None,
                    type_mouvement='retour',
                    quantite=quantite,
                    local_retour_id=local_retour.id,
                    utilisateur_id=session.get('user_id'),
                    notes=f"Retour batch de {prestation.client if prestation else ''}"
                )
                db.session.add(mouvement)
                db.session.flush()
                total_sortie_check = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id,
                    type_mouvement='sortie'
                ).scalar() or 0
                total_retour_check = db.session.query(db.func.coalesce(db.func.sum(MouvementMateriel.quantite), 0)).filter_by(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id,
                    type_mouvement='retour'
                ).scalar() or 0
                if total_retour_check > total_sortie_check:
                    db.session.rollback()
                    return jsonify({'success': False, 'error': 'Conflit de stock, réessayez'}), 409
                all_returned = total_retour_check >= total_sortie_check and total_sortie_check > 0
                if all_returned and total_sortie_check >= materiel.quantite:
                    materiel.local_id = local_retour.id
                success_count += 1
                results.append({'materiel_id': materiel.id, 'success': True, 'message': f"{quantite}x {materiel.nom} retourné(s)"})

            db.session.commit()
        AuditLog.log_action(
            action='creation',
            entite_type='mouvement',
            entite_id=prestation.id if prestation else None,
            entite_nom=f"Retour batch {prestation.client if prestation else ''}",
            details={'mode': 'retour', 'prestation_id': prestation.id if prestation else None, 'items': len(normalized_items), 'success': success_count}
        )
        return jsonify({
            'success': True,
            'success_count': success_count,
            'error_count': len(results) - success_count,
            'results': results
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/materiels/qrcode/<int:materiel_id>')
@login_required
def voir_qrcode_materiel(materiel_id):
    """Page pour voir le QR code d'un matériel"""
    materiel = get_or_404(Materiel, materiel_id)
    return render_template('voir_qrcode.html', materiel=materiel)

@app.route('/materiels/qrcode/<int:materiel_id>.png')
@login_required
def qrcode_materiel_image(materiel_id):
    """Génère l'image QR code d'un matériel"""
    try:
        import qrcode
        from io import BytesIO
        
        materiel = get_or_404(Materiel, materiel_id)
        
        # Générer QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(materiel.generer_qr_code_url())
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Sauvegarder en bytes
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return send_file(img_buffer, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Erreur génération QR code: {e}")
        return "Erreur", 500

@app.route('/materiels/qrcode/scanner')
@login_required
@role_required(['admin', 'manager', 'technicien'])
def scanner_qrcode():
    """Page pour scanner un QR code avec la caméra"""
    return render_template('scanner_qrcode.html')

@app.route('/materiels/mouvements')
@login_required
@role_required(['admin', 'manager', 'technicien'])
def materiel_mouvements():
    """Page de scan batch (sortie/retour)"""
    today = date.today()
    now_dt = datetime.now()
    sortie_avant_h, _ = _get_materiel_logistique_buffers()
    date_min = today - timedelta(days=1)
    date_max = today + timedelta(days=1)
    prestations_candidates_actives = Prestation.query.filter(
        Prestation.statut.in_(['confirmee', 'en_cours']),
        Prestation.date_debut <= date_max,
        Prestation.date_fin >= date_min
    ).order_by(Prestation.heure_debut.asc()).all()
    prestations_actives = []
    for p in prestations_candidates_actives:
        start_dt, end_dt = _build_datetime_range(
            p.date_debut,
            p.date_fin,
            p.heure_debut or time(0, 0),
            p.heure_fin or time(23, 59)
        )
        if not start_dt or not end_dt:
            continue
        window_start = start_dt - timedelta(hours=sortie_avant_h)
        if window_start <= now_dt <= end_dt:
            prestations_actives.append(p)

    prestations_candidates = Prestation.query.filter(
        Prestation.date_debut <= today
    ).order_by(Prestation.date_debut.desc()).limit(60).all()
    prestations_terminees = []
    for p in prestations_candidates:
        if p.statut in ['terminee', 'annulee']:
            prestations_terminees.append(p)
            continue
        start_dt, end_dt = _build_datetime_range(
            p.date_debut,
            p.date_fin,
            p.heure_debut or time(0, 0),
            p.heure_fin or time(23, 59)
        )
        if end_dt and end_dt <= now_dt:
            prestations_terminees.append(p)
    prestations_terminees = prestations_terminees[:30]
    locals = Local.query.order_by(Local.nom.asc()).all()
    recent_movements = MouvementMateriel.query.order_by(
        MouvementMateriel.date_mouvement.desc()
    ).limit(10).all()
    return render_template(
        'materiel_mouvements.html',
        prestations_actives=prestations_actives,
        prestations_terminees=prestations_terminees,
        locals=locals,
        recent_movements=recent_movements
    )

@app.route('/api/materiels/list')
@login_required
def api_materiels_list():
    """API pour lister tous les matériels (pour sélection manuelle)"""
    try:
        materiels = Materiel.query.options(joinedload(Materiel.local)).order_by(Materiel.categorie, Materiel.nom).all()
        return jsonify({
            'success': True,
            'materiels': [{
                'id': m.id,
                'nom': m.nom,
                'categorie': m.categorie,
                'local': m.local.nom if m.local else 'N/A',
                'statut': m.statut,
                'numero_serie': m.numero_serie
            } for m in materiels]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/materiels/detail/<int:materiel_id>')
@login_required
def api_materiel_detail(materiel_id):
    """API pour récupérer un matériel (pour scan batch)"""
    materiel = db.session.get(Materiel, materiel_id)
    if not materiel:
        return jsonify({'success': False, 'error': 'Matériel introuvable'}), 404
    return jsonify({
        'success': True,
        'materiel': {
            'id': materiel.id,
            'nom': materiel.nom,
            'categorie': materiel.categorie,
            'statut': materiel.statut,
            'local': materiel.local.nom if materiel.local else None,
            'local_id': materiel.local_id,
            'numero_serie': materiel.numero_serie,
            'code_barre': materiel.code_barre
        }
    })

@app.route('/api/locals/list')
@login_required
def api_locals_list():
    """API pour lister tous les locaux (pour sélection mobile)"""
    try:
        locals = Local.query.order_by(Local.nom).all()
        return jsonify({
            'success': True,
            'locals': [{
                'id': l.id,
                'nom': l.nom
            } for l in locals]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/materiels/create-from-code', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'technicien'])
def api_create_materiel_from_code():
    """Créer un matériel depuis un code-barres/numéro de série"""
    try:
        data = request.get_json() or {}
        code = (data.get('code') or '').strip()
        local_id = data.get('local_id')
        nom = (data.get('nom') or '').strip()
        if not code or not local_id:
            return jsonify({'success': False, 'error': 'Paramètres manquants'}), 400
        existing = Materiel.query.filter(
            (Materiel.numero_serie == code) | (Materiel.code_barre == code)
        ).first()
        if existing:
            return jsonify({'success': True, 'materiel_id': existing.id, 'created': False})
        materiel = Materiel(
            nom=nom or f"Matériel {code}",
            numero_serie=code,
            code_barre=code,
            local_id=int(local_id),
            quantite=1,
            statut='disponible'
        )
        db.session.add(materiel)
        db.session.commit()
        return jsonify({'success': True, 'materiel_id': materiel.id, 'created': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/materiels/qrcode/generer-pdf')
@login_required
@role_required(['admin', 'manager'])
def generer_qrcodes_pdf():
    """Génère un PDF avec tous les QR codes pour impression d'étiquettes"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        import qrcode
        from io import BytesIO
        from reportlab.lib.utils import ImageReader
        
        materiels = Materiel.query.order_by(Materiel.categorie, Materiel.nom).all()
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Position initiale
        x, y = 2*cm, height - 3*cm
        qr_size = 4*cm
        
        for i, materiel in enumerate(materiels):
            # Générer QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(materiel.generer_qr_code_url())
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Sauvegarder en bytes
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Dessiner sur le PDF
            c.drawImage(ImageReader(img_buffer), x, y - qr_size, width=qr_size, height=qr_size)
            c.drawString(x, y - qr_size - 0.5*cm, f"{materiel.nom}")
            c.drawString(x, y - qr_size - 1*cm, f"ID: {materiel.id} | {materiel.categorie}")
            
            # Passer à la colonne suivante
            x += qr_size + 1*cm
            
            # Si fin de ligne, passer à la ligne suivante
            if x > width - qr_size:
                x = 2*cm
                y -= qr_size + 2*cm
            
            # Si fin de page, nouvelle page
            if y < 3*cm:
                c.showPage()
                x, y = 2*cm, height - 3*cm
        
        c.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'qrcodes_materiel_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Erreur génération QR codes: {e}")
        flash(f'Erreur lors de la génération des QR codes : {str(e)}', 'error')
        return redirect(url_for('materiels'))

@app.route('/api/check-materiel-disponibilite/<int:reservation_id>', methods=['GET'])
@login_required
@role_required(['admin', 'manager'])
def check_materiel_disponibilite_reservation(reservation_id):
    """
    Vérifier la disponibilité de TOUS les matériels pour une réservation
    Retourne le statut détaillé de chaque matériel avec gestion des chevauchements horaires
    
    Logique de chevauchement:
    - Deux périodes se chevauchent SI: debut1 < fin2 ET fin1 > debut2
    - Exemple: 14h-18h et 12h-16h → CHEVAUCHENT (12h < 18h ET 16h > 14h)
    """
    try:
        reservation = get_or_404(ReservationClient, reservation_id)
        
        # Calculer la date/heure de fin de la réservation
        from datetime import date
        date_fin_reservation, heure_fin_reservation = compute_reservation_end(
            reservation.date_souhaitee,
            reservation.heure_souhaitee,
            reservation.duree_heures
        )
        
        # Récupérer TOUS les matériels
        tous_materiels = Materiel.query.all()
        
        resultats = []
        
        for materiel in tous_materiels:
            # Vérifier disponibilité avec la fonction existante
            dispo = verifier_disponibilite_materiel(
                materiel_id=materiel.id,
                quantite_demandee=1,  # On vérifie pour 1 unité
                date_debut=reservation.date_souhaitee,
                date_fin=date_fin_reservation,
                heure_debut=reservation.heure_souhaitee,
                heure_fin=heure_fin_reservation,
                exclure_reservation_id=reservation_id  # Exclure cette réservation si déjà assignée
            )
            
            # Construire le résultat pour ce matériel
            resultat = {
                'id': materiel.id,
                'nom': materiel.nom,
                'categorie': materiel.categorie,
                'local': materiel.local.nom if materiel.local else 'N/A',
                'statut_materiel': materiel.statut,  # disponible, maintenance, hors_service
                'quantite_totale': materiel.quantite,
                'quantite_disponible': dispo['quantite_disponible'],
                'quantite_utilisee': dispo['quantite_utilisee'],
                'disponible': dispo['disponible'] and materiel.statut == 'disponible',
                'conflits': []
            }
            
            # Si pas disponible, indiquer pourquoi
            if materiel.statut != 'disponible':
                resultat['raison_indisponibilite'] = f"Matériel en {materiel.statut}"
            elif not dispo['disponible']:
                resultat['raison_indisponibilite'] = f"Seulement {dispo['quantite_disponible']}/{materiel.quantite} disponible(s)"
                
                # Ajouter les détails des conflits (chevauchements horaires)
                for conflit in dispo.get('conflits', []):
                    resultat['conflits'].append({
                        'type': conflit['type'],
                        'nom': conflit['nom'],
                        'date': conflit['date'].strftime('%d/%m/%Y') if isinstance(conflit['date'], date) else str(conflit['date']),
                        'heure': conflit.get('heure', ''),
                        'quantite': conflit['quantite']
                    })
            else:
                resultat['raison_indisponibilite'] = None
            
            resultats.append(resultat)
        
        # Trier par catégorie puis par nom
        resultats.sort(key=lambda x: ((x.get('categorie') or ''), (x.get('nom') or '')))
        
        return jsonify({
            'success': True,
            'reservation': {
                'id': reservation.id,
                'numero': reservation.numero,
                'date': reservation.date_souhaitee.strftime('%d/%m/%Y'),
                'heure_debut': reservation.heure_souhaitee.strftime('%H:%M'),
                'heure_fin': heure_fin_reservation.strftime('%H:%M'),
                'duree': reservation.duree_heures
            },
            'materiels': resultats,
            'total_disponibles': sum(1 for r in resultats if r['disponible']),
            'total_materiels': len(resultats)
        })
        
    except Exception as e:
        logger.error(f"Erreur vérification disponibilité matériel: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/locals')
@login_required
def locals():
    """Liste des locaux"""
    locals = Local.query.all()
    now = datetime.now()
    heure_debut = now.time()
    heure_fin = (now + timedelta(minutes=1)).time()
    if heure_fin < heure_debut:
        heure_fin = time(23, 59, 59)
    for local in locals:
        local.materiels_en_prestation = sum(
            1 for materiel in local.materiels
            if get_materiel_status_at_time(materiel.id, now.date(), heure_debut, heure_fin) in {'occupe', 'partiel'}
        )
    return render_template('locals.html', locals=locals)

@app.route('/locals/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def nouveau_local():
    """Créer un nouveau local"""
    if request.method == 'POST':
        try:
            local = Local(
                nom=request.form['nom'],
                adresse=request.form['adresse']
            )
            db.session.add(local)
            db.session.commit()
            flash('Local créé avec succès !', 'success')
            return redirect(url_for('locals'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du local : {str(e)}', 'error')
            return redirect(url_for('nouveau_local'))
    
    return render_template('nouveau_local.html')

@app.route('/locals/<int:local_id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def modifier_local(local_id):
    """Modifier un local"""
    local = get_or_404(Local, local_id)
    
    if request.method == 'POST':
        try:
            local.nom = request.form['nom']
            local.adresse = request.form['adresse']
            db.session.commit()
            flash('Local modifié avec succès !', 'success')
            return redirect(url_for('locals'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    return render_template('modifier_local.html', local=local)

@app.route('/locals/<int:local_id>/supprimer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def supprimer_local(local_id):
    """Supprimer un local"""
    local = get_or_404(Local, local_id)
    
    try:
        # Vérifier s'il a du matériel
        if local.materiels:
            flash('Impossible de supprimer ce local car il contient du matériel', 'error')
        else:
            db.session.delete(local)
            db.session.commit()
            flash('Local supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
    
    return redirect(url_for('locals'))

@app.route('/local/<int:local_id>/affichage')
@login_required
def affichage_local(local_id):
    """Interface d'affichage pour un local (lecture seule)"""
    local = get_or_404(Local, local_id)
    materiels = Materiel.query.filter_by(local_id=local_id).all()
    now = datetime.now()
    heure_debut = now.time()
    heure_fin = (now + timedelta(minutes=1)).time()
    if heure_fin < heure_debut:
        heure_fin = time(23, 59, 59)
    for materiel in materiels:
        materiel.statut_affichage = get_materiel_status_at_time(
            materiel.id,
            now.date(),
            heure_debut,
            heure_fin
        )
    return render_template('affichage_local.html', local=local, materiels=materiels)

@app.route('/api/materiels/local/<int:local_id>')
@login_required
def api_materiels_local(local_id):
    """API pour récupérer les matériels d'un local (pour rafraîchissement AJAX)"""
    materiels = Materiel.query.filter_by(local_id=local_id).all()
    now = datetime.now()
    heure_debut = now.time()
    heure_fin = (now + timedelta(minutes=1)).time()
    if heure_fin < heure_debut:
        heure_fin = time(23, 59, 59)
    prestations = Prestation.query.join(MaterielPresta).filter(
        MaterielPresta.materiel_id.in_([m.id for m in materiels]),
        Prestation.statut.in_(['planifiee', 'confirmee', 'en_cours'])
    ).all()
    prestation_map = {}
    sortie_avant_h, retour_apres_h = _get_materiel_logistique_buffers()
    for presta in prestations:
        start_dt, end_dt = _build_datetime_range(
            presta.date_debut,
            presta.date_fin,
            presta.heure_debut or time(0, 0),
            presta.heure_fin or time(23, 59)
        )
        if not start_dt or not end_dt:
            continue
        window_start = start_dt - timedelta(hours=sortie_avant_h)
        window_end = end_dt + timedelta(hours=retour_apres_h)
        if not (window_start <= now <= window_end):
            continue
        for mp in presta.materiel_assignations:
            if mp.materiel_id not in prestation_map:
                prestation_map[mp.materiel_id] = presta.client
    return jsonify([{
        'id': m.id,
        'nom': m.nom,
        'categorie': m.categorie,
        'quantite': m.quantite,
        'statut': m.statut,
        'statut_affichage': get_materiel_status_at_time(m.id, now.date(), heure_debut, heure_fin),
        'prestation': prestation_map.get(m.id)
    } for m in materiels])

@app.route('/djs')
@login_required
def djs():
    """Liste des DJs"""
    djs = DJ.query.all()
    return render_template('djs.html', 
                         djs=djs, 
                         today=date.today())

@app.route('/djs/nouveau', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def nouveau_dj():
    """Créer un nouveau DJ"""
    if request.method == 'POST':
        try:
            dj = DJ(
                nom=request.form['nom'],
                contact=request.form.get('contact', ''),
                notes=request.form.get('notes', '')
            )
            db.session.add(dj)
            db.session.commit()
            flash('DJ créé avec succès !', 'success')
            return redirect(url_for('djs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du DJ : {str(e)}', 'error')
            return redirect(url_for('nouveau_dj'))
    
    return render_template('nouveau_dj.html')

@app.route('/djs/<int:dj_id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager'])
def modifier_dj(dj_id):
    """Modifier un DJ"""
    dj = get_or_404(DJ, dj_id)
    
    if request.method == 'POST':
        try:
            dj.nom = request.form['nom']
            dj.contact = request.form.get('contact', '')
            dj.notes = request.form.get('notes', '')
            db.session.commit()
            flash('DJ modifié avec succès !', 'success')
            return redirect(url_for('djs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    return render_template('modifier_dj.html', dj=dj)

@app.route('/djs/<int:dj_id>/supprimer', methods=['POST'])
@login_required
@role_required(['admin', 'manager'])
def supprimer_dj(dj_id):
    """Supprimer un DJ"""
    dj = get_or_404(DJ, dj_id)
    
    try:
        # Vérifier s'il a des prestations
        if dj.prestations:
            flash('Impossible de supprimer ce DJ car il a des prestations associées', 'error')
        else:
            db.session.delete(dj)
            db.session.commit()
            flash('DJ supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
    
    return redirect(url_for('djs'))

@app.route('/djs/<int:dj_id>')
@login_required
def detail_dj(dj_id):
    """Détail d'un DJ"""
    dj = get_or_404(DJ, dj_id)
    prestations = Prestation.query.filter_by(dj_id=dj_id).order_by(Prestation.date_debut.desc()).all()
    rating_avg, rating_count = _get_rating_stats_for_dj(dj_id)
    return render_template('detail_dj.html', dj=dj, prestations=prestations, rating_avg=rating_avg, rating_count=rating_count)

@app.route('/calendrier')
@login_required
def calendrier():
    """Vue calendrier des prestations"""
    from datetime import timedelta
    
    mois = request.args.get('mois', datetime.now().month, type=int)
    annee = request.args.get('annee', datetime.now().year, type=int)
    
    # Prestations du mois
    debut_mois = date(annee, mois, 1)
    if mois == 12:
        fin_mois = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mois = date(annee, mois + 1, 1) - timedelta(days=1)
    
    prestations_query = Prestation.query.filter(
        and_(
            Prestation.date_debut <= fin_mois,
            Prestation.date_fin >= debut_mois
        )
    )
    current_user = get_current_user()
    if current_user and current_user.role == 'dj':
        dj_profile = DJ.query.filter_by(user_id=current_user.id).first()
        if dj_profile:
            prestations_query = prestations_query.filter(Prestation.dj_id == dj_profile.id)
        else:
            prestations_query = prestations_query.filter(Prestation.id == 0)
    elif current_user and current_user.role == 'technicien':
        prestations_query = prestations_query.filter(Prestation.technicien_id == current_user.id)

    prestations = prestations_query.all()
    
    return render_template('calendrier.html', prestations=prestations, 
                         mois=mois, annee=annee, today=date.today(), 
                         timedelta=timedelta)

# Routes d'export et de rapports (version Excel déjà définie plus haut)

# Route export_materiels déjà définie plus haut (version Excel)

@app.route('/rapports')
def rapports():
    """Page des rapports"""
    # Statistiques générales
    stats = {
        'total_prestations': Prestation.query.count(),
        'prestations_ce_mois': Prestation.query.filter(
            Prestation.date_debut >= date.today().replace(day=1)
        ).count(),
        'materiels_disponibles': Materiel.query.filter_by(statut='disponible').count(),
        'materiels_maintenance': Materiel.query.filter_by(statut='maintenance').count(),
        'djs_actifs': DJ.query.count(),
        'locals_actifs': Local.query.count()
    }
    
    # Prestations par statut
    prestations_par_statut = {}
    for statut in ['planifiee', 'confirmee', 'terminee', 'annulee']:
        prestations_par_statut[statut] = Prestation.query.filter_by(statut=statut).count()

    # Évolution des prestations (6 derniers mois)
    today = date.today()
    start_month = date(today.year, today.month, 1)
    month_labels = []
    month_counts = []
    month_index = {}
    mois_noms = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
    for i in range(5, -1, -1):
        month = (start_month.month - 1 - i) % 12 + 1
        year = start_month.year + ((start_month.month - 1 - i) // 12)
        key = f"{year}-{month:02d}"
        month_index[key] = len(month_labels)
        month_labels.append(f"{mois_noms[month - 1]} {year}")
        month_counts.append(0)

    first_key = list(month_index.keys())[0]
    range_start = date(int(first_key.split('-')[0]), int(first_key.split('-')[1]), 1)
    next_month_year = start_month.year + (start_month.month // 12)
    next_month = (start_month.month % 12) + 1
    range_end = date(next_month_year, next_month, 1)

    prestations_range = Prestation.query.filter(
        Prestation.date_debut >= range_start,
        Prestation.date_debut < range_end
    ).all()
    for p in prestations_range:
        key = f"{p.date_debut.year}-{p.date_debut.month:02d}"
        if key in month_index:
            month_counts[month_index[key]] += 1
    
    return render_template('rapports.html', stats=stats, 
                         prestations_par_statut=prestations_par_statut,
                         prestations_labels=month_labels,
                         prestations_counts=month_counts,
                         now=datetime.now())

@app.route('/api/stats')
@login_required
def api_stats():
    """API pour les statistiques en temps réel"""
    stats = {
        'prestations_aujourdhui': Prestation.query.filter(
            Prestation.date_debut <= date.today(),
            Prestation.date_fin >= date.today()
        ).count(),
        'materiels_disponibles': Materiel.query.filter_by(statut='disponible').count(),
        'materiels_en_prestation': sum(
            1 for m in Materiel.query.all()
            if get_materiel_status_at_time(m.id, date.today(), time(0, 0), time(23, 59)) in {'occupe', 'partiel'}
        ),
        'prestations_ce_mois': Prestation.query.filter(
            Prestation.date_debut >= date.today().replace(day=1)
        ).count()
    }
    return jsonify(stats)

@app.route('/recherche')
@login_required
def recherche():
    """Page de recherche globale"""
    query = request.args.get('q', '')
    results = {
        'prestations': [],
        'materiels': [],
        'djs': [],
        'locals': []
    }
    
    if query:
        # Recherche dans les prestations
        prestations = Prestation.query.filter(
            or_(
                Prestation.client.ilike(f'%{query}%'),
                Prestation.lieu.ilike(f'%{query}%'),
                Prestation.notes.ilike(f'%{query}%')
            )
        ).all()
        results['prestations'] = prestations
        
        # Recherche dans le matériel
        materiels = Materiel.query.filter(
            or_(
                Materiel.nom.ilike(f'%{query}%'),
                Materiel.categorie.ilike(f'%{query}%')
            )
        ).all()
        results['materiels'] = materiels
        
        # Recherche dans les DJs
        djs = DJ.query.filter(
            or_(
                DJ.nom.ilike(f'%{query}%'),
                DJ.contact.ilike(f'%{query}%'),
                DJ.notes.ilike(f'%{query}%')
            )
        ).all()
        results['djs'] = djs
        
        # Recherche dans les locaux
        locals = Local.query.filter(
            or_(
                Local.nom.ilike(f'%{query}%'),
                Local.adresse.ilike(f'%{query}%')
            )
        ).all()
        results['locals'] = locals
    
    return render_template('recherche.html', query=query, results=results)

@app.route('/api/materiels/available', methods=['POST'])
@login_required
def api_materiels_available():
    """API pour récupérer le matériel disponible sur une période donnée."""
    data = request.get_json(silent=True) or {}
    date_debut_str = data.get('date_debut')
    date_fin_str = data.get('date_fin')
    heure_debut_str = data.get('heure_debut')
    heure_fin_str = data.get('heure_fin')
    lieu = normalize_whitespace(data.get('lieu', ''))
    exclude_prestation_id = data.get('exclude_prestation_id')
    include_ids_raw = data.get('include_materiel_ids') or []
    try:
        exclude_prestation_id = int(exclude_prestation_id) if exclude_prestation_id else None
    except (TypeError, ValueError):
        exclude_prestation_id = None
    include_ids = set()
    if isinstance(include_ids_raw, list):
        for raw_id in include_ids_raw:
            try:
                include_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue
    elif isinstance(include_ids_raw, str):
        for raw_id in include_ids_raw.split(','):
            raw_id = raw_id.strip()
            if not raw_id:
                continue
            try:
                include_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue

    if not (date_debut_str and date_fin_str and heure_debut_str and heure_fin_str):
        return jsonify({
            'success': False,
            'message': 'Renseignez les dates et horaires pour afficher le matériel disponible.',
            'recommended': [],
            'available': []
        })

    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        heure_debut = datetime.strptime(heure_debut_str, '%H:%M').time()
        heure_fin = datetime.strptime(heure_fin_str, '%H:%M').time()
    except Exception:
        return jsonify({
            'success': False,
            'message': 'Dates ou horaires invalides.',
            'recommended': [],
            'available': []
        })

    parametres = ParametresEntreprise.query.first()
    contact_email = parametres.email if parametres else None

    target_coords = None
    distance_mode = None
    if app.config.get('ADDRESS_VALIDATION_ENABLED'):
        if lieu:
            geo, err = geocode_address(lieu, contact_email=contact_email)
            if geo:
                target_coords = (geo['lat'], geo['lng'])
                distance_mode = 'prestation'
        if not target_coords:
            company_coords = get_company_coordinates(parametres)
            if company_coords:
                target_coords = company_coords
                distance_mode = 'entreprise'

    local_geo_cache = {}

    def get_local_coords(local):
        if not local or not local.adresse:
            return None
        if local.id in local_geo_cache:
            return local_geo_cache[local.id]
        geo, _ = geocode_address(local.adresse, contact_email=contact_email)
        coords = (geo['lat'], geo['lng']) if geo else None
        local_geo_cache[local.id] = coords
        return coords

    available = []
    materiels = Materiel.query.options(joinedload(Materiel.local)).all()
    for materiel in materiels:
        if materiel.statut in ['maintenance', 'hors_service', 'archive'] and materiel.id not in include_ids:
            continue
        dispo = verifier_disponibilite_materiel(
            materiel_id=materiel.id,
            quantite_demandee=1,
            date_debut=date_debut,
            date_fin=date_fin,
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            exclure_prestation_id=exclude_prestation_id
        )
        is_disponible = bool(dispo.get('disponible'))
        if not is_disponible and materiel.id not in include_ids:
            continue

        item = {
            'id': materiel.id,
            'nom': materiel.nom,
            'categorie': materiel.categorie or '',
            'local': materiel.local.nom if materiel.local else '',
            'local_id': materiel.local_id,
            'quantite_disponible': dispo.get('quantite_disponible', materiel.quantite),
            'quantite_totale': dispo.get('quantite_totale', materiel.quantite),
            'statut': materiel.statut,
            'disponible': is_disponible,
            'force_included': (not is_disponible and materiel.id in include_ids)
        }

        if target_coords:
            coords = get_local_coords(materiel.local)
            if coords:
                distance_km, _ = compute_distance_km(
                    coords[0], coords[1], target_coords[0], target_coords[1]
                )
                item['distance_km'] = distance_km

        available.append(item)

    if target_coords:
        available.sort(key=lambda m: (
            m.get('distance_km') is None,
            m.get('distance_km', 0),
            (m.get('categorie') or '').lower(),
            (m.get('nom') or '').lower()
        ))
    else:
        available.sort(key=lambda m: (
            (m.get('categorie') or '').lower(),
            (m.get('nom') or '').lower()
        ))

    available_for_reco = [item for item in available if item.get('disponible')]
    recommended = []
    used_categories = set()
    for item in available_for_reco:
        if len(recommended) >= 6:
            break
        categorie = (item.get('categorie') or 'Autre').strip().lower()
        if categorie not in used_categories:
            recommended.append(item)
            used_categories.add(categorie)

    if len(recommended) < 6:
        recommended_ids = {item['id'] for item in recommended}
        for item in available_for_reco:
            if item['id'] in recommended_ids:
                continue
            recommended.append(item)
            if len(recommended) >= 6:
                break

    return jsonify({
        'success': True,
        'recommended': recommended,
        'available': available,
        'sorted_by_distance': bool(target_coords),
        'distance_mode': distance_mode
    })

@app.route('/api/rapports-data')
@login_required
def api_rapports_data():
    """API pour récupérer les données détaillées des rapports"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = date.today() - timedelta(days=30)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = date.today()
        
        # Récupérer les prestations de la période
        prestations = Prestation.query.filter(
            Prestation.date_debut.between(start_date, end_date)
        ).all()
        
        # Formater les données pour l'API
        prestations_data = []
        for prestation in prestations:
            prestation_data = {
                'id': prestation.id,
                'date_debut': prestation.date_debut.strftime('%d/%m/%Y'),
                'client': prestation.client,
                'lieu': prestation.lieu,
                'statut': prestation.statut,
                'dj_nom': prestation.dj.nom if prestation.dj else 'N/A',
                'materiels': [{'nom': m.nom} for m in prestation.materiels]
            }
            prestations_data.append(prestation_data)
        
        return jsonify({
            'prestations': prestations_data,
            'total': len(prestations_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# @app.route('/export-clients')
# @login_required
# @role_required(['admin', 'manager'])
# def export_clients():
#     """Export des données clients en Excel"""
#     try:
#         # Récupérer toutes les prestations avec les données clients
#         prestations = Prestation.query.filter(
#             or_(
#                 Prestation.client_telephone.isnot(None),
#                 Prestation.client_email.isnot(None)
#             )
#         ).all()
#         
#         # Créer un dictionnaire pour éviter les doublons de clients
#         clients_data = {}
#         
#         for prestation in prestations:
#             client_key = prestation.client.lower().strip()
#             
#             if client_key not in clients_data:
#                 clients_data[client_key] = {
#                     'nom': prestation.client,
#                     'telephone': prestation.client_telephone or '',
#                     'email': prestation.client_email or '',
#                     'premiere_prestation': prestation.date_debut,
#                     'derniere_prestation': prestation.date_debut,
#                     'nombre_prestations': 1,
#                     'lieux': set([prestation.lieu]),
#                     'djs': set([prestation.dj.nom if prestation.dj else 'N/A'])
#                 }
#             else:
#                 # Mettre à jour les données existantes
#                 client_data = clients_data[client_key]
#                 client_data['derniere_prestation'] = max(client_data['derniere_prestation'], prestation.date_debut)
#                 client_data['nombre_prestations'] += 1
#                 client_data['lieux'].add(prestation.lieu)
#                 client_data['djs'].add(prestation.dj.nom if prestation.dj else 'N/A')
#         
#         # Convertir les sets en listes pour l'export
#         for client_data in clients_data.values():
#             client_data['lieux'] = ', '.join(client_data['lieux'])
#             client_data['djs'] = ', '.join(client_data['djs'])
#         
#         # Créer le fichier Excel
#         from excel_export import excel_exporter
#         
#         # Préparer les données pour l'export
#         export_data = []
#         for client_data in clients_data.values():
#             export_data.append({
#                 'Nom du client': client_data['nom'],
#                 'Téléphone': client_data['telephone'],
#                 'Email': client_data['email'],
#                 'Première prestation': client_data['premiere_prestation'].strftime('%d/%m/%Y'),
#                 'Dernière prestation': client_data['derniere_prestation'].strftime('%d/%m/%Y'),
#                 'Nombre de prestations': client_data['nombre_prestations'],
#                 'Lieux': client_data['lieux'],
#                 'DJs': client_data['djs']
#             })
#         
#         # Générer le fichier Excel
#         excel_data = excel_exporter.export_clients_data(export_data)
#         
#         # Créer la réponse
#         from flask import make_response
#         response = make_response(excel_data)
#         response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         response.headers['Content-Disposition'] = f'attachment; filename="donnees_clients_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
#         
#         return response
#         
#     except Exception as e:
#         flash(f'Erreur lors de l\'export des données clients : {str(e)}', 'error')
#         return redirect(url_for('rapports_avances'))

@app.route('/api/recherche')
@login_required
def api_recherche():
    """API de recherche pour autocomplétion"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    results = []
    
    # Recherche dans les prestations
    prestations = Prestation.query.filter(
        Prestation.client.ilike(f'%{query}%')
    ).limit(5).all()
    
    for prestation in prestations:
        results.append({
            'type': 'prestation',
            'id': prestation.id,
            'titre': prestation.client,
            'sous_titre': f"{prestation.lieu} - {prestation.date_debut.strftime('%d/%m/%Y')}",
            'url': f'/prestations/{prestation.id}'
        })
    
    # Recherche dans le matériel
    materiels = Materiel.query.filter(
        Materiel.nom.ilike(f'%{query}%')
    ).limit(5).all()
    
    for materiel in materiels:
        local_nom = materiel.local.nom if materiel.local else 'Non assigné'
        results.append({
            'type': 'materiel',
            'id': materiel.id,
            'titre': materiel.nom,
            'sous_titre': f"{local_nom} - {materiel.statut}",
            'url': f'/materiels/{materiel.id}'
        })
    
    # Recherche dans les DJs
    djs = DJ.query.filter(
        DJ.nom.ilike(f'%{query}%')
    ).limit(5).all()
    
    for dj in djs:
        results.append({
            'type': 'dj',
            'id': dj.id,
            'titre': dj.nom,
            'sous_titre': dj.contact or 'Pas de contact',
            'url': f'/djs/{dj.id}'
        })
    
    return jsonify(results)

@app.route('/restore', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def restore():
    """Restauration de la base de données (admin uniquement)"""
    from backup_manager import backup_manager
    if request.method == 'POST':
        backup_file = request.files.get('backup_file')
        if not backup_file or not backup_file.filename:
            flash('Fichier de sauvegarde invalide', 'error')
            return redirect(url_for('restore'))
        filename = backup_file.filename.lower()
        if not (filename.endswith('.db') or filename.endswith('.db.gz')):
            flash('Fichier de sauvegarde invalide', 'error')
            return redirect(url_for('restore'))
        from werkzeug.utils import secure_filename
        safe_name = secure_filename(backup_file.filename)
        backup_path = os.path.join(backup_manager.backup_dir, safe_name)
        backup_file.save(backup_path)
        result = backup_manager.restore_backup(safe_name)
        if result['success']:
            flash(f"Base de données restaurée: {safe_name}", 'success')
            return redirect(url_for('login'))
        flash(f"Erreur lors de la restauration: {result.get('error')}", 'error')
        return redirect(url_for('restore'))
    
    # Lister les sauvegardes disponibles
    backups = backup_manager.list_backups()
    
    return render_template('restore.html', backups=backups)

@app.route('/notifications')
@login_required
def notifications():
    """Page des notifications"""
    # Notifications système
    notifications = []
    
    # Vérifier les matériels en maintenance depuis longtemps
    from datetime import timedelta
    materiels_maintenance = Materiel.query.filter_by(statut='maintenance').all()
    for materiel in materiels_maintenance:
        # Simuler une date de mise en maintenance (dans un vrai système, on aurait un champ date_maintenance)
        notifications.append({
            'type': 'warning',
            'title': 'Matériel en maintenance',
            'message': f'{materiel.nom} est en maintenance depuis longtemps',
            'date': '2024-01-15'
        })
    
    # Vérifier les prestations sans matériel
    prestations_avec_materiel = db.select(Prestation.id).join(MaterielPresta)
    prestations_sans_materiel = Prestation.query.filter(
        ~Prestation.id.in_(prestations_avec_materiel)
    ).all()
    for prestation in prestations_sans_materiel:
        notifications.append({
            'type': 'info',
            'title': 'Prestation sans matériel',
            'message': f'La prestation "{prestation.client}" n\'a pas de matériel assigné',
            'date': prestation.date_debut.strftime('%Y-%m-%d')
        })
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/api/notifications')
@login_required
def api_notifications():
    """API pour les notifications en temps réel"""
    notifications = []
    
    # Prestations d'aujourd'hui
    prestations_aujourdhui = Prestation.query.filter(
        Prestation.date_debut <= date.today(),
        Prestation.date_fin >= date.today()
    ).count()
    
    if prestations_aujourdhui > 0:
        notifications.append({
            'type': 'info',
            'title': 'Prestations aujourd\'hui',
            'message': f'{prestations_aujourdhui} prestation(s) prévue(s) aujourd\'hui'
        })
    
    # Matériels en maintenance
    materiels_maintenance = Materiel.query.filter_by(statut='maintenance').count()
    if materiels_maintenance > 0:
        notifications.append({
            'type': 'warning',
            'title': 'Matériel en maintenance',
            'message': f'{materiels_maintenance} matériel(s) en maintenance'
        })
    
    return jsonify(notifications)


# Page web pour scanner les codes-barres via la caméra de l'appareil
@app.route('/scanner')
@login_required
@role_required(['admin', 'manager', 'technicien'])
def scanner_page():
    """Affiche une page web permettant de scanner des codes-barres avec la caméra"""
    return render_template('scanner_camera.html')


# Enregistrer le Blueprint mobile

# Enregistrer le Blueprint IA (v3.0)
app.register_blueprint(ai_bp)
logger.info("✅ Blueprint IA enregistré avec succès")

# API scanner (codes-barres)
try:
    from api_scanner import scanner_bp
    app.register_blueprint(scanner_bp)
    logger.info('✅ API scanner enregistré (/api/scan_material)')
except Exception as e:
    logger.warning(f"Impossible d'enregistrer l'API scanner: {e}")

# Initialisation de la base de données
def ensure_materiel_schema():
    """Ajoute les colonnes manquantes sur la table materiels (SQLite)."""
    try:
        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(materiels)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        missing = []
        if 'numero_serie' not in existing_cols:
            missing.append("ALTER TABLE materiels ADD COLUMN numero_serie VARCHAR(128)")
        if 'notes_technicien' not in existing_cols:
            missing.append("ALTER TABLE materiels ADD COLUMN notes_technicien TEXT")
        if 'derniere_maintenance' not in existing_cols:
            missing.append("ALTER TABLE materiels ADD COLUMN derniere_maintenance DATETIME")
        if missing:
            for stmt in missing:
                db.session.execute(db.text(stmt))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de vérifier/mettre à jour le schéma materiels: {e}")
        db.session.rollback()

def ensure_parametres_schema():
    """Ajoute les colonnes manquantes sur la table parametres_entreprise (SQLite)."""
    try:
        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(parametres_entreprise)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        if 'email_signature' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN email_signature TEXT"))
            db.session.commit()
        if 'groq_api_key' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN groq_api_key TEXT"))
            db.session.commit()
        if 'google_maps_api_key' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN google_maps_api_key TEXT"))
            db.session.commit()
        if 'adresse_lat' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN adresse_lat FLOAT"))
            db.session.commit()
        if 'adresse_lng' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN adresse_lng FLOAT"))
            db.session.commit()
        if 'adresse_formatted' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN adresse_formatted VARCHAR(255)"))
            db.session.commit()
        if 'adresse_geocoded_at' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN adresse_geocoded_at DATETIME"))
            db.session.commit()
        if 'distance_gratuite_km' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN distance_gratuite_km FLOAT DEFAULT 30.0"))
            db.session.commit()
        if 'frais_deplacement_km' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN frais_deplacement_km FLOAT DEFAULT 0.5"))
            db.session.commit()
        if 'materiel_sortie_avant_heures' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN materiel_sortie_avant_heures FLOAT DEFAULT 12.0"))
            db.session.commit()
        if 'materiel_retour_apres_heures' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN materiel_retour_apres_heures FLOAT DEFAULT 12.0"))
            db.session.commit()
        if 'stripe_enabled' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN stripe_enabled BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'stripe_public_key' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN stripe_public_key VARCHAR(200)"))
            db.session.commit()
        if 'stripe_secret_key' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN stripe_secret_key VARCHAR(200)"))
            db.session.commit()
        if 'rib_iban' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN rib_iban TEXT"))
            db.session.commit()
        if 'rib_bic' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN rib_bic TEXT"))
            db.session.commit()
        if 'rib_titulaire' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN rib_titulaire TEXT"))
            db.session.commit()
        if 'rib_banque' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN rib_banque TEXT"))
            db.session.commit()
        if 'terminology_profile' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN terminology_profile VARCHAR(30) DEFAULT 'missions'"))
            db.session.commit()
        if 'ui_theme' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN ui_theme VARCHAR(30) DEFAULT 'classic'"))
            db.session.commit()
        if 'ui_density' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN ui_density VARCHAR(30) DEFAULT 'comfortable'"))
            db.session.commit()
        if 'ui_font' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN ui_font VARCHAR(120)"))
            db.session.commit()
        if 'ui_radius' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN ui_radius INTEGER DEFAULT 14"))
            db.session.commit()
        if 'ui_custom_css' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN ui_custom_css TEXT"))
            db.session.commit()
        if 'show_ai_menu' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN show_ai_menu BOOLEAN DEFAULT 1"))
            db.session.commit()
        if 'show_ai_insights' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN show_ai_insights BOOLEAN DEFAULT 1"))
            db.session.commit()
        if 'show_quick_actions' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN show_quick_actions BOOLEAN DEFAULT 1"))
            db.session.commit()
        if 'show_recent_missions' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN show_recent_missions BOOLEAN DEFAULT 1"))
            db.session.commit()
        if 'show_stats_cards' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN show_stats_cards BOOLEAN DEFAULT 1"))
            db.session.commit()
        if 'custom_fields_prestation' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN custom_fields_prestation TEXT"))
            db.session.commit()
        if 'public_api_token' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN public_api_token VARCHAR(200)"))
            db.session.commit()
        if 'signature_entreprise_path' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN signature_entreprise_path VARCHAR(255)"))
            db.session.commit()
        if 'signature_entreprise_enabled' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN signature_entreprise_enabled BOOLEAN DEFAULT 1"))
            db.session.commit()
        if 'forme_juridique' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN forme_juridique VARCHAR(100)"))
            db.session.commit()
        if 'capital_social' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN capital_social VARCHAR(100)"))
            db.session.commit()
        if 'rcs_ville' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN rcs_ville VARCHAR(100)"))
            db.session.commit()
        if 'numero_rcs' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN numero_rcs VARCHAR(100)"))
            db.session.commit()
        if 'penalites_retard' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN penalites_retard VARCHAR(200)"))
            db.session.commit()
        if 'escompte' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN escompte VARCHAR(200)"))
            db.session.commit()
        if 'indemnite_recouvrement' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN indemnite_recouvrement FLOAT DEFAULT 40.0"))
            db.session.commit()
        if 'tva_non_applicable' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN tva_non_applicable BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'taux_tva_defaut' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE parametres_entreprise ADD COLUMN taux_tva_defaut FLOAT DEFAULT 20.0"))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de vérifier/mettre à jour le schéma parametres_entreprise: {e}")
        db.session.rollback()

def ensure_prestations_schema():
    """Ajoute les colonnes manquantes sur la table prestations (SQLite)."""
    try:
        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(prestations)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        missing = []
        if 'lieu_lat' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN lieu_lat FLOAT")
        if 'lieu_lng' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN lieu_lng FLOAT")
        if 'lieu_formatted' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN lieu_formatted VARCHAR(255)")
        if 'lieu_geocoded_at' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN lieu_geocoded_at DATETIME")
        if 'distance_km' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN distance_km FLOAT")
        if 'distance_source' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN distance_source VARCHAR(20)")
        if 'indemnite_km' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN indemnite_km FLOAT")
        if 'technicien_id' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN technicien_id INTEGER")
        if 'client_id' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN client_id INTEGER")
        if 'custom_fields' not in existing_cols:
            missing.append("ALTER TABLE prestations ADD COLUMN custom_fields TEXT")
        if missing:
            for stmt in missing:
                db.session.execute(db.text(stmt))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de vérifier/mettre à jour le schéma prestations: {e}")
        db.session.rollback()

def ensure_devis_schema():
    """Ajoute les colonnes manquantes sur la table devis (SQLite)."""
    try:
        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(devis)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        if 'contenu_html' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN contenu_html TEXT"))
            db.session.commit()
        if 'date_annulation' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN date_annulation DATETIME"))
            db.session.commit()
        if 'client_siren' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN client_siren VARCHAR(20)"))
            db.session.commit()
        if 'client_tva' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN client_tva VARCHAR(30)"))
            db.session.commit()
        if 'client_professionnel' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN client_professionnel BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'client_id' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN client_id INTEGER"))
            db.session.commit()
        if 'adresse_livraison' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN adresse_livraison TEXT"))
            db.session.commit()
        if 'nature_operation' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN nature_operation VARCHAR(120)"))
            db.session.commit()
        if 'tva_sur_debits' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN tva_sur_debits BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'numero_bon_commande' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN numero_bon_commande VARCHAR(100)"))
            db.session.commit()
        if 'tva_incluse' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN tva_incluse BOOLEAN DEFAULT 1"))
            db.session.commit()
        if 'signature_token' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN signature_token VARCHAR(100)"))
            db.session.commit()
        if 'signature_image' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN signature_image TEXT"))
            db.session.commit()
        if 'signature_date' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN signature_date DATETIME"))
            db.session.commit()
        if 'signature_ip' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN signature_ip VARCHAR(50)"))
            db.session.commit()
        if 'est_signe' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN est_signe BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'acompte_requis' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN acompte_requis BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'acompte_pourcentage' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN acompte_pourcentage FLOAT DEFAULT 0.0"))
            db.session.commit()
        if 'acompte_montant' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN acompte_montant FLOAT DEFAULT 0.0"))
            db.session.commit()
        if 'acompte_paye' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN acompte_paye BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'date_paiement_acompte' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN date_paiement_acompte DATETIME"))
            db.session.commit()
        if 'stripe_payment_intent_id' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN stripe_payment_intent_id VARCHAR(200)"))
            db.session.commit()
        if 'stripe_payment_link' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN stripe_payment_link VARCHAR(500)"))
            db.session.commit()
        if 'payment_token' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE devis ADD COLUMN payment_token VARCHAR(64)"))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de vérifier/mettre à jour le schéma devis: {e}")
        db.session.rollback()

def ensure_factures_schema():
    """Ajoute les colonnes manquantes sur la table factures (SQLite)."""
    try:
        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(factures)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        if 'date_annulation' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN date_annulation DATETIME"))
            db.session.commit()
        if 'client_siren' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN client_siren VARCHAR(20)"))
            db.session.commit()
        if 'client_tva' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN client_tva VARCHAR(30)"))
            db.session.commit()
        if 'adresse_livraison' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN adresse_livraison TEXT"))
            db.session.commit()
        if 'nature_operation' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN nature_operation VARCHAR(120)"))
            db.session.commit()
        if 'tva_sur_debits' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN tva_sur_debits BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'numero_bon_commande' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN numero_bon_commande VARCHAR(100)"))
            db.session.commit()
        if 'client_professionnel' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN client_professionnel BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'client_id' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN client_id INTEGER"))
            db.session.commit()
        if 'payment_token' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN payment_token VARCHAR(64)"))
            db.session.commit()
        if 'mode_paiement_souhaite' not in existing_cols:
            db.session.execute(db.text("ALTER TABLE factures ADD COLUMN mode_paiement_souhaite VARCHAR(50)"))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de vérifier/mettre à jour le schéma factures: {e}")
        db.session.rollback()

def ensure_avoirs_schema():
    """Crée la table avoirs si absente (SQLite)."""
    try:
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS avoirs (
                id INTEGER PRIMARY KEY,
                numero VARCHAR(50) NOT NULL UNIQUE,
                facture_id INTEGER,
                createur_id INTEGER,
                date_creation DATETIME,
                date_annulation DATETIME,
                montant_ht FLOAT NOT NULL DEFAULT 0.0,
                taux_tva FLOAT DEFAULT 0.0,
                montant_tva FLOAT DEFAULT 0.0,
                montant_ttc FLOAT NOT NULL DEFAULT 0.0,
                motif TEXT,
                statut VARCHAR(20) DEFAULT 'emis',
                FOREIGN KEY(facture_id) REFERENCES factures(id),
                FOREIGN KEY(createur_id) REFERENCES users(id)
            )
        """))
        db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de créer le schéma avoirs: {e}")
        db.session.rollback()

def ensure_paiements_schema():
    """Crée la table paiements si absente et ajoute les colonnes manquantes (SQLite)."""
    try:
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS paiements (
                id INTEGER PRIMARY KEY,
                numero VARCHAR(50) NOT NULL UNIQUE,
                montant FLOAT NOT NULL,
                devise VARCHAR(10) DEFAULT 'EUR',
                type_paiement VARCHAR(20) NOT NULL,
                mode_paiement VARCHAR(50),
                description TEXT,
                statut VARCHAR(20) DEFAULT 'en_attente',
                date_creation DATETIME,
                date_paiement DATETIME,
                date_expiration DATETIME,
                stripe_payment_intent_id VARCHAR(200),
                stripe_checkout_session_id VARCHAR(200),
                stripe_customer_id VARCHAR(200),
                stripe_payment_method VARCHAR(50),
                stripe_charge_id VARCHAR(200),
                client_nom VARCHAR(100),
                client_email VARCHAR(120),
                client_telephone VARCHAR(20),
                client_ip VARCHAR(50),
                tentatives_paiement INTEGER DEFAULT 0,
                derniere_erreur TEXT,
                payment_metadata TEXT,
                montant_rembourse FLOAT DEFAULT 0.0,
                date_remboursement DATETIME,
                raison_remboursement TEXT,
                facture_id INTEGER,
                devis_id INTEGER,
                createur_id INTEGER,
                FOREIGN KEY(facture_id) REFERENCES factures(id),
                FOREIGN KEY(devis_id) REFERENCES devis(id),
                FOREIGN KEY(createur_id) REFERENCES users(id)
            )
        """))
        db.session.commit()

        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(paiements)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        missing = []
        if 'mode_paiement' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN mode_paiement VARCHAR(50)")
        if 'stripe_checkout_session_id' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN stripe_checkout_session_id VARCHAR(200)")
        if 'stripe_customer_id' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN stripe_customer_id VARCHAR(200)")
        if 'stripe_payment_method' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN stripe_payment_method VARCHAR(50)")
        if 'stripe_charge_id' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN stripe_charge_id VARCHAR(200)")
        if 'payment_metadata' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN payment_metadata TEXT")
        if 'justificatif_path' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN justificatif_path VARCHAR(255)")
        if 'commentaire' not in existing_cols:
            missing.append("ALTER TABLE paiements ADD COLUMN commentaire TEXT")
        if missing:
            for stmt in missing:
                db.session.execute(db.text(stmt))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de créer le schéma paiements: {e}")
        db.session.rollback()

def ensure_clients_schema():
    """Crée la table clients si absente et ajoute les colonnes manquantes (SQLite)."""
    try:
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                nom VARCHAR(150) NOT NULL,
                categories TEXT,
                notes TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        db.session.commit()

        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(clients)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        missing = []
        if 'categories' not in existing_cols:
            missing.append("ALTER TABLE clients ADD COLUMN categories TEXT")
        if 'notes' not in existing_cols:
            missing.append("ALTER TABLE clients ADD COLUMN notes TEXT")
        if 'created_at' not in existing_cols:
            missing.append("ALTER TABLE clients ADD COLUMN created_at DATETIME")
        if 'updated_at' not in existing_cols:
            missing.append("ALTER TABLE clients ADD COLUMN updated_at DATETIME")
        if missing:
            for stmt in missing:
                db.session.execute(db.text(stmt))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de créer le schéma clients: {e}")
        db.session.rollback()

def ensure_client_contacts_schema():
    """Crée la table client_contacts si absente et ajoute les colonnes manquantes (SQLite)."""
    try:
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS client_contacts (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                nom VARCHAR(150),
                email VARCHAR(120),
                telephone VARCHAR(20),
                role VARCHAR(80),
                created_at DATETIME,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
        """))
        db.session.commit()

        existing_cols = set()
        result = db.session.execute(db.text("PRAGMA table_info(client_contacts)"))
        for row in result.fetchall():
            existing_cols.add(row[1])
        missing = []
        if 'role' not in existing_cols:
            missing.append("ALTER TABLE client_contacts ADD COLUMN role VARCHAR(80)")
        if 'created_at' not in existing_cols:
            missing.append("ALTER TABLE client_contacts ADD COLUMN created_at DATETIME")
        if missing:
            for stmt in missing:
                db.session.execute(db.text(stmt))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de créer le schéma client_contacts: {e}")
        db.session.rollback()

def ensure_document_sequences_schema():
    """Crée la table des séquences documents si absente (SQLite)."""
    try:
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS document_sequences (
                id INTEGER PRIMARY KEY,
                prefix VARCHAR(10) NOT NULL,
                year INTEGER NOT NULL,
                last_number INTEGER NOT NULL DEFAULT 0,
                UNIQUE(prefix, year)
            )
        """))
        db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible de créer le schéma document_sequences: {e}")
        db.session.rollback()

def ensure_sync_config():
    """Crée la configuration de synchronisation si absente."""
    try:
        cfg = db.session.get(SyncConfig, 1)
        if not cfg:
            cfg = SyncConfig(
                id=1,
                enabled=app.config.get('SYNC_ENABLED_DEFAULT', False),
                device_id=get_device_id(),
                sync_interval_seconds=app.config.get('SYNC_INTERVAL_DEFAULT', 20)
            )
            db.session.add(cfg)
            db.session.commit()
        else:
            updated = False
            if not cfg.device_id:
                cfg.device_id = get_device_id()
                updated = True
            if not cfg.sync_interval_seconds:
                cfg.sync_interval_seconds = app.config.get('SYNC_INTERVAL_DEFAULT', 20)
                updated = True
            if updated:
                db.session.commit()
    except Exception as e:
        logger.warning(f"Impossible d'initialiser la config sync: {e}")
        db.session.rollback()

def _is_https_url(url):
    return bool(url) and url.lower().startswith('https://')

def _sync_get_access_token(cfg):
    if cfg.access_token:
        if not cfg.token_expires_at or cfg.token_expires_at > utcnow() + timedelta(seconds=60):
            return cfg.access_token
    if not cfg.token_url or not cfg.client_id or not cfg.client_secret:
        return None
    if not _is_https_url(cfg.token_url) and not app.config.get('SYNC_ALLOW_INSECURE'):
        return None
    try:
        data = {
            'grant_type': 'client_credentials',
            'client_id': cfg.client_id,
            'client_secret': cfg.client_secret
        }
        if cfg.scopes:
            data['scope'] = cfg.scopes
        payload = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(
            cfg.token_url,
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_data = json.loads(resp.read().decode('utf-8'))
        cfg.access_token = token_data.get('access_token')
        if token_data.get('refresh_token'):
            cfg.refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in')
        if expires_in:
            cfg.token_expires_at = utcnow() + timedelta(seconds=int(expires_in))
        db.session.commit()
        return cfg.access_token
    except Exception as e:
        logger.warning(f"OAuth2 token error: {e}")
        return None

def _build_sync_payload(changes, device_id):
    items = []
    for change in changes:
        try:
            items.append({
                'change_id': change.id,
                'entity_type': change.entity_type,
                'entity_id': change.entity_id,
                'operation': change.operation,
                'changed_at': change.changed_at.isoformat(),
                'changed_fields': json.loads(change.changed_fields or '[]'),
                'payload': json.loads(change.payload or '{}'),
            })
        except Exception:
            items.append({
                'change_id': change.id,
                'entity_type': change.entity_type,
                'entity_id': change.entity_id,
                'operation': change.operation,
                'changed_at': change.changed_at.isoformat(),
                'changed_fields': [],
                'payload': {}
            })
    return {
        'device_id': device_id,
        'sent_at': utcnow().isoformat(),
        'changes': items
    }

def _sync_push_changes(cfg):
    if not cfg.server_url:
        return 'config_missing'
    if not _is_https_url(cfg.server_url) and not app.config.get('SYNC_ALLOW_INSECURE'):
        return 'insecure_url'
    access_token = _sync_get_access_token(cfg)
    if not access_token:
        return 'auth_missing'

    changes = SyncChangeLog.query.filter_by(status='pending').order_by(SyncChangeLog.id.asc()).limit(200).all()
    if not changes:
        return 'no_changes'

    payload = _build_sync_payload(changes, cfg.device_id or get_device_id())
    endpoint = cfg.server_url.rstrip('/') + '/api/sync/push'
    data = json.dumps(payload, ensure_ascii=True).encode('utf-8')
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'Planify-Sync/1.0'
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        response_data = json.loads(resp.read().decode('utf-8'))

    accepted = set(response_data.get('accepted_ids', []))
    conflicts = response_data.get('conflicts', []) or []
    errors = response_data.get('errors', []) or []

    now = utcnow()
    if accepted:
        SyncChangeLog.query.filter(SyncChangeLog.id.in_(accepted)).update(
            {'status': 'sent', 'sent_at': now}, synchronize_session=False
        )
    for item in conflicts:
        change_id = item.get('change_id')
        if change_id:
            SyncChangeLog.query.filter_by(id=change_id).update(
                {'status': 'conflict', 'error': item.get('message')}, synchronize_session=False
            )
        db.session.add(SyncConflict(
            entity_type=item.get('entity_type', ''),
            entity_id=item.get('entity_id', 0),
            local_change_id=change_id,
            remote_version=str(item.get('remote_version', '')),
            details=json.dumps(item, ensure_ascii=True)
        ))
    for item in errors:
        change_id = item.get('change_id')
        if change_id:
            SyncChangeLog.query.filter_by(id=change_id).update(
                {'status': 'failed', 'error': item.get('message')}, synchronize_session=False
            )
    db.session.commit()
    return 'synced'

def _sync_once():
    cfg = db.session.get(SyncConfig, 1)
    if not cfg:
        ensure_sync_config()
        cfg = db.session.get(SyncConfig, 1)
    if not cfg or not cfg.enabled:
        return 'disabled'
    cfg.last_sync_at = utcnow()
    try:
        status = _sync_push_changes(cfg)
        cfg.last_sync_status = status
        if status in ('synced', 'no_changes'):
            cfg.last_success_at = utcnow()
            cfg.last_sync_error = None
        elif status not in ('config_missing', 'auth_missing', 'insecure_url', 'disabled'):
            cfg.last_sync_error = 'Erreur inconnue'
        db.session.commit()
        return status
    except Exception as e:
        cfg.last_sync_status = 'failed'
        cfg.last_sync_error = str(e)
        db.session.commit()
        logger.warning(f"Sync error: {e}")
        return 'failed'

_sync_thread = None
_sync_stop_event = threading.Event()

def start_sync_service():
    global _sync_thread
    if app.config.get('TESTING'):
        return
    if _sync_thread and _sync_thread.is_alive():
        return
    def _loop():
        while not _sync_stop_event.is_set():
            try:
                with app.app_context():
                    cfg = db.session.get(SyncConfig, 1)
                    if not cfg:
                        ensure_sync_config()
                        cfg = db.session.get(SyncConfig, 1)
                    interval = cfg.sync_interval_seconds if cfg and cfg.sync_interval_seconds else app.config.get('SYNC_INTERVAL_DEFAULT', 20)
                    if cfg and cfg.enabled:
                        _sync_once()
                    _sync_stop_event.wait(interval)
            except Exception as e:
                logger.warning(f"Sync loop error: {e}")
                _sync_stop_event.wait(app.config.get('SYNC_INTERVAL_DEFAULT', 20))
    _sync_stop_event.clear()
    _sync_thread = threading.Thread(target=_loop, daemon=True)
    _sync_thread.start()

def stop_sync_service():
    _sync_stop_event.set()

def init_db():
    """Initialise la base de données sans créer d'utilisateurs par défaut"""
    if not app.config.get('DB_READY'):
        logger.info("DB non sélectionnée, init_db ignoré")
        return
    with app.app_context():
        db.create_all()
        ensure_materiel_schema()
        ensure_parametres_schema()
        ensure_devis_schema()
        ensure_factures_schema()
        ensure_avoirs_schema()
        ensure_paiements_schema()
        ensure_clients_schema()
        ensure_client_contacts_schema()
        ensure_document_sequences_schema()
        ensure_prestations_schema()
        ensure_sync_config()
        logger.info("Tables créées avec succès")
        logger.info("L'application va maintenant afficher la page d'initialisation")
        backfill_clients()
        
        # Ne pas créer d'utilisateurs par défaut - laisser l'initialisation se faire via l'interface
        # L'initialisation se fait maintenant via le système de clé
        logger.info("Système de clé d'initialisation activé")

_sync_started = False

@app.before_request
def _start_sync_on_request():
    global _sync_started
    if _sync_started:
        return None
    if not app.config.get('DB_READY'):
        return None
    if app.config.get('TESTING'):
        return None
    start_sync_service()
    _sync_started = True
    return None

def find_available_port(start_port=5000, max_port=5100):
    """Trouve un port disponible"""
    import socket
    
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    # Si aucun port n'est trouvé, utiliser le port par défaut
    return start_port

@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    """Servir les fichiers uploadés"""
    return send_from_directory('static/uploads', filename)

# ==================== SÉLECTION BASE .PLF ====================

def _sanitize_db_name(name):
    safe = ''.join(ch for ch in name if ch.isalnum() or ch in ('-', '_')).strip()
    return safe or None

def _activate_db(sqlite_path, plf_path):
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_path}"
    app.config['PLF_TEMP_PATH'] = sqlite_path
    app.config['PLF_ACTIVE_PATH'] = plf_path
    app.config['DB_READY'] = True
    app.config['PLF_DIRTY'] = False
    # Rebind SQLAlchemy engine to the new database
    try:
        db.session.remove()
    except Exception:
        pass
    try:
        db.engine.dispose()
    except Exception:
        pass

def _encrypt_active_db(password):
    if not app.config.get('PLF_TEMP_PATH') or not app.config.get('PLF_ACTIVE_PATH'):
        return
    write_plf_from_sqlite(app.config['PLF_TEMP_PATH'], app.config['PLF_ACTIVE_PATH'], password)
    app.config['PLF_DIRTY'] = False

def mark_plf_dirty():
    if app.config.get('DB_READY'):
        app.config['PLF_DIRTY'] = True

_plf_autosave_thread = None
_plf_autosave_stop = threading.Event()
_plf_autosave_lock = threading.Lock()

def start_plf_autosave_service():
    global _plf_autosave_thread
    if _plf_autosave_thread and _plf_autosave_thread.is_alive():
        return
    def _loop():
        while not _plf_autosave_stop.is_set():
            try:
                with app.app_context():
                    if app.config.get('DB_READY') and app.config.get('PLF_DIRTY'):
                        password = app.config.get('PLF_PASSWORD')
                        if password:
                            with _plf_autosave_lock:
                                _encrypt_active_db(password)
                    interval = app.config.get('PLF_AUTOSAVE_SECONDS', 30)
                _plf_autosave_stop.wait(interval)
            except Exception as e:
                logger.warning(f"PLF autosave error: {e}")
                _plf_autosave_stop.wait(30)
    _plf_autosave_stop.clear()
    _plf_autosave_thread = threading.Thread(target=_loop, daemon=True)
    _plf_autosave_thread.start()

def _finalize_plf_on_exit():
    try:
        if app.config.get('DB_READY') and app.config.get('PLF_PASSWORD'):
            _encrypt_active_db(app.config['PLF_PASSWORD'])
    except Exception as e:
        logger.warning(f"PLF final save error: {e}")

atexit.register(_finalize_plf_on_exit)

def _load_plf_to_temp(plf_path, password):
    temp_path = temp_sqlite_path(PLF_TEMP_FOLDER)
    decrypt_plf_to_sqlite(plf_path, temp_path, password)
    return temp_path

# Stripe Configuration & Routes
# Imported here to avoid circular dependency
try:
    from stripe_routes import stripe_bp
    from stripe_service import stripe_service
    app.register_blueprint(stripe_bp)
    
    # Initialize Stripe with keys from DB
    with app.app_context():
        try:
            params = ParametresEntreprise.query.first()
            stripe_secret = get_stripe_secret(params) if params else None
            if stripe_secret:
                app.config['STRIPE_SECRET_KEY'] = stripe_secret
                stripe_service.init_app(app)
        except Exception:
            pass
except Exception as e:
    logger.warning(f"Stripe initialization skipped: {e}")

if __name__ == '__main__':
    # Initialisation de la base de données
    init_db()

    # Initialiser les systèmes IA et automatisations après création des tables
    try:
        init_smart_assistant(app, db)
        init_automation_system(app, db)
        logger.info("✅ Systèmes IA et automatisations initialisés")
    except Exception as e:
        logger.warning(f"Erreur initialisation IA/automations: {e}")
    
    # Trouver un port disponible
    port = find_available_port()
    
    logger.info(f"Lancement sur le port {port}")
    if port != 5000:
        logger.warning(f"Le port 5000 était occupé, utilisation du port {port}")
    
    # Démarrer le système de notifications
    # try:
    #     notification_system.start_scheduler()
    #     logger.info("Système de notifications démarré")
    # except Exception as e:
    #     logger.warning(f"Erreur démarrage notifications : {e}")
    
    # Lancer l'application
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get('FLASK_ENV') != 'production'))
