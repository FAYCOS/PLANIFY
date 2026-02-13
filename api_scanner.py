#!/usr/bin/env python3
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

scanner_bp = Blueprint('scanner_api', __name__, url_prefix='/api')

@scanner_bp.route('/scan_material', methods=['POST'])
def scan_material():
    """API endpoint to receive barcode scans and create/update a Materiel record.

    Expected JSON body:
    {
      "code_barre": "1234567890123",
      "nom": "Enceinte XYZ",
      "local_id": 1,
      "quantite": 1,
      "categorie": "Son",
      "prix_location": 12.5
    }

    Auth: header `X-API-KEY` must match `app.config['API_KEY']` (simple token auth)
    """
    api_key = current_app.config.get('API_KEY')
    if not api_key:
        return jsonify({'success': False, 'message': 'API key non configurée'}), 503
    header_key = request.headers.get('X-API-KEY')
    if api_key and header_key != api_key:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON body'}), 400

    code = data.get('code_barre')
    numero_serie = data.get('numero_serie') or code
    nom = data.get('nom')
    local_id = data.get('local_id')
    categorie = data.get('categorie')
    update_stock = bool(data.get('update_stock'))
    update_prix = bool(data.get('update_prix'))

    quantite = data.get('quantite')
    if quantite is not None:
        try:
            quantite = int(quantite)
        except (TypeError, ValueError):
            quantite = None

    prix_location = data.get('prix_location')
    if prix_location is not None:
        try:
            prix_location = float(prix_location)
        except (TypeError, ValueError):
            prix_location = None

    # Simple validation
    if not code and not nom:
        return jsonify({'success': False, 'message': 'Missing code_barre or nom'}), 400

    # import models lazily to avoid circular imports
    try:
        from app import db, Materiel
    except Exception as e:
        logger.exception('DB import failed')
        return jsonify({'success': False, 'message': 'Server error'}), 500

    with current_app.app_context():
        try:
            # If barcode provided, try to find existing material
            mat = None
            if numero_serie:
                mat = Materiel.query.filter(
                    (Materiel.numero_serie == numero_serie) | (Materiel.code_barre == numero_serie)
                ).first()

            # If not found by barcode, try to match by name+local
            if not mat and nom and local_id:
                mat = Materiel.query.filter_by(nom=nom, local_id=local_id).first()

            if mat:
                # Update fields (avoid overwriting stock/pricing unless explicitly requested)
                if update_stock and quantite is not None and quantite > 0:
                    mat.quantite = quantite
                if categorie:
                    mat.categorie = categorie
                if update_prix and prix_location is not None:
                    mat.prix_location = prix_location
                if numero_serie and not mat.numero_serie:
                    mat.numero_serie = numero_serie
                if code and not mat.code_barre:
                    mat.code_barre = code
                db.session.commit()
                return jsonify({'success': True, 'action': 'updated', 'materiel_id': mat.id})
            else:
                # Create new material; require local_id
                if not local_id:
                    return jsonify({'success': False, 'message': 'local_id is required to create materiel'}), 400

                if quantite is None or quantite <= 0:
                    quantite = 1
                if prix_location is None:
                    prix_location = 0.0

                new_mat = Materiel(
                    nom=nom or f'Item-{code}',
                    code_barre=code,
                    numero_serie=numero_serie,
                    local_id=local_id,
                    quantite=quantite,
                    categorie=categorie,
                    prix_location=prix_location
                )
                db.session.add(new_mat)
                db.session.commit()
                return jsonify({'success': True, 'action': 'created', 'materiel_id': new_mat.id})

        except Exception as e:
            logger.exception('Error processing scan')
            try:
                db.session.rollback()
            except Exception:
                pass
            return jsonify({'success': False, 'message': str(e)}), 500


@scanner_bp.route('/material/<string:code>', methods=['GET'])
def get_material_by_code(code):
    """Retrieve material by its barcode/code."""
    api_key = current_app.config.get('API_KEY')
    if not api_key:
        return jsonify({'success': False, 'message': 'API key non configurée'}), 503
    header_key = request.headers.get('X-API-KEY')
    if api_key and header_key != api_key:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        from app import Materiel
    except Exception as e:
        logger.exception('DB import failed')
        return jsonify({'success': False, 'message': 'Server error'}), 500

    with current_app.app_context():
        mat = Materiel.query.filter(
            (Materiel.numero_serie == code) | (Materiel.code_barre == code)
        ).first()
        if not mat:
            return jsonify({'success': False, 'message': 'Not found'}), 404

        data = {
            'id': mat.id,
            'nom': mat.nom,
            'code_barre': mat.code_barre,
            'numero_serie': mat.numero_serie,
            'local_id': mat.local_id,
            'quantite': mat.quantite,
            'categorie': mat.categorie,
            'prix_location': float(mat.prix_location) if mat.prix_location is not None else 0.0
        }
        return jsonify({'success': True, 'materiel': data})
