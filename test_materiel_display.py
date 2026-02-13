#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier l'affichage de la section matériel 
dans les devis et factures (avec et sans matériel assigné)
"""

import sys
import pytest
from datetime import datetime, timedelta, date, time
from io import BytesIO
from werkzeug.security import generate_password_hash

# Configuration Flask pour tests
import os
os.environ['FLASK_ENV'] = 'development'

from app import app, db, Devis, Facture, Prestation, DJ, Local, Materiel, MaterielPresta, User
from pdf_generator import DevisPDFGenerator, FacturePDFGenerator

def ensure_test_prestation():
    """Assure une prestation existante avec matériel pour les tests PDF."""
    db.create_all()
    prestation = Prestation.query.first()
    if prestation:
        return prestation

    admin = User.query.filter_by(username="test_admin").first()
    if not admin:
        admin = User(
            username="test_admin",
            email="test_admin@example.com",
            password_hash=generate_password_hash("password"),
            role="admin",
            nom="Admin",
            prenom="Test",
        )
        db.session.add(admin)
        db.session.flush()

    dj = DJ.query.first()
    if not dj:
        dj = DJ(nom="DJ Test", user_id=admin.id)
        db.session.add(dj)
        db.session.flush()

    local = Local.query.first()
    if not local:
        local = Local(nom="Local Test", adresse="1 rue du Test")
        db.session.add(local)
        db.session.flush()

    materiel = Materiel.query.first()
    if not materiel:
        materiel = Materiel(
            nom="Enceinte Test",
            local_id=local.id,
            quantite=1,
            categorie="Son",
            statut="disponible",
            prix_location=10.0,
        )
        db.session.add(materiel)
        db.session.flush()

    prestation = Prestation(
        date_debut=date.today(),
        date_fin=date.today(),
        heure_debut=time(20, 0),
        heure_fin=time(23, 0),
        client="Client Test",
        lieu="Salle Test",
        dj_id=dj.id,
        createur_id=admin.id,
        statut="planifiee",
    )
    db.session.add(prestation)
    db.session.flush()

    assignation = MaterielPresta(
        materiel_id=materiel.id,
        prestation_id=prestation.id,
        quantite=1,
    )
    db.session.add(assignation)
    db.session.commit()
    return prestation

def test_devis_avec_materiel():
    """Test génération devis AVEC matériel assigné"""
    print("\n" + "="*60)
    print("TEST 1: Devis AVEC matériel assigné")
    print("="*60)
    
    with app.app_context():
        # Récupérer une prestation existante avec du matériel
        prestation = ensure_test_prestation()
        
        # Vérifier si du matériel est assigné
        materiels = MaterielPresta.query.filter_by(prestation_id=prestation.id).all()
        print(f"✓ Prestation ID {prestation.id}: {len(materiels)} matériels assignés")
        
        # Créer un devis de test
        devis = Devis(
            numero=f"TEST-MAT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            client_nom=prestation.client,
            client_email=prestation.client_email or "test@example.com",
            client_telephone=prestation.client_telephone or "0123456789",
            client_adresse="123 Rue Test",
            prestation_titre=f"Prestation {prestation.client}",
            prestation_description="Test avec matériel assigné",
            date_prestation=prestation.date_debut,
            heure_debut=prestation.heure_debut,
            heure_fin=prestation.heure_fin,
            lieu=prestation.lieu,
            montant_ht=1000.0,
            taux_tva=20.0,
            montant_tva=200.0,
            montant_ttc=1200.0,
            dj_id=prestation.dj_id,
            prestation_id=prestation.id,
            statut='brouillon',
            date_creation=datetime.now()
        )
        
        # Générer le PDF
        generator = DevisPDFGenerator()
        pdf_bytes = generator.generate_pdf_bytes(devis, include_tva=True, taux_tva=20.0)
        
        # Sauvegarder
        filename = f"test_devis_avec_materiel.pdf"
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ PDF généré: {filename}")
        print(f"   Taille: {len(pdf_bytes)} bytes")
        assert len(pdf_bytes) > 0

def test_devis_sans_materiel():
    """Test génération devis SANS matériel assigné"""
    print("\n" + "="*60)
    print("TEST 2: Devis SANS matériel assigné")
    print("="*60)
    
    with app.app_context():
        # Créer un devis sans prestation_id (donc sans matériel)
        db.create_all()
        dj = DJ.query.first()
        if not dj:
            dj = ensure_test_prestation().dj
        
        devis = Devis(
            numero=f"TEST-NOMAT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            client_nom="Client Test Sans Matériel",
            client_email="test@example.com",
            client_telephone="0123456789",
            client_adresse="123 Rue Test",
            prestation_titre="Prestation sans matériel",
            prestation_description="Test sans matériel assigné",
            date_prestation=(datetime.now() + timedelta(days=30)).date(),
            heure_debut=datetime.now().replace(hour=20, minute=0).time(),
            heure_fin=datetime.now().replace(hour=23, minute=59).time(),
            lieu="Lieu Test",
            montant_ht=800.0,
            taux_tva=20.0,
            montant_tva=160.0,
            montant_ttc=960.0,
            dj_id=dj.id if dj else None,
            prestation_id=None,  # PAS de prestation = PAS de matériel
            statut='brouillon',
            date_creation=datetime.now()
        )
        
        # Générer le PDF
        generator = DevisPDFGenerator()
        pdf_bytes = generator.generate_pdf_bytes(devis, include_tva=False, taux_tva=20.0)
        
        # Sauvegarder
        filename = f"test_devis_sans_materiel.pdf"
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ PDF généré: {filename}")
        print(f"   Taille: {len(pdf_bytes)} bytes")
        print(f"   Message attendu: 'Aucun matériel assigné à cette prestation.'")
        assert len(pdf_bytes) > 0

def test_facture_avec_materiel():
    """Test génération facture AVEC matériel assigné"""
    print("\n" + "="*60)
    print("TEST 3: Facture AVEC matériel assigné")
    print("="*60)
    
    with app.app_context():
        # Récupérer une prestation existante avec du matériel
        prestation = ensure_test_prestation()
        
        # Créer une facture de test
        facture = Facture(
            numero=f"TEST-FAC-MAT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            client_nom=prestation.client,
            client_email=prestation.client_email or "test@example.com",
            client_telephone=prestation.client_telephone or "0123456789",
            client_adresse="123 Rue Test",
            prestation_titre=f"Prestation {prestation.client}",
            date_prestation=prestation.date_debut,
            heure_debut=prestation.heure_debut,
            heure_fin=prestation.heure_fin,
            lieu=prestation.lieu,
            montant_ht=1000.0,
            taux_tva=20.0,
            montant_tva=200.0,
            montant_ttc=1200.0,
            dj_id=prestation.dj_id,
            prestation_id=prestation.id,
            statut='brouillon',
            date_creation=datetime.now()
        )
        
        # Générer le PDF
        from pdf_generator import FacturePDFGenerator
        generator = FacturePDFGenerator()
        pdf_bytes = generator.generate_pdf_bytes(facture)
        
        # Sauvegarder
        filename = f"test_facture_avec_materiel.pdf"
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ PDF généré: {filename}")
        print(f"   Taille: {len(pdf_bytes)} bytes")
        assert len(pdf_bytes) > 0

def test_facture_sans_materiel():
    """Test génération facture SANS matériel assigné"""
    print("\n" + "="*60)
    print("TEST 4: Facture SANS matériel assigné")
    print("="*60)
    
    with app.app_context():
        # Créer une facture sans prestation_id
        db.create_all()
        dj = DJ.query.first()
        if not dj:
            dj = ensure_test_prestation().dj
        
        facture = Facture(
            numero=f"TEST-FAC-NOMAT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            client_nom="Client Test Sans Matériel",
            client_email="test@example.com",
            client_telephone="0123456789",
            client_adresse="123 Rue Test",
            prestation_titre="Prestation sans matériel",
            date_prestation=(datetime.now() + timedelta(days=30)).date(),
            heure_debut=datetime.now().replace(hour=20, minute=0).time(),
            heure_fin=datetime.now().replace(hour=23, minute=59).time(),
            lieu="Lieu Test",
            montant_ht=800.0,
            taux_tva=20.0,
            montant_tva=160.0,
            montant_ttc=960.0,
            dj_id=dj.id if dj else None,
            prestation_id=None,  # PAS de prestation = PAS de matériel
            statut='brouillon',
            date_creation=datetime.now()
        )
        
        # Générer le PDF
        from pdf_generator import FacturePDFGenerator
        generator = FacturePDFGenerator()
        pdf_bytes = generator.generate_pdf_bytes(facture)
        
        # Sauvegarder
        filename = f"test_facture_sans_materiel.pdf"
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ PDF généré: {filename}")
        print(f"   Taille: {len(pdf_bytes)} bytes")
        print(f"   Message attendu: 'Aucun matériel assigné à cette prestation.'")
        assert len(pdf_bytes) > 0

if __name__ == "__main__":
    print("\n" + "🔬 TEST DE L'AFFICHAGE DU MATÉRIEL 🔬".center(60, "="))
    print("Vérification que la section MATÉRIEL INCLUS s'affiche TOUJOURS")
    print("="*60)
    
    try:
        results = []

        def run_test(name, fn):
            try:
                fn()
                results.append((name, True))
            except Exception:
                results.append((name, False))

        # Tests devis
        run_test("Devis avec matériel", test_devis_avec_materiel)
        run_test("Devis sans matériel", test_devis_sans_materiel)
        
        # Tests factures
        run_test("Facture avec matériel", test_facture_avec_materiel)
        run_test("Facture sans matériel", test_facture_sans_materiel)
        
        # Résumé
        print("\n" + "="*60)
        print("RÉSUMÉ DES TESTS")
        print("="*60)
        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {name}")
        
        # Statistiques
        passed = sum(1 for _, r in results if r)
        total = len(results)
        print("\n" + f"Résultat: {passed}/{total} tests réussis".center(60))
        
        if passed == total:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS ! 🎉".center(60))
            print("\nOuvrez les PDFs générés pour vérifier visuellement:")
            print("  - test_devis_avec_materiel.pdf")
            print("  - test_devis_sans_materiel.pdf")
            print("  - test_facture_avec_materiel.pdf")
            print("  - test_facture_sans_materiel.pdf")
        else:
            print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ ⚠️".center(60))
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERREUR PENDANT LES TESTS: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
