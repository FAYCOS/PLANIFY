#!/usr/bin/env python3
"""
Système d'automatisations intelligentes pour Planify v3.0
Relances, rappels, notifications automatiques
"""

from datetime import datetime, timedelta, date, time as dt_time
from flask import current_app
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class AutomationSystem:
    """Système d'automatisations intelligentes"""
    
    def __init__(self, app=None, db=None):
        self.app = app
        self.db = db
        self.email_config = None
    
    def init_app(self, app, db):
        """Initialiser avec l'app Flask"""
        self.app = app
        self.db = db
        self.load_email_config()
    
    def load_email_config(self):
        """Charger la configuration email"""
        if not self.app:
            return
        
        with self.app.app_context():
            try:
                from app import ParametresEntreprise
                params = ParametresEntreprise.query.first()
                if params and params.email_expediteur:
                    self.email_config = {
                        'email': params.email_expediteur,
                        'password': params.email_mot_de_passe,
                        'smtp_server': params.smtp_serveur,
                        'smtp_port': params.smtp_port
                    }
            except Exception as e:
                logger.warning(f"Configuration email non disponible: {e}")
    
    # ==================== RELANCES AUTOMATIQUES ====================
    
    def relance_devis_non_signes(self, jours_apres=7):
        """
        Relancer automatiquement les devis non signés après X jours
        """
        if not self.app or not self.db:
            return []
        
        try:
            with self.app.app_context():
                from app import Devis, Client
                
                date_limite = datetime.now() - timedelta(days=jours_apres)
                
                # Trouver devis non signés de plus de X jours
                devis_a_relancer = Devis.query.filter(
                    Devis.statut == 'en_attente',
                    Devis.date_creation <= date_limite
                ).all()
                
                relances = []
                
                for devis in devis_a_relancer:
                    # Vérifier si pas déjà relancé récemment
                    if self._derniere_relance_recente(devis.id, 'devis'):
                        continue
                    
                    # Envoyer email de relance
                    if devis.client and devis.client.email:
                        success = self.envoyer_relance_devis(devis)
                        if success:
                            self._enregistrer_relance(devis.id, 'devis')
                            relances.append({
                                'type': 'devis',
                                'id': devis.id,
                                'client': devis.client.nom,
                                'montant': devis.montant_total
                            })
                
                return relances
                
        except Exception as e:
            logger.error(f"Erreur relance devis: {e}")
            return []
    
    def relance_factures_impayees(self, jours_apres=15):
        """
        Relancer automatiquement les factures impayées
        """
        if not self.app or not self.db:
            return []
        
        try:
            with self.app.app_context():
                from app import Facture, Client
                
                date_limite = datetime.now() - timedelta(days=jours_apres)
                
                # Trouver factures impayées
                factures_a_relancer = Facture.query.filter(
                    Facture.statut == 'impayee',
                    Facture.date_emission <= date_limite.date()
                ).all()
                
                relances = []
                
                for facture in factures_a_relancer:
                    if self._derniere_relance_recente(facture.id, 'facture'):
                        continue
                    
                    if facture.client and facture.client.email:
                        success = self.envoyer_relance_facture(facture)
                        if success:
                            self._enregistrer_relance(facture.id, 'facture')
                            relances.append({
                                'type': 'facture',
                                'id': facture.id,
                                'client': facture.client.nom,
                                'montant': facture.montant_total
                            })
                
                return relances
                
        except Exception as e:
            logger.error(f"Erreur relance factures: {e}")
            return []
    
    # ==================== RAPPELS AUTOMATIQUES ====================
    
    def rappels_prestations_proches(self, jours_avant=1):
        """
        Envoyer des rappels pour les prestations dans X jours (J-1 par défaut)
        Inclut: rappel client, rappel DJ, vérification matériel
        """
        if not self.app or not self.db:
            return []
        
        try:
            with self.app.app_context():
                from app import Prestation, MaterielPresta, Materiel
                
                date_cible = date.today() + timedelta(days=jours_avant)
                
                # Prestations dans X jours
                prestations = Prestation.query.filter(
                    Prestation.date_debut == date_cible,
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).all()
                
                rappels = []
                
                for prestation in prestations:
                    # ✅ 1. Rappel au CLIENT
                    if prestation.client_email:
                        if not self._rappel_deja_envoye(prestation.id, 'client'):
                            success = self.envoyer_rappel_client(prestation)
                            if success:
                                self._enregistrer_rappel(prestation.id, 'client')
                                rappels.append({
                                    'type': 'client',
                                    'prestation_id': prestation.id,
                                    'client': prestation.client,
                                    'date': prestation.date_debut
                                })
                    
                    # ✅ 2. Rappel au DJ
                    if prestation.dj_id:
                        from app import DJ
                        dj = self.db.session.get(DJ, prestation.dj_id)
                        if dj and dj.user and dj.user.email:
                            if not self._rappel_deja_envoye(prestation.id, 'dj'):
                                success = self.envoyer_rappel_dj(prestation)
                                if success:
                                    self._enregistrer_rappel(prestation.id, 'dj')
                                    rappels.append({
                                        'type': 'dj',
                                        'prestation_id': prestation.id,
                                        'dj': dj.nom,
                                        'date': prestation.date_debut
                                    })
                    
                    # ✅ 3. Vérification MATÉRIEL
                    # Vérifier que tout le matériel assigné est disponible
                    materiels_assignes = MaterielPresta.query.filter_by(prestation_id=prestation.id).all()
                    materiels_problemes = []
                    
                    for mat_presta in materiels_assignes:
                        materiel = self.db.session.get(Materiel, mat_presta.materiel_id)
                        if materiel:
                            # Vérifier statut
                            if materiel.statut == 'maintenance':
                                materiels_problemes.append({
                                    'nom': materiel.nom,
                                    'probleme': 'EN MAINTENANCE',
                                    'quantite': mat_presta.quantite
                                })
                            elif materiel.statut == 'hors_service':
                                materiels_problemes.append({
                                    'nom': materiel.nom,
                                    'probleme': 'HORS SERVICE',
                                    'quantite': mat_presta.quantite
                                })
                    
                    # Si problèmes matériel → alerter le manager
                    if materiels_problemes:
                        if not self._rappel_deja_envoye(prestation.id, 'materiel'):
                            success = self.envoyer_alerte_materiel_manager(prestation, materiels_problemes)
                            if success:
                                self._enregistrer_rappel(prestation.id, 'materiel')
                                rappels.append({
                                    'type': 'materiel_alert',
                                    'prestation_id': prestation.id,
                                    'problemes': len(materiels_problemes),
                                    'details': materiels_problemes
                                })
                
                logger.info(f"Rappels J-{jours_avant}: {len(rappels)} envoyés pour {len(prestations)} prestation(s)")
                return rappels
                
        except Exception as e:
            logger.error(f"Erreur rappels prestations: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def rappels_materiel_maintenance(self):
        """
        Rappeler le matériel en maintenance depuis longtemps
        """
        if not self.app or not self.db:
            return []
        
        try:
            with self.app.app_context():
                from app import Materiel
                
                date_limite = datetime.now() - timedelta(days=30)
                
                # Matériel en maintenance depuis > 30 jours
                materiels = Materiel.query.filter(
                    Materiel.statut == 'maintenance',
                    Materiel.date_derniere_verification <= date_limite.date()
                ).all()
                
                rappels = []
                
                for materiel in materiels:
                    if not self._rappel_deja_envoye(materiel.id, 'maintenance'):
                        # Créer notification
                        self._creer_notification_maintenance(materiel)
                        self._enregistrer_rappel(materiel.id, 'maintenance')
                        rappels.append({
                            'materiel': materiel.nom,
                            'local': materiel.local.nom if materiel.local else None,
                            'jours': (datetime.now().date() - materiel.date_derniere_verification).days
                        })
                
                return rappels
                
        except Exception as e:
            logger.error(f"Erreur rappels maintenance: {e}")
            return []
    
    def alertes_acomptes_non_payes(self, jours_avant=7):
        """
        Alerter les acomptes non payés avant prestation (J-7 par défaut)
        Envoie des rappels au client ET au manager
        """
        if not self.app or not self.db:
            return []
        
        try:
            with self.app.app_context():
                from app import Facture, Prestation
                
                date_limite = datetime.now() + timedelta(days=jours_avant)
                
                # Trouver factures avec acompte requis mais non payé
                # et prestation dans moins de X jours
                factures_acompte = Facture.query.join(Prestation).filter(
                    Facture.acompte_requis == True,
                    Facture.acompte_paye == False,
                    Facture.acompte_montant > 0,
                    Prestation.date_prestation <= date_limite.date(),
                    Prestation.date_prestation >= datetime.now().date(),
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).all()
                
                alertes = []
                
                for facture in factures_acompte:
                    if self._derniere_relance_recente(facture.id, 'acompte'):
                        continue
                    
                    # Envoyer email au client
                    if facture.client_email:
                        success_client = self.envoyer_rappel_acompte_client(facture)
                        if success_client:
                            self._enregistrer_relance(facture.id, 'acompte')
                            
                            # Alerter aussi le manager
                            self._creer_alerte_acompte_manager(facture)
                            
                            alertes.append({
                                'type': 'acompte',
                                'facture': facture.numero,
                                'client': facture.client_nom,
                                'montant': facture.acompte_montant,
                                'prestation_date': facture.prestation.date_prestation if facture.prestation else None,
                                'jours_restants': (facture.prestation.date_prestation - datetime.now().date()).days if facture.prestation else 0
                            })
                
                logger.info(f"Alertes acomptes: {len(alertes)} factures traitées")
                return alertes
                
        except Exception as e:
            logger.error(f"Erreur alertes acomptes: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # ==================== NOTIFICATIONS AUTOMATIQUES ====================
    
    def notifications_quotidiennes(self):
        """
        Générer des notifications quotidiennes
        """
        notifications = []
        
        # Prestations du jour
        prestations_jour = self._get_prestations_jour()
        if prestations_jour:
            notifications.append({
                'type': 'info',
                'titre': f'{len(prestations_jour)} prestation(s) aujourd\'hui',
                'message': 'Consultez le planning du jour',
                'lien': '/calendrier'
            })
        
        # Matériel disponible faible
        materiels_faible = self._get_materiels_stock_faible()
        if materiels_faible:
            notifications.append({
                'type': 'warning',
                'titre': f'{len(materiels_faible)} matériel(s) en stock faible',
                'message': 'Vérifiez les disponibilités',
                'lien': '/materiels'
            })
        
        # Devis expirés
        devis_expires = self._get_devis_expires()
        if devis_expires:
            notifications.append({
                'type': 'warning',
                'titre': f'{len(devis_expires)} devis expiré(s)',
                'message': 'Pensez à relancer les clients',
                'lien': '/devis'
            })
        
        # Acomptes non payés (NOUVEAU)
        acomptes_non_payes = self._get_acomptes_non_payes()
        if acomptes_non_payes:
            notifications.append({
                'type': 'danger',
                'titre': f'⚠️ {len(acomptes_non_payes)} acompte(s) non payé(s)',
                'message': 'Prestations à moins de 7 jours',
                'lien': '/factures'
            })
        
        return notifications
    
    # ==================== ENVOI D'EMAILS ====================
    
    def envoyer_relance_devis(self, devis):
        """Envoyer un email de relance pour un devis"""
        if not self.email_config or not devis.client:
            return False
        
        try:
            sujet = f"Relance - Devis {devis.numero}"
            
            corps = f"""
Bonjour {devis.client.prenom},

Nous revenons vers vous concernant le devis {devis.numero} que nous vous avons envoyé le {devis.date_creation.strftime('%d/%m/%Y')}.

Montant : {devis.montant_total}€
Validité : {devis.date_validite.strftime('%d/%m/%Y') if devis.date_validite else 'Non spécifiée'}

Pour signer votre devis en ligne : [Lien vers devis]

N'hésitez pas à nous contacter pour toute question.

Cordialement,
L'équipe Planify
            """
            
            return self._envoyer_email(devis.client.email, sujet, corps)
            
        except Exception as e:
            logger.error(f"Erreur envoi relance devis: {e}")
            return False
    
    def envoyer_relance_facture(self, facture):
        """Envoyer un email de relance pour une facture"""
        if not self.email_config or not facture.client:
            return False
        
        try:
            jours_retard = (date.today() - facture.date_echeance).days if facture.date_echeance else 0
            
            sujet = f"Rappel - Facture {facture.numero} impayée"
            
            corps = f"""
Bonjour {facture.client.prenom},

Nous constatons que la facture {facture.numero} émise le {facture.date_emission.strftime('%d/%m/%Y')} n'a pas encore été réglée.

Montant : {facture.montant_total}€
Échéance : {facture.date_echeance.strftime('%d/%m/%Y') if facture.date_echeance else 'Non spécifiée'}
Retard : {jours_retard} jour(s)

Merci de procéder au règlement dans les meilleurs délais.

Pour télécharger votre facture : [Lien vers facture]

Cordialement,
L'équipe Planify
            """
            
            return self._envoyer_email(facture.client.email, sujet, corps)
            
        except Exception as e:
            logger.error(f"Erreur envoi relance facture: {e}")
            return False
    
    def envoyer_rappel_client(self, prestation):
        """Envoyer un rappel au client"""
        if not self.email_config or not prestation.client:
            return False
        
        try:
            sujet = f"Rappel - {prestation.nom} dans 2 jours"
            
            corps = f"""
Bonjour {prestation.client.prenom},

Nous vous rappelons que votre événement "{prestation.nom}" aura lieu dans 2 jours :

📅 Date : {prestation.date.strftime('%d/%m/%Y')}
🕐 Heure : {prestation.heure_debut if prestation.heure_debut else '--:--'}
📍 Lieu : {prestation.lieu if prestation.lieu else 'À confirmer'}

Nous sommes prêts pour faire de votre événement un moment inoubliable !

Pour toute question : [Contact]

À très bientôt,
L'équipe Planify
            """
            
            return self._envoyer_email(prestation.client.email, sujet, corps)
            
        except Exception as e:
            logger.error(f"Erreur envoi rappel client: {e}")
            return False
    
    def envoyer_rappel_dj(self, prestation):
        """Envoyer un rappel au DJ"""
        if not self.email_config or not prestation.dj:
            return False
        
        try:
            sujet = f"Rappel - Prestation {prestation.nom} dans 2 jours"
            
            materiels = ', '.join([m.nom for m in prestation.materiels]) if prestation.materiels else 'Aucun'
            
            corps = f"""
Bonjour {prestation.dj.prenom},

Rappel de votre prestation dans 2 jours :

📅 Date : {prestation.date.strftime('%d/%m/%Y')}
🕐 Horaires : {prestation.heure_debut} - {prestation.heure_fin if prestation.heure_fin else '--:--'}
📍 Lieu : {prestation.lieu if prestation.lieu else 'À confirmer'}
🎵 Type : {prestation.type_evenement if prestation.type_evenement else 'Non spécifié'}

Matériel réservé : {materiels}

Bon show !
L'équipe Planify
            """
            
            return self._envoyer_email(prestation.dj.email, sujet, corps)
            
        except Exception as e:
            logger.error(f"Erreur envoi rappel DJ: {e}")
            return False
    
    def _envoyer_email(self, destinataire, sujet, corps):
        """Méthode générique d'envoi d'email"""
        if not self.email_config:
            logger.warning("Configuration email non disponible")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['email']
            msg['To'] = destinataire
            msg['Subject'] = sujet
            
            msg.attach(MIMEText(corps, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['email'], self.email_config['password'])
                server.send_message(msg)
            
            logger.info(f"Email envoyé à {destinataire}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False
    
    def envoyer_rappel_acompte_client(self, facture):
        """Envoyer un rappel d'acompte au client"""
        if not self.email_config or not facture.client_email:
            return False
        
        try:
            jours_restants = (facture.prestation.date_prestation - datetime.now().date()).days if facture.prestation else 0
            
            sujet = f"⚠️ Rappel acompte - Facture {facture.numero}"
            corps = f"""Bonjour {facture.client_nom},

Nous vous rappelons qu'un acompte est requis pour votre prestation.

📋 FACTURE : {facture.numero}
📅 DATE PRESTATION : {facture.prestation.date_prestation.strftime('%d/%m/%Y') if facture.prestation else 'Non définie'}
⏰ DANS {jours_restants} JOUR(S)

💰 ACOMPTE À VERSER : {facture.acompte_montant:.2f} € ({facture.acompte_pourcentage:.0f}% du total)
💳 SOLDE RESTANT : {facture.montant_solde:.2f} €

⚠️ L'acompte doit être réglé AVANT la prestation pour confirmer votre réservation.

Modes de paiement acceptés :
• Virement bancaire
• Chèque
• Espèces

Pour toute question, n'hésitez pas à nous contacter.

Cordialement,
L'équipe Planify
            """
            
            return self._envoyer_email(facture.client_email, sujet, corps)
            
        except Exception as e:
            logger.error(f"Erreur envoi rappel acompte: {e}")
            return False
    
    def envoyer_alerte_materiel_manager(self, prestation, materiels_problemes):
        """
        Envoyer une alerte au manager si du matériel assigné a un problème
        Appelé lors des rappels J-1
        """
        try:
            # Récupérer l'email du manager/admin
            from app import User
            managers = User.query.filter(User.role.in_(['admin', 'manager']), User.actif == True).all()
            
            if not managers:
                logger.warning("Aucun manager trouvé pour envoyer l'alerte matériel")
                return False
            
            # Préparer le message
            materiels_str = "\n".join([
                f"  - {m['nom']} (x{m['quantite']}) → {m['probleme']}"
                for m in materiels_problemes
            ])
            
            sujet = f"⚠️ ALERTE MATÉRIEL - Prestation {prestation.client} - J-1"
            corps = f"""⚠️ ALERTE MATÉRIEL - PRESTATION DEMAIN

📅 DATE : {prestation.date_debut.strftime('%d/%m/%Y')}
👤 CLIENT : {prestation.client}
🎵 DJ : {prestation.dj.nom if prestation.dj else 'Non assigné'}
📍 LIEU : {prestation.lieu}

🚨 PROBLÈMES MATÉRIEL DÉTECTÉS ({len(materiels_problemes)}) :
{materiels_str}

⚠️ ACTION REQUISE :
- Vérifier le statut du matériel
- Trouver du matériel de remplacement si nécessaire
- Contacter le DJ pour confirmer

Cette prestation a lieu DEMAIN. Intervention urgente requise.

Cordialement,
Système automatisé Planify
            """
            
            # Envoyer à tous les managers
            success_count = 0
            for manager in managers:
                if manager.email:
                    if self._envoyer_email(manager.email, sujet, corps):
                        success_count += 1
            
            logger.warning(f"Alerte matériel envoyée à {success_count}/{len(managers)} manager(s)")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Erreur envoi alerte matériel: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _creer_alerte_acompte_manager(self, facture):
        """Créer une alerte pour le manager sur un acompte non payé"""
        try:
            # TODO: Implémenter avec le système de notifications
            # Pour l'instant, juste logger
            logger.warning(f"⚠️ ACOMPTE NON PAYÉ: Facture {facture.numero} - {facture.client_nom} - {facture.acompte_montant:.2f}€ - Prestation dans {(facture.prestation.date_prestation - datetime.now().date()).days if facture.prestation else '?'} jour(s)")
            return True
        except Exception as e:
            logger.error(f"Erreur création alerte manager: {e}")
            return False
    
    def _get_acomptes_non_payes(self):
        """Récupérer les factures avec acomptes non payés (prestation < 7 jours)"""
        try:
            with self.app.app_context():
                from app import Facture, Prestation
                
                date_limite = datetime.now() + timedelta(days=7)
                
                return Facture.query.join(Prestation).filter(
                    Facture.acompte_requis == True,
                    Facture.acompte_paye == False,
                    Facture.acompte_montant > 0,
                    Prestation.date_prestation <= date_limite.date(),
                    Prestation.date_prestation >= datetime.now().date(),
                    Prestation.statut.in_(['planifiee', 'confirmee'])
                ).all()
        except Exception as e:
            logger.error(f"Erreur récupération acomptes non payés: {e}")
            return []
    
    # ==================== HELPERS ====================
    
    def _derniere_relance_recente(self, objet_id, type_objet, jours=7):
        """Vérifier si une relance récente existe"""
        # TODO: Implémenter avec une table de suivi des relances
        return False
    
    def _enregistrer_relance(self, objet_id, type_objet):
        """Enregistrer qu'une relance a été envoyée"""
        # TODO: Implémenter avec une table de suivi
        pass
    
    def _rappel_deja_envoye(self, objet_id, type_rappel):
        """Vérifier si un rappel a déjà été envoyé"""
        # TODO: Implémenter avec une table de suivi
        return False
    
    def _enregistrer_rappel(self, objet_id, type_rappel):
        """Enregistrer qu'un rappel a été envoyé"""
        # TODO: Implémenter avec une table de suivi
        pass
    
    def _creer_notification_maintenance(self, materiel):
        """Créer une notification pour matériel en maintenance"""
        # TODO: Implémenter avec le système de notifications
        pass
    
    def _get_prestations_jour(self):
        """Récupérer les prestations du jour"""
        try:
            with self.app.app_context():
                from app import Prestation
                return Prestation.query.filter_by(date=date.today()).all()
        except:
            return []
    
    def _get_materiels_stock_faible(self):
        """Récupérer les matériels en stock faible"""
        # TODO: Implémenter selon votre logique métier
        return []
    
    def _get_devis_expires(self):
        """Récupérer les devis expirés"""
        try:
            with self.app.app_context():
                from app import Devis
                return Devis.query.filter(
                    Devis.statut == 'en_attente',
                    Devis.date_validite < date.today()
                ).all()
        except:
            return []


# Instance globale
automation_system = AutomationSystem()


def envoyer_rappels_quotidiens():
    """
    Fonction à appeler quotidiennement pour envoyer tous les rappels J-1
    Peut être appelée depuis un cron job ou un scheduler
    
    Envoie:
    - Rappels aux clients (J-1)
    - Rappels aux DJs (J-1)
    - Alertes matériel au manager si problèmes
    """
    logger.info("🔔 Démarrage des rappels quotidiens J-1...")
    
    try:
        # Rappels prestations J-1 (inclut client, DJ, et vérif matériel)
        rappels = automation_system.rappels_prestations_proches(jours_avant=1)
        
        # Compter les rappels par type
        rappels_clients = [r for r in rappels if r['type'] == 'client']
        rappels_djs = [r for r in rappels if r['type'] == 'dj']
        alertes_materiel = [r for r in rappels if r['type'] == 'materiel_alert']
        
        logger.info(f"✅ Rappels quotidiens terminés:")
        logger.info(f"  - {len(rappels_clients)} rappel(s) client")
        logger.info(f"  - {len(rappels_djs)} rappel(s) DJ")
        logger.info(f"  - {len(alertes_materiel)} alerte(s) matériel")
        
        if alertes_materiel:
            logger.warning(f"⚠️ ATTENTION: {len(alertes_materiel)} alerte(s) matériel envoyée(s) aux managers!")
        
        return {
            'success': True,
            'total': len(rappels),
            'clients': len(rappels_clients),
            'djs': len(rappels_djs),
            'alertes_materiel': len(alertes_materiel),
            'details': rappels
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors des rappels quotidiens: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def init_automation_system(app, db):
    """Initialiser le système d'automatisation"""
    automation_system.init_app(app, db)
    return automation_system
