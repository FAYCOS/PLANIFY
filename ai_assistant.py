#!/usr/bin/env python3
"""
Assistant IA pour aider les clients à définir la mission idéale
Utilise Groq (Llama 3) - Gratuit et ultra-rapide
"""

import os
import json
import logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Groq non installé - mode fallback activé")
    GROQ_AVAILABLE = False
    Groq = None

class AIAssistant:
    def __init__(self):
        # Clé API Groq (variable d'environnement prioritaire, sinon base)
        self.api_key = self._load_api_key()
        self.client = None
        self._init_client()

        # Santé et diagnostics
        self.last_ok_at = None
        self.last_error = None
        self.last_error_at = None
        
        # Historique de conversation
        self.conversation_history = {}
        
        # Nom de l'entreprise (sera chargé dynamiquement)
        self.nom_entreprise = self.get_nom_entreprise()

    def _load_api_key(self):
        env_key = os.environ.get('GROQ_API_KEY', '').strip()
        if env_key:
            return env_key
        try:
            from app import ParametresEntreprise, app
            with app.app_context():
                parametres = ParametresEntreprise.query.first()
                if parametres and parametres.groq_api_key:
                    return parametres.groq_api_key.strip()
        except Exception as e:
            logger.warning(f"⚠️ Impossible de charger la clé Groq: {e}")
        return ''

    def _init_client(self):
        if not self.api_key:
            logger.warning("⚠️ GROQ_API_KEY non définie - mode fallback activé")
            self.client = None
            return
        logger.info("✅ GROQ_API_KEY détectée")
        if GROQ_AVAILABLE and Groq and self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("✅ Groq initialisé avec succès")
            except Exception as e:
                logger.error(f"❌ Erreur initialisation Groq: {e}")
                self._mark_error(e)
                self.client = None
        else:
            logger.warning("⚠️ Groq non disponible - utilisation du mode fallback")

    def refresh_api_key(self):
        new_key = self._load_api_key()
        if new_key != self.api_key:
            self.api_key = new_key
            self._init_client()
        elif self.api_key and self.client is None:
            # Réessaye d'initialiser si la clé est la même mais le client absent
            self._init_client()

    def _mark_ok(self):
        self.last_ok_at = datetime.now(timezone.utc)
        self.last_error = None
        self.last_error_at = None

    def _mark_error(self, err):
        self.last_error = f"{type(err).__name__}: {err}"
        self.last_error_at = datetime.now(timezone.utc)

    def test_connection(self):
        """Teste l'accès API Groq sans impacter l'historique."""
        if not GROQ_AVAILABLE:
            return False, "SDK manquant"
        if not self.api_key:
            return False, "Clé manquante"
        if not self.client:
            self._init_client()
        if not self.client:
            return False, "Init échouée"
        try:
            self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "ping"}],
                temperature=0,
                max_tokens=1,
                top_p=1
            )
            self._mark_ok()
            return True, "Connexion OK"
        except Exception as e:
            logger.error(f"❌ Erreur test Groq: {type(e).__name__}: {e}")
            self._mark_error(e)
            return False, f"{type(e).__name__}: {e}"
    
    def get_nom_entreprise(self):
        """Récupère le nom de l'entreprise depuis la base de données"""
        try:
            # Import local pour éviter les dépendances circulaires
            from app import ParametresEntreprise, db, app
            with app.app_context():
                parametres = ParametresEntreprise.query.first()
                if parametres and parametres.nom_entreprise:
                    return parametres.nom_entreprise
        except Exception as e:
            logger.warning(f"⚠️ Impossible de charger le nom de l'entreprise: {e}")
        
        # Valeur par défaut
        return "Planify"
    
    def get_system_prompt(self):
        """Génère le prompt système avec le nom de l'entreprise"""
        return f"""Tu es un assistant professionnel pour {self.nom_entreprise}, une entreprise de gestion de missions et services.

RÈGLES STRICTES :
- Sois direct et concis, SANS emojis
- Ne commente JAMAIS les réponses du client
- Pose UNE question à la fois
- NE DEMANDE JAMAIS le budget

QUESTIONS À POSER (exactement dans cet ordre) :
1. Type de mission/service
2. Nombre de participants/bénéficiaires
3. Contraintes ou préférences clés
4. Nom complet du client
5. Email du client
6. Téléphone du client

STRUCTURE DE TES RÉPONSES :
- Question 1 : "Quel type de mission ou service souhaitez-vous ?"
- Question 2 : "Combien de participants ou bénéficiaires attendez-vous ?"
- Question 3 : "Quelles contraintes ou préférences clés souhaitez-vous ?"
- Question 4 : "Quel est votre nom complet ?"
- Question 5 : "Quelle est votre adresse email ?"
- Question 6 : "Quel est votre numéro de téléphone ?"

APRÈS LA 6ème RÉPONSE :
Donne les recommandations avec cette structure exacte :
"Basé sur vos besoins, voici mes recommandations :

- Prestataire principal
- Équipement adapté
- Support technique

Le formulaire va se pré-remplir automatiquement. Pensez à indiquer la date et les horaires de votre mission dans le formulaire ci-dessus."

SERVICES DISPONIBLES :
- Prestataire principal (DJ / intervenant)
- Sonorisation / support audio
- Éclairage & effets / visuel
- Karaoké / option

IMPORTANT :
- Pas d'emojis
- Pas de commentaires sur les réponses
- Questions directes et simples
- Ton professionnel mais aimable"""
    
    def get_response(self, user_message, conversation_id="default"):
        """Obtient une réponse de l'IA"""
        try:
            if not self.client and self.api_key:
                self._init_client()
            # Mode fallback si pas de client Groq
            if not self.client:
                logger.info(f"🔄 Mode fallback activé pour: {user_message[:50]}...")
                return self._fallback_response(user_message, conversation_id)
            
            logger.info(f"🤖 Utilisation de Groq pour: {user_message[:50]}...")
            
            # Initialiser l'historique si nécessaire
            if conversation_id not in self.conversation_history:
                self.conversation_history[conversation_id] = [
                    {"role": "system", "content": self.get_system_prompt()}
                ]
                logger.info(f"📝 Nouvel historique créé pour {conversation_id} ({self.nom_entreprise})")
            
            # Ajouter le message utilisateur
            self.conversation_history[conversation_id].append({
                "role": "user",
                "content": user_message
            })
            
            logger.info(f"📨 Envoi à Groq (historique: {len(self.conversation_history[conversation_id])} messages)")
            
            # Appeler l'API Groq
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Nouveau modèle (remplace llama-3.1)
                messages=self.conversation_history[conversation_id],
                temperature=0.7,
                max_tokens=500,
                top_p=0.9
            )
            
            # Extraire la réponse
            assistant_message = response.choices[0].message.content
            logger.info(f"✅ Réponse reçue: {assistant_message[:100]}...")
            self._mark_ok()
            
            # Ajouter à l'historique
            self.conversation_history[conversation_id].append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"❌ Erreur Groq: {type(e).__name__}: {e}")
            self._mark_error(e)
            import traceback
            traceback.print_exc()
            logger.info(f"🔄 Basculement en mode fallback...")
            return self._fallback_response(user_message, conversation_id)
    
    def _fallback_response(self, user_message, conversation_id):
        """Réponses de secours si l'API n'est pas disponible"""
        message_lower = user_message.lower()
        
        # Initialiser le compteur de messages
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        count = len(self.conversation_history[conversation_id])
        self.conversation_history[conversation_id].append(user_message)
        
        # Questions dans l'ordre
        if count == 0:
            return f"Bonjour, je suis votre assistant {self.nom_entreprise}. Quel type de mission ou service souhaitez-vous ?"
        elif count == 1:
            return "Combien de participants ou bénéficiaires attendez-vous ?"
        elif count == 2:
            return "Quelles contraintes ou préférences clés souhaitez-vous ?"
        elif count == 3:
            return "Quel est votre nom complet ?"
        elif count == 4:
            return "Quelle est votre adresse email ?"
        elif count == 5:
            return "Quel est votre numéro de téléphone ?"
        elif count == 6:
            return """Basé sur vos besoins, voici mes recommandations :

- Prestataire principal
- Équipement adapté
- Support technique

Le formulaire va se pré-remplir automatiquement. Pensez à indiquer la date et les horaires de votre mission dans le formulaire ci-dessus."""
        
        return "Le formulaire va se pré-remplir automatiquement avec vos informations."
    
    def reset_conversation(self, conversation_id="default"):
        """Réinitialise une conversation"""
        if conversation_id in self.conversation_history:
            del self.conversation_history[conversation_id]
    
    def get_recommendations(self, conversation_id="default"):
        """Analyse la conversation et retourne des recommandations structurées"""
        if conversation_id not in self.conversation_history:
            return {}
        
        # Extraire les messages utilisateur
        user_messages = []
        for msg in self.conversation_history[conversation_id]:
            if isinstance(msg, dict) and msg.get('role') == 'user':
                user_messages.append(msg.get('content', ''))
            elif isinstance(msg, str):
                user_messages.append(msg)
        
        conversation = ' '.join(user_messages).lower()
        
        recommendations = {
            'type_evenement': '',
            'nb_invites': None,
            'services': [],
            'client_nom': '',
            'client_email': '',
            'client_telephone': ''
        }
        
        # Détecter le type d'événement (1er message)
        if len(user_messages) >= 1:
            first_msg = user_messages[0].lower()
            if 'mariage' in first_msg:
                recommendations['type_evenement'] = 'mariage'
            elif 'anniversaire' in first_msg:
                recommendations['type_evenement'] = 'anniversaire'
            elif 'entreprise' in first_msg or 'professionnel' in first_msg:
                recommendations['type_evenement'] = 'soiree_entreprise'
            elif 'privée' in first_msg or 'privé' in first_msg:
                recommendations['type_evenement'] = 'soiree_privee'
            elif 'concert' in first_msg:
                recommendations['type_evenement'] = 'concert'
            else:
                recommendations['type_evenement'] = 'soiree_privee'
        
        # Extraire le nombre d'invités (2ème message)
        if len(user_messages) >= 2:
            import re
            numbers = re.findall(r'\b(\d+)\b', user_messages[1])
            if numbers:
                num_int = int(numbers[0])
                if 10 <= num_int <= 10000:
                    recommendations['nb_invites'] = num_int
        
        # Extraire le nom du client (4ème message)
        if len(user_messages) >= 4:
            recommendations['client_nom'] = user_messages[3].strip()
        
        # Extraire l'email du client (5ème message)
        if len(user_messages) >= 5:
            recommendations['client_email'] = user_messages[4].strip()
        
        # Extraire le téléphone du client (6ème message)
        if len(user_messages) >= 6:
            recommendations['client_telephone'] = user_messages[5].strip()
        
        # Services recommandés par défaut
        recommendations['services'] = ['dj', 'sonorisation', 'eclairage']
        
        if 'karaoké' in conversation or 'karaoke' in conversation:
            recommendations['services'].append('karaoke')
        
        return recommendations

# Instance globale
ai_assistant = AIAssistant()
