
from werkzeug.security import generate_password_hash


def _ensure_admin_user(app_instance):
    from app import db, User
    with app_instance.app_context():
        user = User.query.filter_by(username='admin').first()
        if not user:
            user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('password'),
                role='admin',
                nom='Admin',
                prenom='User',
            )
            db.session.add(user)
        user.password_hash = generate_password_hash('password')
        user.actif = True
        db.session.commit()


def test_mobile_login_and_profile(client, app_instance):
    _ensure_admin_user(app_instance)
    response = client.post('/api/mobile/auth/login', json={
        'username': 'admin',
        'password': 'password'
    })
    assert response.status_code == 200
    data = response.get_json()
    token = data.get('token')
    assert token

    profile_resp = client.get('/api/mobile/profile', headers={'Authorization': f'Bearer {token}'})
    assert profile_resp.status_code == 200
    profile = profile_resp.get_json()
    assert profile.get('username') == 'admin'


def test_mobile_prestations_endpoint(client, app_instance):
    _ensure_admin_user(app_instance)
    login_resp = client.post('/api/mobile/auth/login', json={
        'username': 'admin',
        'password': 'password'
    })
    token = login_resp.get_json().get('token')
    assert token

    response = client.get('/api/mobile/prestations', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'prestations' in data
