#!/usr/bin/env python3
"""
Générateur de factures automatiques pour Planify
"""

from datetime import datetime, date
# Import sera fait dans les fonctions pour éviter les imports circulaires
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)

class InvoiceGenerator:
    """Générateur de factures automatiques"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Configure les styles personnalisés"""
        # Style pour le titre
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#667eea')
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#374151')
        ))
        
        # Style pour les informations
        self.styles.add(ParagraphStyle(
            name='InfoText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
    
    def generate_invoice_from_prestation(self, prestation, output_path=None):
        """Génère une facture à partir d'une prestation"""
        try:
            from app import ParametresEntreprise
            # Récupérer les paramètres de l'entreprise
            params = ParametresEntreprise.query.first()
            if not params:
                raise Exception("Paramètres d'entreprise non configurés")
            
            # Créer le document PDF
            if output_path:
                doc = SimpleDocTemplate(output_path, pagesize=A4)
            else:
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4)
            
            # Contenu de la facture
            story = []
            
            # En-tête de la facture
            story.append(self._create_header(params))
            story.append(Spacer(1, 20))
            
            # Informations client
            story.append(self._create_client_info(prestation))
            story.append(Spacer(1, 20))
            
            # Détails de la prestation
            story.append(self._create_prestation_details(prestation))
            story.append(Spacer(1, 20))
            
            # Tableau des tarifs
            story.append(self._create_pricing_table(prestation))
            story.append(Spacer(1, 20))
            
            # Total et mentions
            story.append(self._create_total_and_notes(prestation))
            
            # Construire le PDF
            doc.build(story)
            
            if output_path:
                return output_path
            else:
                buffer.seek(0)
                return buffer.getvalue()
                
        except Exception as e:
            logger.exception('Erreur génération facture')
            return None
    
    def _create_header(self, params):
        """Crée l'en-tête de la facture"""
        elements = []
        
        # Titre de l'entreprise
        elements.append(Paragraph(f"<b>{params.nom_entreprise}</b>", self.styles['CustomTitle']))
        
        # Informations de l'entreprise
        company_info = []
        if params.adresse:
            company_info.append(params.adresse)
        if params.code_postal and params.ville:
            company_info.append(f"{params.code_postal} {params.ville}")
        if params.telephone:
            company_info.append(f"Tél: {params.telephone}")
        if params.email:
            company_info.append(f"Email: {params.email}")
        if params.site_web:
            company_info.append(f"Web: {params.site_web}")
        
        for info in company_info:
            elements.append(Paragraph(info, self.styles['InfoText']))
        
        # Numéro de facture et date
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"<b>FACTURE N° {self._generate_invoice_number()}</b>", self.styles['CustomSubtitle']))
        elements.append(Paragraph(f"Date: {date.today().strftime('%d/%m/%Y')}", self.styles['InfoText']))
        
        return elements
    
    def _create_client_info(self, prestation):
        """Crée la section informations client"""
        elements = []
        
        elements.append(Paragraph("<b>FACTURÉ À :</b>", self.styles['CustomSubtitle']))
        elements.append(Paragraph(f"<b>{prestation.client}</b>", self.styles['InfoText']))
        
        if prestation.client_telephone:
            elements.append(Paragraph(f"Téléphone: {prestation.client_telephone}", self.styles['InfoText']))
        if prestation.client_email:
            elements.append(Paragraph(f"Email: {prestation.client_email}", self.styles['InfoText']))
        
        return elements
    
    def _create_prestation_details(self, prestation):
        """Crée la section détails de la prestation"""
        elements = []
        
        elements.append(Paragraph("<b>DÉTAILS DE LA PRESTATION :</b>", self.styles['CustomSubtitle']))
        
        # Tableau des détails
        data = [
            ['Date', prestation.date_debut.strftime('%d/%m/%Y')],
            ['Heure', f"{prestation.heure_debut.strftime('%H:%M')} - {prestation.heure_fin.strftime('%H:%M')}"],
            ['Lieu', prestation.lieu],
            ['DJ', prestation.dj.nom if prestation.dj else 'À confirmer'],
            ['Statut', prestation.statut.title()]
        ]
        
        if prestation.notes:
            data.append(['Notes', prestation.notes])
        
        table = Table(data, colWidths=[4*cm, 8*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        return elements
    
    def _create_pricing_table(self, prestation):
        """Crée le tableau des tarifs"""
        elements = []
        
        elements.append(Paragraph("<b>TARIFS :</b>", self.styles['CustomSubtitle']))
        
        # Calculer la durée
        start_time = datetime.combine(prestation.date_debut, prestation.heure_debut)
        end_time = datetime.combine(prestation.date_fin, prestation.heure_fin)
        
        # Si l'événement se termine le lendemain
        if prestation.date_fin > prestation.date_debut:
            end_time += timedelta(days=1)
        
        duration = end_time - start_time
        hours = duration.total_seconds() / 3600
        
        # Tarif par défaut (à personnaliser selon vos besoins)
        hourly_rate = 150.0  # €/heure
        total_ht = hours * hourly_rate
        tva_rate = 20.0  # %
        tva_amount = total_ht * (tva_rate / 100)
        total_ttc = total_ht + tva_amount
        
        data = [
            ['Description', 'Quantité', 'Prix unitaire', 'Total HT'],
            ['Prestation DJ', f"{hours:.1f}h", f"{hourly_rate:.2f} €", f"{total_ht:.2f} €"]
        ]
        
        table = Table(data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        # Totaux
        totals_data = [
            ['', '', 'Sous-total HT:', f"{total_ht:.2f} €"],
            ['', '', f'TVA ({tva_rate}%):', f"{tva_amount:.2f} €"],
            ['', '', '<b>TOTAL TTC:</b>', f"<b>{total_ttc:.2f} €</b>"]
        ]
        
        totals_table = Table(totals_data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (2, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (2, 2), (-1, 2), 12),
            ('GRID', (2, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(totals_table)
        return elements
    
    def _create_total_and_notes(self, prestation):
        """Crée la section total et mentions"""
        elements = []
        
        elements.append(Paragraph("<b>CONDITIONS DE PAIEMENT :</b>", self.styles['CustomSubtitle']))
        elements.append(Paragraph("Paiement à réception de facture", self.styles['InfoText']))
        elements.append(Paragraph("Virement bancaire accepté", self.styles['InfoText']))
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>MENTIONS LÉGALES :</b>", self.styles['CustomSubtitle']))
        elements.append(Paragraph("En cas de retard de paiement, des pénalités de 3 fois le taux d'intérêt légal seront appliquées.", self.styles['InfoText']))
        elements.append(Paragraph("Une indemnité forfaitaire pour frais de recouvrement de 40€ sera exigée.", self.styles['InfoText']))
        
        return elements
    
    def _generate_invoice_number(self):
        """Génère un numéro de facture unique"""
        from app import generate_document_number
        return generate_document_number('FAC')
    
    def generate_invoice_pdf(self, prestation_id, output_path=None):
        """Génère une facture PDF pour une prestation"""
        try:
            from app import app, db, Prestation
            with app.app_context():
                prestation = db.session.get(Prestation, prestation_id)
                if not prestation:
                    return None
                
                return self.generate_invoice_from_prestation(prestation, output_path)
        except Exception as e:
            logger.error(f"Erreur génération facture PDF : {e}")
            return None

# Instance globale
invoice_generator = InvoiceGenerator()
