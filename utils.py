import hmac
import hashlib
import smtplib
import requests
from email.message import EmailMessage
from ACIMClient import ACIMSMSClient
from flask import current_app

def shorten(url):
  base_url = 'http://tinyurl.com/api-create.php?url='
  response = requests.get(base_url+url)
  short_url = response.text
  return short_url

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

def generate_vote_url(vote_token, election_uid) -> str:
    frontend = current_app.config.get('FRONTEND_URL', '').rstrip('/')
    obf = obfuscate_token(vote_token.token)
    vote_url = f"{frontend}/elections/{election_uid}/vote/{obf}"
    short_url = shorten(vote_url)
    return short_url

def generate_vote_message(vote_token, election_uid, body=None) -> str:
    if not body:
        vote_url = generate_vote_url(vote_token, election_uid)
        sms_message = f"Bonjour,\nVeuillez voter pour l'election du BDE en suivant ce lien : {vote_url} \nCordialement."
        return sms_message
    return body

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
    
def _create_sms_client():
    username = current_app.config.get('SMS_API_USERNAME')
    token = current_app.config.get('SMS_API_TOKEN')
    sender = current_app.config.get('SMS_API_SENDER')
    return ACIMSMSClient(username=username, token=token, sender=sender)


def send_vote_one_sms(vtoken, election_uid: str, flash: int = 0, titre: str = "") -> dict:
    """Send an SMS containing the voting URL using external SMS API.

    Returns a dict with `success` (bool) and `error` (str) on failure.
    """

    smsclient = _create_sms_client()
    message = generate_vote_message(vote_token=vtoken, election_uid=election_uid)
    result = smsclient.send_one_sms(dest=vtoken.phone_number, message=message, flash=flash, titre=titre)

    if result.get('success'):
        return {'success': True, 'ref': result.get('ref', 'N/A')}
    else:
        return {'success': False, 'error': result.get('error', result.get('status', 'unknown error'))}

def prepare_sms_bulk(vtokens: list, election_uid: str, flash: int) -> list:
    """Prépare une liste de numéros de téléphone pour l'envoi en masse.

    Extrait les numéros de téléphone des objets VoteToken fournis.
    """
    messages = []
    for token in vtokens:
        payload = {
            'Dest': token.phone_number,
            'Sms': generate_vote_message(token, election_uid),
            'Sender': current_app.config.get('SMS_API_SENDER'),
            'Flash': flash,
        }
        messages.append(payload)
    return messages

def send_vote_sms_bulk(vtokens: list, election_uid: str, flash: int) -> dict:
    """Send SMS messages in bulk containing the voting URL using external SMS API.

    Returns a dict with `success` (bool) and `error` (str) on failure.
    """
    messages = prepare_sms_bulk(vtokens, election_uid, flash)
    smsclient = _create_sms_client()
    result = smsclient.send_bulk_sms(messages)

    if result.get('success'):
        return {'success': True, 'ref': result.get('ref', 'N/A')}
    else:
        return {'success': False, 'error': result.get('error', 'unknown error')}