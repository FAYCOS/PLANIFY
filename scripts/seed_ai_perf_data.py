#!/usr/bin/env python3
"""
Seed massif de données fictives pour tester les perfs IA.
"""

import argparse
import random
import string
import uuid
import os
import sys
from datetime import datetime, date, time, timedelta

from werkzeug.security import generate_password_hash

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app, db
from app import User, DJ, Local, Materiel, Prestation, MaterielPresta, Devis, Facture, ReservationClient, ParametresEntreprise
from init_key_manager import init_key_manager


FIRST_NAMES = [
    "Alex", "Camille", "Jordan", "Sacha", "Lina", "Noah", "Maya", "Hugo", "Lola", "Jade",
    "Liam", "Emma", "Lou", "Mila", "Eden", "Nina", "Théo", "Zoé", "Leo", "Ines"
]
LAST_NAMES = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy", "Moreau",
    "Simon", "Laurent", "Lefevre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier"
]
EVENT_TYPES = ["mariage", "anniversaire", "soirée entreprise", "festival", "bar", "club", "concert", "gala"]
LOCATIONS = ["Paris", "Lyon", "Marseille", "Bordeaux", "Lille", "Nantes", "Toulouse", "Nice", "Strasbourg"]
MUSIC_STYLES = ["house", "pop", "electro", "hip-hop", "funk", "rock", "afro", "disco"]
MATERIEL_CATEGORIES = ["Son", "Lumière", "Micro", "Décor", "Effets"]


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_phone():
    return "06" + "".join(random.choice(string.digits) for _ in range(8))


def random_email(name):
    local = name.lower().replace(" ", ".")
    token = uuid.uuid4().hex[:8]
    return f"{local}.{token}@example.com"


def random_date_between(start_date, end_date):
    delta = (end_date - start_date).days
    if delta <= 0:
        return start_date
    return start_date + timedelta(days=random.randint(0, delta))


def random_time_slot():
    start_hour = random.choice([18, 19, 20, 21])
    duration = random.choice([3, 4, 5, 6])
    start = time(start_hour, random.choice([0, 30]))
    end_hour = (start_hour + duration) % 24
    end = time(end_hour, random.choice([0, 30]))
    return start, end, duration


def compute_totals(tarif_horaire, duree_heures, frais_transport, frais_materiel, remise_pourcentage, remise_montant, taux_tva):
    montant_ht = (tarif_horaire * duree_heures) + frais_transport + frais_materiel
    if remise_pourcentage > 0:
        montant_ht -= montant_ht * (remise_pourcentage / 100)
    elif remise_montant > 0:
        montant_ht -= remise_montant
    montant_ht = max(0, montant_ht)
    montant_tva = montant_ht * (taux_tva / 100)
    montant_ttc = montant_ht + montant_tva
    return montant_ht, montant_tva, montant_ttc


def chunked(iterable, size):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def seed(scale, batch_size, seed_value, reset_db, admin_username, admin_password, admin_email, admin_nom, admin_prenom):
    random.seed(seed_value)
    today = date.today()
    start_date = today - timedelta(days=540)
    end_date = today + timedelta(days=180)

    base_counts = {
        "locals": 20,
        "djs": 80,
        "materiels": 300,
        "prestations": 3000,
        "devis": 2500,
        "factures": 2000,
        "reservations": 1200,
        "dj_users": 40,
        "managers": 6,
        "techniciens": 6,
    }
    counts = {k: max(1, int(v * scale)) for k, v in base_counts.items()}

    with app.app_context():
        if reset_db:
            db.drop_all()
            db.create_all()
            params = ParametresEntreprise(nom_entreprise="Planify (Test IA)")
            db.session.add(params)
            db.session.commit()
            init_key_manager.reset_initialization()

        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(
                username=admin_username,
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                role="admin",
                nom=admin_nom,
                prenom=admin_prenom,
                telephone=random_phone(),
                actif=True
            )
            db.session.add(admin)
            db.session.commit()

        if not init_key_manager.is_initialized():
            init_key_manager.create_init_key({
                'nom': admin_nom,
                'prenom': admin_prenom,
                'email': admin_email,
                'telephone': admin.telephone,
                'username': admin_username
            })

        # Managers / techniciens
        users = []
        for idx in range(counts["managers"]):
            name = random_name()
            unique = uuid.uuid4().hex[:8]
            users.append(User(
                username=f"manager_seed_{unique}",
                email=random_email(name),
                password_hash=generate_password_hash("password"),
                role="manager",
                nom=name.split(" ")[1],
                prenom=name.split(" ")[0],
                telephone=random_phone(),
                actif=True
            ))
        for idx in range(counts["techniciens"]):
            name = random_name()
            unique = uuid.uuid4().hex[:8]
            users.append(User(
                username=f"tech_seed_{unique}",
                email=random_email(name),
                password_hash=generate_password_hash("password"),
                role="technicien",
                nom=name.split(" ")[1],
                prenom=name.split(" ")[0],
                telephone=random_phone(),
                actif=True
            ))
        for batch in chunked(users, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        # DJ users (optionnels)
        dj_users = []
        for idx in range(counts["dj_users"]):
            name = random_name()
            unique = uuid.uuid4().hex[:8]
            dj_users.append(User(
                username=f"dj_seed_{unique}",
                email=random_email(name),
                password_hash=generate_password_hash("password"),
                role="dj",
                nom=name.split(" ")[1],
                prenom=name.split(" ")[0],
                telephone=random_phone(),
                actif=True
            ))
        for batch in chunked(dj_users, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        dj_users = User.query.filter(User.username.like('dj_seed_%')).all()

        # Locals
        locals_objs = []
        for idx in range(counts["locals"]):
            locals_objs.append(Local(
                nom=f"Local {idx + 1}",
                adresse=f"{random.randint(1, 150)} rue {random.choice(LAST_NAMES)}"
            ))
        for batch in chunked(locals_objs, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        locals_list = Local.query.all()

        # DJs
        djs = []
        for idx in range(counts["djs"]):
            name = random_name()
            link_user = dj_users[idx] if idx < len(dj_users) else None
            djs.append(DJ(
                nom=name,
                contact=random_email(name),
                notes=random.choice(["", "Spécialiste mariage", "DJ club", "Polyvalent"]),
                user_id=link_user.id if link_user else None
            ))
        for batch in chunked(djs, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        djs_list = DJ.query.all()

        # Materiels
        materiels = []
        for idx in range(counts["materiels"]):
            local = random.choice(locals_list)
            materiels.append(Materiel(
                nom=f"Materiel {idx + 1}",
                local_id=local.id,
                quantite=random.randint(1, 5),
                categorie=random.choice(MATERIEL_CATEGORIES),
                statut=random.choice(["disponible", "maintenance"]) if idx % 20 == 0 else "disponible",
                prix_location=round(random.uniform(5, 80), 2)
            ))
        for batch in chunked(materiels, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        materiel_ids = [m.id for m in Materiel.query.all()]

        # Prestations
        prestations = []
        for idx in range(counts["prestations"]):
            client = random_name()
            event_date = random_date_between(start_date, end_date)
            start_time, end_time, _ = random_time_slot()
            prestations.append(Prestation(
                date_debut=event_date,
                date_fin=event_date,
                heure_debut=start_time,
                heure_fin=end_time,
                client=client,
                client_telephone=random_phone(),
                client_email=random_email(client),
                lieu=random.choice(LOCATIONS),
                dj_id=random.choice(djs_list).id,
                createur_id=admin.id,
                notes=random.choice(["", "Prévoir micro", "Set house", "Mix généraliste"]),
                statut=random.choice(["planifiee", "confirmee", "terminee", "annulee"]) if idx % 10 != 0 else "planifiee"
            ))
        for batch in chunked(prestations, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        prestations_ids = [p.id for p in Prestation.query.all()]

        # Assignations matériel
        assignations = []
        for pid in random.sample(prestations_ids, k=min(len(prestations_ids), counts["prestations"] // 2)):
            for _ in range(random.randint(1, 3)):
                assignations.append(MaterielPresta(
                    prestation_id=pid,
                    materiel_id=random.choice(materiel_ids),
                    quantite=random.randint(1, 2)
                ))
        for batch in chunked(assignations, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        # Devis
        devis_list = []
        devis_start = Devis.query.count() + 1
        for idx in range(counts["devis"]):
            client = random_name()
            event_date = random_date_between(start_date, end_date)
            start_time, end_time, duration = random_time_slot()
            tarif_horaire = round(random.uniform(60, 200), 2)
            frais_transport = round(random.uniform(0, 150), 2)
            frais_materiel = round(random.uniform(0, 200), 2)
            remise_pourcentage = random.choice([0, 0, 10, 15])
            remise_montant = 0.0 if remise_pourcentage else random.choice([0, 20, 30])
            taux_tva = random.choice([10.0, 20.0])
            montant_ht, montant_tva, montant_ttc = compute_totals(
                tarif_horaire, duration, frais_transport, frais_materiel, remise_pourcentage, remise_montant, taux_tva
            )
            devis = Devis(
                numero=f"DEV-LOAD-{datetime.now().strftime('%Y%m%d')}-{devis_start + idx:05d}",
                client_nom=client,
                client_email=random_email(client),
                client_telephone=random_phone(),
                client_adresse=f"{random.randint(1, 150)} rue {random.choice(LAST_NAMES)}",
                prestation_titre=f"Prestation DJ - {random.choice(EVENT_TYPES)}",
                prestation_description=random.choice(["", "Set complet", "Animation micro"]),
                date_prestation=event_date,
                heure_debut=start_time,
                heure_fin=end_time,
                lieu=random.choice(LOCATIONS),
                tarif_horaire=tarif_horaire,
                duree_heures=duration,
                montant_ht=montant_ht,
                taux_tva=taux_tva,
                montant_tva=montant_tva,
                montant_ttc=montant_ttc,
                remise_pourcentage=remise_pourcentage,
                remise_montant=remise_montant,
                frais_transport=frais_transport,
                frais_materiel=frais_materiel,
                statut=random.choice(["brouillon", "envoye", "accepte", "refuse", "expire"]),
                createur_id=admin.id,
                dj_id=random.choice(djs_list).id,
                prestation_id=random.choice(prestations_ids) if idx % 3 == 0 and prestations_ids else None
            )
            devis_list.append(devis)
        for batch in chunked(devis_list, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        # Factures
        factures = []
        factures_start = Facture.query.count() + 1
        devis_all = Devis.query.all()
        for idx in range(counts["factures"]):
            if devis_all and idx % 3 == 0:
                base = random.choice(devis_all)
                montant_ttc = float(base.montant_ttc or 0)
                montant_paye = montant_ttc if idx % 4 == 0 else round(montant_ttc * random.uniform(0, 0.8), 2)
                statut = "payee" if montant_paye >= montant_ttc else random.choice(["envoyee", "partiellement_payee", "en_retard"])
                factures.append(Facture(
                    numero=f"FAC-LOAD-{datetime.now().strftime('%Y%m%d')}-{factures_start + idx:05d}",
                    client_nom=base.client_nom,
                    client_email=base.client_email,
                    client_telephone=base.client_telephone,
                    client_adresse=base.client_adresse,
                    prestation_titre=base.prestation_titre,
                    prestation_description=base.prestation_description,
                    date_prestation=base.date_prestation,
                    heure_debut=base.heure_debut,
                    heure_fin=base.heure_fin,
                    lieu=base.lieu,
                    tarif_horaire=base.tarif_horaire,
                    duree_heures=base.duree_heures,
                    montant_ht=base.montant_ht,
                    taux_tva=base.taux_tva,
                    montant_tva=base.montant_tva,
                    montant_ttc=base.montant_ttc,
                    montant_paye=montant_paye,
                    remise_pourcentage=base.remise_pourcentage,
                    remise_montant=base.remise_montant,
                    frais_transport=base.frais_transport,
                    frais_materiel=base.frais_materiel,
                    statut=statut,
                    createur_id=admin.id,
                    dj_id=base.dj_id,
                    prestation_id=base.prestation_id,
                    devis_id=base.id
                ))
            else:
                client = random_name()
                event_date = random_date_between(start_date, end_date)
                start_time, end_time, duration = random_time_slot()
                tarif_horaire = round(random.uniform(80, 240), 2)
                frais_transport = round(random.uniform(0, 150), 2)
                frais_materiel = round(random.uniform(0, 200), 2)
                remise_pourcentage = random.choice([0, 5, 10])
                remise_montant = 0.0 if remise_pourcentage else random.choice([0, 20])
                taux_tva = random.choice([10.0, 20.0])
                montant_ht, montant_tva, montant_ttc = compute_totals(
                    tarif_horaire, duration, frais_transport, frais_materiel, remise_pourcentage, remise_montant, taux_tva
                )
                montant_paye = montant_ttc if idx % 4 == 0 else round(montant_ttc * random.uniform(0, 0.8), 2)
                statut = "payee" if montant_paye >= montant_ttc else random.choice(["envoyee", "partiellement_payee", "en_retard"])
                factures.append(Facture(
                    numero=f"FAC-LOAD-{datetime.now().strftime('%Y%m%d')}-{factures_start + idx:05d}",
                    client_nom=client,
                    client_email=random_email(client),
                    client_telephone=random_phone(),
                    client_adresse=f"{random.randint(1, 150)} rue {random.choice(LAST_NAMES)}",
                    prestation_titre=f"Prestation DJ - {random.choice(EVENT_TYPES)}",
                    prestation_description=random.choice(["", "Set complet", "Animation micro"]),
                    date_prestation=event_date,
                    heure_debut=start_time,
                    heure_fin=end_time,
                    lieu=random.choice(LOCATIONS),
                    tarif_horaire=tarif_horaire,
                    duree_heures=duration,
                    montant_ht=montant_ht,
                    taux_tva=taux_tva,
                    montant_tva=montant_tva,
                    montant_ttc=montant_ttc,
                    montant_paye=montant_paye,
                    remise_pourcentage=remise_pourcentage,
                    remise_montant=remise_montant,
                    frais_transport=frais_transport,
                    frais_materiel=frais_materiel,
                    statut=statut,
                    createur_id=admin.id,
                    dj_id=random.choice(djs_list).id,
                    prestation_id=random.choice(prestations_ids) if idx % 3 == 0 and prestations_ids else None
                ))
        for batch in chunked(factures, batch_size):
            db.session.add_all(batch)
            db.session.commit()

        # Réservations
        reservations = []
        reservations_start = ReservationClient.query.count() + 1
        for idx in range(counts["reservations"]):
            client = random_name()
            event_date = random_date_between(start_date, end_date)
            start_time, _, duration = random_time_slot()
            reservations.append(ReservationClient(
                numero=f"RES-LOAD-{datetime.now().strftime('%Y%m%d')}-{reservations_start + idx:05d}",
                nom=client,
                email=random_email(client),
                telephone=random_phone(),
                adresse=f"{random.randint(1, 150)} rue {random.choice(LAST_NAMES)}",
                nb_invites=random.randint(30, 300),
                type_lieu=random.choice(["salle", "extérieur", "club", "entreprise"]),
                demandes_speciales=random.choice(["", "Lumières LED", "Karaoké", "Bass boost"]),
                type_prestation=random.choice(EVENT_TYPES),
                prix_prestation=round(random.uniform(300, 2500), 2),
                duree_heures=duration,
                date_souhaitee=event_date,
                heure_souhaitee=start_time,
                statut=random.choice(["en_attente", "validee", "confirmee", "rejetee"])
            ))
        for batch in chunked(reservations, batch_size):
            db.session.add_all(batch)
            db.session.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scale', type=float, default=1.0, help='Facteur de multiplication des volumes')
    parser.add_argument('--batch-size', type=int, default=500, help='Taille des lots de commit')
    parser.add_argument('--seed', type=int, default=42, help='Seed aléatoire')
    parser.add_argument('--reset', action='store_true', help='Réinitialiser la base avant seed')
    parser.add_argument('--admin-username', default='gnizery')
    parser.add_argument('--admin-password', default='greg12345')
    parser.add_argument('--admin-email', default='gnizery@example.com')
    parser.add_argument('--admin-nom', default='Gnizery')
    parser.add_argument('--admin-prenom', default='Greg')
    args = parser.parse_args()

    seed(
        scale=args.scale,
        batch_size=args.batch_size,
        seed_value=args.seed,
        reset_db=args.reset,
        admin_username=args.admin_username,
        admin_password=args.admin_password,
        admin_email=args.admin_email,
        admin_nom=args.admin_nom,
        admin_prenom=args.admin_prenom
    )
    print("Seed terminé.")
