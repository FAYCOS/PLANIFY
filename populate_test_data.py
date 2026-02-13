#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour peupler la base de données avec des données de test
pour tester le système de gestion du matériel
"""

import os
import sys
from datetime import datetime, date, time, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Local, Materiel, DJ, Prestation, ReservationClient, MaterielPresta, User
from werkzeug.security import generate_password_hash
import logging
logger = logging.getLogger(__name__)

def populate_test_data():
    with app.app_context():
        logger.info("🎯 Début du peuplement de la base de données...")
        logger.info("=" * 70)
        
        # 1. CRÉER DES LOCAUX
        logger.info("\n📍 Création des locaux...")
        locaux_data = [
            {"nom": "Entrepôt Paris", "adresse": "15 rue de Rivoli, 75001 Paris"},
            {"nom": "Entrepôt Lyon", "adresse": "42 rue de la République, 69002 Lyon"},
            {"nom": "Stock Marseille", "adresse": "8 avenue du Prado, 13008 Marseille"}
        ]
        
        locaux = []
        for data in locaux_data:
            local = Local.query.filter_by(nom=data["nom"]).first()
            if not local:
                local = Local(**data)
                db.session.add(local)
                logger.info(f"  ✅ Local créé : {data['nom']}")
            else:
                logger.info(f"  ⏭️  Local existant : {data['nom']}")
            locaux.append(local)
        
        db.session.commit()
        
        # 2. CRÉER DU MATÉRIEL
        logger.info("\n🔊 Création du matériel...")
        materiels_data = [
            # Sonorisation
            {"nom": "Enceinte JBL PRX815W", "local": locaux[0], "quantite": 4, "categorie": "Sonorisation", "statut": "disponible"},
            {"nom": "Enceinte QSC K12.2", "local": locaux[0], "quantite": 6, "categorie": "Sonorisation", "statut": "disponible"},
            {"nom": "Caisson de basse JBL PRX818", "local": locaux[0], "quantite": 2, "categorie": "Sonorisation", "statut": "disponible"},
            {"nom": "Table de mixage Pioneer DJM-900", "local": locaux[0], "quantite": 3, "categorie": "Sonorisation", "statut": "disponible"},
            {"nom": "Microphone Shure SM58", "local": locaux[1], "quantite": 10, "categorie": "Sonorisation", "statut": "disponible"},
            
            # Éclairage
            {"nom": "Projecteur LED PAR64", "local": locaux[0], "quantite": 12, "categorie": "Éclairage", "statut": "disponible"},
            {"nom": "Lyre LED Moving Head", "local": locaux[0], "quantite": 8, "categorie": "Éclairage", "statut": "disponible"},
            {"nom": "Stroboscope LED", "local": locaux[1], "quantite": 4, "categorie": "Éclairage", "statut": "disponible"},
            {"nom": "Machine à fumée", "local": locaux[1], "quantite": 3, "categorie": "Éclairage", "statut": "disponible"},
            
            # Matériel en maintenance
            {"nom": "Enceinte QSC K10.2 (HS)", "local": locaux[2], "quantite": 1, "categorie": "Sonorisation", "statut": "maintenance"},
            {"nom": "Lyre LED (réparation)", "local": locaux[2], "quantite": 1, "categorie": "Éclairage", "statut": "maintenance"},
        ]
        
        materiels = []
        for data in materiels_data:
            materiel = Materiel.query.filter_by(nom=data["nom"], local_id=data["local"].id).first()
            if not materiel:
                materiel = Materiel(
                    nom=data["nom"],
                    local_id=data["local"].id,
                    quantite=data["quantite"],
                    categorie=data["categorie"],
                    statut=data["statut"]
                )
                db.session.add(materiel)
                logger.info(f"  ✅ Matériel créé : {data['nom']} ({data['statut']})")
            else:
                logger.info(f"  ⏭️  Matériel existant : {data['nom']}")
            materiels.append(materiel)
        
        db.session.commit()
        
        # 3. CRÉER DES DJs (si pas déjà existants)
        logger.info("\n🎧 Vérification des DJs...")
        djs = DJ.query.all()
        if len(djs) == 0:
            logger.warning("  ⚠️  Aucun DJ trouvé. Création de DJs de test...")
            
            # Créer des utilisateurs DJ
            djs_data = [
                {"username": "dj_martin", "nom": "Martin", "prenom": "Alex", "email": "alex.martin@test.com"},
                {"username": "dj_sophie", "nom": "Dubois", "prenom": "Sophie", "email": "sophie.dubois@test.com"},
                {"username": "dj_thomas", "nom": "Bernard", "prenom": "Thomas", "email": "thomas.bernard@test.com"}
            ]
            
            for dj_data in djs_data:
                user = User.query.filter_by(username=dj_data["username"]).first()
                if not user:
                    user = User(
                        username=dj_data["username"],
                        nom=dj_data["nom"],
                        prenom=dj_data["prenom"],
                        email=dj_data["email"],
                        password_hash=generate_password_hash("test123"),
                        role="dj",
                        actif=True
                    )
                    db.session.add(user)
                    db.session.flush()
                    
                    # Créer le DJ
                    dj = DJ(
                        nom=f"{dj_data['prenom']} {dj_data['nom']}",
                        contact=dj_data["email"],
                        user_id=user.id
                    )
                    db.session.add(dj)
                    logger.info(f"  ✅ DJ créé : {dj.nom}")
            
            db.session.commit()
            djs = DJ.query.all()
        else:
            logger.info(f"  ✅ {len(djs)} DJ(s) trouvé(s)")
        
        # 4. CRÉER DES PRESTATIONS AVEC MATÉRIEL
        logger.info("\n🎉 Création des prestations...")
        
        today = date.today()
        
        prestations_data = [
            {
                "client": "Mairie de Paris",
                "lieu": "Hôtel de Ville, Paris",
                "date_debut": today + timedelta(days=5),
                "date_fin": today + timedelta(days=5),
                "heure_debut": time(14, 0),
                "heure_fin": time(18, 0),
                "dj": djs[0] if len(djs) > 0 else None,
                "notes": "Cérémonie officielle - Matériel haut de gamme requis",
                "statut": "planifiee",
                "materiels": [0, 1, 5, 6]  # Indices dans la liste materiels
            },
            {
                "client": "Entreprise TechCorp",
                "lieu": "La Défense, Paris",
                "date_debut": today + timedelta(days=5),
                "date_fin": today + timedelta(days=5),
                "heure_debut": time(20, 0),
                "heure_fin": time(2, 0),  # Passe minuit !
                "dj": djs[1] if len(djs) > 1 else djs[0],
                "notes": "Soirée d'entreprise - Ambiance festive",
                "statut": "confirmee",
                "materiels": [0, 2, 6, 7]  # Même jour, heures différentes !
            },
            {
                "client": "Association Les Amis du Jazz",
                "lieu": "Salle Pleyel, Paris",
                "date_debut": today + timedelta(days=10),
                "date_fin": today + timedelta(days=10),
                "heure_debut": time(19, 0),
                "heure_fin": time(23, 0),
                "dj": djs[2] if len(djs) > 2 else djs[0],
                "notes": "Concert de jazz - Sonorisation premium",
                "statut": "planifiee",
                "materiels": [1, 3, 4, 5]
            },
            {
                "client": "Famille Dupont",
                "lieu": "Château de Versailles",
                "date_debut": today + timedelta(days=15),
                "date_fin": today + timedelta(days=15),
                "heure_debut": time(16, 0),
                "heure_fin": time(1, 0),
                "dj": djs[0] if len(djs) > 0 else None,
                "notes": "Mariage - Configuration complète",
                "statut": "planifiee",
                "materiels": [0, 1, 2, 5, 6, 7, 8]
            }
        ]
        
        # Récupérer l'utilisateur admin pour créer les prestations
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User.query.first()
        
        prestations = []
        for data in prestations_data:
            # Vérifier si la prestation existe déjà
            existing = Prestation.query.filter_by(
                client=data["client"],
                date_debut=data["date_debut"]
            ).first()
            
            if not existing:
                prestation = Prestation(
                    client=data["client"],
                    lieu=data["lieu"],
                    date_debut=data["date_debut"],
                    date_fin=data["date_fin"],
                    heure_debut=data["heure_debut"],
                    heure_fin=data["heure_fin"],
                    dj_id=data["dj"].id if data["dj"] else None,
                    createur_id=admin.id if admin else 1,
                    notes=data["notes"],
                    statut=data["statut"]
                )
                db.session.add(prestation)
                db.session.flush()
                
                # Assigner le matériel
                for mat_idx in data["materiels"]:
                    if mat_idx < len(materiels):
                        mp = MaterielPresta(
                            materiel_id=materiels[mat_idx].id,
                            prestation_id=prestation.id,
                            quantite=1
                        )
                        db.session.add(mp)
                
                prestations.append(prestation)
                logger.info(f"  ✅ Prestation créée : {data['client']} - {data['date_debut']} {data['heure_debut']}-{data['heure_fin']}")
            else:
                prestations.append(existing)
                logger.info(f"  ⏭️  Prestation existante : {data['client']}")
        
        db.session.commit()
        
        # 5. CRÉER DES RÉSERVATIONS CLIENT
        logger.info("\n📅 Création des réservations...")
        
        # Générer des numéros de réservation uniques
        count = ReservationClient.query.count()
        
        reservations_data = [
            {
                "numero": f"RES-{datetime.now().strftime('%Y%m%d')}-{count + 1:03d}",
                "nom": "Jean Durand",
                "email": "jean.durand@example.com",
                "telephone": "06 12 34 56 78",
                "adresse": "10 avenue des Champs-Élysées, 75008 Paris",
                "date_souhaitee": today + timedelta(days=20),
                "heure_souhaitee": time(18, 0),
                "duree_heures": 5.0,
                "type_prestation": "Mariage",
                "nb_invites": 150,
                "prix_prestation": 0.0,  # Sera défini par le manager
                "demandes_speciales": "Besoin d'éclairage d'ambiance et sonorisation complète",
                "statut": "en_attente"
            },
            {
                "numero": f"RES-{datetime.now().strftime('%Y%m%d')}-{count + 2:03d}",
                "nom": "Marie Leclerc",
                "email": "marie.leclerc@example.com",
                "telephone": "06 98 76 54 32",
                "adresse": "5 rue de la Paix, 69001 Lyon",
                "date_souhaitee": today + timedelta(days=25),
                "heure_souhaitee": time(20, 0),
                "duree_heures": 6.0,
                "type_prestation": "Anniversaire",
                "nb_invites": 80,
                "prix_prestation": 0.0,  # Sera défini par le manager
                "demandes_speciales": "Soirée années 80, besoin de jeux de lumière",
                "statut": "en_attente"
            }
        ]
        
        for data in reservations_data:
            existing = ReservationClient.query.filter_by(
                email=data["email"],
                date_souhaitee=data["date_souhaitee"]
            ).first()
            
            if not existing:
                reservation = ReservationClient(**data)
                db.session.add(reservation)
                logger.info(f"  ✅ Réservation créée : {data['nom']} - {data['date_souhaitee']}")
            else:
                logger.info(f"  ⏭️  Réservation existante : {data['nom']}")
        
        db.session.commit()
        
        # 6. RÉSUMÉ
        logger.info("\n" + "=" * 70)
        logger.info("✅ PEUPLEMENT TERMINÉ !")
        logger.info("=" * 70)
        logger.info(f"\n📊 RÉSUMÉ :")
        logger.info(f"  • Locaux : {Local.query.count()}")
        logger.info(f"  • Matériels : {Materiel.query.count()}")
        logger.info(f"    - Disponibles : {Materiel.query.filter_by(statut='disponible').count()}")
        logger.info(f"    - En maintenance : {Materiel.query.filter_by(statut='maintenance').count()}")
        logger.info(f"  • DJs : {DJ.query.count()}")
        logger.info(f"  • Prestations : {Prestation.query.count()}")
        logger.info(f"  • Réservations : {ReservationClient.query.count()}")
        logger.info(f"  • Assignations matériel : {MaterielPresta.query.count()}")
        
        logger.info("\n🎯 SCÉNARIOS DE TEST DISPONIBLES :")
        logger.info("=" * 70)
        logger.info("\n1️⃣  MÊME JOUR, CRÉNEAUX DIFFÉRENTS :")
        logger.info(f"   Date : {today + timedelta(days=5)}")
        logger.info("   • 14h-18h : Mairie de Paris (Enceinte JBL, LED PAR64, Lyre)")
        logger.info("   • 20h-02h : TechCorp (Enceinte JBL, Caisson, Lyre, Stroboscope)")
        logger.info("   → L'Enceinte JBL est utilisée 2x le même jour !")
        
        logger.info("\n2️⃣  MATÉRIEL EN MAINTENANCE :")
        logger.info("   • Enceinte QSC K10.2 (HS) - Ne devrait JAMAIS apparaître")
        logger.info("   • Lyre LED (réparation) - Ne devrait JAMAIS apparaître")
        
        logger.info("\n3️⃣  RÉSERVATIONS EN ATTENTE :")
        logger.info(f"   • Jean Durand - {today + timedelta(days=20)} à 18h (5h)")
        logger.info(f"   • Marie Leclerc - {today + timedelta(days=25)} à 20h (6h)")
        logger.info("   → Essaye d'assigner du matériel à ces réservations !")
        
        logger.info("\n4️⃣  TESTS À FAIRE :")
        logger.info("   ✓ Assigner du matériel à une réservation")
        logger.info("   ✓ Vérifier qu'un matériel assigné le 5 est dispo le 10")
        logger.info("   ✓ Essayer d'assigner un matériel au même créneau (doit échouer)")
        logger.info("   ✓ Vérifier que le matériel en maintenance n'apparaît pas")
        
        logger.info("\n" + "=" * 70)
        logger.info("🚀 Tu peux maintenant tester le système !")
        logger.info("=" * 70)

if __name__ == '__main__':
    populate_test_data()
    logger.info("\n✨ Script terminé avec succès !")

