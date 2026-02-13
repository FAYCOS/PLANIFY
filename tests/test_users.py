def test_users_page_admin(client, login_as):
    login_as('admin')
    response = client.get('/users')
    assert response.status_code == 200
