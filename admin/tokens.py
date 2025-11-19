from flask import request, jsonify, current_app
from . import admin_bp
from models import db, VoteToken
from utils import obfuscate_token, send_vote_email
import csv
import io


@admin_bp.route('/elections/<int:election_id>/tokens/create', methods=['POST'])
def create_tokens(election_id):
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
            vtoken = VoteToken(email=email)
            #vtoken._generate_unique_uuid()
            if vtoken:
                created.append({'email': email, 'token': vtoken.token})
                db.session.add(vtoken)
            else:
                errors.append({'email': email, 'error': 'failed to generate token'})

        db.session.commit()

    return jsonify({'created': len(created), 'errors': errors}), 201

@admin_bp.route('/elections/<int:election_id>/tokens/send', methods=['POST'])
def send_tokens(election_id):
    """
    Send mails to voters with their voting URLs.
    """
    vote_tokens = VoteToken.query.all()
    election_id = election_id
    sent = []
    errors = []
    for vote_token in vote_tokens:
        result = send_vote_email(to_email=vote_token.email, token=vote_token.token, election_id=election_id)
        if result.get('success'):
            sent.append({'email': vote_token.email})
        else:
            errors.append({'email': vote_token.email, 'error': result.get('error', 'unknown error')})
    
    return jsonify({'sent': len(sent), 'errors': errors}), 200
