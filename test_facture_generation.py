#!/usr/bin/env python3
"""
Script de test pour générer une facture PDF avec le nouveau système
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Facture, DJ, Prestation
from datetime import datetime, date, time
from pdf_generator import generate_facture_pdf

def test_facture_generation():
    """Teste la génération d'une facture avec matériel visible"""
    
    with app.app_context():
        print("=" * 70)
        print("TEST DE GÉNÉRATION DES FACTURES")
        print("=" * 70)
        
        # Récupérer une prestation existante qui a du matériel
        prestation = Prestation.query.first()
        
        if not prestation:
            print("❌ Aucune prestation trouvée. Exécutez populate_test_data.py")
            return
        
        print(f"\n✅ Prestation trouvée : {prestation.client}")
        
        # Récupérer le DJ
        dj = db.session.get(DJ, prestation.dj_id) if prestation.dj_id else DJ.query.first()
        
        # Créer une facture de test
        facture_test = Facture(
            numero=f"FACT-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            client_nom=prestation.client,
            client_email="test@example.com",
            client_telephone="06 12 34 56 78",
            client_adresse="123 Rue de Test, 75001 Paris",
            
            prestation_titre=f"Prestation {prestation.client}",
            prestation_description="Test de facture",
            date_prestation=prestation.date_debut,
            heure_debut=prestation.heure_debut,
            heure_fin=prestation.heure_fin,
            lieu=prestation.lieu,
            
            tarif_horaire=150.0,
            duree_heures=6.0,
            montant_ht=1200.0,
            taux_tva=20.0,
            montant_tva=240.0,
            montant_ttc=1440.0,
            
            dj_id=dj.id if dj else None,
            prestation_id=prestation.id,  # ← IMPORTANT : lier à la prestation
            statut='envoyee'
        )
        
        db.session.add(facture_test)
        db.session.commit()
        
        print(f"✅ Facture créée : {facture_test.numero}")
        print(f"   Lié à la prestation ID : {prestation.id}")
        print(f"   DJ : {dj.nom if dj else 'Aucun'}")
        print(f"   Montant HT : {facture_test.montant_ht:.2f} €")
        print(f"   → Prestation DJ (60%) : {facture_test.montant_ht * 0.6:.2f} €")
        print(f"   → Frais matériel (40%) : {facture_test.montant_ht * 0.4:.2f} €")
        print(f"   → TVA (20%) : {facture_test.montant_tva:.2f} €")
        print(f"   → Total TTC : {facture_test.montant_ttc:.2f} €")
        
        # Génération du PDF
        print("\n📄 Génération du PDF de facture...")
        try:
            pdf_bytes = generate_facture_pdf(facture_test, None)
            filename = f"test_facture_{facture_test.numero}.pdf"
            
            with open(filename, 'wb') as f:
                f.write(pdf_bytes)
            
            montant_dj = facture_test.montant_ht * 0.60
            montant_mat = facture_test.montant_ht * 0.40
            
            print(f"   ✅ PDF généré : {filename}")
            print(f"\n   📋 Contenu du PDF :")
            print(f"   ┌─────────────────────────────────────────┐")
            print(f"   │ MATÉRIEL INCLUS                         │")
            print(f"   │ (liste du matériel de la prestation)    │")
            print(f"   └─────────────────────────────────────────┘")
            print(f"\n   ┌─────────────────────────────────────────┐")
            print(f"   │ DÉTAIL DE LA TARIFICATION               │")
            print(f"   ├───────────────────────────┬─────────────┤")
            print(f"   │ Prestation DJ {dj.nom if dj else 'N/A':<12} │ {montant_dj:>8.2f} € │")
            print(f"   │ Frais de matériel         │ {montant_mat:>8.2f} € │")
            print(f"   │ TVA (20%)                 │ {facture_test.montant_tva:>8.2f} € │")
            print(f"   ├───────────────────────────┼─────────────┤")
            print(f"   │ TOTAL TTC                 │ {facture_test.montant_ttc:>8.2f} € │")
            print(f"   └───────────────────────────┴─────────────┘")
            
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            import traceback
            traceback.print_exc()
        
        # Supprimer la facture de test
        db.session.delete(facture_test)
        db.session.commit()
        print(f"\n🗑️  Facture de test supprimée")
        
        print("\n" + "=" * 70)
        print("✅ TEST TERMINÉ !")
        print("=" * 70)
        print(f"\n📄 Fichier PDF : {filename}")
        print("\nOuvre le PDF pour vérifier que :")
        print("  ✅ La liste du matériel s'affiche")
        print("  ✅ Le nom du DJ apparaît dans 'Prestation DJ [Nom]'")
        print("  ✅ Les calculs sont corrects (60/40)")
        print("  ✅ La TVA est affichée (toujours dans les factures)")
        print("  ✅ Le total TTC est correct")

if __name__ == '__main__':
    test_facture_generation()
