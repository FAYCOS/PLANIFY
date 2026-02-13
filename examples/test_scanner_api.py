#!/usr/bin/env python3
"""Run quick tests using Flask test client: POST a scan then GET by code."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db
import json

API_KEY = app.config.get('API_KEY')

with app.app_context():
    db.create_all()

client = app.test_client()

payload = {
    'code_barre': 'TESTCODE12345',
    'nom': 'Test Speaker 2000',
    'local_id': 1,
    'quantite': 3,
    'categorie': 'Sonorisation',
    'prix_location': 20.0
}
headers = {'Content-Type': 'application/json', 'X-API-KEY': API_KEY}

r = client.post('/api/scan_material', data=json.dumps(payload), headers=headers)
print('POST', r.status_code, r.get_json())

r2 = client.get(f"/api/material/{payload['code_barre']}", headers={'X-API-KEY': API_KEY})
print('GET', r2.status_code, r2.get_json())
