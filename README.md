# ElectionApp Backend (Flask)

Backend Flask minimal pour une application de vote en ligne.

Base URL API: `/api/v1/`

Prérequis
- Python 3.8+

# API Documentation

Base URL: `/api/v1`

Authentication (admin)
- Admin endpoints require JWT `access_token` in the `Authorization` header:

  Authorization: Bearer <ACCESS_TOKEN>

- Some endpoints accept a `refresh_token` to obtain a new `access_token`.

Notes
- Default content-type is `application/json` unless `multipart/form-data` is specified (file uploads).
- Response examples show typical JSON bodies and HTTP status codes.

## Admin endpoints (prefix: `/api/v1/admin`)

- POST `/login`
  - Description: authenticate admin and return tokens.
  - Request (JSON):
    - {"username": string, "password": string}
  - Response 200 (JSON):
    - {"access_token": string, "refresh_token": string}

- POST `/logout`
  - Description: revoke a token (add to blocklist).
  - Auth: `Authorization: Bearer <TOKEN>` or body {"token": string}
  - Response 200: {"message": "token revoked"}

- GET `/me`
  - Description: return current admin info.
  - Auth: `Authorization: Bearer <ACCESS_TOKEN>`
  - Response 200: {"id": int, "username": string}

- POST `/token/refresh`
  - Description: exchange a `refresh_token` for a new `access_token`.
  - Request (JSON): {"refresh_token": string} or Authorization header with refresh token
  - Response 200: {"access_token": string}

- GET `/debug/jwt?token=<TOKEN>`
  - Description: development helper to decode a JWT and return payload (do not expose in production).
  - Response 200: {"payload": {...}}

## Elections (admin)

- GET `/elections`
  - Description: list all elections.
  - Response 200 (JSON):
    - [ {"uid": string, "title": string, "start_at": datetime|null, "end_at": datetime|null}, ... ]

- POST `/elections`
  - Description: create an election (optionally with initial candidates).
  - Request (JSON):
    - {"title": string, "start_at": string optional (ISO datetime), "end_at": string optional, "candidates": optional array }
    - `candidates` items: either `string` (name) or object {"name": string, "prenom": string, "photo": string}
  - Response 201 (JSON): {"uid": string, "title": string}

- DELETE `/elections/<election_uid>`
  - Description: delete election and related objects (candidates, votes, tokens) — DB cascade expected.
  - Response 200: {"message": "Election deleted"}

- PUT/PATCH `/elections/<election_uid>`
  - Description: update election fields.
  - Request (JSON): {"title": string optional, "start_at": string optional, "end_at": string optional}
  - Response 200: {"uid": string, "title": string, "start_at": datetime|null, "end_at": datetime|null}

## Candidates (admin)

- POST `/elections/<election_uid>/candidates`
  - Description: add a candidate to an election.
  - Request: either JSON or multipart/form-data
    - JSON: {"name": string, "prenom": string optional, "photo": string optional (URL)}
    - multipart/form-data: fields `name`, `prenom` (optional), `photo` (file) — file must be one of png/jpg/jpeg/gif
  - Response 201: {"uid": string, "name": string, "prenom": string}

- GET `/elections/<election_uid>/candidates`
  - Description: list candidates for an election.
  - Response 200: [ {"uid": string, "name": string, "prenom": string, "photo": string}, ... ]

- PUT/PATCH `/elections/<election_uid>/candidates/<candidate_uid>`
  - Description: update candidate metadata and/or photo.
  - Request: JSON or multipart/form-data (same fields as POST candidate)
  - Response 200: {"uid": string, "name": string, "prenom": string, "photo": string}

- DELETE `/elections/<election_uid>/candidates/<candidate_uid>`
  - Description: remove candidate (forbidden while election in progress).
  - Response 200: {"message": "Candidate deleted"}

## Voting tokens (admin)

- POST `/elections/<election_uid>/tokens/create/csv`
  - Description: import tokens from CSV uploaded as multipart/form-data field `file`.
  - CSV: must include column `phone` or `phone_number` (header).
  - Response 201: {"created": int, "errors": [ {"error": string, ...}, ... ] }

- POST `/elections/<election_uid>/tokens/create/phone`
  - Description: create a single token for a phone number.
  - Request (JSON): {"phone": string}
  - Response 201: {"phone": string, "token": string}

- POST `/elections/<election_uid>/tokens/send`
  - Description: send voting SMS to generated tokens that haven't been sent yet.
  - Response 200: {"sent": int, "errors": [ ... ]}

- POST `/elections/<election_uid>/tokens/send/all`
  - Description: send voting SMS to all generated tokens (resend).
  - Response 200: {"sent": int, "errors": [ ... ]}

- GET `/elections/<election_uid>/votants`
  - Description: list voters/tokens for the election.
  - Response 200: [ {"phone": string, "token": string, "is_active": bool, "sent": bool}, ... ]

- DELETE `/elections/<election_uid>/votants/<phone>`
  - Description: delete a voter token by phone number.
  - Response 200: {"message": "Token deleted"}

## Public voting endpoints (prefix: `/api/v1`)

- GET `/elections/<election_uid>/vote/<token_hash>`
  - Description: validate token and return election + candidates.
  - Response 200: {"election": {"id": int, "title": string}, "candidates": [ {"id": int, "name": string, "prenom": string, "photo": string}, ... ]}
  - Errors: 403 when token invalid or election outside date range.

- POST `/elections/<election_uid>/vote/<token_hash>`
  - Description: submit a vote and consume the token.
  - Request (JSON): {"candidate_id": int}
  - Response 201: {"message": "vote recorded"}
  - Errors:
    - 400: missing `candidate_id`
    - 403: invalid/expired token or voting outside election period

## Stats / results (admin)

- GET `/elections/<election_uid>/results`
  - Description: return vote counts per candidate for the election.
  - Response 200: {"election": {"uid": string, "title": string}, "results": [ {"candidate_uid": string, "name": string, "prenom": string, "photo": string, "vote_count": int}, ... ]}

- GET `/stats`
  - Description: global stats listing per-election participation numbers.
  - Response 200: [ {"election_uid": string, "title": string, "total_voters": int, "total_tokens": int, "votes_cast": int, "total_candidates": int, "participation_rate": float}, ... ]

## Debug / utility

- GET `/debug/routes` (app root)
  - Description: list all registered routes (development helper).

- GET `/debug/request-headers` (app root)
  - Description: echo request headers (development helper).

- GET `/uploads/<filename>` (app root)
  - Description: serve uploaded files. Use `url_for('uploaded_file', filename=...)` to build public URLs for candidate photos.

## Examples (curl)

Login example:
```bash
curl -X POST http://localhost:5000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'
```

Create election example:
```bash
curl -X POST http://localhost:5000/api/v1/admin/elections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"title":"Scrutin 2025","start_at":"2025-11-20T12:00:00","end_at":"2025-11-20T18:00:00","candidates":[{"name":"Dupont","prenom":"Jean"}]}'
```

Create tokens from CSV example:
```bash
curl -X POST http://localhost:5000/api/v1/admin/elections/<election_uid>/tokens/create/csv \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@voters.csv"
```
(CSV file should have a `phone` column)

Vote example (public):
```bash
curl -X POST http://localhost:5000/api/v1/elections/<election_uid>/vote/<token_hash> \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": 42}'
```

## Migrations

If you change models (example: add `ondelete` or cascade options), create and apply a migration:

```bash
flask db migrate -m "describe changes"
flask db upgrade
```

Note: Alembic may not detect `ondelete` changes automatically on some backends; you may need to edit the migration file to ALTER the foreign key constraints.

## Environment variables

- `DATABASE_URL`: SQLAlchemy URI (e.g. `sqlite:///electionapp.db` or Postgres URL)
- `SECRET_KEY`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXP_DELTA_SECONDS`
- `FRONTEND_URL` (used to build voting links)
- SMS settings: `SMS_API_USERNAME`, `SMS_API_TOKEN`, `SMS_API_SENDER`
- Mail settings (legacy/optional): `MAIL_HOST`, `MAIL_PORT`, `MAIL_USER`, `MAIL_PASS`, `MAIL_FROM`, `MAIL_USE_TLS`

## Next steps I can help with

- Generate OpenAPI/Swagger from these routes.
- Add automated tests for important flows (login/refresh/revoke, vote flow).
- Create Postman collection example.

*** End API Documentation ***
