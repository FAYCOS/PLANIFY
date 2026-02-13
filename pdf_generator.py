#!/usr/bin/env python3
"""
Générateur PDF professionnel pour les devis - Design sobre noir et blanc
"""

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfgen import canvas
from functools import partial
from reportlab.platypus.frames import Frame
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from reportlab.lib.colors import black, white, grey, lightgrey
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import re
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, footer_text='', font_name='Helvetica', **kwargs):
        self.footer_text = footer_text
        self.font_name = font_name
        self._saved_page_states = []
        super().__init__(*args, **kwargs)

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        self.setFont(self.font_name, 8)
        y = 18
        if self.footer_text:
            self.drawString(40, y, self.footer_text)
        self.drawRightString(555, y, f"{self._pageNumber} / {page_count}")


def _ensure_devis_fonts():
    """Register Manrope fonts if available, fallback to Helvetica."""
    try:
        fonts_dir = os.path.join('static', 'fonts')
        regular_path = os.path.join(fonts_dir, 'Manrope-Regular.ttf')
        semibold_path = os.path.join(fonts_dir, 'Manrope-SemiBold.ttf')
        if os.path.exists(regular_path):
            pdfmetrics.registerFont(TTFont('Manrope-Regular', regular_path))
        if os.path.exists(semibold_path):
            pdfmetrics.registerFont(TTFont('Manrope-SemiBold', semibold_path))
    except Exception as e:
        logger.warning(f"Impossible d'enregistrer les polices Manrope: {e}")


class DevisPDFGenerator:
    def __init__(self, parametres_entreprise=None):
        _ensure_devis_fonts()
        self.styles = getSampleStyleSheet()
        self.parametres_entreprise = parametres_entreprise
        self.font_regular = 'Manrope-Regular' if 'Manrope-Regular' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        self.font_semibold = 'Manrope-SemiBold' if 'Manrope-SemiBold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
        self.setup_custom_styles()

    def _get_company_signature_image(self):
        """Retourne l'image de signature entreprise si disponible."""
        if not self.parametres_entreprise:
            return None
        signature_path = getattr(self.parametres_entreprise, 'signature_entreprise_path', None)
        if not signature_path:
            return None
        full_path = os.path.join("static", "uploads", signature_path)
        if not os.path.exists(full_path):
            return None
        try:
            return Image(full_path, width=3*inch, height=1.5*inch, kind='proportional')
        except Exception as e:
            logger.error(f"Erreur chargement signature entreprise: {e}")
            return None
    
    def setup_custom_styles(self):
        """Configure les styles personnalisés - Design sobre noir et blanc"""
        
        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=black,
            fontName=self.font_semibold,
            leading=32
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=black,
            fontName=self.font_semibold,
            leading=16
        ))
        
        # Style pour les informations client
        self.styles.add(ParagraphStyle(
            name='ClientInfo',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=4,
            textColor=black,
            fontName=self.font_regular,
            leading=13
        ))
        
        # Style pour les informations entreprise
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=3,
            textColor=black,
            fontName=self.font_regular,
            leading=12,
            alignment=TA_RIGHT
        ))
        
        # Style pour les montants
        self.styles.add(ParagraphStyle(
            name='Amount',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=black,
            fontName=self.font_semibold,
            alignment=TA_RIGHT,
            leading=14
        ))
        
        # Style pour le total
        self.styles.add(ParagraphStyle(
            name='Total',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=black,
            fontName=self.font_semibold,
            alignment=TA_RIGHT,
            leading=18
        ))
        
        # Style pour les conditions
        self.styles.add(ParagraphStyle(
            name='Conditions',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=black,
            fontName=self.font_regular,
            leading=11,
            alignment=TA_JUSTIFY
        ))

        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=black,
            fontName=self.font_regular,
            leading=14,
            alignment=TA_JUSTIFY
        ))
    
    def create_entreprise_header(self):
        """Crée l'en-tête avec les informations de l'entreprise et logo"""
        if not self.parametres_entreprise:
            return []
        
        elements = []
        
        # Tableau principal avec logo et informations
        header_data = [['', '']]
        
        # Logo (si disponible) - Support PNG optimisé
        if self.parametres_entreprise.logo_path:
            logo_path = f"static/uploads/{self.parametres_entreprise.logo_path}"
            if os.path.exists(logo_path):
                try:
                    # Redimensionner le logo pour qu'il soit proportionnel
                    logo = Image(logo_path, width=2.5*inch, height=1.2*inch, kind='proportional')
                    header_data[0][0] = logo
                except Exception as e:
                    logger.error(f"Erreur lors du chargement du logo: {e}")
                    # Si le logo ne peut pas être chargé, on laisse la cellule vide
                    header_data[0][0] = ""
        
        # Nom de l'entreprise et informations
        nom_entreprise = self.parametres_entreprise.nom_entreprise or "DJ Prestations Manager"
        company_text = f"<b>{nom_entreprise}</b>"
        
        # Informations de contact
        contact_info = []
        if self.parametres_entreprise.adresse:
            contact_info.append(self.parametres_entreprise.adresse)
        if self.parametres_entreprise.code_postal and self.parametres_entreprise.ville:
            contact_info.append(f"{self.parametres_entreprise.code_postal} {self.parametres_entreprise.ville}")
        if self.parametres_entreprise.telephone:
            contact_info.append(f"Tél: {self.parametres_entreprise.telephone}")
        if self.parametres_entreprise.email:
            contact_info.append(f"Email: {self.parametres_entreprise.email}")
        if self.parametres_entreprise.site_web:
            contact_info.append(f"Web: {self.parametres_entreprise.site_web}")
        
        if contact_info:
            company_text += "<br/><br/>" + "<br/>".join(contact_info)
        
        # Informations légales
        legal_info = []
        if self.parametres_entreprise.forme_juridique:
            legal_info.append(f"Forme juridique: {self.parametres_entreprise.forme_juridique}")
        if self.parametres_entreprise.capital_social:
            legal_info.append(f"Capital social: {self.parametres_entreprise.capital_social}")
        if self.parametres_entreprise.numero_rcs or self.parametres_entreprise.rcs_ville:
            rcs = " ".join([x for x in [self.parametres_entreprise.rcs_ville, self.parametres_entreprise.numero_rcs] if x])
            if rcs:
                legal_info.append(f"RCS: {rcs}")
        if self.parametres_entreprise.siret:
            legal_info.append(f"SIRET: {self.parametres_entreprise.siret}")
        if self.parametres_entreprise.tva_intracommunautaire:
            legal_info.append(f"TVA: {self.parametres_entreprise.tva_intracommunautaire}")
        elif getattr(self.parametres_entreprise, 'tva_non_applicable', False):
            legal_info.append("TVA non applicable, art. 293 B du CGI")
        
        if legal_info:
            company_text += "<br/><br/>" + "<br/>".join(legal_info)
        
        header_data[0][1] = Paragraph(company_text, self.styles['CompanyInfo'])
        
        # Créer le tableau d'en-tête
        header_table = Table(header_data, colWidths=[3*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Logo à gauche
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # Infos entreprise à droite
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(header_table)
        
        # Ligne de séparation
        elements.append(Spacer(1, 15))
        # Utiliser un tableau pour créer une ligne
        line_table = Table([['']], colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, black),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 20))
        
        return elements

    def create_header(self, devis):
        """Crée l'en-tête du devis"""
        story = []

        # Titre principal
        title = Paragraph("Devis", self.styles['CustomTitle'])
        story.append(title)
        
        # Informations du devis dans un tableau sobre
        creation_date = devis.date_creation.strftime('%d/%m/%Y') if devis.date_creation else datetime.now().strftime('%d/%m/%Y')
        validity_date = devis.date_validite.strftime('%d/%m/%Y') if devis.date_validite else 'Non définie'
        
        info_data = [
            ['Numéro de devis:', devis.numero],
            ['Date d\'émission:', creation_date],
            ['Validité jusqu\'au:', validity_date]
        ]
        
        info_table = Table(info_data, colWidths=[2.5*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (0, -1), lightgrey),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 25))
        
        return story
    
    def create_client_section(self, devis):
        """Crée la section client"""
        story = []

        # Émetteur
        if self.parametres_entreprise:
            story.append(Paragraph("Émetteur ou Émettrice", self.styles['CustomHeading2']))
            line_table = Table([['']], colWidths=[1.6*inch])
            line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
            story.append(line_table)
            story.append(Spacer(1, 6))
            info = f"<b>{self.parametres_entreprise.nom_entreprise or 'Entreprise'}</b>"
            if self.parametres_entreprise.adresse:
                info += f"<br/>{self.parametres_entreprise.adresse}"
            cp_ville = " ".join([x for x in [self.parametres_entreprise.code_postal, self.parametres_entreprise.ville] if x])
            if cp_ville.strip():
                info += f"<br/>{cp_ville}"
            if self.parametres_entreprise.email:
                info += f"<br/>{self.parametres_entreprise.email}"
            story.append(Paragraph(info, self.styles['ClientInfo']))
            story.append(Spacer(1, 12))

        story.append(Paragraph("Client ou Cliente", self.styles['CustomHeading2']))
        line_table = Table([['']], colWidths=[1.2*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        story.append(line_table)
        story.append(Spacer(1, 6))

        client_info = f"<b>{devis.client_nom}</b>"
        if devis.client_adresse:
            client_info += f"<br/>{devis.client_adresse.replace(chr(10), '<br/>')}"
        if devis.client_email:
            client_info += f"<br/>{devis.client_email}"

        story.append(Paragraph(client_info, self.styles['ClientInfo']))
        story.append(Spacer(1, 12))

        return story
    
    def create_prestation_section(self, devis):
        """Crée la section description prestation"""
        story = []
        story.append(Paragraph("Description de la prestation", self.styles['CustomHeading2']))
        line_table = Table([['']], colWidths=[2.2*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        story.append(line_table)
        story.append(Spacer(1, 6))

        description = devis.prestation_description or ''
        if not description:
            description = f"Prestation le {devis.date_prestation.strftime('%d/%m/%Y')} à {devis.lieu}"
        story.append(Paragraph(description, self.styles['CustomBody']))
        story.append(Spacer(1, 12))
        return story

    def _sanitize_html_for_pdf(self, html_content):
        """Nettoie le HTML du contenu riche pour un rendu PDF simple."""
        if not html_content:
            return ''
        text = html_content
        text = text.replace('&nbsp;', ' ')
        text = re.sub(r'<\\s*(br|BR)\\s*/?>', '<br/>', text)
        text = re.sub(r'<\\s*/?p\\s*>', '<br/>', text)
        text = re.sub(r'<\\s*/?div\\s*>', '<br/>', text)
        text = re.sub(r'<\\s*strong\\s*>', '<b>', text, flags=re.IGNORECASE)
        text = re.sub(r'<\\s*/\\s*strong\\s*>', '</b>', text, flags=re.IGNORECASE)
        text = re.sub(r'<\\s*em\\s*>', '<i>', text, flags=re.IGNORECASE)
        text = re.sub(r'<\\s*/\\s*em\\s*>', '</i>', text, flags=re.IGNORECASE)
        text = re.sub(r'<\\s*h[1-4][^>]*>', '<b>', text, flags=re.IGNORECASE)
        text = re.sub(r'</\\s*h[1-4]\\s*>', '</b><br/>', text, flags=re.IGNORECASE)
        text = re.sub(r'<\\s*li\\s*>', '&#8226; ', text, flags=re.IGNORECASE)
        text = re.sub(r'</\\s*li\\s*>', '<br/>', text, flags=re.IGNORECASE)
        text = re.sub(r'</?ul[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?ol[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?span[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?a[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?[^>]+>', '', text)
        return text

    def create_custom_content_section(self, devis):
        """Ajoute le contenu personnalise du devis si present."""
        if not getattr(devis, 'contenu_html', None):
            return []
        sanitized = self._sanitize_html_for_pdf(devis.contenu_html)
        if not sanitized.strip():
            return []
        story = []
        story.append(Paragraph("CONTENU DU DEVIS", self.styles['CustomHeading2']))
        line_table = Table([['']], colWidths=[2.2*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, black),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 8))
        story.append(Paragraph(sanitized, self.styles['CustomBody']))
        story.append(Spacer(1, 20))
        return story

    def create_materiel_section(self, devis):
        """Crée la section matériel fourni (liste synthétique)"""
        story = []

        story.append(Paragraph("Matériel fourni", self.styles['CustomHeading2']))
        line_table = Table([['']], colWidths=[1.6*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, black),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 8))

        materiel_assignes = []
        try:
            from app import MaterielPresta, Materiel
            if hasattr(devis, 'prestation_id') and devis.prestation_id:
                materiel_assignes = MaterielPresta.query.filter_by(prestation_id=devis.prestation_id).all()
            elif hasattr(devis, 'reservation_origine') and devis.reservation_origine:
                materiel_assignes = MaterielPresta.query.filter_by(reservation_id=devis.reservation_origine.id).all()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du matériel: {e}")
            materiel_assignes = []

        if materiel_assignes:
            categories = []
            for mp in materiel_assignes:
                materiel = Materiel.query.get(mp.materiel_id)
                if materiel and materiel.categorie and materiel.categorie not in categories:
                    categories.append(materiel.categorie)
            if categories:
                story.append(Paragraph("<br/>".join(categories), self.styles['CustomBody']))
            else:
                story.append(Paragraph("Matériel fourni selon la configuration validée.", self.styles['CustomBody']))
        else:
            story.append(Paragraph("Aucun matériel assigné à cette prestation.", self.styles['CustomBody']))

        story.append(Spacer(1, 16))
        return story
    
    def create_pricing_table(self, devis, include_tva=False, taux_tva=20.0):
        """Crée le tableau de tarification avec sous-totaux par groupe."""
        story = []

        story.append(Paragraph("Produits", self.styles['CustomHeading2']))
        line_table = Table([['']], colWidths=[1.2*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        story.append(line_table)
        story.append(Spacer(1, 6))

        from app import MaterielPresta, Materiel
        groups = []

        # Prestation / services group
        prestation_lines = []
        if devis.tarif_horaire and devis.duree_heures:
            total_ht = devis.tarif_horaire * devis.duree_heures
            prestation_lines.append({
                'label': devis.prestation_titre or 'Prestation',
                'quantite': f"{devis.duree_heures:.0f} heures",
                'prix_unitaire': devis.tarif_horaire,
                'total_ht': total_ht
            })
        if devis.frais_transport and devis.frais_transport > 0:
            prestation_lines.append({
                'label': 'Frais de déplacement',
                'quantite': '1 unité',
                'prix_unitaire': devis.frais_transport,
                'total_ht': devis.frais_transport
            })
        if devis.frais_materiel and devis.frais_materiel > 0:
            prestation_lines.append({
                'label': 'Frais matériel',
                'quantite': '1 unité',
                'prix_unitaire': devis.frais_materiel,
                'total_ht': devis.frais_materiel
            })
        if prestation_lines:
            groups.append(('Prestations', prestation_lines))

        # Matériel groupé par catégorie
        try:
            materiel_assignes = MaterielPresta.query.filter_by(prestation_id=devis.prestation_id).all() if devis.prestation_id else []
        except Exception:
            materiel_assignes = []

        if materiel_assignes:
            grouped = {}
            for mp in materiel_assignes:
                materiel = Materiel.query.get(mp.materiel_id)
                if not materiel:
                    continue
                key = materiel.categorie or 'Produits'
                grouped.setdefault(key, []).append((materiel, mp))
            for key, items in grouped.items():
                lines = []
                for materiel, mp in items:
                    qte = mp.quantite
                    pu = materiel.prix_location or 0.0
                    lines.append({
                        'label': materiel.nom,
                        'quantite': f"{qte} unité{'s' if qte > 1 else ''}",
                        'prix_unitaire': pu,
                        'total_ht': pu * qte
                    })
                groups.append((key, lines))

        grand_total_ht = 0.0
        grand_total_ttc = 0.0

        for group_name, lines in groups:
            data = [[
                'Produits', 'Qté', 'Prix u. HT', 'TVA (%)', 'Total HT', 'Total TTC'
            ]]
            group_total_ht = 0.0
            group_total_ttc = 0.0

            for line in lines:
                total_ht = line['total_ht']
                total_ttc = total_ht * (1 + (taux_tva / 100.0) if include_tva else 1)
                data.append([
                    line['label'],
                    line['quantite'],
                    f"{line['prix_unitaire']:.2f} €",
                    f"{taux_tva:.0f}%" if include_tva else '0%',
                    f"{total_ht:.2f} €",
                    f"{total_ttc:.2f} €",
                ])
                group_total_ht += total_ht
                group_total_ttc += total_ttc

            data.append(['Sous-Total', '', '', '', f"{group_total_ht:.2f} €", f"{group_total_ttc:.2f} €"])

            table = Table(data, colWidths=[2.8*inch, 0.8*inch, 1.0*inch, 0.8*inch, 1.0*inch, 1.0*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), self.font_semibold),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 1), (-1, -2), 'RIGHT'),
                ('GRID', (0, 0), (-1, -2), 0.25, grey),
                ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), self.font_semibold),
                ('ALIGN', (4, -1), (-1, -1), 'RIGHT'),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

            grand_total_ht += group_total_ht
            grand_total_ttc += group_total_ttc

        # Totals recap
        recap = Table([
            ['Récapitulatif', ''],
            ['Total HT', f"{grand_total_ht:.2f} €"],
            ['Total TVA', f"{(grand_total_ttc - grand_total_ht):.2f} €"],
            ['Total TTC', f"{grand_total_ttc:.2f} €"],
        ], colWidths=[2.0*inch, 2.0*inch])
        recap.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_regular),
            ('FONTNAME', (0, 0), (0, 0), self.font_semibold),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.25, grey),
        ]))
        story.append(recap)
        story.append(Spacer(1, 12))

        if include_tva:
            details = Table([
                ['Détails TVA', ''],
                ['Taux', f"{taux_tva:.0f}%"],
                ['Montant TVA', f"{(grand_total_ttc - grand_total_ht):.2f} €"],
                ['Base HT', f"{grand_total_ht:.2f} €"],
            ], colWidths=[2.0*inch, 2.0*inch])
            details.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_regular),
                ('FONTNAME', (0, 0), (0, 0), self.font_semibold),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.25, grey),
            ]))
            story.append(details)
            story.append(Spacer(1, 12))
        return story

    def create_conditions_section(self, devis):
        """Crée la section conditions de paiement"""
        story = []
        story.append(Paragraph("Paiement", self.styles['CustomHeading2']))
        line_table = Table([['']], colWidths=[1.0*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        story.append(line_table)
        story.append(Spacer(1, 6))

        iban = getattr(self.parametres_entreprise, 'rib_iban', '') if self.parametres_entreprise else ''
        titulaire = getattr(self.parametres_entreprise, 'rib_titulaire', '') if self.parametres_entreprise else ''
        bloc = []
        if titulaire:
            bloc.append(f"Établissement : {titulaire}")
        if iban:
            bloc.append(f"IBAN : {iban}")
        if not bloc:
            bloc.append("Paiement par virement ou carte.")

        story.append(Paragraph('<br/>'.join(bloc), self.styles['CustomBody']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(
            "Pénalités de retard : trois fois le taux annuel d’intérêt légal en vigueur calculé depuis la date d’échéance jusqu’à complet paiement du prix.",
            self.styles['CustomBody']
        ))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "Indemnité forfaitaire pour frais de recouvrement en cas de retard de paiement : 40 €",
            self.styles['CustomBody']
        ))
        return story
    
    def create_signature_section(self, devis, include_company_signature=True):
        """Crée la section signature"""
        story = []
        story.append(Paragraph('Date et signature précédées de la mention "Bon pour accord"', self.styles['CustomBody']))
        story.append(Spacer(1, 12))
        if include_company_signature:
            signature_img = self._get_company_signature_image()
            if signature_img:
                story.append(signature_img)
        story.append(Spacer(1, 12))
        return story
    
    def generate_pdf(self, devis, output_path=None):
        """Génère le PDF complet du devis"""
        if output_path is None:
            output_path = f"devis_{devis.numero}.pdf"
        
        # Création du document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        # Construction du contenu
        story = []
        
        # En-tête
        story.extend(self.create_header(devis))
        
        # Section client
        story.extend(self.create_client_section(devis))
        
        # Section prestation
        story.extend(self.create_prestation_section(devis))

        # Contenu personnalise
        story.extend(self.create_custom_content_section(devis))
        
        # Section matériel
        story.extend(self.create_materiel_section(devis))
        
        # Tableau tarification
        story.extend(self.create_pricing_table(devis))
        
        # Conditions
        story.extend(self.create_conditions_section(devis))
        
        # Signature
        include_company_signature = bool(getattr(self.parametres_entreprise, 'signature_entreprise_enabled', False))
        story.extend(self.create_signature_section(devis, include_company_signature))
        
        footer_text = ''
        if self.parametres_entreprise:
            parts = []
            if self.parametres_entreprise.nom_entreprise:
                parts.append(self.parametres_entreprise.nom_entreprise)
            legal = []
            if self.parametres_entreprise.forme_juridique:
                legal.append(self.parametres_entreprise.forme_juridique)
            if self.parametres_entreprise.capital_social:
                legal.append(f"au capital social de {self.parametres_entreprise.capital_social}")
            if legal:
                parts.append(' '.join(legal))
            if self.parametres_entreprise.siret:
                parts.append(f"N° SIRET {self.parametres_entreprise.siret}")
            if self.parametres_entreprise.tva_intracommunautaire:
                parts.append(f"N° de TVA {self.parametres_entreprise.tva_intracommunautaire}")
            footer_text = " | ".join(parts)

        # Génération du PDF
        doc.build(story, canvasmaker=partial(NumberedCanvas, footer_text=footer_text, font_name=self.font_regular))
        
        return output_path
    
    def generate_pdf_bytes(self, devis, include_tva=False, taux_tva=20.0, include_company_signature=None):
        """Génère le PDF en mémoire et retourne les bytes"""
        buffer = BytesIO()
        
        # Création du document en mémoire
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        # Construction du contenu
        story = []
        
        # En-tête
        story.extend(self.create_header(devis))
        
        # Section client
        story.extend(self.create_client_section(devis))
        
        # Section prestation
        story.extend(self.create_prestation_section(devis))

        # Contenu personnalise
        story.extend(self.create_custom_content_section(devis))
        
        # Section matériel
        story.extend(self.create_materiel_section(devis))
        
        # Tableau tarification
        story.extend(self.create_pricing_table(devis, include_tva, taux_tva))
        
        # Conditions
        story.extend(self.create_conditions_section(devis))
        
        # Signature
        if include_company_signature is None:
            include_company_signature = bool(getattr(self.parametres_entreprise, 'signature_entreprise_enabled', False))
        story.extend(self.create_signature_section(devis, include_company_signature))
        
        footer_text = ''
        if self.parametres_entreprise:
            parts = []
            if self.parametres_entreprise.nom_entreprise:
                parts.append(self.parametres_entreprise.nom_entreprise)
            legal = []
            if self.parametres_entreprise.forme_juridique:
                legal.append(self.parametres_entreprise.forme_juridique)
            if self.parametres_entreprise.capital_social:
                legal.append(f"au capital social de {self.parametres_entreprise.capital_social}")
            if legal:
                parts.append(' '.join(legal))
            if self.parametres_entreprise.siret:
                parts.append(f"N° SIRET {self.parametres_entreprise.siret}")
            if self.parametres_entreprise.tva_intracommunautaire:
                parts.append(f"N° de TVA {self.parametres_entreprise.tva_intracommunautaire}")
            footer_text = " | ".join(parts)

        # Génération du PDF
        doc.build(story, canvasmaker=partial(NumberedCanvas, footer_text=footer_text, font_name=self.font_regular))
        
        # Retour des bytes
        buffer.seek(0)
        return buffer.getvalue()

def generate_devis_pdf(devis, parametres_entreprise=None, include_tva=False, taux_tva=20.0, include_company_signature=None):
    """Fonction utilitaire pour générer un PDF de devis"""
    generator = DevisPDFGenerator(parametres_entreprise)
    return generator.generate_pdf_bytes(devis, include_tva, taux_tva, include_company_signature=include_company_signature)

class FacturePDFGenerator:
    """Générateur PDF pour les factures - Design sobre noir et blanc"""
    
    def __init__(self, parametres_entreprise=None):
        self.parametres = parametres_entreprise
        _ensure_devis_fonts()
        self.font_regular = 'Manrope-Regular' if 'Manrope-Regular' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        self.font_semibold = 'Manrope-SemiBold' if 'Manrope-SemiBold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _get_company_signature_image(self):
        """Retourne l'image de signature entreprise si disponible."""
        if not self.parametres:
            return None
        signature_path = getattr(self.parametres, 'signature_entreprise_path', None)
        if not signature_path:
            return None
        full_path = os.path.join("static", "uploads", signature_path)
        if not os.path.exists(full_path):
            return None
        try:
            return Image(full_path, width=3*inch, height=1.5*inch, kind='proportional')
        except Exception as e:
            logger.error(f"Erreur chargement signature entreprise (facture): {e}")
            return None
    
    def _create_company_header(self):
        """Crée l'en-tête entreprise avec logo pour les factures"""
        elements = []
        if not self.parametres:
            return elements
        
        header_data = [['', '']]
        
        # Logo (PNG recommandé)
        if getattr(self.parametres, 'logo_path', None):
            logo_path = f"static/uploads/{self.parametres.logo_path}"
            if os.path.exists(logo_path):
                try:
                    # Grand logo 6cm x 6cm, en conservant le ratio (s'adapte dans le carré)
                    logo = Image(logo_path, width=6*cm, height=6*cm, kind='proportional')
                    header_data[0][0] = logo
                except Exception as e:
                    logger.error(f"Erreur chargement logo facture: {e}")
                    header_data[0][0] = ''
        
        # Infos entreprise
        nom_entreprise = self.parametres.nom_entreprise or 'Mon Entreprise'
        company_text = f"<b>{nom_entreprise}</b>"
        lines = []
        if self.parametres.adresse:
            lines.append(self.parametres.adresse)
        cp_ville = " ".join([x for x in [self.parametres.code_postal, self.parametres.ville] if x])
        if cp_ville.strip():
            lines.append(cp_ville)
        if self.parametres.telephone:
            lines.append(f"Tél: {self.parametres.telephone}")
        if self.parametres.email:
            lines.append(f"Email: {self.parametres.email}")
        if getattr(self.parametres, 'site_web', None):
            lines.append(f"Web: {self.parametres.site_web}")
        if lines:
            company_text += "<br/><br/>" + "<br/>".join(lines)
        
        legal = []
        if getattr(self.parametres, 'forme_juridique', None):
            legal.append(f"Forme juridique: {self.parametres.forme_juridique}")
        if getattr(self.parametres, 'capital_social', None):
            legal.append(f"Capital social: {self.parametres.capital_social}")
        if getattr(self.parametres, 'numero_rcs', None) or getattr(self.parametres, 'rcs_ville', None):
            rcs = " ".join([x for x in [getattr(self.parametres, 'rcs_ville', None), getattr(self.parametres, 'numero_rcs', None)] if x])
            if rcs:
                legal.append(f"RCS: {rcs}")
        if getattr(self.parametres, 'siret', None):
            legal.append(f"SIRET: {self.parametres.siret}")
        if getattr(self.parametres, 'tva_intracommunautaire', None):
            legal.append(f"TVA: {self.parametres.tva_intracommunautaire}")
        elif getattr(self.parametres, 'tva_non_applicable', False):
            legal.append("TVA non applicable, art. 293 B du CGI")
        if legal:
            company_text += "<br/><br/>" + "<br/>".join(legal)
        
        header_data[0][1] = Paragraph(company_text, self.styles['CompanyInfo'])
        
        header_table = Table(header_data, colWidths=[3*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 15))
        line_table = Table([['']], colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, black),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 20))
        return elements

    def _setup_styles(self):
        """Configure les styles personnalisés - Design sobre"""
        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='FactureTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=black,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=self.font_semibold
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='FactureSubtitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=black,
            spaceAfter=8,
            spaceBefore=12,
            fontName=self.font_semibold
        ))
        
        # Style pour les informations de l'entreprise
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=black,
            alignment=TA_RIGHT,
            fontName=self.font_regular
        ))
        
        # Style pour les informations du client
        self.styles.add(ParagraphStyle(
            name='ClientInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=black,
            spaceAfter=4,
            fontName=self.font_regular
        ))
    
    def generate_pdf_bytes(self, facture, include_company_signature=None):
        """Génère le PDF de la facture et retourne les bytes"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        
        # Construction du contenu
        story = []
        
        # En-tête facture
        story.extend(self._create_header(facture))
        story.append(Spacer(1, 20))
        
        # Informations client et entreprise
        story.extend(self._create_info_section(facture))
        story.append(Spacer(1, 20))
        
        # Détails de la prestation
        story.extend(self._create_prestation_section(facture))
        story.append(Spacer(1, 20))
        
        # Section matériel
        story.extend(self._create_materiel_section(facture))
        story.append(Spacer(1, 20))
        
        # Tableau de tarification
        story.extend(self._create_pricing_table(facture))
        story.append(Spacer(1, 30))
        
        # Conditions de paiement
        story.extend(self._create_payment_conditions(facture))
        story.append(Spacer(1, 20))
        
        # Notes
        if facture.notes:
            story.extend(self._create_notes_section(facture))

        if include_company_signature is None:
            include_company_signature = bool(getattr(self.parametres, 'signature_entreprise_enabled', False))
        story.extend(self._create_signature_section(include_company_signature))
        
        footer_text = ''
        if self.parametres:
            parts = []
            if self.parametres.nom_entreprise:
                parts.append(self.parametres.nom_entreprise)
            legal = []
            if getattr(self.parametres, 'forme_juridique', None):
                legal.append(self.parametres.forme_juridique)
            if getattr(self.parametres, 'capital_social', None):
                legal.append(f"au capital social de {self.parametres.capital_social}")
            if legal:
                parts.append(' '.join(legal))
            if getattr(self.parametres, 'siret', None):
                parts.append(f"N° SIRET {self.parametres.siret}")
            if getattr(self.parametres, 'tva_intracommunautaire', None):
                parts.append(f"N° de TVA {self.parametres.tva_intracommunautaire}")
            footer_text = " | ".join(parts)

        # Construction du PDF
        doc.build(story, canvasmaker=partial(NumberedCanvas, footer_text=footer_text, font_name=self.font_regular))
        buffer.seek(0)
        return buffer.getvalue()
    
    def _create_header(self, facture):
        """Crée l'en-tête de la facture"""
        elements = []

        elements.append(Paragraph("Facture", self.styles['FactureTitle']))

        creation_date = facture.date_creation.strftime('%d %b. %Y') if facture.date_creation else datetime.now().strftime('%d %b. %Y')
        info_data = [
            ['Numéro', facture.numero],
            ['Date d’émission', creation_date],
        ]
        if facture.date_echeance:
            info_data.append(['Date d’échéance', facture.date_echeance.strftime('%d %b. %Y')])
        if getattr(facture, 'numero_bon_commande', None):
            info_data.append(['Bon de commande', facture.numero_bon_commande])

        info_table = Table(info_data, colWidths=[2.0*inch, 4.0*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.font_semibold),
            ('FONTNAME', (1, 0), (1, -1), self.font_regular),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 12))

        return elements
    
    def _create_info_section(self, facture):
        """Crée la section des informations client et entreprise"""
        elements = []

        if self.parametres:
            elements.append(Paragraph("Émetteur ou Émettrice", self.styles['FactureSubtitle']))
            line_table = Table([['']], colWidths=[1.6*inch])
            line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
            elements.append(line_table)
            elements.append(Spacer(1, 6))
            company_info = [
                f"<b>{self.parametres.nom_entreprise if self.parametres else 'Mon Entreprise'}</b>",
                self.parametres.adresse if self.parametres else '',
                f"{self.parametres.code_postal if self.parametres else ''} {self.parametres.ville if self.parametres else ''}",
                f"{self.parametres.email if self.parametres else ''}"
            ]
            elements.append(Paragraph("<br/>".join([info for info in company_info if info]), self.styles['ClientInfo']))
            elements.append(Spacer(1, 12))

        elements.append(Paragraph("Client ou Cliente", self.styles['FactureSubtitle']))
        line_table = Table([['']], colWidths=[1.2*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        elements.append(line_table)
        elements.append(Spacer(1, 6))

        client_info = [f"<b>{facture.client_nom}</b>"]
        if facture.client_adresse:
            client_info.append(facture.client_adresse)
        if facture.client_email:
            client_info.append(facture.client_email)
        if getattr(facture, 'client_siren', None):
            client_info.append(f"SIREN : {facture.client_siren}")
        if getattr(facture, 'client_tva', None):
            client_info.append(f"TVA : {facture.client_tva}")
        if getattr(facture, 'adresse_livraison', None):
            client_info.append(f"Adresse livraison : {facture.adresse_livraison}")
        elements.append(Paragraph("<br/>".join([info for info in client_info if info]), self.styles['ClientInfo']))

        return elements
    
    def _create_prestation_section(self, facture):
        """Crée la section des détails de la prestation"""
        elements = []

        elements.append(Paragraph("Description de la prestation", self.styles['FactureSubtitle']))
        line_table = Table([['']], colWidths=[2.2*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        elements.append(line_table)
        elements.append(Spacer(1, 8))

        description = facture.prestation_description or ''
        if not description:
            description = f"Prestation le {facture.date_prestation.strftime('%d/%m/%Y')} à {facture.lieu}"
        elements.append(Paragraph(description, self.styles['Normal']))
        elements.append(Spacer(1, 12))
        return elements
    
    def _create_materiel_section(self, facture):
        """Crée la section matériel fourni (liste synthétique)"""
        elements = []

        elements.append(Paragraph("Matériel fourni", self.styles['FactureSubtitle']))
        line_table = Table([['']], colWidths=[1.6*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        elements.append(line_table)
        elements.append(Spacer(1, 8))

        materiel_assignes = []
        try:
            from app import MaterielPresta, Materiel, Devis
            if hasattr(facture, 'prestation_id') and facture.prestation_id:
                materiel_assignes = MaterielPresta.query.filter_by(prestation_id=facture.prestation_id).all()
            elif getattr(facture, 'devis_id', None):
                devis = Devis.query.get(facture.devis_id)
                if devis and devis.prestation_id:
                    materiel_assignes = MaterielPresta.query.filter_by(prestation_id=devis.prestation_id).all()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du matériel pour facture: {e}")
            materiel_assignes = []

        if materiel_assignes:
            categories = []
            for mp in materiel_assignes:
                materiel = Materiel.query.get(mp.materiel_id)
                if materiel and materiel.categorie and materiel.categorie not in categories:
                    categories.append(materiel.categorie)
            if categories:
                elements.append(Paragraph("<br/>".join(categories), self.styles['Normal']))
            else:
                elements.append(Paragraph("Matériel fourni selon la configuration validée.", self.styles['Normal']))
        else:
            elements.append(Paragraph("Aucun matériel assigné à cette prestation.", self.styles['Normal']))

        elements.append(Spacer(1, 12))
        return elements
    
    def _create_pricing_table(self, facture):
        """Crée le tableau de tarification - aligné sur le devis"""
        elements = []

        elements.append(Paragraph("Produits", self.styles['FactureSubtitle']))
        line_table = Table([['']], colWidths=[1.2*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        elements.append(line_table)
        elements.append(Spacer(1, 6))

        from app import calculer_cout_materiel_reel

        lines = []
        total_ht = 0.0
        taux_tva = facture.taux_tva or 0.0

        # Prestation
        if facture.duree_heures and facture.tarif_horaire:
            montant = facture.duree_heures * facture.tarif_horaire
            lines.append({
                'label': facture.prestation_titre or 'Prestation',
                'quantite': f"{facture.duree_heures:.0f} heures",
                'prix_unitaire': facture.tarif_horaire,
                'total_ht': montant
            })
            total_ht += montant

        # Transport
        if facture.frais_transport and facture.frais_transport > 0:
            lines.append({
                'label': 'Frais de déplacement',
                'quantite': '1 unité',
                'prix_unitaire': facture.frais_transport,
                'total_ht': facture.frais_transport
            })
            total_ht += facture.frais_transport

        # Matériel détaillé
        cout_materiel_reel, details_materiel = calculer_cout_materiel_reel(prestation_id=facture.prestation_id)
        if details_materiel:
            for item in details_materiel:
                quantite = item.get('quantite', 1) or 1
                prix_unitaire = item.get('prix_unitaire', 0.0) or 0.0
                cout_total = item.get('cout_total', quantite * prix_unitaire)
                lines.append({
                    'label': item.get('nom', 'Matériel'),
                    'quantite': f"{quantite} unité{'s' if quantite > 1 else ''}",
                    'prix_unitaire': prix_unitaire,
                    'total_ht': cout_total
                })
                total_ht += cout_total
        elif facture.frais_materiel and facture.frais_materiel > 0:
            lines.append({
                'label': 'Frais matériel',
                'quantite': '1 unité',
                'prix_unitaire': facture.frais_materiel,
                'total_ht': facture.frais_materiel
            })
            total_ht += facture.frais_materiel

        # Remise
        remise = 0.0
        if facture.remise_pourcentage and facture.remise_pourcentage > 0:
            remise = total_ht * (facture.remise_pourcentage / 100)
        elif facture.remise_montant and facture.remise_montant > 0:
            remise = facture.remise_montant
        if remise > 0:
            lines.append({
                'label': 'Remise',
                'quantite': '-',
                'prix_unitaire': -remise,
                'total_ht': -remise
            })
            total_ht -= remise

        data = [[
            'Produits', 'Qté', 'Prix u. HT', 'TVA (%)', 'Total HT', 'Total TTC'
        ]]

        for line in lines:
            line_ht = line['total_ht']
            line_ttc = line_ht * (1 + (taux_tva / 100.0))
            data.append([
                line['label'],
                line['quantite'],
                f"{line['prix_unitaire']:.2f} €",
                f"{taux_tva:.0f}%" if taux_tva else '0%',
                f"{line_ht:.2f} €",
                f"{line_ttc:.2f} €",
            ])

        total_ttc = total_ht * (1 + (taux_tva / 100.0))
        data.append(['Sous-Total', '', '', '', f"{total_ht:.2f} €", f"{total_ttc:.2f} €"])

        table = Table(data, colWidths=[2.8*inch, 0.8*inch, 1.0*inch, 0.8*inch, 1.0*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), self.font_semibold),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 1), (-1, -2), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.25, grey),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), self.font_semibold),
            ('ALIGN', (4, -1), (-1, -1), 'RIGHT'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        recap = Table([
            ['Récapitulatif', ''],
            ['Total HT', f"{total_ht:.2f} €"],
            ['Total TVA', f"{(total_ttc - total_ht):.2f} €"],
            ['Total TTC', f"{total_ttc:.2f} €"],
        ], colWidths=[2.0*inch, 2.0*inch])
        recap.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_regular),
            ('FONTNAME', (0, 0), (0, 0), self.font_semibold),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.25, grey),
        ]))
        elements.append(recap)
        elements.append(Spacer(1, 12))

        if taux_tva:
            details = Table([
                ['Détails TVA', ''],
                ['Taux', f"{taux_tva:.0f}%"],
                ['Montant TVA', f"{(total_ttc - total_ht):.2f} €"],
                ['Base HT', f"{total_ht:.2f} €"],
            ], colWidths=[2.0*inch, 2.0*inch])
            details.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_regular),
                ('FONTNAME', (0, 0), (0, 0), self.font_semibold),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.25, grey),
            ]))
            elements.append(details)
            elements.append(Spacer(1, 12))

        return elements

    def _create_payment_conditions(self, facture):
        """Crée les conditions de paiement"""
        elements = []
        elements.append(Paragraph("Paiement", self.styles['FactureSubtitle']))
        line_table = Table([['']], colWidths=[1.0*inch])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 1, black)]))
        elements.append(line_table)
        elements.append(Spacer(1, 6))

        iban = getattr(self.parametres, 'rib_iban', '') if self.parametres else ''
        titulaire = getattr(self.parametres, 'rib_titulaire', '') if self.parametres else ''
        bloc = []
        if titulaire:
            bloc.append(f"Établissement : {titulaire}")
        if iban:
            bloc.append(f"IBAN : {iban}")
        if not bloc:
            bloc.append("Paiement par virement ou carte.")

        elements.append(Paragraph('<br/>'.join(bloc), self.styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(
            "Pénalités de retard : trois fois le taux annuel d’intérêt légal en vigueur calculé depuis la date d’échéance jusqu’à complet paiement du prix.",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            "Indemnité forfaitaire pour frais de recouvrement en cas de retard de paiement : 40 €",
            self.styles['Normal']
        ))
        return elements
    
    def _create_notes_section(self, facture):
        """Crée la section des notes"""
        elements = []
        
        elements.append(Paragraph("NOTES", self.styles['FactureSubtitle']))
        # Utiliser un tableau pour créer une ligne
        line_table = Table([['']], colWidths=[0.8*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, black),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(facture.notes, self.styles['Normal']))
        
        return elements

    def _create_signature_section(self, include_company_signature=False):
        """Ajoute la signature entreprise si disponible."""
        elements = []
        if not include_company_signature:
            return elements
        signature_img = self._get_company_signature_image()
        if not signature_img:
            return elements
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Signature de l'entreprise", self.styles['FactureSubtitle']))
        line_table = Table([['']], colWidths=[1.2*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, black),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 8))
        signature_frame = Table([[signature_img]], colWidths=[3.5*inch])
        signature_frame.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (-1, -1), white),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(signature_frame)
        return elements
    
    def _create_footer(self, facture):
        """Crée le pied de page"""
        elements = []
        
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("Merci pour votre confiance !", self.styles['Normal']))
        
        # Informations légales
        if self.parametres:
            if self.parametres.forme_juridique:
                elements.append(Paragraph(f"Forme juridique: {self.parametres.forme_juridique}", self.styles['CompanyInfo']))
            if self.parametres.capital_social:
                elements.append(Paragraph(f"Capital social: {self.parametres.capital_social}", self.styles['CompanyInfo']))
            if self.parametres.numero_rcs or self.parametres.rcs_ville:
                rcs = " ".join([x for x in [self.parametres.rcs_ville, self.parametres.numero_rcs] if x])
                if rcs:
                    elements.append(Paragraph(f"RCS: {rcs}", self.styles['CompanyInfo']))
            if self.parametres.siret:
                elements.append(Paragraph(f"SIRET: {self.parametres.siret}", self.styles['CompanyInfo']))
            if self.parametres.tva_intracommunautaire:
                elements.append(Paragraph(f"TVA Intracommunautaire: {self.parametres.tva_intracommunautaire}", self.styles['CompanyInfo']))
            elif getattr(self.parametres, 'tva_non_applicable', False):
                elements.append(Paragraph("TVA non applicable, art. 293 B du CGI", self.styles['CompanyInfo']))
        
        return elements

def generate_facture_pdf(facture, parametres_entreprise=None, include_company_signature=None):
    """Fonction utilitaire pour générer un PDF de facture"""
    generator = FacturePDFGenerator(parametres_entreprise)
    return generator.generate_pdf_bytes(facture, include_company_signature=include_company_signature)
