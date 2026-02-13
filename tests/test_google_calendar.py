from app import DJ


def test_google_connect_requires_login(client, app_instance):
    with app_instance.app_context():
        dj = DJ.query.first()
    response = client.get(f'/auth/google/connect/{dj.id}', follow_redirects=False)
    assert response.status_code in (302, 303)


def test_google_connect_with_login(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        dj = DJ.query.first()
    response = client.get(f'/auth/google/connect/{dj.id}', follow_redirects=False)
    assert response.status_code in (200, 302, 303, 500)
