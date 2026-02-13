#!/usr/bin/env python3
"""
Générateur de manuel PDF professionnel pour Planify
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
from io import BytesIO
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class PlanifyManualGenerator:
    """Générateur de manuel PDF pour Planify"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Configure les styles personnalisés"""
        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#667eea'),
            fontName='Helvetica-Bold'
        ))
        
        # Style pour les titres de chapitre
        self.styles.add(ParagraphStyle(
            name='ChapterTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            spaceBefore=30,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica-Bold'
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#4B5563'),
            fontName='Helvetica-Bold'
        ))
        
        # Style pour les fonctionnalités
        self.styles.add(ParagraphStyle(
            name='FeatureTitle',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=15,
            textColor=colors.HexColor('#667eea'),
            fontName='Helvetica-Bold'
        ))
        
        # Style pour le texte normal
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        # Style pour les listes
        self.styles.add(ParagraphStyle(
            name='ListText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            leftIndent=20,
            fontName='Helvetica'
        ))
        
        # Style pour les codes/technique
        self.styles.add(ParagraphStyle(
            name='CodeText',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=6,
            leftIndent=15,
            fontName='Courier',
            textColor=colors.HexColor('#6B7280'),
            backColor=colors.HexColor('#F3F4F6')
        ))
    
    def generate_manual(self, output_path="Planify_Manuel_Complet.pdf"):
        """Génère le manuel complet"""
        doc = SimpleDocTemplate(output_path, pagesize=A4, 
                              rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Page de couverture
        story.extend(self._create_cover_page())
        story.append(PageBreak())
        
        # Table des matières
        story.extend(self._create_table_of_contents())
        story.append(PageBreak())
        
        # Introduction
        story.extend(self._create_introduction())
        story.append(PageBreak())
        
        # Fonctionnalités principales
        story.extend(self._create_main_features())
        story.append(PageBreak())
        
        # Gestion des prestations
        story.extend(self._create_prestations_section())
        story.append(PageBreak())
        
        # Gestion du matériel
        story.extend(self._create_materiel_section())
        story.append(PageBreak())
        
        # Gestion des DJs
        story.extend(self._create_djs_section())
        story.append(PageBreak())
        
        # Rapports et statistiques
        story.extend(self._create_reports_section())
        story.append(PageBreak())
        
        # API et intégrations
        story.extend(self._create_api_section())
        story.append(PageBreak())
        
        # Installation et configuration
        story.extend(self._create_installation_section())
        story.append(PageBreak())
        
        # Support et contact
        story.extend(self._create_support_section())
        
        # Construire le PDF
        doc.build(story)
        return output_path
    
    def _create_cover_page(self):
        """Crée la page de couverture"""
        elements = []
        
        # Titre principal
        elements.append(Spacer(1, 3*cm))
        elements.append(Paragraph("🎵 PLANIFY v2.1", self.styles['MainTitle']))
        elements.append(Spacer(1, 1*cm))
        
        # Sous-titre
        elements.append(Paragraph(
            "<b>Application Complète de Gestion de Prestations DJ</b>",
            self.styles['ChapterTitle']
        ))
        elements.append(Spacer(1, 2*cm))
        
        # Description
        elements.append(Paragraph(
            "Solution professionnelle pour la gestion complète de votre activité DJ : "
            "planification des prestations, gestion du matériel, suivi des clients, "
            "rapports financiers et bien plus encore.",
            self.styles['NormalText']
        ))
        elements.append(Spacer(1, 2*cm))
        
        # Fonctionnalités clés
        key_features = [
            "✅ Gestion complète des prestations",
            "✅ Inventaire et réservation du matériel",
            "✅ Synchronisation Google Calendar",
            "✅ Rapports financiers avancés",
            "✅ Notifications automatiques",
            "✅ Application mobile",
            "✅ Génération de factures",
            "✅ Interface moderne et intuitive"
        ]
        
        for feature in key_features:
            elements.append(Paragraph(feature, self.styles['ListText']))
        
        elements.append(Spacer(1, 3*cm))
        
        # Date et version
        elements.append(Paragraph(
            f"Version 2.1 - {datetime.now().strftime('%B %Y')}",
            self.styles['CodeText']
        ))
        
        return elements
    
    def _create_table_of_contents(self):
        """Crée la table des matières"""
        elements = []
        
        elements.append(Paragraph("TABLE DES MATIÈRES", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 1*cm))
        
        toc_items = [
            ("1. Introduction", "3"),
            ("2. Fonctionnalités Principales", "4"),
            ("3. Gestion des Prestations", "5"),
            ("4. Gestion du Matériel", "6"),
            ("5. Gestion des DJs", "7"),
            ("6. Rapports et Statistiques", "8"),
            ("7. API et Intégrations", "9"),
            ("8. Installation et Configuration", "10"),
            ("9. Support et Contact", "11")
        ]
        
        for title, page in toc_items:
            elements.append(Paragraph(f"{title} ................. {page}", self.styles['ListText']))
        
        return elements
    
    def _create_introduction(self):
        """Crée la section introduction"""
        elements = []
        
        elements.append(Paragraph("1. INTRODUCTION", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph(
            "Planify v2.1 est une application complète de gestion de prestations DJ "
            "développée spécifiquement pour les professionnels du secteur. Cette solution "
            "intègre toutes les fonctionnalités nécessaires à la gestion efficace de votre "
            "activité, de la planification des prestations à la facturation en passant par "
            "la gestion du matériel et le suivi des clients.",
            self.styles['NormalText']
        ))
        
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph("🎯 Objectifs de Planify", self.styles['SectionTitle']))
        
        objectives = [
            "Centraliser la gestion de toutes vos prestations DJ",
            "Optimiser la planification et l'organisation",
            "Automatiser les tâches répétitives",
            "Améliorer la communication avec vos clients",
            "Générer des rapports détaillés pour le suivi financier",
            "Synchroniser avec vos outils existants (Google Calendar, etc.)"
        ]
        
        for objective in objectives:
            elements.append(Paragraph(f"• {objective}", self.styles['ListText']))
        
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph("👥 Utilisateurs Ciblés", self.styles['SectionTitle']))
        
        elements.append(Paragraph(
            "Planify s'adresse aux DJs professionnels, aux entreprises de prestations "
            "musicales, aux organisateurs d'événements et à toute structure nécessitant "
            "une gestion efficace des prestations musicales.",
            self.styles['NormalText']
        ))
        
        return elements
    
    def _create_main_features(self):
        """Crée la section fonctionnalités principales"""
        elements = []
        
        elements.append(Paragraph("2. FONCTIONNALITÉS PRINCIPALES", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Interface utilisateur
        elements.append(Paragraph("🎨 Interface Moderne et Intuitive", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Planify dispose d'une interface utilisateur moderne, responsive et intuitive "
            "qui s'adapte à tous les écrans (desktop, tablette, mobile). L'interface est "
            "conçue pour une utilisation professionnelle avec des couleurs soignées et "
            "une navigation fluide.",
            self.styles['NormalText']
        ))
        
        # Gestion des rôles
        elements.append(Paragraph("👥 Système de Rôles Avancé", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Planify intègre un système de rôles complet permettant de gérer différents "
            "types d'utilisateurs avec des permissions spécifiques :",
            self.styles['NormalText']
        ))
        
        roles = [
            "🔑 <b>Administrateur</b> : Accès complet à toutes les fonctionnalités",
            "👨‍💼 <b>Manager</b> : Gestion des prestations, rapports et équipe",
            "🎧 <b>DJ</b> : Consultation et mise à jour de ses prestations",
            "🔧 <b>Technicien</b> : Gestion du matériel et maintenance"
        ]
        
        for role in roles:
            elements.append(Paragraph(role, self.styles['ListText']))
        
        # Fonctionnalités clés
        elements.append(Paragraph("⭐ Fonctionnalités Clés", self.styles['SectionTitle']))
        
        features = [
            "📅 <b>Planification Avancée</b> : Calendrier interactif avec gestion des conflits",
            "🔧 <b>Gestion du Matériel</b> : Inventaire complet avec réservation automatique",
            "👥 <b>Gestion des Équipes</b> : DJs, techniciens avec profils détaillés",
            "📊 <b>Rapports Financiers</b> : Analyses détaillées et prévisions",
            "📱 <b>Application Mobile</b> : Accès mobile avec API REST complète",
            "📧 <b>Notifications</b> : Rappels automatiques par email",
            "🧾 <b>Facturation</b> : Génération automatique de factures PDF",
            "📅 <b>Intégrations</b> : Synchronisation Google Calendar bidirectionnelle"
        ]
        
        for feature in features:
            elements.append(Paragraph(feature, self.styles['ListText']))
        
        return elements
    
    def _create_prestations_section(self):
        """Crée la section gestion des prestations"""
        elements = []
        
        elements.append(Paragraph("3. GESTION DES PRESTATIONS", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph(
            "Le module de gestion des prestations est le cœur de Planify. Il permet de "
            "créer, organiser et suivre toutes vos prestations DJ avec une précision "
            "professionnelle.",
            self.styles['NormalText']
        ))
        
        # Création de prestations
        elements.append(Paragraph("📝 Création de Prestations", self.styles['SectionTitle']))
        
        creation_features = [
            "Informations client complètes (nom, téléphone, email)",
            "Sélection des dates et heures avec vérification des conflits",
            "Association automatique du DJ et du matériel",
            "Gestion des lieux et adresses",
            "Notes et commentaires personnalisés",
            "Statuts multiples : planifiée, confirmée, terminée, annulée"
        ]
        
        for feature in creation_features:
            elements.append(Paragraph(f"• {feature}", self.styles['ListText']))
        
        # Vérification automatique
        elements.append(Paragraph("🔍 Vérification Automatique", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Planify vérifie automatiquement la disponibilité du matériel et des DJs "
            "lors de la création d'une prestation, évitant ainsi les conflits et les "
            "double-réservations.",
            self.styles['NormalText']
        ))
        
        # Suivi des prestations
        elements.append(Paragraph("📈 Suivi et Historique", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Chaque prestation est suivie avec un historique complet des modifications, "
            "des notifications automatiques et un suivi des statuts en temps réel.",
            self.styles['NormalText']
        ))
        
        return elements
    
    def _create_materiel_section(self):
        """Crée la section gestion du matériel"""
        elements = []
        
        elements.append(Paragraph("4. GESTION DU MATÉRIEL", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph(
            "Le module de gestion du matériel permet de gérer efficacement votre inventaire "
            "de matériel DJ avec un système de réservation intelligent et une traçabilité "
            "complète.",
            self.styles['NormalText']
        ))
        
        # Inventaire
        elements.append(Paragraph("📦 Gestion de l'Inventaire", self.styles['SectionTitle']))
        
        inventory_features = [
            "Catalogue complet du matériel par catégorie",
            "Gestion des quantités et stocks",
            "Localisation par entrepôt/local",
            "Statuts dynamiques : disponible, réservé, maintenance",
            "Historique des mouvements",
            "Alertes de maintenance préventive"
        ]
        
        for feature in inventory_features:
            elements.append(Paragraph(f"• {feature}", self.styles['ListText']))
        
        # Réservation automatique
        elements.append(Paragraph("🔒 Système de Réservation", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Lors de la création d'une prestation, le matériel est automatiquement "
            "réservé pour la période concernée, évitant les conflits et les "
            "double-réservations.",
            self.styles['NormalText']
        ))
        
        # Interface d'affichage
        elements.append(Paragraph("📺 Interface d'Affichage", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Planify dispose d'une interface d'affichage optimisée pour les écrans "
            "dédiés, permettant de visualiser en temps réel l'état du matériel par local.",
            self.styles['NormalText']
        ))
        
        return elements
    
    def _create_djs_section(self):
        """Crée la section gestion des DJs"""
        elements = []
        
        elements.append(Paragraph("5. GESTION DES DJS", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph(
            "Le module de gestion des DJs permet d'organiser votre équipe avec des "
            "profils détaillés, des statistiques de performance et une intégration "
            "Google Calendar pour chaque DJ.",
            self.styles['NormalText']
        ))
        
        # Profils DJ
        elements.append(Paragraph("👤 Profils DJ Complets", self.styles['SectionTitle']))
        
        profile_features = [
            "Informations personnelles et de contact",
            "Historique des prestations",
            "Statistiques de performance",
            "Notes et commentaires",
            "Gestion des disponibilités",
            "Intégration Google Calendar personnelle"
        ]
        
        for feature in profile_features:
            elements.append(Paragraph(f"• {feature}", self.styles['ListText']))
        
        # Synchronisation Google Calendar
        elements.append(Paragraph("📅 Synchronisation Google Calendar", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Chaque DJ peut connecter son compte Google Calendar personnel pour une "
            "synchronisation bidirectionnelle automatique de ses prestations.",
            self.styles['NormalText']
        ))
        
        # Statistiques
        elements.append(Paragraph("📊 Statistiques de Performance", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Planify génère automatiquement des statistiques détaillées pour chaque DJ : "
            "nombre de prestations, revenus générés, taux de confirmation, etc.",
            self.styles['NormalText']
        ))
        
        return elements
    
    def _create_reports_section(self):
        """Crée la section rapports et statistiques"""
        elements = []
        
        elements.append(Paragraph("6. RAPPORTS ET STATISTIQUES", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph(
            "Planify intègre un système de rapports complet permettant d'analyser "
            "votre activité, vos performances et vos revenus avec des données précises "
            "et des visualisations claires.",
            self.styles['NormalText']
        ))
        
        # Rapports financiers
        elements.append(Paragraph("💰 Rapports Financiers", self.styles['SectionTitle']))
        
        financial_reports = [
            "Analyse des revenus par période",
            "Calcul de la rentabilité par prestation",
            "Analyse des clients et de leur valeur",
            "Performance des DJs",
            "Prévisions de revenus",
            "Export des données pour comptabilité"
        ]
        
        for report in financial_reports:
            elements.append(Paragraph(f"• {report}", self.styles['ListText']))
        
        # Tableau de bord
        elements.append(Paragraph("📊 Tableau de Bord Temps Réel", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Le tableau de bord principal affiche en temps réel les métriques clés : "
            "prestations du jour, matériel réservé, revenus du mois, etc.",
            self.styles['NormalText']
        ))
        
        # Calendrier interactif
        elements.append(Paragraph("📅 Calendrier Interactif", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Un calendrier interactif permet de visualiser toutes les prestations "
            "avec des filtres par DJ, local ou type de prestation.",
            self.styles['NormalText']
        ))
        
        return elements
    
    def _create_api_section(self):
        """Crée la section API et intégrations"""
        elements = []
        
        elements.append(Paragraph("7. API ET INTÉGRATIONS", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph(
            "Planify dispose d'une API REST complète permettant l'intégration avec "
            "d'autres systèmes et le développement d'applications mobiles personnalisées.",
            self.styles['NormalText']
        ))
        
        # API Mobile
        elements.append(Paragraph("📱 API Mobile", self.styles['SectionTitle']))
        
        mobile_api_features = [
            "Authentification JWT sécurisée",
            "Consultation des prestations",
            "Mise à jour des statuts",
            "Accès aux statistiques personnelles",
            "Gestion des notifications",
            "Synchronisation hors-ligne"
        ]
        
        for feature in mobile_api_features:
            elements.append(Paragraph(f"• {feature}", self.styles['ListText']))
        
        # Intégrations
        elements.append(Paragraph("🔗 Intégrations Externes", self.styles['SectionTitle']))
        
        integrations = [
            "Google Calendar : Synchronisation bidirectionnelle",
            "Email : Notifications automatiques",
            "Export : CSV, PDF, Excel",
            "Webhooks : Intégrations personnalisées"
        ]
        
        for integration in integrations:
            elements.append(Paragraph(f"• {integration}", self.styles['ListText']))
        
        return elements
    
    def _create_installation_section(self):
        """Crée la section installation"""
        elements = []
        
        elements.append(Paragraph("8. INSTALLATION ET CONFIGURATION", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Prérequis
        elements.append(Paragraph("📋 Prérequis Système", self.styles['SectionTitle']))
        
        requirements = [
            "macOS 10.14 ou supérieur",
            "Python 3.8+ (inclus dans l'installation)",
            "2 GB RAM minimum",
            "500 MB d'espace disque",
            "Connexion internet pour les mises à jour"
        ]
        
        for requirement in requirements:
            elements.append(Paragraph(f"• {requirement}", self.styles['ListText']))
        
        # Installation
        elements.append(Paragraph("⚙️ Installation", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "L'installation de Planify est simple et guidée :",
            self.styles['NormalText']
        ))
        
        installation_steps = [
            "1. Télécharger l'application Planify",
            "2. Lancer l'installation automatique",
            "3. Configurer les paramètres initiaux",
            "4. Créer le compte administrateur",
            "5. Commencer à utiliser l'application"
        ]
        
        for step in installation_steps:
            elements.append(Paragraph(step, self.styles['ListText']))
        
        # Configuration
        elements.append(Paragraph("🔧 Configuration", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Planify se configure automatiquement lors du premier lancement avec "
            "une interface d'initialisation guidée.",
            self.styles['NormalText']
        ))
        
        return elements
    
    def _create_support_section(self):
        """Crée la section support"""
        elements = []
        
        elements.append(Paragraph("9. SUPPORT ET CONTACT", self.styles['ChapterTitle']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Support technique
        elements.append(Paragraph("🛠️ Support Technique", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Notre équipe technique est disponible pour vous accompagner dans "
            "l'utilisation de Planify et résoudre tout problème technique.",
            self.styles['NormalText']
        ))
        
        # Formation
        elements.append(Paragraph("📚 Formation", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Nous proposons des sessions de formation personnalisées pour "
            "vous familiariser avec toutes les fonctionnalités de Planify.",
            self.styles['NormalText']
        ))
        
        # Mises à jour
        elements.append(Paragraph("🔄 Mises à Jour", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Planify évolue régulièrement avec de nouvelles fonctionnalités. "
            "Les mises à jour sont automatiques et gratuites.",
            self.styles['NormalText']
        ))
        
        # Contact
        elements.append(Paragraph("📞 Contact", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Pour toute question ou demande d'information :",
            self.styles['NormalText']
        ))
        
        contact_info = [
            "📧 Email : greg.nizery@outlook.fr",
            "📱 Téléphone : 06 46 42 97 06",
            "🌐 Site web : www.planify.app",
            "💬 Chat en ligne disponible 24/7"
        ]
        
        for info in contact_info:
            elements.append(Paragraph(info, self.styles['ListText']))
        
        return elements

# Générer le manuel
if __name__ == "__main__":
    generator = PlanifyManualGenerator()
    output_file = generator.generate_manual()
    logger.info(f"✅ Manuel PDF généré : {output_file}")





