#!/usr/bin/env python3
"""
Service d'envoi d'emails pour Planify
"""

import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
import logging
from email.utils import formataddr
import html
import re

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Configuration SMTP Gmail
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = "noreply.planifymanagement@gmail.com"
        self.password = "fxdh unyj nlgh umkx"
        
        # Stockage temporaire des codes (en production, utiliser Redis ou base de données)
        self.verification_codes = {}
    
    def generate_verification_code(self):
        """Génère un code de vérification à 6 chiffres"""
        return ''.join(random.choices(string.digits, k=6))

    def _get_parametres(self):
        try:
            from flask import current_app
            from app import ParametresEntreprise
            if current_app:
                with current_app.app_context():
                    return ParametresEntreprise.query.first()
        except Exception:
            return None
        return None

    def _build_signature(self, parametres):
        signature = ''
        if parametres and parametres.email_signature:
            signature = parametres.email_signature.strip()
        else:
            nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
            signature = f"L'équipe {nom_entreprise}"
        contact = []
        if parametres and parametres.telephone:
            contact.append(f"Tél : {parametres.telephone}")
        if parametres and parametres.email:
            contact.append(f"Email : {parametres.email}")
        if parametres and parametres.site_web:
            contact.append(f"Site : {parametres.site_web}")
        return signature, contact

    def _append_signature_text(self, body, parametres):
        signature_text, contact = self._build_signature(parametres)
        if signature_text and signature_text in body:
            return body
        parts = [body.rstrip(), "", signature_text]
        if contact:
            parts.extend(contact)
        return "\n".join(parts).strip() + "\n"

    def _build_html_template(self, title, subtitle, greeting, content_html, parametres):
        primary = parametres.couleur_principale if parametres and parametres.couleur_principale else '#0b84ff'
        secondary = parametres.couleur_secondaire if parametres and parametres.couleur_secondaire else '#0f5bd6'
        nom_entreprise = parametres.nom_entreprise if parametres else 'Planify'
        signature_text, contact = self._build_signature(parametres)
        signature_html = "<br>".join([html.escape(signature_text)] + [html.escape(c) for c in contact])

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0; padding:0; background:#f2f2f4; font-family:-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', sans-serif; color:#1d1d1f;">
            <div style="max-width:640px; margin:40px auto; padding:0 16px;">
                <div style="background:#ffffff; border-radius:20px; overflow:hidden; box-shadow:0 20px 60px rgba(0, 0, 0, 0.08);">
                    <div style="padding:20px 32px; background:#ffffff; border-bottom:1px solid #f0f1f4;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:36px; height:36px; border-radius:12px; background:linear-gradient(135deg, {primary} 0%, {secondary} 100%);"></div>
                            <div style="font-size:13px; letter-spacing:0.4px; text-transform:uppercase; color:#6e6e73;">
                                {html.escape(nom_entreprise)}
                            </div>
                        </div>
                    </div>
                    <div style="padding:32px 36px 24px;">
                        <div style="font-size:26px; font-weight:700; letter-spacing:-0.4px; margin-bottom:6px;">
                            {html.escape(title)}
                        </div>
                        <div style="font-size:15px; color:#6e6e73; margin-bottom:20px;">
                            {html.escape(subtitle)}
                        </div>
                        <p style="font-size:16px; margin:0 0 18px; color:#1d1d1f;">{html.escape(greeting)}</p>
                        <div style="font-size:15px; line-height:1.6; color:#1d1d1f;">
                            {content_html}
                        </div>
                    </div>
                    <div style="padding:0 36px 32px; font-size:13px; color:#6e6e73;">
                        <div style="border-top:1px solid #f0f1f4; padding-top:16px;">
                            {signature_html}
                        </div>
                    </div>
                </div>
                <div style="text-align:center; margin-top:18px; font-size:12px; color:#9b9ba0;">
                    Cet email a ete genere automatiquement par Planify.
                </div>
            </div>
        </body>
        </html>
        """

    def _plain_to_html(self, text, parametres, title='Notification Planify'):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            content_html = "<p style='font-size:15px;'>Message Planify.</p>"
            greeting = "Bonjour,"
        else:
            greeting = lines[0]
            body_lines = lines[1:]
            paragraphs = ""
            for line in body_lines:
                escaped = html.escape(line)
                linked = re.sub(r'(https?://[^\\s]+)', r'<a href="\\1" style="color:#0b84ff; text-decoration:none;">\\1</a>', escaped)
                paragraphs += f"<p style='font-size:15px; line-height:1.6; margin:0 0 14px;'>{linked}</p>"
            content_html = paragraphs or "<p style='font-size:15px;'>.</p>"
        return self._build_html_template(title, "Planify", greeting, content_html, parametres)
    
    def send_verification_email(self, to_email, user_name, code):
        """Envoie un email de vérification"""
        try:
            parametres = self._get_parametres()
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Vérification de votre compte Planify"
            # Envoyer depuis un expéditeur lisible
            msg['From'] = formataddr(('Planify', self.email))
            msg['To'] = to_email
            info_list = """
                <div style="background:#f6f7fb; border-radius:12px; padding:14px 16px; margin-top:20px;">
                    <ul style="margin:0; padding-left:18px; font-size:14px; color:#1d1d1f;">
                        <li>Ce code est valide pendant 10 minutes</li>
                        <li>Ne partagez jamais ce code</li>
                        <li>Si vous n'etes pas a l'origine de cette demande, ignorez cet email</li>
                    </ul>
                </div>
            """
            code_block = f"""
                <div style="margin:18px 0; padding:18px 16px; border-radius:14px; background:#111827; color:#ffffff; text-align:center;">
                    <div style="font-size:12px; letter-spacing:2px; opacity:0.7;">CODE DE VERIFICATION</div>
                    <div style="font-size:32px; font-weight:700; letter-spacing:8px; margin-top:8px; font-family:'SF Mono','Monaco','Courier New',monospace;">
                        {html.escape(code)}
                    </div>
                </div>
            """
            content_html = f"""
                <p style="font-size:15px; line-height:1.6; margin:0 0 16px;">
                    Merci de vous etre inscrit sur Planify. Pour finaliser la configuration de votre compte,
                    veuillez utiliser le code de verification ci-dessous :
                </p>
                {code_block}
                {info_list}
            """
            html_content = self._build_html_template(
                "Vérification de compte",
                "Sécurisation de votre accès",
                f"Bonjour {user_name},",
                content_html,
                parametres
            )
            
            # Contenu texte simple
            text_content = f"""
            Bonjour {user_name} !
            
            Votre code de vérification Planify : {code}
            
            Ce code est valide pendant 10 minutes.
            """
            text_content = self._append_signature_text(text_content.strip(), parametres)
            
            # Attacher les contenus
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Connexion et envoi
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            
            # Stocker le code avec expiration
            self.verification_codes[to_email] = {
                'code': code,
                'expires': datetime.now() + timedelta(minutes=10),
                'user_name': user_name
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email : {str(e)}")
            return False
    
    def verify_code(self, email, code):
        """Vérifie le code de vérification"""
        if email not in self.verification_codes:
            return False
        
        stored_data = self.verification_codes[email]
        
        # Vérifier l'expiration
        if datetime.now() > stored_data['expires']:
            del self.verification_codes[email]
            return False
        
        # Vérifier le code
        if stored_data['code'] == code:
            # Marquer comme vérifié
            stored_data['verified'] = True
            return True
        
        return False
    
    def get_user_data(self, email):
        """Récupère les données de l'utilisateur après vérification"""
        if email in self.verification_codes and self.verification_codes[email].get('verified'):
            return {
                'user_name': self.verification_codes[email]['user_name'],
                'email': email
            }
        return None
    
    def send_email(self, to_email, subject, body):
        """Envoie un email simple"""
        try:
            parametres = self._get_parametres()
            body_with_signature = self._append_signature_text(body, parametres)
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr(('Planify', self.email))
            msg['To'] = to_email

            html_body = self._plain_to_html(body, parametres, title=subject)
            text_part = MIMEText(body_with_signature, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(text_part)
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            logger.info(f"Email envoyé à {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email : {e}")
            return False

    def send_email_with_attachment(self, to_email, subject, body, attachment_data, attachment_filename, bcc=None, html_body=None):
        """Envoie un email avec pièce jointe et support BCC"""
        try:
            from email.mime.base import MIMEBase
            from email import encoders

            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = formataddr(('Planify', self.email))
            msg['To'] = to_email
            
            # Ajouter les destinataires BCC (copie cachée)
            if bcc:
                if isinstance(bcc, list):
                    msg['Bcc'] = ', '.join(bcc)
                else:
                    msg['Bcc'] = bcc
            
            # Corps du message
            parametres = self._get_parametres()
            body_with_signature = self._append_signature_text(body, parametres)
            if html_body is None:
                html_body = self._plain_to_html(body, parametres, title=subject)
            alt = MIMEMultipart('alternative')
            alt.attach(MIMEText(body_with_signature, 'plain', 'utf-8'))
            alt.attach(MIMEText(html_body, 'html', 'utf-8'))
            msg.attach(alt)
            
            # Pièce jointe
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_data)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment_filename}'
            )
            msg.attach(part)
            
            # Préparer la liste de tous les destinataires (To + BCC)
            all_recipients = [to_email]
            if bcc:
                if isinstance(bcc, list):
                    all_recipients.extend(bcc)
                else:
                    all_recipients.append(bcc)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.sendmail(self.email, all_recipients, msg.as_string())
            
            logger.info(f"Email avec pièce jointe envoyé à {to_email}" + (f" avec {len(bcc)} copie(s) cachée(s)" if bcc else ""))
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email avec pièce jointe : {e}")
            return False

    def cleanup_expired_codes(self):
        """Nettoie les codes expirés"""
        current_time = datetime.now()
        expired_emails = [
            email for email, data in self.verification_codes.items()
            if current_time > data['expires']
        ]
        for email in expired_emails:
            del self.verification_codes[email]

# Instance globale du service email
email_service = EmailService()
