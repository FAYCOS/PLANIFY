import os
from app import db, SyncIncomingLog


def test_sync_push_server_mode(app_instance):
    app_instance.config['TESTING'] = True
    app_instance.config['SYNC_SERVER_MODE'] = True
    app_instance.config['SYNC_SERVER_TOKEN'] = 'test-token'
    os.environ['SYNC_SERVER_MODE'] = '1'
    os.environ['SYNC_SERVER_TOKEN'] = 'test-token'
    os.environ['FLASK_ENV'] = 'testing'

    client = app_instance.test_client()
    resp = client.post(
        '/api/sync/push',
        json={
            'device_id': 'dev-1',
            'changes': [
                {
                    'change_id': 1,
                    'entity_type': 'Local',
                    'entity_id': 99,
                    'operation': 'insert',
                    'payload': {'nom': 'Local X'}
                }
            ]
        },
        headers={'X-Sync-Token': 'test-token', 'X-Test-Mode': '1'}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert 1 in data.get('accepted_ids', [])

    with app_instance.app_context():
        assert SyncIncomingLog.query.count() == 1
        db.session.query(SyncIncomingLog).delete()
        db.session.commit()
    os.environ.pop('SYNC_SERVER_MODE', None)
    os.environ.pop('SYNC_SERVER_TOKEN', None)
