from app import DJ, Prestation


def test_icalendar_exports(client, app_instance, login_as):
    login_as('admin')
    with app_instance.app_context():
        dj = DJ.query.first()
        prestation = Prestation.query.first()
        assert dj is not None
        assert prestation is not None

    response = client.get(f'/export/icalendar/dj/{dj.id}')
    assert response.status_code == 200
    assert 'text/calendar' in response.headers.get('Content-Type', '')

    response = client.get(f'/export/icalendar/prestation/{prestation.id}')
    assert response.status_code == 200
    assert 'text/calendar' in response.headers.get('Content-Type', '')
