def test_backup_page(client, login_as):
    login_as('admin')
    response = client.get('/backup')
    assert response.status_code == 200


def test_backup_create_and_restore(tmp_path):
    from backup_manager import BackupManager

    db_path = tmp_path / "test.db"
    db_path.write_bytes(b"planify-test")

    backup_dir = tmp_path / "backups"
    manager = BackupManager(db_path=str(db_path), backup_dir=str(backup_dir), max_backups=5)

    result = manager.create_backup(compress=False)
    assert result['success'] is True

    # Modifier la base puis restaurer
    db_path.write_bytes(b"modified")
    backup_filename = result['backup_file'].split('/')[-1]
    restore = manager.restore_backup(backup_filename)
    assert restore['success'] is True
    assert db_path.read_bytes() == b"planify-test"
