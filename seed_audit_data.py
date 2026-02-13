#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed non-destructive audit data for key flows.
Creates data only if missing (identified by AUDIT prefix).
"""

import os
import sys
from datetime import datetime, date, time, timedelta, timezone
from werkzeug.security import generate_password_hash

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import (
    app,
    db,
    Local,
    Materiel,
    DJ,
    User,
    Prestation,
    MaterielPresta,
    ReservationClient,
    Devis,
    Facture,
    Paiement,
    ParametresEntreprise,
)


AUDIT_PREFIX = "AUDIT"


def _get_or_create_user(username, email, role, nom, prenom, telephone=None):
    user = User.query.filter_by(username=username).first()
    if user:
        return user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash("audit123"),
        role=role,
        nom=nom,
        prenom=prenom,
        telephone=telephone or "",
        actif=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def seed_audit_data():
    with app.app_context():
        # Parametres entreprise
        if not ParametresEntreprise.query.first():
            params = ParametresEntreprise(
                nom_entreprise="Audit Events Manager",
                email="audit@example.com",
                telephone="0102030405",
                adresse="1 Audit Street",
                code_postal="75001",
                ville="Paris",
                siret="12345678901234",
                tva_intracommunautaire="FR12345678901",
                slogan="Audit ready",
                description_courte="Audit dataset for full feature coverage",
                module_google_calendar=False,
                module_excel_export=True,
                module_pdf_generation=True,
                module_notifications=True,
                module_icalendar=True,
            )
            db.session.add(params)

        # Users
        audit_admin = _get_or_create_user(
            "audit_admin",
            "audit_admin@example.com",
            "admin",
            "Audit",
            "Admin",
            "0600000001",
        )
        admin = User.query.filter_by(role="admin").first() or audit_admin
        manager = User.query.filter_by(role="manager").first()
        if not manager:
            manager = _get_or_create_user(
                "audit_manager",
                "audit_manager@example.com",
                "manager",
                "Audit",
                "Manager",
                "0600000002",
            )
        technicien = User.query.filter_by(role="technicien").first()
        if not technicien:
            technicien = _get_or_create_user(
                "audit_tech",
                "audit_tech@example.com",
                "technicien",
                "Audit",
                "Tech",
                "0600000003",
            )

        # DJs
        dj = DJ.query.first()
        if not dj:
            dj_user = _get_or_create_user(
                "audit_dj",
                "audit_dj@example.com",
                "dj",
                "Audit",
                "DJ",
                "0600000004",
            )
            dj = DJ(nom="Audit DJ", contact="audit_dj@example.com", notes="Audit DJ", user_id=dj_user.id)
            db.session.add(dj)

        # Locaux
        local_a = Local.query.filter_by(nom=f"{AUDIT_PREFIX} Local A").first()
        if not local_a:
            local_a = Local(nom=f"{AUDIT_PREFIX} Local A", adresse="10 Audit Road")
            db.session.add(local_a)
        local_b = Local.query.filter_by(nom=f"{AUDIT_PREFIX} Local B").first()
        if not local_b:
            local_b = Local(nom=f"{AUDIT_PREFIX} Local B", adresse="20 Audit Road")
            db.session.add(local_b)
        db.session.flush()

        # Materiel
        materiel_specs = [
            ("Speaker A", "Audio", "disponible", local_a),
            ("Speaker B", "Audio", "disponible", local_a),
            ("Mixer A", "Console", "disponible", local_b),
            ("Light A", "Lighting", "maintenance", local_b),
            ("Light B", "Lighting", "hors_service", local_b),
            ("Mic A", "Audio", "disponible", local_a),
        ]
        materiels = []
        for idx, (name, categorie, statut, local) in enumerate(materiel_specs, start=1):
            sn = f"{AUDIT_PREFIX}-SN-{idx:03d}"
            code = f"{AUDIT_PREFIX}-CB-{idx:03d}"
            materiel = Materiel.query.filter_by(numero_serie=sn).first()
            if not materiel:
                materiel = Materiel(
                    nom=f"{AUDIT_PREFIX} {name}",
                    categorie=categorie,
                    quantite=2 if idx in (1, 2) else 1,
                    statut=statut,
                    local_id=local.id,
                    numero_serie=sn,
                    code_barre=code,
                    prix_location=25.0 + idx,
                    notes_technicien="Audit notes",
                    derniere_maintenance=datetime.now(timezone.utc) - timedelta(days=30) if statut != "disponible" else None,
                )
                db.session.add(materiel)
            materiels.append(materiel)
        db.session.flush()

        # Prestations
        today = date.today()
        prestation_specs = [
            ("Audit Client 1", today + timedelta(days=3), time(18, 0), time(23, 0), "planifiee"),
            ("Audit Client 2", today + timedelta(days=3), time(20, 0), time(1, 0), "confirmee"),
            ("Audit Client 3", today - timedelta(days=2), time(19, 0), time(23, 0), "terminee"),
            ("Audit Client 4", today + timedelta(days=10), time(17, 0), time(22, 0), "annulee"),
        ]
        prestations = []
        for idx, (client, date_debut, heure_debut, heure_fin, statut) in enumerate(prestation_specs, start=1):
            existing = Prestation.query.filter_by(client=client, date_debut=date_debut).first()
            if not existing:
                prestation = Prestation(
                    client=client,
                    client_email=f"audit_client_{idx}@example.com",
                    client_telephone=f"06000001{idx:02d}",
                    lieu=f"Audit Venue {idx}",
                    date_debut=date_debut,
                    date_fin=date_debut,
                    heure_debut=heure_debut,
                    heure_fin=heure_fin,
                    dj_id=dj.id,
                    createur_id=admin.id,
                    notes="Audit prestation",
                    statut=statut,
                )
                db.session.add(prestation)
                db.session.flush()
                prestations.append(prestation)
            else:
                prestations.append(existing)

        # Assignations materiel -> prestations
        if prestations:
            assignations = [
                (prestations[0], materiels[0], 1),
                (prestations[0], materiels[1], 1),
                (prestations[1], materiels[0], 1),
                (prestations[1], materiels[2], 1),
                (prestations[2], materiels[5], 1),
            ]
            for prestation, materiel, quantite in assignations:
                exists = MaterielPresta.query.filter_by(
                    prestation_id=prestation.id, materiel_id=materiel.id
                ).first()
                if not exists:
                    db.session.add(
                        MaterielPresta(
                            prestation_id=prestation.id,
                            materiel_id=materiel.id,
                            quantite=quantite,
                        )
                    )

        # Reservations
        reservation_specs = [
            ("AUDIT-RES-001", "Audit Guest 1", "audit1@example.com", "0600001001", "en_attente"),
            ("AUDIT-RES-002", "Audit Guest 2", "audit2@example.com", "0600001002", "en_attente_dj"),
            ("AUDIT-RES-003", "Audit Guest 3", "audit3@example.com", "0600001003", "validee"),
            ("AUDIT-RES-004", "Audit Guest 4", "audit4@example.com", "0600001004", "confirmee"),
        ]
        reservations = []
        for idx, (numero, nom, email, tel, statut) in enumerate(reservation_specs, start=1):
            existing = ReservationClient.query.filter_by(numero=numero).first()
            if not existing:
                reservation = ReservationClient(
                    numero=numero,
                    nom=nom,
                    email=email,
                    telephone=tel,
                    adresse=f"{idx} Audit Avenue",
                    nb_invites=80 + idx * 5,
                    type_lieu="salle",
                    demandes_speciales="Audit reservation",
                    type_prestation="mariage",
                    prix_prestation=1200.0 + idx * 50,
                    duree_heures=5,
                    date_souhaitee=today + timedelta(days=20 + idx),
                    heure_souhaitee=time(18, 30),
                    statut=statut,
                    manager_id=manager.id,
                    validee_par_manager=statut in ("validee", "confirmee"),
                    dj_id=dj.id,
                    validee_par_dj=statut == "confirmee",
                )
                if statut == "validee":
                    reservation.date_validation = datetime.now(timezone.utc)
                if statut == "confirmee":
                    reservation.date_confirmation = datetime.now(timezone.utc)
                    reservation.prestation_id = prestations[0].id if prestations else None
                db.session.add(reservation)
                db.session.flush()
                reservations.append(reservation)
            else:
                reservations.append(existing)

        # Assignation materiel -> reservation
        if reservations:
            reservation = reservations[0]
            materiel = materiels[2]
            exists = MaterielPresta.query.filter_by(
                reservation_id=reservation.id, materiel_id=materiel.id
            ).first()
            if not exists:
                db.session.add(
                    MaterielPresta(
                        reservation_id=reservation.id,
                        materiel_id=materiel.id,
                        quantite=1,
                    )
                )

        # Devis
        devis_numero = f"{AUDIT_PREFIX}-DEV-001"
        devis = Devis.query.filter_by(numero=devis_numero).first()
        if not devis:
            devis = Devis(
                numero=devis_numero,
                client_nom="Audit Client Devis",
                client_email="audit_devis@example.com",
                client_telephone="0600002001",
                client_adresse="30 Audit Street",
                prestation_titre="Audit Devis Event",
                prestation_description="Audit devis description",
                date_prestation=today + timedelta(days=30),
                heure_debut=time(19, 0),
                heure_fin=time(1, 0),
                lieu="Audit Hall",
                tarif_horaire=120.0,
                duree_heures=6.0,
                montant_ht=720.0,
                taux_tva=20.0,
                montant_tva=144.0,
                montant_ttc=864.0,
                statut="envoye",
                date_creation=datetime.now(timezone.utc) - timedelta(days=2),
                date_validite=today + timedelta(days=30),
                dj_id=dj.id,
                createur_id=admin.id,
                prestation_id=prestations[0].id if prestations else None,
            )
            db.session.add(devis)

        # Factures
        facture_numero = f"{AUDIT_PREFIX}-FAC-001"
        facture = Facture.query.filter_by(numero=facture_numero).first()
        if not facture:
            facture = Facture(
                numero=facture_numero,
                client_nom="Audit Client Facture",
                client_email="audit_facture@example.com",
                client_telephone="0600003001",
                client_adresse="40 Audit Street",
                prestation_titre="Audit Facture Event",
                prestation_description="Audit facture description",
                date_prestation=today - timedelta(days=3),
                heure_debut=time(20, 0),
                heure_fin=time(2, 0),
                lieu="Audit Club",
                tarif_horaire=150.0,
                duree_heures=6.0,
                montant_ht=900.0,
                taux_tva=20.0,
                montant_tva=180.0,
                montant_ttc=1080.0,
                montant_paye=1080.0,
                statut="payee",
                date_creation=datetime.now(timezone.utc) - timedelta(days=10),
                date_echeance=today + timedelta(days=10),
                date_paiement=today - timedelta(days=1),
                mode_paiement="virement",
                notes="Audit facture",
                dj_id=dj.id,
                createur_id=admin.id,
                prestation_id=prestations[2].id if len(prestations) > 2 else None,
                devis_id=devis.id if devis else None,
            )
            db.session.add(facture)

        db.session.flush()

        # Paiements
        paiement_numero = f"{AUDIT_PREFIX}-PAY-001"
        paiement = Paiement.query.filter_by(numero=paiement_numero).first()
        if not paiement:
            paiement = Paiement(
                numero=paiement_numero,
                montant=1080.0,
                devise="EUR",
                type_paiement="facture",
                description="Audit payment",
                statut="reussi",
                date_paiement=datetime.now(timezone.utc) - timedelta(days=1),
                client_nom="Audit Client Facture",
                client_email="audit_facture@example.com",
                client_telephone="0600003001",
                facture_id=facture.id if facture else None,
                createur_id=admin.id,
            )
            db.session.add(paiement)

        db.session.commit()


if __name__ == "__main__":
    seed_audit_data()
    print("Audit seed completed.")
