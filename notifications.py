#!/usr/bin/env python3
"""
Système de notifications par email
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import os
from flask import current_app
import logging
logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = os.getenv('NOTIFICATION_EMAIL', 'dj.prestations@gmail.com')
        self.password = os.getenv('NOTIFICATION_PASSWORD', 'your_app_password')
        
    def send_email(self, to_email, subject, body, html_body=None, attachments=None):
        """Envoie un email de notification"""
        try:
            # Création du message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Corps du message
            if html_body:
                msg.attach(MIMEText(body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Pièces jointes
            if attachments:
                for attachment in attachments:
                    with open(attachment['path'], 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment["filename"]}'
                        )
                        msg.attach(part)
            
            # Connexion et envoi
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            text = msg.as_string()
            server.sendmail(self.email, to_email, text)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False
    
    def notify_new_prestation(self, prestation, dj_email=None):
        """Notification pour nouvelle prestation"""
        subject = f"🎵 Nouvelle prestation: {prestation.client}"
        
        body = f"""
Bonjour,

Une nouvelle prestation a été créée:

📅 Date: {prestation.date_debut.strftime('%d/%m/%Y')}
🕐 Heure: {prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}
👤 Client: {prestation.client}
📍 Lieu: {prestation.lieu}
🎧 DJ: {prestation.dj.nom if prestation.dj else 'Non assigné'}

Cordialement,
DJ Prestations Manager
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">🎵 Nouvelle prestation créée</h2>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1f2937;">{prestation.client}</h3>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                        <div>
                            <strong>📅 Date:</strong><br>
                            {prestation.date_debut.strftime('%d/%m/%Y')}
                        </div>
                        <div>
                            <strong>🕐 Heure:</strong><br>
                            {prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}
                        </div>
                        <div>
                            <strong>📍 Lieu:</strong><br>
                            {prestation.lieu}
                        </div>
                        <div>
                            <strong>🎧 DJ:</strong><br>
                            {prestation.dj.nom if prestation.dj else 'Non assigné'}
                        </div>
                    </div>
                </div>
                
                <p style="color: #6b7280; font-size: 14px;">
                    Cordialement,<br>
                    <strong>DJ Prestations Manager</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        # Envoi à l'admin
        admin_emails = self.get_admin_emails()
        for admin_email in admin_emails:
            self.send_email(admin_email, subject, body, html_body)
        
        # Envoi au DJ si assigné
        if dj_email:
            self.send_email(dj_email, subject, body, html_body)
    
    def notify_prestation_reminder(self, prestation, hours_before=24):
        """Rappel de prestation"""
        subject = f"⏰ Rappel: Prestation {prestation.client} dans {hours_before}h"
        
        body = f"""
Rappel de prestation:

📅 Date: {prestation.date_debut.strftime('%d/%m/%Y')}
🕐 Heure: {prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}
👤 Client: {prestation.client}
📍 Lieu: {prestation.lieu}
🎧 DJ: {prestation.dj.nom if prestation.dj else 'Non assigné'}

N'oubliez pas de préparer le matériel nécessaire !

Cordialement,
DJ Prestations Manager
        """
        
        # Envoi au DJ assigné
        if prestation.dj and prestation.dj.email:
            self.send_email(prestation.dj.email, subject, body)
    
    def notify_materiel_maintenance(self, materiel, technicien_email=None):
        """Notification de maintenance matériel"""
        subject = f"🔧 Matériel en maintenance: {materiel.nom}"
        
        body = f"""
Le matériel suivant a été mis en maintenance:

🔧 Matériel: {materiel.nom}
📍 Local: {materiel.local.nom if materiel.local else 'Non assigné'}
📅 Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}
⚠️ Statut: Maintenance

Cordialement,
DJ Prestations Manager
        """
        
        # Envoi au technicien
        if technicien_email:
            self.send_email(technicien_email, subject, body)
        
        # Envoi aux admins
        admin_emails = self.get_admin_emails()
        for admin_email in admin_emails:
            self.send_email(admin_email, subject, body)
    
    def notify_devis_sent(self, devis, client_email):
        """Notification d'envoi de devis"""
        subject = f"📄 Devis envoyé: {devis.numero}"
        
        body = f"""
Votre devis a été envoyé avec succès:

📄 Numéro: {devis.numero}
👤 Client: {devis.client_nom}
💰 Montant: {devis.montant_ttc:.2f}€
📅 Validité: {devis.date_validite.strftime('%d/%m/%Y') if devis.date_validite else 'Non définie'}

Cordialement,
DJ Prestations Manager
        """
        
        # Envoi au client
        if client_email:
            self.send_email(client_email, subject, body)
    
    def get_admin_emails(self):
        """Récupère les emails des administrateurs"""
        from app import User
        admins = User.query.filter_by(role='admin', actif=True).all()
        return [admin.email for admin in admins if admin.email]
    
    def send_daily_report(self):
        """Envoie le rapport quotidien"""
        from app import Prestation, Materiel, DJ
        from datetime import date, timedelta
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Statistiques du jour
        prestations_today = Prestation.query.filter(
            db.func.date(Prestation.date_debut) == today
        ).count()
        
        materiel_maintenance = Materiel.query.filter_by(statut='maintenance').count()
        
        subject = f"📊 Rapport quotidien - {today.strftime('%d/%m/%Y')}"
        
        body = f"""
Rapport quotidien - {today.strftime('%d/%m/%Y')}

📅 Prestations aujourd'hui: {prestations_today}
🔧 Matériel en maintenance: {materiel_maintenance}

Cordialement,
DJ Prestations Manager
        """
        
        admin_emails = self.get_admin_emails()
        for admin_email in admin_emails:
            self.send_email(admin_email, subject, body)

# Instance globale
notification_manager = NotificationManager()











