import hmac
import hashlib
import smtplib
from email.message import EmailMessage
from flask import current_app, jsonify

def obfuscate_token(token: str) -> str:
    """Hash sécurisé du token UUID avec HMAC-SHA256.

    Utilise la clé secrète de l'application courante (`SECRET_KEY`).
    """
    secret = current_app.config.get("SECRET_KEY", "")
    token_str = str(token)
    return hmac.new(secret.encode(), token_str.encode(), hashlib.sha256).hexdigest()


def extract_token_from_obfuscated(hashed_token: str):
    """Retourne le UUID brut correspondant au `hashed_token` ou None.

    Importe `VoteToken` localement pour éviter import circulaire entre `models` et `utils`.
    """
    from models import VoteToken

    for vote_token in VoteToken.query.all():
        if obfuscate_token(vote_token.token) == hashed_token:
            return str(vote_token.token)
    return None

def send_vote_email(to_email: str, vote_url: str, subject: str = None, body: str = None) -> dict:
    """Send an email containing the voting URL using SMTP settings from current_app.

    Returns a dict with `success` (bool) and `error` (str) on failure.
    """

    host = current_app.config.get('MAIL_HOST')
    port = int(current_app.config.get('MAIL_PORT', 587))
    user = current_app.config.get('MAIL_USER')
    password = current_app.config.get('MAIL_PASS')
    use_tls = current_app.config.get('MAIL_USE_TLS', True)
    mail_from = current_app.config.get('MAIL_FROM', user)

    if not host:
        return {'success': False, 'error': 'MAIL_HOST not configured'}
    

    subject = subject or 'Votre lien de vote'
    body = body or f'Bonjour,\n\nVeuillez voter en suivant ce lien : {vote_url}\n\nCordialement.'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if user:
                server.login(user, password)
            server.send_message(msg)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}