import pytest
from app import Facture


def test_factures_list(client, login_as):
    login_as('admin')
    response = client.get('/factures')
    assert response.status_code == 200


def test_facture_detail(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        facture = Facture.query.first()
    response = client.get(f'/factures/{facture.id}')
    assert response.status_code == 200


def test_facture_pdf(client, app_instance, login_as):
    pytest.importorskip('reportlab')
    login_as('admin')
    with app_instance.app_context():
        facture = Facture.query.first()
    response = client.get(f'/factures/{facture.id}/pdf')
    assert response.status_code == 200
    assert 'application/pdf' in response.headers.get('Content-Type', '')
