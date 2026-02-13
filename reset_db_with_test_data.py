#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reinitialise la base et injecte un jeu de donnees propre et modere.
- Conserve le superadmin (meme username/email/mot de passe hashe).
- Ajoute quelques utilisateurs, prestations, devis, factures et materiel.
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta, date, time
from typing import Optional, Dict

from werkzeug.security import generate_password_hash

DB_PATH = "instance/dj_prestations.db"
logger = logging.getLogger(__name__)


def _row_to_dict(cursor, row):
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def fetch_superadmin() -> Optional[Dict]:
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            conn.close()
            return None
        # Priorite au compte gnizery si present
        cursor.execute("SELECT * FROM users WHERE username = ? LIMIT 1", ("gnizery",))
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT * FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
            row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT * FROM users ORDER BY id LIMIT 1")
            row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        admin = _row_to_dict(cursor, row)
        conn.close()
        return admin
    except Exception as exc:
        logger.error(f"Erreur lecture superadmin: {exc}")
        return None


def reset_database():
    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Backup DB: {backup_path}")
        os.remove(DB_PATH)
        logger.info("Ancienne DB supprimee")
    os.makedirs("instance", exist_ok=True)


def init_database(superadmin: Optional[Dict]):
    from app import app, db, init_db, User

    with app.app_context():
        init_db()

        # Reinserer le superadmin si trouve, sinon creer gnizery/greg12345
        if superadmin:
            user = User(
                id=superadmin.get("id"),
                username=superadmin.get("username"),
                email=superadmin.get("email"),
                password_hash=superadmin.get("password_hash"),
                role=superadmin.get("role") or "admin",
                nom=superadmin.get("nom") or "Gnizery",
                prenom=superadmin.get("prenom") or "Greg",
                telephone=superadmin.get("telephone"),
                actif=bool(superadmin.get("actif", True)),
                date_creation=_parse_dt(superadmin.get("date_creation")),
                derniere_connexion=_parse_dt(superadmin.get("derniere_connexion")),
                photo_profil=superadmin.get("photo_profil"),
                bio=superadmin.get("bio"),
                adresse=superadmin.get("adresse"),
                ville=superadmin.get("ville"),
                code_postal=superadmin.get("code_postal"),
                date_naissance=_parse_date(superadmin.get("date_naissance")),
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Superadmin conserve: {user.username}")
            return user

        user = User(
            username="gnizery",
            email="admin@planify.local",
            password_hash=generate_password_hash("greg12345"),
            role="admin",
            nom="Gnizery",
            prenom="Greg",
            actif=True,
            date_creation=datetime.now(),
        )
        db.session.add(user)
        db.session.commit()
        logger.info("Superadmin cree: gnizery")
        return user


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


def _duration_hours(heure_debut: time, heure_fin: time) -> float:
    start = datetime.combine(date.today(), heure_debut)
    end = datetime.combine(date.today(), heure_fin)
    if end <= start:
        end += timedelta(days=1)
    return round((end - start).total_seconds() / 3600, 1)


def seed_data(superadmin_user):
    from app import (
        app, db, User, DJ, Local, Materiel, Prestation,
        ReservationClient, MaterielPresta, Devis, Facture, MouvementMateriel,
        ParametresEntreprise, generate_document_number, utcnow
    )

    with app.app_context():
        # Parametres entreprise
        params = ParametresEntreprise.query.first()
        if not params:
            params = ParametresEntreprise(
                nom_entreprise="Planify Labs",
                email="contact@planify.local",
                telephone="06 10 20 30 40",
                adresse="12 Rue de la Paix",
                code_postal="75002",
                ville="Paris",
                siret="12345678900011",
                tva_intracommunautaire="FR12345678901",
                slogan="Gestion claire des missions",
                description_courte="Pilotage des missions, materiel et facturation",
            )
            db.session.add(params)
            db.session.commit()

        # Utilisateurs
        def create_user(username, nom, prenom, email, role):
            user = User(
                username=username,
                nom=nom,
                prenom=prenom,
                email=email,
                password_hash=generate_password_hash("test12345"),
                role=role,
                actif=True,
                date_creation=datetime.now() - timedelta(days=30)
            )
            db.session.add(user)
            db.session.flush()
            return user

        managers = [
            create_user("manager_01", "Durand", "Alice", "alice.manager@test.com", "manager"),
            create_user("manager_02", "Moreau", "Nicolas", "nicolas.manager@test.com", "manager"),
        ]
        techniciens = [
            create_user("tech_01", "Martin", "Lea", "lea.tech@test.com", "technicien"),
            create_user("tech_02", "Bernard", "Marc", "marc.tech@test.com", "technicien"),
        ]
        dj_users = [
            create_user("dj_antoine", "Lefevre", "Antoine", "antoine.dj@test.com", "dj"),
            create_user("dj_ines", "Petit", "Ines", "ines.dj@test.com", "dj"),
            create_user("dj_luc", "Robert", "Luc", "luc.dj@test.com", "dj"),
        ]

        djs = []
        for user in dj_users:
            dj = DJ(nom=f"{user.prenom} {user.nom}", contact=user.email, user_id=user.id)
            db.session.add(dj)
            djs.append(dj)
        db.session.commit()

        # Locaux
        locaux_data = [
            {"nom": "Stock Paris Centre", "adresse": "20 Rue de Rivoli, 75004 Paris"},
            {"nom": "Entrepot Lyon", "adresse": "10 Place Bellecour, 69002 Lyon"},
            {"nom": "Hub Marseille", "adresse": "5 Quai des Belges, 13001 Marseille"},
        ]
        locaux = []
        for data in locaux_data:
            local = Local(nom=data["nom"], adresse=data["adresse"])
            db.session.add(local)
            locaux.append(local)
        db.session.commit()

        # Materiel
        materiels_data = [
            {"nom": "Enceinte JBL PRX815", "categorie": "Sonorisation", "quantite": 6, "prix_location": 30, "local": locaux[0]},
            {"nom": "Caisson JBL PRX818", "categorie": "Sonorisation", "quantite": 3, "prix_location": 40, "local": locaux[0]},
            {"nom": "Console Pioneer DDJ-1000", "categorie": "Console", "quantite": 2, "prix_location": 50, "local": locaux[0]},
            {"nom": "Micro Shure SM58", "categorie": "Sonorisation", "quantite": 10, "prix_location": 5, "local": locaux[1]},
            {"nom": "Projecteur LED PAR 64", "categorie": "Eclairage", "quantite": 12, "prix_location": 8, "local": locaux[1]},
            {"nom": "Lyre LED Spot", "categorie": "Eclairage", "quantite": 6, "prix_location": 15, "local": locaux[1]},
            {"nom": "Machine a fumee 1500W", "categorie": "Effets", "quantite": 3, "prix_location": 12, "local": locaux[2]},
            {"nom": "Stroboscope LED", "categorie": "Effets", "quantite": 4, "prix_location": 10, "local": locaux[2]},
            {"nom": "Pieds enceintes", "categorie": "Accessoires", "quantite": 8, "prix_location": 4, "local": locaux[0]},
            {"nom": "Pack cables XLR", "categorie": "Accessoires", "quantite": 20, "prix_location": 2, "local": locaux[0]},
        ]
        materiels = []
        for idx, data in enumerate(materiels_data, start=1):
            serial = f"SN-{idx:04d}"
            barcode = f"CB-{idx:04d}"
            materiel = Materiel(
                nom=data["nom"],
                categorie=data["categorie"],
                quantite=data["quantite"],
                prix_location=data["prix_location"],
                local_id=data["local"].id,
                statut="disponible",
                numero_serie=serial,
                code_barre=barcode
            )
            db.session.add(materiel)
            materiels.append(materiel)
        db.session.commit()

        # Prestations
        base_date = date.today()
        now = datetime.now()
        sortie_start = (now - timedelta(hours=1)).time().replace(second=0, microsecond=0)
        sortie_end = (now + timedelta(hours=3)).time().replace(second=0, microsecond=0)
        retour_start = time(9, 0)
        retour_end = time(12, 0)
        prestations_data = [
            {
                "client": "TEST SORTIE (aujourd'hui)",
                "lieu": "Atelier Planify, 12 Rue de la Paix, 75002 Paris",
                "lat": 48.8686, "lng": 2.3322,
                "date": base_date,
                "start": sortie_start, "end": sortie_end,
                "dj": djs[0], "technicien": techniciens[0],
                "statut": "confirmee",
                "materiel": [(0, 2), (1, 1), (8, 2)],
                "tag": "test_sortie",
            },
            {
                "client": "TEST RETOUR (terminée)",
                "lieu": "Stock Paris Centre, 20 Rue de Rivoli, 75004 Paris",
                "lat": 48.8566, "lng": 2.3522,
                "date": base_date - timedelta(days=1),
                "start": retour_start, "end": retour_end,
                "dj": djs[1], "technicien": techniciens[1],
                "statut": "terminee",
                "materiel": [(2, 1), (3, 2), (9, 4)],
                "tag": "test_retour",
            },
            {
                "client": "Hotel de Ville Paris",
                "lieu": "Place de l'Hotel de Ville, 75004 Paris",
                "lat": 48.8566, "lng": 2.3522,
                "date": base_date + timedelta(days=3),
                "start": time(14, 0), "end": time(18, 0),
                "dj": djs[0], "technicien": techniciens[0],
                "statut": "planifiee",
                "materiel": [(0, 2), (4, 4), (8, 2)],
            },
            {
                "client": "Studio Orion",
                "lieu": "5 Avenue Anatole France, 75007 Paris",
                "lat": 48.8584, "lng": 2.2945,
                "date": base_date + timedelta(days=4),
                "start": time(10, 0), "end": time(16, 0),
                "dj": djs[1], "technicien": techniciens[1],
                "statut": "confirmee",
                "materiel": [(1, 1), (2, 1), (4, 3), (5, 2)],
            },
            {
                "client": "Maison des Arts Lyon",
                "lieu": "20 Place Bellecour, 69002 Lyon",
                "lat": 45.7578, "lng": 4.8320,
                "date": base_date + timedelta(days=7),
                "start": time(18, 0), "end": time(23, 0),
                "dj": djs[2], "technicien": techniciens[0],
                "statut": "planifiee",
                "materiel": [(0, 2), (3, 2), (4, 4)],
            },
            {
                "client": "Entreprise Nova",
                "lieu": "1 Rue Scribe, 75009 Paris",
                "lat": 48.8718, "lng": 2.3322,
                "date": base_date + timedelta(days=9),
                "start": time(9, 0), "end": time(13, 30),
                "dj": djs[0], "technicien": None,
                "statut": "planifiee",
                "materiel": [(2, 1), (4, 2), (9, 6)],
            },
            {
                "client": "Cafe des Arts",
                "lieu": "2 Rue de la Republique, 13001 Marseille",
                "lat": 43.2965, "lng": 5.3754,
                "date": base_date + timedelta(days=11),
                "start": time(19, 0), "end": time(23, 30),
                "dj": djs[1], "technicien": techniciens[1],
                "statut": "confirmee",
                "materiel": [(0, 1), (6, 1), (7, 1)],
            },
            {
                "client": "Festival Riverside",
                "lieu": "Quai des Celestins, 75004 Paris",
                "lat": 48.8529, "lng": 2.3622,
                "date": base_date + timedelta(days=15),
                "start": time(16, 0), "end": time(22, 0),
                "dj": djs[2], "technicien": techniciens[0],
                "statut": "planifiee",
                "materiel": [(0, 3), (1, 1), (4, 6), (5, 3)],
            },
            {
                "client": "Musee Lumiere",
                "lieu": "25 Rue du Premier Film, 69008 Lyon",
                "lat": 45.7450, "lng": 4.8706,
                "date": base_date + timedelta(days=1),
                "start": time(13, 0), "end": time(18, 0),
                "dj": djs[0], "technicien": None,
                "statut": "terminee",
                "materiel": [(3, 2), (4, 2), (8, 2)],
            },
            {
                "client": "Soiree Privee Lagune",
                "lieu": "12 Quai de Rive Neuve, 13007 Marseille",
                "lat": 43.2927, "lng": 5.3649,
                "date": base_date + timedelta(days=20),
                "start": time(20, 0), "end": time(1, 0),
                "dj": djs[1], "technicien": techniciens[1],
                "statut": "planifiee",
                "materiel": [(0, 2), (6, 1), (7, 1)],
            },
        ]

        prestations = []
        test_sortie_presta = None
        test_retour_presta = None
        for data in prestations_data:
            date_fin = data["date"]
            if data["end"] <= data["start"]:
                date_fin = data["date"] + timedelta(days=1)
            prestation = Prestation(
                client=data["client"],
                lieu=data["lieu"],
                date_debut=data["date"],
                date_fin=date_fin,
                heure_debut=data["start"],
                heure_fin=data["end"],
                dj_id=data["dj"].id,
                technicien_id=data["technicien"].id if data["technicien"] else None,
                createur_id=superadmin_user.id,
                notes="Mission generee pour tests",
                statut=data["statut"],
                lieu_lat=data["lat"],
                lieu_lng=data["lng"],
                lieu_formatted=data["lieu"],
            )
            db.session.add(prestation)
            db.session.flush()

            for materiel_index, quantite in data["materiel"]:
                materiel = materiels[materiel_index]
                assign = MaterielPresta(
                    materiel_id=materiel.id,
                    prestation_id=prestation.id,
                    quantite=quantite
                )
                db.session.add(assign)

            if data.get("tag") == "test_sortie":
                test_sortie_presta = prestation
            if data.get("tag") == "test_retour":
                test_retour_presta = prestation

            prestations.append(prestation)
        db.session.commit()

        # Créer des mouvements de sortie pour la prestation de retour (afin de tester les retours)
        if test_retour_presta:
            assigned_items = MaterielPresta.query.filter_by(prestation_id=test_retour_presta.id).all()
            for assign in assigned_items:
                materiel = db.session.get(Materiel, assign.materiel_id)
                mouvement = MouvementMateriel(
                    materiel_id=assign.materiel_id,
                    prestation_id=test_retour_presta.id,
                    type_mouvement='sortie',
                    quantite=assign.quantite,
                    local_depart_id=materiel.local_id if materiel else None,
                    utilisateur_id=superadmin_user.id,
                    date_mouvement=utcnow(),
                    notes="Sortie test pour retour"
                )
                db.session.add(mouvement)
            db.session.commit()

        # Reservations
        reservations = [
            {
                "numero": f"RES-{datetime.now().strftime('%Y%m%d')}-001",
                "nom": "Paul Girard",
                "email": "paul.girard@example.com",
                "telephone": "06 11 22 33 44",
                "adresse": "8 Rue de Provence, 75009 Paris",
                "date_souhaitee": base_date + timedelta(days=18),
                "heure_souhaitee": time(19, 0),
                "duree_heures": 4.0,
                "type_prestation": "Entreprise",
                "nb_invites": 120,
                "prix_prestation": 0.0,
                "demandes_speciales": "Sonorisation et eclairage ambiance",
                "statut": "en_attente",
            },
            {
                "numero": f"RES-{datetime.now().strftime('%Y%m%d')}-002",
                "nom": "Camille Noel",
                "email": "camille.noel@example.com",
                "telephone": "06 22 33 44 55",
                "adresse": "3 Rue Merciere, 69002 Lyon",
                "date_souhaitee": base_date + timedelta(days=22),
                "heure_souhaitee": time(20, 30),
                "duree_heures": 5.0,
                "type_prestation": "Anniversaire",
                "nb_invites": 60,
                "prix_prestation": 0.0,
                "demandes_speciales": "Set DJ + micro",
                "statut": "en_attente",
            },
        ]
        for data in reservations:
            reservation = ReservationClient(**data)
            db.session.add(reservation)
        db.session.commit()

        # Devis
        devis_list = []
        for idx, prestation in enumerate(prestations[:5], start=1):
            duree = _duration_hours(prestation.heure_debut, prestation.heure_fin)
            devis = Devis(
                numero=generate_document_number("DEV"),
                prestation_id=prestation.id,
                client_nom=prestation.client,
                client_email=f"client{idx}@example.com",
                client_telephone="06 00 00 00 00",
                client_adresse=prestation.lieu,
                prestation_titre=f"Mission Prestataire - {prestation.client}",
                prestation_description="Prestations DJ + technique",
                date_prestation=prestation.date_debut,
                heure_debut=prestation.heure_debut,
                heure_fin=prestation.heure_fin,
                lieu=prestation.lieu,
                tarif_horaire=120.0,
                duree_heures=duree,
                frais_transport=20.0,
                taux_tva=20.0,
                statut="brouillon",
                dj_id=prestation.dj_id,
                createur_id=superadmin_user.id,
                date_creation=utcnow(),
                tva_incluse=True,
            )
            devis.calculer_totaux()

            if idx == 2:
                devis.statut = "envoye"
                devis.date_envoi = utcnow()
            if idx == 3:
                devis.est_signe = True
                devis.statut = "accepte"
                devis.date_acceptation = utcnow()
                devis.signature_date = utcnow()
                devis.signature_ip = "127.0.0.1"
                devis.signature_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
            devis_list.append(devis)
            db.session.add(devis)
        db.session.commit()

        # Factures
        for idx, devis in enumerate(devis_list[:3], start=1):
            prestation = devis.prestation
            facture = Facture(
                numero=generate_document_number("FAC"),
                prestation_id=prestation.id,
                devis_id=devis.id,
                client_nom=devis.client_nom,
                client_email=devis.client_email,
                client_telephone=devis.client_telephone,
                client_adresse=devis.client_adresse,
                prestation_titre=devis.prestation_titre,
                prestation_description=devis.prestation_description,
                date_prestation=devis.date_prestation,
                heure_debut=devis.heure_debut,
                heure_fin=devis.heure_fin,
                lieu=devis.lieu,
                tarif_horaire=devis.tarif_horaire,
                duree_heures=devis.duree_heures,
                frais_transport=devis.frais_transport,
                taux_tva=devis.taux_tva,
                statut="envoyee",
                date_creation=utcnow(),
                date_echeance=date.today() + timedelta(days=15),
                createur_id=superadmin_user.id,
                dj_id=devis.dj_id,
            )
            facture.calculer_totaux()

            if idx == 2:
                facture.statut = "partiellement_payee"
                facture.montant_paye = round(facture.montant_ttc * 0.4, 2)
            if idx == 3:
                facture.statut = "payee"
                facture.montant_paye = facture.montant_ttc
                facture.date_paiement = date.today()
            if idx == 1:
                facture.date_echeance = date.today() - timedelta(days=5)

            db.session.add(facture)
        db.session.commit()


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Reinitialisation de la base...")
    superadmin = fetch_superadmin()
    reset_database()
    admin_user = init_database(superadmin)
    seed_data(admin_user)
    logger.info("Base propre creee avec donnees de test.")


if __name__ == "__main__":
    main()
