def test_notifications_page(client, login_as):
    login_as('admin')
    response = client.get('/notifications')
    assert response.status_code == 200


def test_notifications_api(client, login_as):
    login_as('admin')
    response = client.get('/api/notifications')
    assert response.status_code == 200
