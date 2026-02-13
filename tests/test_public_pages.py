
def test_zone_clients_page(client):
    response = client.get('/zone-clients')
    assert response.status_code == 200


def test_offline_page(client):
    response = client.get('/offline')
    assert response.status_code == 200
