def test_search_page(client, login_as):
    login_as('admin')
    response = client.get('/recherche')
    assert response.status_code == 200


def test_search_api(client, login_as):
    login_as('admin')
    response = client.get('/api/recherche?q=test')
    assert response.status_code == 200
