from flask import jsonify, request, redirect
from . import public_bp
from models import Election, Candidate, Vote, VoteToken
from utils import extract_token_from_obfuscated
from models import db


@public_bp.route('/elections/<int:election_id>/vote/<token_hash>', methods=['GET'])
def vote_get(election_id, token_hash):
    if not token_hash:
        return redirect('/')
    real_token = extract_token_from_obfuscated(token_hash)
    if not real_token:
        return jsonify({'error': 'invalid or expired token'}), 403

    election = Election.query.get_or_404(election_id)
    candidates = [{'id': c.id, 'name': c.name, 'prenom': getattr(c, 'prenom', ''), 'photo': getattr(c, 'photo', '')} for c in election.candidates]
    return jsonify({'election': {'id': election.id, 'title': election.title}, 'candidates': candidates})


@public_bp.route('/elections/<int:election_id>/vote/<token_hash>', methods=['POST'])
def vote_post(election_id, token_hash):
    data = request.get_json() or {}
    real_token = extract_token_from_obfuscated(token_hash)
    if not real_token:
        return jsonify({'error': 'invalid or expired token'}), 403

    candidate_id = data.get('candidate_id')
    if not candidate_id:
        return jsonify({'error': 'candidate_id required'}), 400
    candidate = Candidate.query.filter_by(id=candidate_id, election_id=election_id).first()
    if not candidate:
        return jsonify({'error': 'candidate not found for this election'}), 404
    
    vote = Vote(election_id=election_id, candidate_id=candidate_id)
    db.session.add(vote)
    
    vtoken = VoteToken.query.filter_by(token=real_token).first()
    if vtoken:
        db.session.delete(vtoken)

    db.session.commit()
    return jsonify({'message': 'vote recorded'}), 201
