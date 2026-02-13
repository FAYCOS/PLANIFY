import os
import pytest
from datetime import datetime, date, time, timedelta
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="session")
def app_instance(tmp_path_factory):
    os.environ.setdefault("FLASK_ENV", "testing")

    from app import app, db
    from app import User, DJ, Local, Materiel, MaterielPresta, Prestation, ParametresEntreprise, Devis, Facture, ReservationClient
    from init_key_manager import init_key_manager

    db_path = tmp_path_factory.mktemp("db") / "planify_test.db"
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SECRET_KEY="test-secret-key",
        API_KEY="test-api-key",
    )
    app.config['DB_READY'] = True
    app.config['PLF_TEMP_PATH'] = str(db_path)

    init_key_manager.key_data = {"initialized": True}

    with app.app_context():
        db.drop_all()
        db.create_all()

        params = ParametresEntreprise(nom_entreprise="Planify Tests")
        db.session.add(params)

        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("password"),
            role="admin",
            nom="Admin",
            prenom="User",
        )
        manager = User(
            username="manager",
            email="manager@example.com",
            password_hash=generate_password_hash("password"),
            role="manager",
            nom="Manager",
            prenom="User",
        )
        dj_user = User(
            username="dj",
            email="dj@example.com",
            password_hash=generate_password_hash("password"),
            role="dj",
            nom="DJ",
            prenom="User",
        )
        technicien = User(
            username="tech",
            email="tech@example.com",
            password_hash=generate_password_hash("password"),
            role="technicien",
            nom="Tech",
            prenom="User",
        )
        db.session.add_all([admin, manager, dj_user, technicien])
        db.session.flush()

        dj_profile = DJ(nom="DJ Test", user_id=dj_user.id)
        local = Local(nom="Local Test", adresse="1 rue du Test")
        db.session.add_all([dj_profile, local])
        db.session.flush()

        materiel = Materiel(
            nom="Enceinte",
            local_id=local.id,
            quantite=2,
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
            dj_id=dj_profile.id,
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

        devis = Devis(
            numero="DEV-TEST-001",
            client_nom="Client Test",
            client_email="client@example.com",
            client_telephone="0102030405",
            prestation_titre="Prestation Test",
            date_prestation=date.today(),
            heure_debut=time(20, 0),
            heure_fin=time(23, 0),
            lieu="Salle Test",
            tarif_horaire=100.0,
            duree_heures=3.0,
            montant_ht=300.0,
            montant_ttc=360.0,
            dj_id=dj_profile.id,
            createur_id=admin.id,
            prestation_id=prestation.id,
        )
        db.session.add(devis)

        facture = Facture(
            numero="FAC-TEST-001",
            client_nom="Client Test",
            client_email="client@example.com",
            client_telephone="0102030405",
            prestation_titre="Prestation Test",
            date_prestation=date.today(),
            heure_debut=time(20, 0),
            heure_fin=time(23, 0),
            lieu="Salle Test",
            tarif_horaire=100.0,
            duree_heures=3.0,
            montant_ht=300.0,
            montant_ttc=360.0,
            dj_id=dj_profile.id,
            createur_id=admin.id,
            prestation_id=prestation.id,
        )
        db.session.add(facture)

        reservation = ReservationClient(
            numero="RES-TEST-001",
            nom="Client Public",
            email="client@example.com",
            telephone="0102030405",
            adresse="1 rue du Client",
            type_prestation="mariage",
            prix_prestation=500.0,
            duree_heures=4,
            date_souhaitee=date.today() + timedelta(days=7),
            heure_souhaitee=time(20, 0),
        )
        db.session.add(reservation)

        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture
def login_as(client):
    def _login(username="admin", password="password"):
        return client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )
    return _login


@pytest.fixture
def csrf_token(client):
    def _csrf():
        with client.session_transaction() as sess:
            return sess.get("csrf_token")
    return _csrf
