
def test_sync_settings_page(client, login_as):
    login_as('admin')
    response = client.get('/sync')
    assert response.status_code == 200


def test_sync_settings_update(client, login_as):
    login_as('admin')
    response = client.post(
        '/sync/update',
        data={
            'enabled': 'on',
            'server_url': 'http://localhost:5001',
            'sync_interval_seconds': '30'
        },
        follow_redirects=False
    )
    assert response.status_code in (302, 303)
