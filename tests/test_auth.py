def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200


def test_login_success_and_logout(client, login_as):
    response = login_as('admin')
    assert response.status_code == 200
    logout_response = client.get('/logout', follow_redirects=False)
    assert logout_response.status_code in (302, 303)


def test_profile_requires_auth(client):
    response = client.get('/profil', follow_redirects=False)
    assert response.status_code in (302, 303)


def test_profile_update_with_csrf(client, login_as, csrf_token):
    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/profil',
        data={
            'nom': 'Admin',
            'prenom': 'User',
            'email': 'admin@example.com',
            'csrf_token': token,
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
