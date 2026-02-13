from app import db, Local, SyncChangeLog


def test_sync_log_created(app_instance):
    with app_instance.app_context():
        before = SyncChangeLog.query.count()
        local = Local(nom="Local Sync", adresse="123 Rue Test")
        db.session.add(local)
        db.session.commit()
        after = SyncChangeLog.query.count()
        assert after == before + 1
