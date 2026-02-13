#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de fichiers iCalendar (.ics) pour Google Calendar
Alternative simple à OAuth2
"""

from datetime import datetime, timedelta
import os
import logging
logger = logging.getLogger(__name__)

class ICalendarGenerator:
    """Générateur de fichiers iCalendar pour les prestations"""
    
    def __init__(self):
        self.timezone = "Europe/Paris"
    
    def generate_ics_for_dj(self, dj, prestations):
        """Génère un fichier .ics pour un DJ avec toutes ses prestations"""
        
        ics_content = self._generate_ics_header()
        
        for prestation in prestations:
            ics_content += self._generate_event(prestation, dj)
        
        ics_content += self._generate_ics_footer()
        
        return ics_content
    
    def generate_ics_for_prestation(self, prestation, dj):
        """Génère un fichier .ics pour une prestation spécifique"""
        
        ics_content = self._generate_ics_header()
        ics_content += self._generate_event(prestation, dj)
        ics_content += self._generate_ics_footer()
        
        return ics_content
    
    def _generate_ics_header(self):
        """Génère l'en-tête du fichier .ics"""
        return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//DJ Prestations Manager//Planify//FR
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Prestations DJ
X-WR-CALDESC:Prestations DJ - Planify
X-WR-TIMEZONE:{self.timezone}
"""
    
    def _generate_ics_footer(self):
        """Génère le pied du fichier .ics"""
        return "END:VCALENDAR"
    
    def _generate_event(self, prestation, dj):
        """Génère un événement iCalendar pour une prestation"""
        
        # Convertir les dates et heures
        start_datetime = datetime.combine(prestation.date_debut, prestation.heure_debut)
        end_datetime = datetime.combine(prestation.date_fin, prestation.heure_fin)
        
        # Si l'heure de fin est avant l'heure de début, c'est le lendemain
        if end_datetime <= start_datetime:
            end_datetime += timedelta(days=1)
        
        # Formater les dates pour iCalendar (format UTC)
        start_utc = start_datetime.strftime('%Y%m%dT%H%M%SZ')
        end_utc = end_datetime.strftime('%Y%m%dT%H%M%SZ')
        
        # Générer un UID unique
        uid = f"prestation-{prestation.id}-{dj.id}@planify.local"
        
        # Créer la description
        description = f"Prestation DJ\\n\\n"
        description += f"Client: {prestation.client}\\n"
        description += f"Lieu: {prestation.lieu}\\n"
        if prestation.notes:
            description += f"Notes: {prestation.notes}\\n"
        description += f"\\nGénéré par Planify - DJ Prestations Manager"
        
        # Générer l'événement
        event = f"""BEGIN:VEVENT
UID:{uid}
DTSTART:{start_utc}
DTEND:{end_utc}
SUMMARY:Prestation DJ - {prestation.client}
DESCRIPTION:{description}
LOCATION:{prestation.lieu}
STATUS:CONFIRMED
TRANSP:OPAQUE
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:Rappel: Prestation DJ dans 30 minutes
END:VALARM
BEGIN:VALARM
TRIGGER:-PT1H
ACTION:DISPLAY
DESCRIPTION:Rappel: Prestation DJ dans 1 heure
END:VALARM
END:VEVENT
"""
        
        return event
    
    def save_ics_file(self, ics_content, filename):
        """Sauvegarde le contenu .ics dans un fichier"""
        
        # Créer le dossier d'export s'il n'existe pas
        export_dir = "static/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        # Chemin complet du fichier
        filepath = os.path.join(export_dir, filename)
        
        # Sauvegarder le fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        
        return filepath
    
    def generate_dj_calendar(self, dj, prestations):
        """Génère un calendrier complet pour un DJ"""
        
        # Filtrer les prestations du DJ
        dj_prestations = [p for p in prestations if p.dj_id == dj.id]
        
        if not dj_prestations:
            return None
        
        # Générer le contenu .ics
        ics_content = self.generate_ics_for_dj(dj, dj_prestations)
        
        # Nom du fichier
        dj_name = dj.nom.replace(' ', '_').replace('/', '_')
        filename = f"Prestations_{dj_name}_{datetime.now().strftime('%Y%m%d')}.ics"
        
        # Sauvegarder le fichier
        filepath = self.save_ics_file(ics_content, filename)
        
        return filepath, filename

# Instance globale
icalendar_generator = ICalendarGenerator()








