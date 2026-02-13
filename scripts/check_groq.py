#!/usr/bin/env python3
"""
Vérifie la configuration Groq et effectue un ping minimal.
"""

import os
import sys

from ai_assistant import ai_assistant, GROQ_AVAILABLE


def main():
    if not os.environ.get('GROQ_API_KEY') and not getattr(ai_assistant, 'api_key', ''):
        print("Aucune clé Groq configurée (variable d'environnement ou base).")
        return 1

    if not GROQ_AVAILABLE or not ai_assistant.client:
        print("Groq non disponible (client non initialisé). Vérifiez la clé et l'installation du SDK.")
        return 2

    try:
        response = ai_assistant.get_response("Bonjour", conversation_id="healthcheck")
        preview = response[:160].replace("\n", " ").strip()
        print("Groq OK. Réponse:", preview)
        return 0
    except Exception as exc:
        print("Erreur lors du test Groq:", exc)
        return 3


if __name__ == "__main__":
    sys.exit(main())
