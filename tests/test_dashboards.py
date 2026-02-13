def test_admin_dashboard(client, login_as):
    login_as('admin')
    response = client.get('/admin')
    assert response.status_code == 200


def test_manager_dashboard(client, login_as):
    login_as('manager')
    response = client.get('/manager')
    assert response.status_code == 200


def test_dj_dashboard(client, login_as):
    login_as('dj')
    response = client.get('/dj')
    assert response.status_code == 200


def test_technicien_dashboard(client, login_as):
    login_as('tech')
    response = client.get('/technicien')
    assert response.status_code == 200

