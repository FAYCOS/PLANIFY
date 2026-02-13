import pytest
from app import Materiel


def test_materiels_list(client, login_as):
    login_as('admin')
    response = client.get('/materiels')
    assert response.status_code == 200


def test_materiel_detail(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        materiel = Materiel.query.first()
    response = client.get(f'/materiels/{materiel.id}')
    assert response.status_code == 200


def test_materiel_qrcode_page(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        materiel = Materiel.query.first()
    response = client.get(f'/materiels/qrcode/{materiel.id}')
    assert response.status_code == 200


def test_materiel_qrcode_pdf(client, login_as):
    pytest.importorskip('reportlab')
    pytest.importorskip('qrcode')
    login_as('admin')
    response = client.get('/materiels/qrcode/generer-pdf')
    assert response.status_code == 200
    assert 'application/pdf' in response.headers.get('Content-Type', '')


def test_materiel_mouvements_page(client, login_as):
    login_as('admin')
    response = client.get('/materiels/mouvements')
    assert response.status_code == 200
