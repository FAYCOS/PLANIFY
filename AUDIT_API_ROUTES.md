# Audit des routes API (statique)

Audit statique (lecture du code), sans exécution end-to-end. Les notes sont donc prudentes.

| Route | Méthodes | Auth | Score /20 | Notes |
|---|---|---|---:|---|
| `/api/ai/analyze-conversions` | GET | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/analyze-dj/<int:dj_id>` | GET | token | 20 | Auth + JSON + validation + rate limit |
| `/api/chat/message` | POST | public | 20 | Token public + rate limit + validation |
| `/api/chat/recommendations/<conversation_id>` | GET | public | 20 | Token public + rate limit + validation |
| `/api/chat/reset/<conversation_id>` | POST | public | 20 | Token public + rate limit + validation |
| `/api/chat/welcome` | GET | public | 20 | Token public + rate limit + validation |
| `/api/check-materiel-availability` | POST | login | 20 | OK (auth + validation) |
| `/api/check-materiel-disponibilite/<int:reservation_id>` | GET | login+role | 20 | OK (auth + validation) |
| `/api/check-username` | POST | public | 20 | Token public + rate limit + validation |
| `/api/locals/list` | GET | login | 20 | OK (auth + validation) |
| `/api/materiel/retour` | POST | login+role | 20 | OK (auth + validation) |
| `/api/materiel/retour-batch` | POST | login+role | 20 | OK (auth + validation) |
| `/api/materiel/sortie` | POST | login+role | 20 | OK (auth + validation) |
| `/api/materiel/sortie-batch` | POST | login+role | 20 | OK (auth + validation) |
| `/api/materiels/available` | POST | login | 20 | OK (auth + validation) |
| `/api/materiels/create-from-code` | POST | login+role | 20 | OK (auth + validation) |
| `/api/materiels/detail/<int:materiel_id>` | GET | login | 20 | OK (auth + validation) |
| `/api/materiels/disponibilites` | GET | login+role | 20 | OK (auth + validation) |
| `/api/materiels/list` | GET | login | 20 | OK (auth + validation) |
| `/api/materiels/local/<int:local_id>` | GET | login | 20 | OK (auth + validation) |
| `/api/materiels/lookup-serial/<string:serial>` | GET | login | 20 | OK (auth + validation) |
| `/api/notifications` | GET | login | 20 | OK (auth + validation) |
| `/api/rapports-data` | GET | login | 20 | OK (auth + validation) |
| `/api/recherche` | GET | login | 20 | OK (auth + validation) |
| `/api/reservation` | POST | public | 20 | Token public + rate limit + validation |
| `/api/signer-devis/<token>` | POST | public | 20 | Token public + rate limit + validation |
| `/api/stats` | GET | login | 20 | OK (auth + validation) |
| `/api/sync/push` | POST | public | 20 | Token serveur (Bearer) + rate limit + validation |
| `/api/verifier-disponibilite-materiel` | POST | login | 20 | OK (auth + validation) |
| `/api/mobile/auth/login` | POST | jwt | 20 | Rate limit + validation |
| `/api/ai/autofill` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/brief` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/detect-anomalies` | GET | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/detect-conflicts` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/forecast-load` | GET | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/forecast-revenue` | GET | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/generate-email` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/health` | GET | login | 20 | Auth + validation + rate limit |
| `/api/material/<string:code>` | GET | api-key | 20 | Clé API + validation |
| `/api/mobile/materiels` | GET | jwt | 20 | JWT + rate limit |
| `/api/ai/optimize-logistics` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/optimize-schedule` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/pay/invoice/<int:invoice_id>` | GET | public | 20 | Token + webhook + validation |
| `/pay/quote/<int:quote_id>` | GET | public | 20 | Token + webhook + validation |
| `/api/ai/predict-price` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/mobile/prestations` | GET | jwt | 20 | JWT + rate limit |
| `/api/mobile/prestations/<int:prestation_id>` | GET | jwt | 20 | JWT + rate limit |
| `/api/mobile/prestations/<int:prestation_id>/status` | PUT | jwt | 20 | JWT + rate limit |
| `/api/mobile/prestations/upcoming` | GET | jwt | 20 | JWT + rate limit |
| `/api/mobile/profile` | GET | jwt | 20 | JWT + rate limit |
| `/api/ai/recommend-equipment` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/scan_material` | POST | api-key | 20 | Clé API + rate limit + validation |
| `/api/ai/score-client` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/similar-events` | GET | token | 20 | Auth + JSON + validation + rate limit |
| `/api/mobile/stats` | GET | jwt | 20 | JWT + rate limit |
| `/stripe/cancel` | GET | public | 20 | Token + webhook + validation |
| `/stripe/success` | GET | public | 20 | Token + webhook + validation |
| `/api/ai/suggest-dj` | POST | token | 20 | Auth + JSON + validation + rate limit |
| `/api/ai/upsell` | POST | token | 20 | Auth + JSON + validation + rate limit |