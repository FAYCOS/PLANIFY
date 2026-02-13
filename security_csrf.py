#!/usr/bin/env python3
"""
Module de protection CSRF
"""

from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DateField, TimeField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from wtforms.widgets import TextArea
from datetime import datetime, date
import logging
logger = logging.getLogger(__name__)

class CSRFProtection:
    """Classe pour gérer la protection CSRF"""
    
    @staticmethod
    def init_app(app):
        """Initialise la protection CSRF pour l'application"""
        csrf = CSRFProtect()
        csrf.init_app(app)
        
        # Configuration CSRF
        app.config['WTF_CSRF_ENABLED'] = True
        app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 heure
        app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', 'dev-secret-key-change-in-production')
        
        return csrf

# Formulaires sécurisés avec protection CSRF

class SecureLoginForm(FlaskForm):
    """Formulaire de connexion sécurisé"""
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message='Le nom d\'utilisateur est requis'),
        Length(min=3, max=50, message='Le nom d\'utilisateur doit contenir entre 3 et 50 caractères')
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Le mot de passe est requis'),
        Length(min=8, max=128, message='Le mot de passe doit contenir entre 8 et 128 caractères')
    ])

class SecureUserForm(FlaskForm):
    """Formulaire utilisateur sécurisé"""
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message='Le nom d\'utilisateur est requis'),
        Length(min=3, max=50, message='Le nom d\'utilisateur doit contenir entre 3 et 50 caractères')
    ])
    nom = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100, message='Le nom doit contenir entre 2 et 100 caractères')
    ])
    prenom = StringField('Prénom', validators=[
        DataRequired(message='Le prénom est requis'),
        Length(min=2, max=100, message='Le prénom doit contenir entre 2 et 100 caractères')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='L\'email est requis'),
        Email(message='Format d\'email invalide'),
        Length(max=254, message='L\'email est trop long')
    ])
    role = SelectField('Rôle', choices=[
        ('admin', 'Administrateur'),
        ('manager', 'Manager'),
        ('dj', 'DJ'),
        ('technicien', 'Technicien')
    ], validators=[DataRequired(message='Le rôle est requis')])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Le mot de passe est requis'),
        Length(min=8, max=128, message='Le mot de passe doit contenir entre 8 et 128 caractères')
    ])

class SecureDJForm(FlaskForm):
    """Formulaire DJ sécurisé"""
    nom = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100, message='Le nom doit contenir entre 2 et 100 caractères')
    ])
    contact = StringField('Contact', validators=[
        Optional(),
        Length(max=200, message='Le contact est trop long')
    ])
    notes = TextAreaField('Notes', widget=TextArea(), validators=[
        Optional(),
        Length(max=1000, message='Les notes sont trop longues')
    ])

class SecureLocalForm(FlaskForm):
    """Formulaire Local sécurisé"""
    nom = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100, message='Le nom doit contenir entre 2 et 100 caractères')
    ])
    adresse = TextAreaField('Adresse', widget=TextArea(), validators=[
        DataRequired(message='L\'adresse est requise'),
        Length(max=500, message='L\'adresse est trop longue')
    ])

class SecureMaterielForm(FlaskForm):
    """Formulaire Matériel sécurisé"""
    nom = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100, message='Le nom doit contenir entre 2 et 100 caractères')
    ])
    categorie = StringField('Catégorie', validators=[
        DataRequired(message='La catégorie est requise'),
        Length(min=2, max=50, message='La catégorie doit contenir entre 2 et 50 caractères')
    ])
    quantite = IntegerField('Quantité', validators=[
        DataRequired(message='La quantité est requise'),
        NumberRange(min=1, max=9999, message='La quantité doit être entre 1 et 9999')
    ])
    statut = SelectField('Statut', choices=[
        ('disponible', 'Disponible'),
        ('maintenance', 'Maintenance'),
        ('hors_service', 'Hors service')
    ], validators=[DataRequired(message='Le statut est requis')])
    local_id = SelectField('Local', coerce=int, validators=[
        DataRequired(message='Le local est requis')
    ])

class SecurePrestationForm(FlaskForm):
    """Formulaire Prestation sécurisé"""
    client = StringField('Client', validators=[
        DataRequired(message='Le client est requis'),
        Length(min=2, max=100, message='Le client doit contenir entre 2 et 100 caractères')
    ])
    lieu = StringField('Lieu', validators=[
        DataRequired(message='Le lieu est requis'),
        Length(min=2, max=200, message='Le lieu doit contenir entre 2 et 200 caractères')
    ])
    date_debut = DateField('Date de début', validators=[
        DataRequired(message='La date de début est requise')
    ])
    date_fin = DateField('Date de fin', validators=[
        DataRequired(message='La date de fin est requise')
    ])
    heure_debut = TimeField('Heure de début', validators=[
        DataRequired(message='L\'heure de début est requise')
    ])
    heure_fin = TimeField('Heure de fin', validators=[
        DataRequired(message='L\'heure de fin est requise')
    ])
    dj_id = SelectField('DJ', coerce=int, validators=[
        DataRequired(message='Le DJ est requis')
    ])
    notes = TextAreaField('Notes', widget=TextArea(), validators=[
        Optional(),
        Length(max=1000, message='Les notes sont trop longues')
    ])

class SecureDevisForm(FlaskForm):
    """Formulaire Devis sécurisé"""
    client_nom = StringField('Nom du client', validators=[
        DataRequired(message='Le nom du client est requis'),
        Length(min=2, max=100, message='Le nom du client doit contenir entre 2 et 100 caractères')
    ])
    client_email = StringField('Email du client', validators=[
        Optional(),
        Email(message='Format d\'email invalide'),
        Length(max=254, message='L\'email est trop long')
    ])
    client_telephone = StringField('Téléphone du client', validators=[
        Optional(),
        Length(max=20, message='Le téléphone est trop long')
    ])
    client_adresse = TextAreaField('Adresse du client', widget=TextArea(), validators=[
        Optional(),
        Length(max=500, message='L\'adresse est trop longue')
    ])
    prestation_titre = StringField('Titre de la prestation', validators=[
        DataRequired(message='Le titre de la prestation est requis'),
        Length(min=2, max=200, message='Le titre doit contenir entre 2 et 200 caractères')
    ])
    prestation_description = TextAreaField('Description', widget=TextArea(), validators=[
        Optional(),
        Length(max=1000, message='La description est trop longue')
    ])
    date_prestation = DateField('Date de prestation', validators=[
        DataRequired(message='La date de prestation est requise')
    ])
    heure_debut = TimeField('Heure de début', validators=[
        DataRequired(message='L\'heure de début est requise')
    ])
    heure_fin = TimeField('Heure de fin', validators=[
        DataRequired(message='L\'heure de fin est requise')
    ])
    lieu = StringField('Lieu', validators=[
        DataRequired(message='Le lieu est requis'),
        Length(min=2, max=200, message='Le lieu doit contenir entre 2 et 200 caractères')
    ])
    tarif_horaire = DecimalField('Tarif horaire', validators=[
        DataRequired(message='Le tarif horaire est requis'),
        NumberRange(min=0, max=9999.99, message='Le tarif doit être entre 0 et 9999.99')
    ])
    duree_heures = DecimalField('Durée en heures', validators=[
        DataRequired(message='La durée est requise'),
        NumberRange(min=0.5, max=24, message='La durée doit être entre 0.5 et 24 heures')
    ])
    taux_tva = DecimalField('Taux de TVA', validators=[
        DataRequired(message='Le taux de TVA est requis'),
        NumberRange(min=0, max=100, message='Le taux de TVA doit être entre 0 et 100%')
    ])
    remise_pourcentage = DecimalField('Remise en %', validators=[
        Optional(),
        NumberRange(min=0, max=100, message='La remise doit être entre 0 et 100%')
    ])
    remise_montant = DecimalField('Remise en €', validators=[
        Optional(),
        NumberRange(min=0, max=9999.99, message='La remise doit être entre 0 et 9999.99€')
    ])
    frais_transport = DecimalField('Frais de transport', validators=[
        Optional(),
        NumberRange(min=0, max=9999.99, message='Les frais de transport doivent être entre 0 et 9999.99€')
    ])
    frais_materiel = DecimalField('Frais de matériel', validators=[
        Optional(),
        NumberRange(min=0, max=9999.99, message='Les frais de matériel doivent être entre 0 et 9999.99€')
    ])
    date_validite = DateField('Date de validité', validators=[
        Optional()
    ])
    dj_id = SelectField('DJ', coerce=int, validators=[
        Optional()
    ])

def validate_csrf_token(request):
    """
    Valide manuellement un token CSRF
    """
    from flask_wtf.csrf import validate_csrf
    from wtforms import ValidationError
    
    try:
        validate_csrf(request.form.get('csrf_token'))
        return True
    except ValidationError:
        return False

def get_csrf_token():
    """
    Génère un token CSRF
    """
    from flask_wtf.csrf import generate_csrf
    return generate_csrf()










