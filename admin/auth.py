from flask import request, current_app, Response, jsonify, g
from werkzeug.security import check_password_hash
from . import admin_bp
from models import Admin, TokenBlocklist
import jwt
from datetime import datetime, timedelta
import uuid

# Use configured algorithm and expiry values from app config
JWT_ALGO = None

def _get_jwt_settings():
    algo = current_app.config.get('JWT_ALGORITHM')
    return algo


def create_access_token(identity, additional_claims=None, expires_delta=None):
    """Create a JWT access token."""
    algo = _get_jwt_settings()
    now = datetime.utcnow()
    exp = now + expires_delta if expires_delta else now + timedelta(seconds=int(current_app.config.get('JWT_EXP_DELTA_SECONDS')))
    jti = str(uuid.uuid4())
    payload = {
        'sub': str(identity),
        'iat': now,
        'exp': exp,
        'jti': jti,
        'type': 'access',
    }
    if additional_claims:
        payload.update(additional_claims)
    token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm=algo)
    # PyJWT >=2 returns a str; earlier versions returned bytes
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def create_refresh_token(identity, expires_delta=None):
    algo = _get_jwt_settings()
    now = datetime.utcnow()
    # Default refresh expiry: 7 days
    exp = now + (expires_delta if expires_delta else timedelta(days=7))
    jti = str(uuid.uuid4())
    payload = {
        'sub': str(identity),
        'iat': now,
        'exp': exp,
        'jti': jti,
        'type': 'refresh',
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm=algo)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

def decode_token(token):
    """Decode a JWT token and return its payload."""
    algo = _get_jwt_settings()
    payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=[algo])
    # Check blocklist
    jti = payload.get('jti')
    if jti and TokenBlocklist.is_blocked(jti):
        raise jwt.InvalidTokenError('Token has been revoked')
    return payload

def verify_jwt_in_request():
    """Verify JWT in the Authorization header of the request."""
    auth_header = request.headers.get('Authorization', None)
    if not auth_header:
        raise Exception('Missing Authorization Header')

    parts = auth_header.split()

    if parts[0].lower() != 'bearer':
        raise Exception('Invalid Authorization Header: must start with Bearer')
    elif len(parts) == 1:
        raise Exception('Invalid Authorization Header: token not found')
    elif len(parts) > 2:
        raise Exception('Invalid Authorization Header: contains extra content')

    token = parts[1]
    try:
        payload = decode_token(token)
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError as e:
        raise Exception(f'Invalid token: {str(e)}')
    
def get_jwt_identity():
    """Get the identity (sub) from the verified JWT in the request."""
    payload = verify_jwt_in_request()
    sub = payload.get('sub')
    # Try to return integer id when appropriate
    if isinstance(sub, str):
        try:
            return int(sub)
        except ValueError:
            return sub
    return sub

def get_jwt():
    """Get the full JWT payload from the verified JWT in the request."""
    payload = verify_jwt_in_request()
    return payload


@admin_bp.before_request
def require_admin_token():
    """Require a valid JWT for admin endpoints.

    - Allows OPTIONS (CORS preflight).
    - Allows the `login` and `logout` endpoints without a token.
    - For other endpoints expects `Authorization: Bearer <token>` header verified by Flask-JWT-Extended.
    """
    if request.method == 'OPTIONS':
        return None

    endpoint = request.endpoint or ''
    # Allow login, refresh and logout without access token (refresh endpoint will validate refresh token separately)
    if endpoint.endswith('.login') or endpoint.endswith('.logout') or endpoint.endswith('.refresh_token'):
        return None

    try:
        payload = verify_jwt_in_request()
        # Only allow access tokens for protected routes
        if payload.get('type') != 'access':
            raise Exception('A valid access token is required')
        # Prefer numeric admin_id when possible
        try:
            g.admin_id = int(payload.get('sub'))
        except Exception:
            g.admin_id = payload.get('sub')
        g.admin_username = payload.get('username') or None
        return None
    except Exception as exc:
        current_app.logger.debug('JWT verification failed: %s', exc)
        return jsonify({'error': 'authentication required', 'reason': str(exc)}), 401


@admin_bp.route('/login', methods=['POST'])
def login():
    """Authenticate admin and return a JWT.

    Expects JSON: { "username": "...", "password": "..." }
    Returns: { "access_token": "..." }
    """
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    admin = Admin.query.filter_by(username=username).first()
    if admin and check_password_hash(admin.password_hash, password):
        # Create access and refresh tokens
        access_expires = timedelta(seconds=int(current_app.config.get('JWT_EXP_DELTA_SECONDS', 3600)))
        access_token = create_access_token(identity=admin.id, additional_claims={'username': admin.username}, expires_delta=access_expires)
        refresh_token = create_refresh_token(identity=admin.id)
        return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200

    return jsonify({'error': 'invalid credentials'}), 401


@admin_bp.route('/logout', methods=['POST'])
def logout():
    # If client sends Authorization header, revoke that token
    auth_header = request.headers.get('Authorization', None)
    body = request.get_json(silent=True) or {}
    token = None
    if auth_header and auth_header.split()[0].lower() == 'bearer':
        token = auth_header.split()[1]
    elif body.get('token'):
        token = body.get('token')

    if not token:
        return jsonify({'message': 'no token provided, client should remove tokens locally'}), 200

    try:
        payload = decode_token(token)
        jti = payload.get('jti')
        ttype = payload.get('type') or 'access'
        # Save jti to blocklist (store numeric admin_id when possible)
        admin_id_val = None
        try:
            admin_id_val = int(payload.get('sub'))
        except Exception:
            admin_id_val = payload.get('sub')
        if jti:
            tb = TokenBlocklist(jti=jti, token_type=ttype, admin_id=admin_id_val)
            from models import db
            db.session.add(tb)
            db.session.commit()
        return jsonify({'message': 'token revoked'}), 200
    except Exception as exc:
        current_app.logger.debug('logout token revoke failed: %s', exc)
        return jsonify({'error': 'invalid token', 'reason': str(exc)}), 400


@admin_bp.route('/me', methods=['GET'])
def me():
    try:
        verify_jwt_in_request()
        payload = get_jwt()
        return jsonify({'id': get_jwt_identity(), 'username': payload.get('username')}), 200
    except Exception as exc:
        current_app.logger.debug('JWT verification failed in /me: %s', exc)
        return jsonify({'error': 'not authenticated', 'reason': str(exc)}), 401


@admin_bp.route('/debug/jwt', methods=['GET'])
def debug_decode_jwt():
    """Development helper: decode a JWT and show its payload.

    Usage: GET /api/v1/admin/debug/jwt?token=... (dev only)
    """
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'token query parameter required'}), 400
    try:
        payload = decode_token(token)
        return jsonify({'payload': payload}), 200
    except Exception as exc:
        current_app.logger.debug('debug_decode_jwt failed: %s', exc)
        return jsonify({'error': 'invalid token', 'reason': str(exc)}), 400


@admin_bp.route('/token/refresh', methods=['POST'])
def refresh_token():
    """Exchange a refresh token for a new access token.

    Expects JSON: { "refresh_token": "..." } or Authorization: Bearer <token>
    """
    data = request.get_json(silent=True) or {}
    token = None
    auth_header = request.headers.get('Authorization', None)
    if auth_header and auth_header.split()[0].lower() == 'bearer':
        token = auth_header.split()[1]
    else:
        token = data.get('refresh_token')

    if not token:
        return jsonify({'error': 'refresh_token required'}), 400

    try:
        payload = decode_token(token)
        if payload.get('type') != 'refresh':
            return jsonify({'error': 'token is not a refresh token'}), 400

        admin_id = payload.get('sub')
        # Ensure we query with correct type
        try:
            admin_key = int(admin_id)
        except Exception:
            admin_key = admin_id
        admin = Admin.query.get(admin_key)
        if not admin:
            return jsonify({'error': 'admin not found'}), 404

        # Issue a new access token
        access_expires = timedelta(seconds=int(current_app.config.get('JWT_EXP_DELTA_SECONDS', 3600)))
        access_token = create_access_token(identity=admin.id, additional_claims={'username': admin.username}, expires_delta=access_expires)
        return jsonify({'access_token': access_token}), 200
    except Exception as exc:
        current_app.logger.debug('refresh failed: %s', exc)
        return jsonify({'error': 'invalid refresh token', 'reason': str(exc)}), 401