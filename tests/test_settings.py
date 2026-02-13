def test_settings_page(client, login_as):
    login_as('admin')
    response = client.get('/settings')
    assert response.status_code == 200


def test_parametres_page(client, login_as):
    login_as('admin')
    response = client.get('/parametres')
    assert response.status_code == 200


def test_personnalisation_page(client, login_as):
    login_as('admin')
    response = client.get('/personnalisation')
    assert response.status_code == 200


def test_ia_hub_page(client, login_as):
    login_as('admin')
    response = client.get('/ia')
    assert response.status_code == 200


def test_groq_key_update_and_clear(client, app_instance, login_as, csrf_token, monkeypatch):
    from app import ParametresEntreprise
    from ai_assistant import ai_assistant

    monkeypatch.delenv('GROQ_API_KEY', raising=False)

    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/parametres/modifier',
        data={'nom_entreprise': 'Planify Tests', 'groq_api_key': 'test-key'},
        headers={'X-CSRF-Token': token} if token else None,
        follow_redirects=True
    )
    assert response.status_code == 200

    with app_instance.app_context():
        params = ParametresEntreprise.query.first()
        assert params.groq_api_key == 'test-key'

    ai_assistant.refresh_api_key()
    assert ai_assistant.api_key == 'test-key'

    response = client.post(
        '/parametres/modifier',
        data={'nom_entreprise': 'Planify Tests', 'clear_groq_api_key': '1'},
        headers={'X-CSRF-Token': token} if token else None,
        follow_redirects=True
    )
    assert response.status_code == 200

    with app_instance.app_context():
        params = ParametresEntreprise.query.first()
        assert params.groq_api_key is None
