from app import Prestation


def test_prestations_list(client, login_as):
    login_as('admin')
    response = client.get('/prestations')
    assert response.status_code == 200


def test_prestation_detail(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        prestation = Prestation.query.first()
    response = client.get(f'/prestations/{prestation.id}')
    assert response.status_code == 200


def test_prestation_calendar(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        prestation = Prestation.query.first()
    response = client.get(f'/prestations/{prestation.id}/modifier')
    assert response.status_code == 200
