def test_public_reservation_page(client):
    response = client.get('/reservation')
    assert response.status_code == 200


def test_public_reservation_api_validation(client):
    response = client.post('/api/reservation', data={})
    assert response.status_code in (400, 422)


def test_reservations_list_requires_login(client):
    response = client.get('/reservations', follow_redirects=False)
    assert response.status_code in (302, 303)


def test_reservations_list_admin(client, login_as):
    login_as('admin')
    response = client.get('/reservations')
    assert response.status_code == 200


def test_public_reservation_api_success(client, monkeypatch):
    from datetime import date, timedelta

    monkeypatch.setattr('app.send_reservation_confirmation_email', lambda reservation: True)
    monkeypatch.setattr('app.notify_managers_new_reservation', lambda reservation: True)

    future_date = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    response = client.post(
        '/api/reservation',
        data={
            'nom': 'Client Test',
            'email': 'client@example.com',
            'telephone': '0102030405',
            'lieu': 'Salle Test',
            'type_evenement': 'mariage',
            'date': future_date,
            'heure_debut': '20:00',
            'heure_fin': '23:00',
            'nb_invites': '80',
            'preferences': 'house',
            'message': 'Test',
        }
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('success') is True
