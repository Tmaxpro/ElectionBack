from flask import request, jsonify, current_app
from . import admin_bp
from models import Election, db, VoteToken
from utils import obfuscate_token, send_vote_email
import csv
import io


@admin_bp.route('/elections/<election_uid>/tokens/create', methods=['POST'])
def create_tokens(election_uid):
    """Import a CSV of voters and send each a voting URL containing their token.

    Expects a multipart/form-data file field named `file` (CSV) with a header column `email`.
    """
    # file required
    upload = request.files.get('file')
    if not upload:
        return jsonify({'error': 'file is required (multipart/form-data with field "file")'}), 400

    # read CSV
    try:
        content = upload.stream.read().decode('utf-8')
    except Exception:
        return jsonify({'error': 'cannot read uploaded file'}), 400
    
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    reader = csv.DictReader(io.StringIO(content))
    created = []
    errors = []
    with current_app.app_context():
        for row in reader:
            email = (row.get('email') or row.get('mail') or '').strip()
            if not email:
                errors.append({'row': row, 'error': 'missing email'})
                continue
            # create token
            vtoken = VoteToken(email=email, election_id=election.id)
            #vtoken._generate_unique_uuid()
            if vtoken:
                created.append({'email': email, 'token': vtoken.token})
                db.session.add(vtoken)
            else:
                errors.append({'email': email, 'error': 'failed to generate token'})

        db.session.commit()
    
    if not created:
        return jsonify({'error': 'no tokens created', 'errors': errors}), 400

    return jsonify({'created': len(created), 'errors': errors}), 201

@admin_bp.route('/elections/<election_uid>/tokens/send', methods=['POST'])
def send_tokens(election_uid):
    """
    Send mails to voters with their voting URLs.
    """
    vote_tokens = VoteToken.query.all()
    sent = []
    errors = []
    for vote_token in vote_tokens:
        # Build the public vote URL using the configured frontend base URL and the election UID
        frontend = current_app.config.get('FRONTEND_URL', '').rstrip('/')
        obf = obfuscate_token(vote_token.token)
        vote_url = f"{frontend}/elections/{election_uid}/vote/{obf}"
        result = send_vote_email(to_email=vote_token.email, vote_url=vote_url)
        if result.get('success'):
            sent.append({'email': vote_token.email})
        else:
            errors.append({'email': vote_token.email, 'error': result.get('error', 'unknown error')})
    
    return jsonify({'sent': len(sent), 'errors': errors}), 200
