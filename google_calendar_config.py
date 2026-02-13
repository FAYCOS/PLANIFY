#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Google Calendar pour les DJs
"""

import os
import json
import base64
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from flask import current_app, url_for

# Scopes nécessaires
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarManager:
    """Gestionnaire Google Calendar pour les DJs"""
    
    def __init__(self):
        self.service = None
        self.credentials = None

    def _get_settings(self):
        """Récupère les paramètres entreprise depuis la DB"""
        try:
            from app import ParametresEntreprise
            return ParametresEntreprise.query.first()
        except Exception as e:
            logging.error(f"Erreur récupération paramètres: {e}")
            return None
    
    def is_configured(self):
        """Vérifie si Google Calendar est configuré"""
        settings = self._get_settings()
        if not settings:
            return False
        return bool(settings.google_calendar_enabled and 
                   settings.google_client_id and 
                   settings.google_client_secret)
    
    def get_client_config(self):
        """Retourne la configuration client OAuth"""
        settings = self._get_settings()
        if not settings or not settings.google_client_id or not settings.google_client_secret:
            return None
            
        return {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [url_for('google_calendar_callback', _external=True)]
            }
        }
    
    def get_authorization_url(self, dj_id):
        """Génère l'URL d'autorisation pour un DJ"""
        try:
            config = self.get_client_config()
            if not config:
                logging.error("Credentials Google Calendar non configurés")
                return None, None
            
            flow = Flow.from_client_config(
                config,
                scopes=SCOPES
            )
            flow.redirect_uri = url_for('google_calendar_callback', _external=True)
            
            # Ajouter l'état pour identifier le DJ
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=str(dj_id)
            )
            
            return authorization_url, state
        except Exception as e:
            logging.error(f"Erreur génération URL auth: {e}")
            return None, None
    
    def exchange_code_for_tokens(self, code, state):
        """Échange le code d'autorisation contre les tokens"""
        try:
            config = self.get_client_config()
            if not config:
                return None

            flow = Flow.from_client_config(
                config,
                scopes=SCOPES
            )
            flow.redirect_uri = url_for('google_calendar_callback', _external=True)
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
        except Exception as e:
            logging.error(f"Erreur échange tokens: {e}")
            return None
    
    def get_credentials(self, dj):
        """Récupère les credentials pour un DJ"""
        if not dj.google_access_token:
            return None
        
        settings = self._get_settings()
        if not settings:
            return None

        credentials = Credentials(
            token=dj.google_access_token,
            refresh_token=dj.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret
        )
        
        # Vérifier si le token a expiré
        if dj.google_token_expiry and datetime.now() >= dj.google_token_expiry:
            try:
                credentials.refresh(Request())
                # Mettre à jour les tokens dans la base de donnéees
                self.update_dj_tokens(dj, credentials)
            except Exception as e:
                logging.error(f"Erreur refresh token: {e}")
                return None
        
        return credentials
    
    def update_dj_tokens(self, dj, credentials):
        """Met à jour les tokens d'un DJ dans la base de données"""
        from app import db
        
        dj.google_access_token = credentials.token
        if credentials.refresh_token:
            dj.google_refresh_token = credentials.refresh_token
        if credentials.expiry:
            dj.google_token_expiry = credentials.expiry
        
        db.session.commit()
    
    def get_service(self, dj):
        """Récupère le service Google Calendar pour un DJ"""
        credentials = self.get_credentials(dj)
        if not credentials:
            return None
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            return service
        except Exception as e:
            logging.error(f"Erreur création service: {e}")
            return None
    
    def create_event(self, dj, prestation):
        """Crée un événement dans le calendrier du DJ"""
        service = self.get_service(dj)
        if not service:
            return False
        
        try:
            # Construire la date/heure de début
            start_datetime = datetime.combine(
                prestation.date_debut, 
                prestation.heure_debut
            )
            
            # Construire la date/heure de fin
            end_datetime = datetime.combine(
                prestation.date_fin, 
                prestation.heure_fin
            )
            
            # Si l'heure de fin est avant l'heure de début, c'est le lendemain
            if end_datetime <= start_datetime:
                end_datetime += timedelta(days=1)
            
            event = {
                'summary': f'Prestation DJ - {prestation.client}',
                'description': f'Prestation à {prestation.lieu}\nClient: {prestation.client}\nNotes: {prestation.notes or "Aucune"}',
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/Paris',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Paris',
                },
                'location': prestation.lieu,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                        {'method': 'popup', 'minutes': 60},
                    ],
                },
            }
            
            # Utiliser le calendrier principal ou un calendrier spécifique
            calendar_id = dj.google_calendar_id or 'primary'
            
            event = service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            return event.get('id')
            
        except HttpError as e:
            logging.error(f"Erreur création événement: {e}")
            return False
        except Exception as e:
            logging.error(f"Erreur création événement: {e}")
            return False
    
    def update_event(self, dj, prestation, event_id):
        """Met à jour un événement dans le calendrier du DJ"""
        service = self.get_service(dj)
        if not service:
            return False
        
        try:
            # Construire la date/heure de début
            start_datetime = datetime.combine(
                prestation.date_debut, 
                prestation.heure_debut
            )
            
            # Construire la date/heure de fin
            end_datetime = datetime.combine(
                prestation.date_fin, 
                prestation.heure_fin
            )
            
            # Si l'heure de fin est avant l'heure de début, c'est le lendemain
            if end_datetime <= start_datetime:
                end_datetime += timedelta(days=1)
            
            event = {
                'summary': f'Prestation DJ - {prestation.client}',
                'description': f'Prestation à {prestation.lieu}\nClient: {prestation.client}\nNotes: {prestation.notes or "Aucune"}',
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/Paris',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Paris',
                },
                'location': prestation.lieu,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                        {'method': 'popup', 'minutes': 60},
                    ],
                },
            }
            
            calendar_id = dj.google_calendar_id or 'primary'
            
            service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return True
            
        except HttpError as e:
            logging.error(f"Erreur mise à jour événement: {e}")
            return False
        except Exception as e:
            logging.error(f"Erreur mise à jour événement: {e}")
            return False
    
    def delete_event(self, dj, event_id):
        """Supprime un événement du calendrier du DJ"""
        service = self.get_service(dj)
        if not service:
            return False
        
        try:
            calendar_id = dj.google_calendar_id or 'primary'
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return True
            
        except HttpError as e:
            logging.error(f"Erreur suppression événement: {e}")
            return False
        except Exception as e:
            logging.error(f"Erreur suppression événement: {e}")
            return False
    
    def test_connection(self, dj):
        """Teste la connexion Google Calendar d'un DJ"""
        service = self.get_service(dj)
        if not service:
            return False
        
        try:
            # Essayer de récupérer la liste des calendriers
            calendar_list = service.calendarList().list().execute()
            return True
        except Exception as e:
            logging.error(f"Erreur test connexion: {e}")
            return False

# Instance globale
google_calendar_manager = GoogleCalendarManager()
