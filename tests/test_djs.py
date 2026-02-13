from app import DJ


def test_djs_list(client, login_as):
    login_as('admin')
    response = client.get('/djs')
    assert response.status_code == 200


def test_dj_detail(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        dj = DJ.query.first()
    response = client.get(f'/djs/{dj.id}')
    assert response.status_code == 200
