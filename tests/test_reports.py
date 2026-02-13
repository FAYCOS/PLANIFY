def test_reports_page(client, login_as):
    login_as('admin')
    response = client.get('/rapports')
    assert response.status_code == 200


def test_advanced_reports_page(client, login_as):
    login_as('admin')
    response = client.get('/rapports-avances')
    assert response.status_code == 200
