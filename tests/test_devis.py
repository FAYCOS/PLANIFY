import pytest
from app import Devis, db


def test_devis_list(client, login_as):
    login_as('admin')
    response = client.get('/devis', follow_redirects=True)
    assert response.status_code == 200


def test_devis_detail(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        devis = Devis.query.first()
    response = client.get(f'/devis/{devis.id}')
    assert response.status_code == 200


def test_devis_pdf(client, app_instance, login_as):
    pytest.importorskip('reportlab')
    login_as('admin')
    with app_instance.app_context():
        devis = Devis.query.first()
    response = client.get(f'/devis/{devis.id}/pdf')
    assert response.status_code == 200
    assert 'application/pdf' in response.headers.get('Content-Type', '')


def test_devis_signature_page_and_api(client, app_instance, monkeypatch):
    monkeypatch.setattr('app.notifier_signature_devis', lambda devis: None)
    with app_instance.app_context():
        devis = Devis.query.first()
        devis.signature_token = devis.signature_token or 'token-test-devis'
        db.session.commit()
        token = devis.signature_token

    response = client.get(f'/signer-devis/{token}')
    assert response.status_code == 200

    response = client.post(
        f'/api/signer-devis/{token}',
        json={'signature': 'data:image/png;base64,AAA'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('success') is True
