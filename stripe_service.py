import stripe
import logging
from flask import url_for, current_app

logger = logging.getLogger(__name__)

class StripeService:
    def __init__(self):
        self.api_key = None
        self.is_initialized = False
        
    def init_app(self, app):
        """Initialize Stripe with keys from app config"""
        self.api_key = app.config.get('STRIPE_SECRET_KEY')
        if self.api_key:
            stripe.api_key = self.api_key
            self.is_initialized = True
            logger.info("✅ StripeService initialized")
        else:
            logger.warning("⚠️ STRIPE_SECRET_KEY not found in config")
            
    def create_checkout_session(self, amount, currency='eur', success_url=None, cancel_url=None, 
                              customer_email=None, metadata=None, description=None):
        """
        Create a Stripe Checkout Session
        amount: Amount in CENTIMES (e.g., 1000 for 10.00€)
        """
        if not self.is_initialized:
            logger.error("Attempted to use StripeService without initialization")
            return None, "Stripe not configured"
            
        try:
            session_data = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': description or 'Prestation',
                        },
                        'unit_amount': int(amount),  # Amount in cents
                    },
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'customer_email': customer_email,
                'metadata': metadata or {}
            }
            
            checkout_session = stripe.checkout.Session.create(**session_data)
            return checkout_session, None
            
        except Exception as e:
            logger.error(f"Stripe Create Session Error: {str(e)}")
            return None, str(e)

    def retrieve_session(self, session_id):
        if not self.is_initialized:
            return None
        try:
            return stripe.checkout.Session.retrieve(session_id)
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None

# Singleton instance
stripe_service = StripeService()
