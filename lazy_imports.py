#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de chargement paresseux pour alléger l'application
"""

import importlib
import sys
import logging
logger = logging.getLogger(__name__)

class LazyImporter:
    """Gestionnaire d'imports paresseux"""
    
    def __init__(self):
        self._modules = {}
        self._import_errors = {}
        self._parametres = None
    
    def set_parametres(self, parametres):
        """Définit les paramètres d'entreprise pour vérifier les modules activés"""
        self._parametres = parametres
    
    def is_module_enabled(self, module_name):
        """Vérifie si un module est activé dans les paramètres"""
        if not self._parametres:
            return True  # Par défaut, tous les modules sont activés
        
        module_mapping = {
            'google_calendar': 'module_google_calendar',
            'excel_export': 'module_excel_export', 
            'pdf_generation': 'module_pdf_generation',
            'financial_reports': 'module_financial_reports',
            'notifications': 'module_notifications',
            'icalendar': 'module_icalendar'
        }
        
        param_name = module_mapping.get(module_name)
        if param_name:
            return getattr(self._parametres, param_name, True)
        return True
    
    def get_module(self, module_name, package=None):
        """Charge un module de manière paresseuse"""
        if module_name in self._import_errors:
            raise self._import_errors[module_name]
        
        if module_name not in self._modules:
            try:
                self._modules[module_name] = importlib.import_module(module_name, package)
            except ImportError as e:
                self._import_errors[module_name] = e
                raise e
        
        return self._modules[module_name]
    
    def get_google_calendar_manager(self):
        """Charge le gestionnaire Google Calendar"""
        if not self.is_module_enabled('google_calendar'):
            return None
        try:
            google_calendar_config = self.get_module('google_calendar_config')
            return google_calendar_config.google_calendar_manager
        except ImportError:
            return None
    
    def get_excel_exporter(self):
        """Charge l'exporteur Excel"""
        if not self.is_module_enabled('excel_export'):
            return None
        try:
            excel_export = self.get_module('excel_export')
            return excel_export.excel_exporter
        except ImportError:
            return None
    
    def get_notification_manager(self):
        """Charge le gestionnaire de notifications"""
        if not self.is_module_enabled('notifications'):
            return None
        try:
            notifications = self.get_module('notifications')
            return notifications.notification_manager
        except ImportError:
            return None
    
    def get_icalendar_generator(self):
        """Charge le générateur iCalendar"""
        if not self.is_module_enabled('icalendar'):
            return None
        try:
            icalendar_generator = self.get_module('icalendar_generator')
            return icalendar_generator.icalendar_generator
        except ImportError:
            return None
    
    def get_pdf_generator(self):
        """Charge le générateur PDF"""
        if not self.is_module_enabled('pdf_generation'):
            return None
        try:
            pdf_generator = self.get_module('pdf_generator')
            return pdf_generator.DevisPDFGenerator
        except ImportError:
            return None
    
    def get_financial_reports(self):
        """Charge les rapports financiers"""
        if not self.is_module_enabled('financial_reports'):
            return None
        try:
            financial_reports = self.get_module('financial_reports')
            return financial_reports.FinancialReportGenerator
        except ImportError:
            return None

# Instance globale
lazy_importer = LazyImporter()

# Fonctions de convenance
def get_google_calendar_manager():
    return lazy_importer.get_google_calendar_manager()

def get_excel_exporter():
    return lazy_importer.get_excel_exporter()

def get_notification_manager():
    return lazy_importer.get_notification_manager()

def get_icalendar_generator():
    return lazy_importer.get_icalendar_generator()

def get_pdf_generator():
    return lazy_importer.get_pdf_generator()

def get_financial_reports():
    return lazy_importer.get_financial_reports()
