def test_public_ai_welcome(client):
    response = client.get('/api/chat/welcome')
    assert response.status_code == 200


def test_public_ai_message_validation(client):
    response = client.post('/api/chat/message', json={"message": ""})
    assert response.status_code in (400, 422)


def test_ai_predict_requires_login(client):
    response = client.post('/api/ai/predict-price', json={})
    assert response.status_code == 401


def test_ai_predict_with_login(client, login_as, csrf_token):
    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/api/ai/predict-price',
        json={"type_evenement": "mariage", "nombre_invites": 100, "date": "2026-02-01", "duree_heures": 4},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200


def test_ai_recommend_equipment_with_login(client, login_as, csrf_token):
    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/api/ai/recommend-equipment',
        json={"type_evenement": "mariage", "nombre_invites": 120, "duree_heures": 6},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200
    data = response.get_json()
    assert 'recommendations' in data


def test_ai_suggest_dj_with_login(client, app_instance, login_as, csrf_token):
    from app import DJ

    login_as('admin')
    token = csrf_token()
    with app_instance.app_context():
        dj = DJ.query.first()
        assert dj is not None

    response = client.post(
        '/api/ai/suggest-dj',
        json={"date": "2026-02-01", "style_musical": "house", "localisation": "Paris"},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200
    data = response.get_json()
    assert 'success' in data


def test_ai_detect_conflicts_with_login(client, app_instance, login_as, csrf_token):
    from app import DJ, Materiel

    login_as('admin')
    token = csrf_token()
    with app_instance.app_context():
        dj = DJ.query.first()
        materiel = Materiel.query.first()
        assert dj is not None
        assert materiel is not None

    response = client.post(
        '/api/ai/detect-conflicts',
        json={
            "date": "2026-02-01",
            "heure_debut": "20:00",
            "heure_fin": "23:00",
            "materiel_ids": [materiel.id],
            "dj_id": dj.id
        },
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200
    data = response.get_json()
    assert 'conflicts' in data


def test_ai_forecast_revenue_with_login(client, login_as):
    login_as('admin')
    response = client.get('/api/ai/forecast-revenue?mois=2')
    assert response.status_code == 200
    data = response.get_json()
    assert 'forecasts' in data


def test_ai_brief_with_login(client, app_instance, login_as, csrf_token):
    from app import Prestation

    login_as('admin')
    token = csrf_token()
    with app_instance.app_context():
        prestation = Prestation.query.first()
        assert prestation is not None

    response = client.post(
        '/api/ai/brief',
        json={'prestation_id': prestation.id},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200


def test_ai_detect_anomalies_with_login(client, login_as):
    login_as('admin')
    response = client.get('/api/ai/detect-anomalies?scope=all&limit=10')
    assert response.status_code == 200


def test_ai_upsell_with_login(client, login_as, csrf_token):
    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/api/ai/upsell',
        json={'type_evenement': 'mariage', 'nombre_invites': 150, 'budget': 2000},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200


def test_ai_forecast_load_with_login(client, login_as):
    login_as('admin')
    response = client.get('/api/ai/forecast-load?mois=2')
    assert response.status_code == 200


def test_ai_optimize_logistics_with_login(client, login_as, csrf_token):
    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/api/ai/optimize-logistics',
        json={'date_debut': '2026-02-01', 'date_fin': '2026-02-10'},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200


def test_ai_analyze_conversions_with_login(client, login_as):
    login_as('admin')
    response = client.get('/api/ai/analyze-conversions')
    assert response.status_code == 200


def test_ai_generate_email_with_login(client, login_as, csrf_token):
    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/api/ai/generate-email',
        json={'purpose': 'confirmation', 'client_name': 'Test Client'},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200


def test_ai_score_client_with_login(client, login_as, csrf_token):
    login_as('admin')
    token = csrf_token()
    response = client.post(
        '/api/ai/score-client',
        json={'client_name': 'Test Client', 'budget': 1200, 'nb_invites': 80, 'lead_days': 20},
        headers={'X-CSRF-Token': token} if token else None
    )
    assert response.status_code == 200
