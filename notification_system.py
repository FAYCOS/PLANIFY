#!/usr/bin/env python3
"""
Système de notifications et rappels automatiques pour Planify
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, date
# Import sera fait dans les fonctions pour éviter les imports circulaires
import os
from threading import Thread
import schedule
import time
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    """Gestionnaire de notifications et rappels"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@planify.app')
    
    def send_email(self, to_email, subject, html_content, text_content=None):
        """Envoie un email de notification"""
        try:
            if not self.email_user or not self.email_password:
                logger.error("Configuration email manquante")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Contenu texte
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Contenu HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Connexion SMTP
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.exception('Erreur envoi email')
            return False
    
    def send_prestation_reminder(self, prestation, reminder_type="24h"):
        """Envoie un rappel pour une prestation"""
        try:
            dj = prestation.dj
            if not dj or not dj.user:
                return False
            
            # Contenu de l'email
            subject = f"🔔 Rappel {reminder_type} - Prestation {prestation.client}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                    .prestation-info {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                    .info-row {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                    .label {{ font-weight: bold; color: #666; }}
                    .value {{ color: #333; }}
                    .button {{ background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎵 Planify - Rappel Prestation</h1>
                        <p>Rappel {reminder_type} avant votre prestation</p>
                    </div>
                    <div class="content">
                        <div class="prestation-info">
                            <h2>📅 Détails de la prestation</h2>
                            <div class="info-row">
                                <span class="label">Client :</span>
                                <span class="value">{prestation.client}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Date :</span>
                                <span class="value">{prestation.date_debut.strftime('%d/%m/%Y')}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Heure :</span>
                                <span class="value">{prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Lieu :</span>
                                <span class="value">{prestation.lieu}</span>
                            </div>
                            {f'<div class="info-row"><span class="label">Téléphone :</span><span class="value">{prestation.client_telephone}</span></div>' if prestation.client_telephone else ''}
                            {f'<div class="info-row"><span class="label">Email :</span><span class="value">{prestation.client_email}</span></div>' if prestation.client_email else ''}
                            {f'<div class="info-row"><span class="label">Notes :</span><span class="value">{prestation.notes}</span></div>' if prestation.notes else ''}
                        </div>
                        
                        <p><strong>💡 N'oubliez pas :</strong></p>
                        <ul>
                            <li>Vérifiez votre matériel la veille</li>
                            <li>Confirmez votre arrivée avec le client</li>
                            <li>Préparez votre playlist</li>
                        </ul>
                        
                        <a href="{os.getenv('APP_URL', 'http://localhost:5000')}/prestations/{prestation.id}" class="button">
                            Voir les détails
                        </a>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Rappel {reminder_type} - Prestation {prestation.client}
            
            Date : {prestation.date_debut.strftime('%d/%m/%Y')}
            Heure : {prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}
            Lieu : {prestation.lieu}
            {'Téléphone : ' + prestation.client_telephone if prestation.client_telephone else ''}
            {'Email : ' + prestation.client_email if prestation.client_email else ''}
            {'Notes : ' + prestation.notes if prestation.notes else ''}
            
            N'oubliez pas de vérifier votre matériel et de confirmer votre arrivée !
            """
            
            return self.send_email(dj.user.email, subject, html_content, text_content)
            
        except Exception as e:
            logger.exception('Erreur envoi rappel')
            return False
    
    def send_prestation_confirmation(self, prestation):
        """Envoie une confirmation de prestation au client"""
        try:
            if not prestation.client_email:
                return False
            
            subject = f"✅ Confirmation de votre prestation DJ - {prestation.client}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                    .prestation-info {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                    .info-row {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                    .label {{ font-weight: bold; color: #666; }}
                    .value {{ color: #333; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎵 Planify - Confirmation</h1>
                        <p>Votre prestation DJ a été confirmée</p>
                    </div>
                    <div class="content">
                        <div class="prestation-info">
                            <h2>📅 Détails de votre prestation</h2>
                            <div class="info-row">
                                <span class="label">Date :</span>
                                <span class="value">{prestation.date_debut.strftime('%d/%m/%Y')}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Heure :</span>
                                <span class="value">{prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Lieu :</span>
                                <span class="value">{prestation.lieu}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">DJ :</span>
                                <span class="value">{prestation.dj.nom if prestation.dj else 'À confirmer'}</span>
                            </div>
                            {f'<div class="info-row"><span class="label">Notes :</span><span class="value">{prestation.notes}</span></div>' if prestation.notes else ''}
                        </div>
                        
                        <p><strong>📞 Contact :</strong></p>
                        <p>Pour toute question, n'hésitez pas à nous contacter.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self.send_email(prestation.client_email, subject, html_content)
            
        except Exception as e:
            logger.exception('Erreur envoi confirmation client')
            return False
    
    def check_and_send_reminders(self):
        """Vérifie et envoie les rappels automatiques"""
        try:
            from app import app, db, Prestation
            with app.app_context():
                # Rappels 24h avant
                tomorrow = date.today() + timedelta(days=1)
                prestations_24h = Prestation.query.filter(
                    Prestation.date_debut == tomorrow,
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).all()
                
                for prestation in prestations_24h:
                    self.send_prestation_reminder(prestation, "24h")
                
                # Rappels 48h avant
                day_after_tomorrow = date.today() + timedelta(days=2)
                prestations_48h = Prestation.query.filter(
                    Prestation.date_debut == day_after_tomorrow,
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).all()
                
                for prestation in prestations_48h:
                    self.send_prestation_reminder(prestation, "48h")
                
                logger.info(f"Rappels envoyés : {len(prestations_24h)} (24h) + {len(prestations_48h)} (48h)")
                
        except Exception as e:
            logger.exception('Erreur vérification rappels')
    
    def start_scheduler(self):
        """Démarre le planificateur de tâches"""
        # Vérifier les rappels toutes les heures
        schedule.every().hour.do(self.check_and_send_reminders)
        
        # Vérifier les rappels tous les jours à 9h
        schedule.every().day.at("09:00").do(self.check_and_send_reminders)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Vérifier toutes les minutes
        
        # Démarrer le scheduler dans un thread séparé
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("📅 Planificateur de rappels démarré")

# Instance globale
notification_manager = NotificationManager()
