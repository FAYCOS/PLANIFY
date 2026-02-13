from app import Local


def test_locaux_list(client, login_as):
    login_as('admin')
    response = client.get('/locals')
    assert response.status_code == 200


def test_local_affichage(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        local = Local.query.first()
    response = client.get(f'/local/{local.id}/affichage')
    assert response.status_code == 200
