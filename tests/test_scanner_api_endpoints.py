from app import Local


def test_scan_material_unauthorized(client):
    response = client.post('/api/scan_material', json={'code_barre': '123', 'local_id': 1, 'quantite': 1})
    assert response.status_code in (401, 403, 503)


def test_scan_material_authorized(client, app_instance):
    with app_instance.app_context():
        local = Local.query.first()
    response = client.post(
        '/api/scan_material',
        json={'code_barre': '123', 'local_id': local.id, 'quantite': 1},
        headers={'X-API-KEY': 'test-api-key'}
    )
    assert response.status_code in (200, 201)
