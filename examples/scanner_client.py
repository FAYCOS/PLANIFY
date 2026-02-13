#!/usr/bin/env python3
"""
Example mobile/device client that POSTs a scanned barcode to Planify API.
Requires `requests`.
"""
import requests
import logging
logger = logging.getLogger(__name__)

API_URL = 'http://127.0.0.1:5000/api/scan_material'
API_KEY = 'changeme_test_api_key'  # override with PLANIFY_API_KEY in server or set here

def main():
    payload = {
        'code_barre': '0123456789012',
        'nom': 'Enceinte Scannée X100',
        'local_id': 1,
        'quantite': 2,
        'categorie': 'Sonorisation',
        'prix_location': 15.0
    }

    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }

    r = requests.post(API_URL, json=payload, headers=headers)
    try:
        logger.info('%s %s', r.status_code, r.json())
    except Exception:
        logger.info('%s', r.status_code)


if __name__ == '__main__':
    main()
