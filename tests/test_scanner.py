def test_scanner_page_requires_login(client):
    response = client.get('/scanner', follow_redirects=False)
    assert response.status_code in (302, 303)


def test_scanner_page_admin(client, login_as):
    login_as('admin')
    response = client.get('/scanner')
    assert response.status_code == 200
