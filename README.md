# ElectionApp Backend (Flask)

Backend Flask minimal pour une application de vote en ligne.

Base URL API: `/api/v1/`

Prérequis
- Python 3.8+

# ElectionApp Backend — Documentation API

Cette documentation décrit les routes disponibles et comment les utiliser pour l'API backend.

**Base URL**: `/api/v1`

**Authentification (admin)**: Le namespace admin utilise JWT. Pour accéder aux endpoints protégés, envoyez l'`access_token` dans l'en-tête:

```
Authorization: Bearer <ACCESS_TOKEN>
```

Les tokens retournés par `/api/v1/admin/login` contiennent un `access_token` (courte durée) et un `refresh_token` (durée plus longue). Utilisez `/api/v1/admin/token/refresh` pour obtenir un nouvel access token.

**Format**: JSON pour les requêtes et réponses sauf indication contraire.

**Endpoints Admin**

- `POST /api/v1/admin/login`
  - Description: authentifie un admin et retourne `access_token` + `refresh_token`.
  - Body JSON: `{ "username": "...", "password": "..." }`
  - Réponse 200: `{ "access_token": "...", "refresh_token": "..." }`

- `POST /api/v1/admin/logout`
  - Description: révoque le token fourni (ajoute le `jti` au blocklist côté serveur).
  - En-tête: `Authorization: Bearer <TOKEN>` ou Body JSON `{ "token": "..." }`
  - Réponse 200: `{ "message": "token revoked" }` ou 400 si token invalide.

- `GET /api/v1/admin/me`
  - Description: retourne l'admin courant (protégé par `access_token`).
  - En-tête: `Authorization: Bearer <ACCESS_TOKEN>`
  - Réponse 200: `{ "id": <id>, "username": "..." }`

- `POST /api/v1/admin/token/refresh`
  - Description: échange un `refresh_token` contre un nouveau `access_token`.
  - Body JSON: `{ "refresh_token": "..." }` ou `Authorization: Bearer <refresh_token>`
  - Réponse 200: `{ "access_token": "..." }`

- `GET /api/v1/admin/debug/jwt`
  - Description: (dev) décode un token passé en query param `?token=...` et renvoie le payload.
  - Usage: `GET /api/v1/admin/debug/jwt?token=<TOKEN>`

- `GET /api/v1/admin/elections`
  - Description: liste les élections (protégé).
  - Réponse 200: `{ "elections": [ {"id":1, "title":"..."}, ... ] }`

- `POST /api/v1/admin/elections`
  - Description: crée une élection et ses candidats.
  - Body JSON: `{ "title": "Titre", "candidates": ["Nom1", {"name":"Nom2","prenom":"Prénom"}] }`
  - Réponse 201: `{ "id": <election_id>, "title": "..." }`

- `POST /api/v1/admin/elections/<int:election_id>/candidates`
  - Description: ajoute un candidat à l'élection.
  - Body JSON: `{ "name": "Nom", "prenom": "Prénom", "photo": "..." }`
  - Réponse 201: `{ "id": <candidate_id>, ... }`

- `GET /api/v1/admin/elections/<int:election_id>/resultats`
  - Description: récupère les résultats (votes par candidat) pour l'élection.
  - Réponse 200: `{ "election_id": <id>, "results": [ {"candidate_id":1, "votes": 12}, ... ] }`

- `POST /api/v1/admin/elections/<int:election_id>/tokens/create`
  - Description: importe un CSV (multipart/form-data field `file`) contenant des emails et crée des `VoteToken`.
  - CSV attendu: header `email` (ou `mail`).
  - Réponse 201: `{ "created": <n>, "errors": [...] }`

- `POST /api/v1/admin/elections/<int:election_id>/tokens/send`
  - Description: envoie les emails de vote construits à partir des tokens (`FRONTEND_URL` est utilisé pour générer les liens).
  - Réponse: `{ "sent": <n>, "errors": [...] }`

**Endpoints Public (vote)**

- `GET /api/v1/elections/<int:election_id>/vote/<token_hash>`
  - Description: retourne l'élection et la liste des candidats si `token_hash` est valide.
  - Réponse 200: `{ "election": {...}, "candidates": [ {...}, ... ] }`
  - Si token invalide: 403 ou comportement front-end (redirection vers `/`).

- `POST /api/v1/elections/<int:election_id>/vote/<token_hash>`
  - Description: enregistre un vote pour `candidate_id` et consomme le token.
  - Body JSON: `{ "candidate_id": <id> }`
  - Réponses:
    - 201: `{ "message": "vote recorded" }`
    - 400: `candidate_id` manquant
    - 403: token invalide

**Exemples d'appels (curl)**

Login (récupère tokens):
```bash
curl -X POST http://localhost:5000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'
```

Appel protégé (`/me`):
```bash
curl http://localhost:5000/api/v1/admin/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Rafraîchir access token:
```bash
curl -X POST http://localhost:5000/api/v1/admin/token/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<REFRESH_TOKEN>"}'
```

Révocation d'un token:
```bash
curl -X POST http://localhost:5000/api/v1/admin/logout \
  -H "Authorization: Bearer <TOKEN>"
```

**Variables d'environnement importantes**

- `DATABASE_URL` — SQLAlchemy URI (ex: `sqlite:///electionapp.db` ou Postgres `postgresql://user:pass@host:5432/db`).
- `SECRET_KEY` — clé d'application.
- `JWT_SECRET_KEY` — clé utilisée pour signer les JWT.
- `JWT_ALGORITHM` — ex: `HS256`.
- `JWT_EXP_DELTA_SECONDS` — durée (s) d'un access token.
- `FRONTEND_URL` — URL du frontend pour construire les liens de vote.
- Mail settings: `MAIL_HOST`, `MAIL_PORT`, `MAIL_USER`, `MAIL_PASS`, `MAIL_FROM`, `MAIL_USE_TLS`.

**Migrations**

Si vous avez modifié les modèles (ex: ajout du `TokenBlocklist`), créez et appliquez les migrations :

```powershell
flask db migrate -m "add token blocklist"
flask db upgrade
```

**Bonnes pratiques & sécurité**

- Protégez `.env` (ne pas le committer). Ajoutez-le à `.gitignore`.
- Utilisez HTTPS en production et des clés fortes pour `SECRET_KEY` et `JWT_SECRET_KEY`.
- Pour envois importants d'e-mails, utilisez une file (Celery, RQ) et des workers.

**Options possibles (je peux aider)**

- Générer un fichier OpenAPI / Swagger pour ces routes.
- Ajouter des tests automatisés pour le flow JWT (login / refresh / revoke).
- Créer des exemples Postman ou collection exportable.

*** End API Documentation ***