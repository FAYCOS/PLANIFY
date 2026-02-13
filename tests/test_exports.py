import pytest


def test_exports_require_login(client):
    response = client.get('/export/prestations', follow_redirects=False)
    assert response.status_code in (302, 303)


def test_export_prestations_file(client, login_as):
    pytest.importorskip('pandas')
    login_as('admin')
    response = client.get('/export/prestations')
    assert response.status_code == 200
    assert response.headers.get('Content-Type')


def test_export_materiels_file(client, login_as):
    pytest.importorskip('pandas')
    login_as('admin')
    response = client.get('/export/materiels')
    assert response.status_code == 200
    assert response.headers.get('Content-Type')


def test_export_djs_file(client, login_as):
    pytest.importorskip('pandas')
    login_as('admin')
    response = client.get('/export/djs')
    assert response.status_code == 200
    assert response.headers.get('Content-Type')


def test_export_devis_file(client, login_as):
    pytest.importorskip('pandas')
    login_as('admin')
    response = client.get('/export/devis')
    assert response.status_code == 200
    assert response.headers.get('Content-Type')


def test_export_factures_file(client, login_as):
    pytest.importorskip('pandas')
    login_as('admin')
    response = client.get('/export/factures')
    assert response.status_code == 200
    assert response.headers.get('Content-Type')


def test_export_rapport_complet_file(client, login_as):
    pytest.importorskip('pandas')
    login_as('admin')
    response = client.get('/export/rapport-complet?start_date=2026-01-01&end_date=2026-02-01')
    assert response.status_code == 200
    assert response.headers.get('Content-Type')
