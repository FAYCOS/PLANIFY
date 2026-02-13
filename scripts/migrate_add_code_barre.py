#!/usr/bin/env python3
"""Migration helper: ensure tables exist then add `code_barre` column to `materiels` table if missing.

Safe steps:
- call SQLAlchemy `db.create_all()` to create tables if absent
- use sqlite PRAGMA to check column existence
- ALTER TABLE to add column if missing
- create UNIQUE INDEX IF NOT EXISTS on `code_barre` (will fail if duplicates exist)

Run: python3 scripts/migrate_add_code_barre.py
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db
import sqlite3
import logging
logger = logging.getLogger(__name__)

# Determine actual SQLite file used by SQLAlchemy engine
with app.app_context():
    try:
        DB_PATH = db.engine.url.database
    except Exception:
        DB_PATH = os.path.join(os.getcwd(), 'dj_prestations.db')
    logger.info('Using DB path:', DB_PATH)

def ensure_tables():
    with app.app_context():
        db.create_all()

def add_column_if_missing():
    if not os.path.exists(DB_PATH):
        logger.info('DB file not found, created by SQLAlchemy create_all')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check if table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='materiels'")
    if not cur.fetchone():
        logger.info('Table materiels does not exist yet. Ensure models are declared and run create_all first.')
        conn.close()
        return

    # Get columns
    cur.execute("PRAGMA table_info(materiels)")
    cols = [r[1] for r in cur.fetchall()]
    logger.info('Existing columns:', cols)

    if 'code_barre' in cols:
        logger.info('code_barre already present — nothing to do')
        conn.close()
        return

    try:
        logger.info('Adding column code_barre...')
        cur.execute("ALTER TABLE materiels ADD COLUMN code_barre TEXT")
        conn.commit()
        logger.info('Column added')
    except Exception as e:
        logger.info('Failed to add column:', e)

    # Create unique index to enforce uniqueness (if data allows)
    try:
        logger.info('Creating unique index idx_materiels_code_barre if not exists...')
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_materiels_code_barre ON materiels(code_barre)")
        conn.commit()
        logger.info('Index created (or already existed)')
    except Exception as e:
        logger.info('Failed to create unique index (duplicates may exist):', e)

    conn.close()

if __name__ == '__main__':
    logger.info('Running migration: ensure tables, add code_barre')
    ensure_tables()
    add_column_if_missing()
    logger.info('Migration finished')
