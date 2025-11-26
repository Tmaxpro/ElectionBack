from flask import request, jsonify, current_app
from . import admin_bp
from models import Election, db, VoteToken
from utils import obfuscate_token, send_vote_one_sms, send_vote_sms_bulk
import csv
import io


@admin_bp.route('/elections/<election_uid>/tokens/create/csv', methods=['POST'])
def create_tokens_csv(election_uid):
    """Import a CSV of voters and send each a voting URL containing their token.

    Expects a multipart/form-data file field named `file` (CSV) with a header column `phone` or `phone_number`.
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
            phone = (row.get('phone') or row.get('phone_number') or row.get('telephone') or row.get('numero') or '').strip()
            if not phone:
                errors.append({'row': row, 'error': 'missing phone number'})
                continue
            # create token by phone number
            vtoken = VoteToken.query.filter_by(phone_number=phone, election_id=election.id).first()
            if not vtoken:
                vtoken = VoteToken(phone_number=phone, election_id=election.id)

            if vtoken:
                created.append({'phone': phone, 'token': vtoken.token})
                db.session.add(vtoken)
            else:
                errors.append({'phone': phone, 'error': 'token for this phone already exists'})

        db.session.commit()
    
    if not created:
        return jsonify({'error': 'no tokens created', 'errors': errors}), 400

    return jsonify({'created': len(created), 'errors': errors}), 201

@admin_bp.route('/elections/<election_uid>/tokens/create/phone', methods=['POST'])
def create_token_phone(election_uid):
    """
    Create a single vote token for the specified phone number provided in JSON body.
    Example JSON body: {"phone": "2250554760285"}
    """
    data = request.get_json() or {}
    phone = (data.get('phone') or data.get('phone_number') or '').strip()
    if not phone:
        return jsonify({'error': 'phone parameter is required'}), 400

    election = Election.query.filter_by(uid=election_uid).first_or_404()
    if not VoteToken.query.filter_by(phone_number=phone, election_id=election.id).first():
        vtoken = VoteToken(phone_number=phone, election_id=election.id)
        db.session.add(vtoken)
        db.session.commit()
        return jsonify({'phone': phone, 'token': vtoken.token}), 201
    else:
        return jsonify({'error': 'token for this phone already exists'}), 400

@admin_bp.route('/elections/<election_uid>/tokens/send', methods=['POST'])
def send_tokens(election_uid):
    """
    Send SMS to voters with their voting URLs.
    """
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    vote_tokens = VoteToken.query.filter_by(election_id=election.id, sent=False).all()
    sent = []
    errors = []
    for vote_token in vote_tokens:
        result = send_vote_one_sms(vote_token, election_uid)
        if result.get('success'):
            vote_token.sent = True
            db.session.commit()
            sent.append({'phone': vote_token.phone_number, 'is_active': vote_token.is_active, 'sent': vote_token.sent})
        else:
            errors.append({'phone': vote_token.phone_number, 'error': result.get('error', 'unknown error')})
    
    return jsonify({'sent': len(sent), 'errors': errors}), 200

@admin_bp.route('/elections/<election_uid>/tokens/send/all', methods=['POST'])
def send_all_tokens(election_uid):
    """
    Send SMS to all voters with their voting URLs, regardless of sent status.
    """
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    vote_tokens = VoteToken.query.filter_by(election_id=election.id).all()
    sent = []
    errors = []
    for vote_token in vote_tokens:
        result = send_vote_one_sms(vote_token, election_uid)
        if result.get('success'):
            vote_token.sent = True
            sent.append({'phone': vote_token.phone_number, 'is_active': vote_token.is_active, 'sent': vote_token.sent})
            db.session.commit()
        else:
            errors.append({'phone': vote_token.phone_number, 'error': result.get('error', 'unknown error')})
    
    return jsonify({'sent': len(sent), 'errors': errors}), 200
