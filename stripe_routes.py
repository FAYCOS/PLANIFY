from flask import Blueprint, request, redirect, url_for, render_template, flash, current_app, session
from stripe_service import stripe_service
import logging
import secrets
import json
from datetime import datetime, timezone
import os
import stripe

stripe_bp = Blueprint('stripe_bp', __name__)
logger = logging.getLogger(__name__)

def _get_stripe_params():
    from app import ParametresEntreprise, get_stripe_secret
    params = ParametresEntreprise.query.first()
    stripe_secret = get_stripe_secret(params) if params else None
    if not params or not params.stripe_enabled or not stripe_secret:
        return None, "Stripe non configuré"
    current_app.config['STRIPE_SECRET_KEY'] = stripe_secret
    if not stripe_service.is_initialized:
        stripe_service.init_app(current_app)
    return params, None

def _tokens_match(expected, provided):
    if not expected or not provided:
        return False
    return secrets.compare_digest(expected, provided)

def _session_attr(sess, key, default=None):
    if isinstance(sess, dict):
        return sess.get(key, default)
    return getattr(sess, key, default)

def _get_webhook_secret():
    return current_app.config.get('STRIPE_WEBHOOK_SECRET') or os.environ.get('STRIPE_WEBHOOK_SECRET')

@stripe_bp.route('/pay/invoice/<int:invoice_id>')
def pay_invoice(invoice_id):
    """Initiate payment for an invoice"""
    from app import Facture  # Local import
    facture = Facture.query.get_or_404(invoice_id)
    token = request.args.get('token', '')
    if not _tokens_match(facture.payment_token, token):
        flash('Lien de paiement invalide ou expiré.', 'error')
        return redirect(url_for('index'))
    params, err = _get_stripe_params()
    if err:
        flash(err, 'error')
        return redirect(url_for('index'))
    
    # Check if already paid
    if facture.statut == 'payee':
        flash('Cette facture est déjà payée.', 'info')
        return redirect(url_for('index'))
    if facture.statut == 'annulee':
        flash('Cette facture est annulée.', 'info')
        return redirect(url_for('index'))
        
    amount = facture.montant_restant
    amount_cents = int(round(amount * 100))
    
    if amount_cents <= 0:
        flash('Le montant à payer est nul.', 'warning')
        return redirect(url_for('index'))

    try:
        session, error = stripe_service.create_checkout_session(
            amount=amount_cents,
            currency=(params.devise or 'EUR').lower(),
            description=f"Facture #{facture.numero}",
            customer_email=facture.client_email,
            success_url=url_for('stripe_bp.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('stripe_bp.payment_cancel', _external=True),
            metadata={'type': 'invoice', 'id': invoice_id, 'token': token, 'amount_cents': amount_cents}
        )
        
        if error:
            flash(f"Erreur lors de l'initialisation du paiement: {error}", 'error')
            return redirect(url_for('index'))
            
        return redirect(session.url)
        
    except Exception as e:
        logger.error(f"Payment init error: {e}")
        flash("Une erreur est survenue.", 'error')
        return redirect(url_for('index'))

@stripe_bp.route('/pay/quote/<int:quote_id>')
def pay_quote(quote_id):
    """Initiate deposit payment for a quote"""
    from app import Devis # Local import
    devis = Devis.query.get_or_404(quote_id)
    token = request.args.get('token', '')
    if not _tokens_match(devis.signature_token, token):
        flash('Lien de paiement invalide ou expiré.', 'error')
        return redirect(url_for('index'))
    params, err = _get_stripe_params()
    if err:
        flash(err, 'error')
        return redirect(url_for('index'))
    
    if not devis.acompte_requis or devis.acompte_paye:
        flash("Aucun acompte requis ou déjà payé.", 'info')
        return redirect(url_for('index'))
    if not devis.est_signe:
        flash("Le devis doit être signé avant le paiement.", 'info')
        return redirect(url_for('index'))
        
    amount_cents = int(devis.acompte_montant * 100)
    
    if amount_cents <= 0:
         flash("Montant de l'acompte invalide.", 'warning')
         return redirect(url_for('index'))

    try:
        session, error = stripe_service.create_checkout_session(
            amount=amount_cents,
            currency=(params.devise or 'EUR').lower(),
            description=f"Acompte Devis #{devis.numero}",
            customer_email=devis.client_email,
            success_url=url_for('stripe_bp.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('stripe_bp.payment_cancel', _external=True),
            metadata={'type': 'quote', 'id': quote_id, 'token': token, 'amount_cents': amount_cents}
        )
        
        if error:
            flash(f"Erreur: {error}", 'error')
            return redirect(url_for('index'))
            
        return redirect(session.url)
        
    except Exception as e:
        logger.error(f"Payment init error: {e}")
        flash("Une erreur est survenue.", 'error')
        return redirect(url_for('index'))

@stripe_bp.route('/stripe/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('index'))
        
    # Verify session with Stripe
    sess = stripe_service.retrieve_session(session_id)
    if not sess or _session_attr(sess, 'payment_status') != 'paid':
        flash("Paiement non validé ou session invalide.", 'error')
        return redirect(url_for('index'))
        
    # Handle fulfillment
    metadata = _session_attr(sess, 'metadata', {}) or {}
    if metadata.get('type') == 'invoice':
        _handle_invoice_payment(metadata.get('id'), sess)
        return render_template('payment_success.html', type='facture', id=metadata.get('id'))
    elif metadata.get('type') == 'quote':
        _handle_quote_payment(metadata.get('id'), sess)
        return render_template('payment_success.html', type='devis', id=metadata.get('id'))
        
    return redirect(url_for('index'))

@stripe_bp.route('/stripe/cancel')
def payment_cancel():
    return render_template('payment_cancel.html')

@stripe_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    secret = _get_webhook_secret()
    if not secret:
        return '', 204
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature', '')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception as e:
        logger.warning("Webhook Stripe invalide: %s", e)
        return '', 400

    event_type = getattr(event, 'type', None) or event.get('type')
    data_obj = getattr(event, 'data', None)
    session_obj = None
    if data_obj:
        session_obj = getattr(data_obj, 'object', None)
    if session_obj is None and isinstance(event, dict):
        session_obj = event.get('data', {}).get('object')

    if event_type == 'checkout.session.completed' and session_obj:
        if _session_attr(session_obj, 'payment_status') == 'paid':
            metadata = _session_attr(session_obj, 'metadata', {}) or {}
            if metadata.get('type') == 'invoice':
                _handle_invoice_payment(metadata.get('id'), session_obj)
            elif metadata.get('type') == 'quote':
                _handle_quote_payment(metadata.get('id'), session_obj)

    return '', 200

def _handle_invoice_payment(invoice_id, session):
    from app import db, Facture # Local import
    facture = Facture.query.get(invoice_id)
    if not facture:
        return
    metadata = _session_attr(session, 'metadata', {}) or {}
    token = metadata.get('token')
    if not _tokens_match(facture.payment_token, token):
        logger.warning("Stripe payment token mismatch for invoice %s", invoice_id)
        return
    meta_amount = metadata.get('amount_cents')
    if meta_amount is not None:
        try:
            if int(meta_amount) != int(_session_attr(session, 'amount_total') or 0):
                logger.warning("Stripe amount metadata mismatch for invoice %s", invoice_id)
                return
        except (TypeError, ValueError):
            pass
    payment_intent = _session_attr(session, 'payment_intent')
    if facture.stripe_payment_intent_id and payment_intent and facture.stripe_payment_intent_id == payment_intent:
        return
    amount_paid = (_session_attr(session, 'amount_total') or 0) / 100.0
    if amount_paid <= 0:
        return
    if amount_paid - facture.montant_restant > 0.01:
        logger.warning("Stripe amount exceeds remaining balance for invoice %s", invoice_id)
        return
    ok, msg = facture.ajouter_paiement(amount_paid)
    if not ok:
        logger.warning("Stripe payment rejected for invoice %s: %s", invoice_id, msg)
        return
    facture.mode_paiement = 'stripe'
    facture.reference_paiement = _session_attr(session, 'id')
    if payment_intent:
        facture.stripe_payment_intent_id = payment_intent
    from app import Paiement, generate_document_number, ParametresEntreprise
    existing = None
    if payment_intent:
        existing = Paiement.query.filter_by(stripe_payment_intent_id=payment_intent).first()
    if not existing:
        params = ParametresEntreprise.query.first()
        paiement = Paiement(
            numero=generate_document_number('PAY'),
            montant=amount_paid,
            devise=(params.devise if params else 'EUR'),
            type_paiement='facture',
            mode_paiement='stripe',
            description=f"Paiement facture {facture.numero}",
            statut='reussi',
            date_paiement=datetime.now(timezone.utc).replace(tzinfo=None),
            facture_id=facture.id,
            client_nom=facture.client_nom,
            client_email=facture.client_email,
            client_telephone=facture.client_telephone,
            stripe_payment_intent_id=payment_intent,
            stripe_checkout_session_id=_session_attr(session, 'id'),
            payment_metadata=json.dumps({'session_id': _session_attr(session, 'id'), 'amount_total': _session_attr(session, 'amount_total')}, ensure_ascii=False)
        )
        db.session.add(paiement)
    db.session.commit()
        
def _handle_quote_payment(quote_id, session):
    from app import db, Devis # Local import
    devis = Devis.query.get(quote_id)
    if not devis:
        return
    metadata = _session_attr(session, 'metadata', {}) or {}
    token = metadata.get('token')
    if not _tokens_match(devis.signature_token, token):
        logger.warning("Stripe payment token mismatch for quote %s", quote_id)
        return
    meta_amount = metadata.get('amount_cents')
    if meta_amount is not None:
        try:
            if int(meta_amount) != int(_session_attr(session, 'amount_total') or 0):
                logger.warning("Stripe amount metadata mismatch for quote %s", quote_id)
                return
        except (TypeError, ValueError):
            pass
    if devis.acompte_paye:
        return
    amount_paid = (_session_attr(session, 'amount_total') or 0) / 100.0
    expected = devis.acompte_montant or 0.0
    if expected <= 0 or abs(amount_paid - expected) > 0.01:
        logger.warning("Stripe amount mismatch for quote %s", quote_id)
        return
    devis.acompte_paye = 1
    devis.date_paiement_acompte = datetime.now(timezone.utc).replace(tzinfo=None)
    if devis.statut != 'accepte':
        devis.statut = 'accepte'
    from app import Paiement, generate_document_number, ParametresEntreprise
    existing = None
    payment_intent = _session_attr(session, 'payment_intent')
    if payment_intent:
        existing = Paiement.query.filter_by(stripe_payment_intent_id=payment_intent).first()
    if not existing:
        params = ParametresEntreprise.query.first()
        paiement = Paiement(
            numero=generate_document_number('PAY'),
            montant=amount_paid,
            devise=(params.devise if params else 'EUR'),
            type_paiement='acompte',
            mode_paiement='stripe',
            description=f"Acompte devis {devis.numero}",
            statut='reussi',
            date_paiement=datetime.now(timezone.utc).replace(tzinfo=None),
            devis_id=devis.id,
            client_nom=devis.client_nom,
            client_email=devis.client_email,
            client_telephone=devis.client_telephone,
            stripe_payment_intent_id=payment_intent,
            stripe_checkout_session_id=_session_attr(session, 'id'),
            payment_metadata=json.dumps({'session_id': _session_attr(session, 'id'), 'amount_total': _session_attr(session, 'amount_total')}, ensure_ascii=False)
        )
        db.session.add(paiement)
    db.session.commit()
