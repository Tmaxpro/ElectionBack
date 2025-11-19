from flask import jsonify, request, redirect
from datetime import datetime
from . import public_bp
from models import Election, Candidate, Vote, VoteToken
from utils import extract_token_from_obfuscated
from models import db


@public_bp.route('/elections/<election_uid>/vote/<token_hash>', methods=['GET'])
def vote_get(election_uid, token_hash):
    if not token_hash:
        return redirect('/')
    # Récupérer l'élection et vérifier si elle est déjà terminée
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    now = datetime.utcnow()
    if election.end_at and now > election.end_at:
        # Ne rien retourner si l'élection est passée
        return jsonify({'error': "Voting is not allowed outside the election period"}), 204

    real_token = extract_token_from_obfuscated(token_hash)
    if not real_token:
        return jsonify({'error': 'invalid or expired token'}), 403

    candidates = [{'id': c.id, 'name': c.name, 'prenom': getattr(c, 'prenom', ''), 'photo': getattr(c, 'photo', '')} for c in election.candidates]
    return jsonify({'election': {'id': election.id, 'title': election.title}, 'candidates': candidates})


@public_bp.route('/elections/<election_uid>/vote/<token_hash>', methods=['POST'])
def vote_post(election_uid, token_hash):
    data = request.get_json() or {}
    # Vérifier période de l'élection
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    now = datetime.utcnow()
    # Autoriser seulement si (start_at absent ou now >= start_at) ET (end_at absent ou now <= end_at)
    if (election.start_at and now < election.start_at) or (election.end_at and now > election.end_at):
        return jsonify({'error': "Voting is not allowed outside the election period"}), 403

    real_token = extract_token_from_obfuscated(token_hash)
    if not real_token:
        return jsonify({'error': 'invalid or expired token'}), 403

    candidate_id = data.get('candidate_id')
    if not candidate_id:
        return jsonify({'error': 'candidate_id required'}), 400
    candidate = Candidate.query.filter_by(id=candidate_id, election_id=election.id).first()
    if not candidate:
        return jsonify({'error': 'candidate not found for this election'}), 404
    
    vote = Vote(election_id=election.id, candidate_id=candidate_id)
    db.session.add(vote)
    
    vtoken = VoteToken.query.filter_by(token=real_token).first()
    if vtoken:
        db.session.delete(vtoken)

    db.session.commit()
    return jsonify({'message': 'vote recorded'}), 201
