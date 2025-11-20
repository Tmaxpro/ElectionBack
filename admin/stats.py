from flask import jsonify
from . import admin_bp
from models import db, Vote, VoteToken, Candidate, Election
from sqlalchemy import func


@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    elections = Election.query.order_by(Election.created_at.desc()).all()
    stats_list = []
    for e in elections:
        total_voters = db.session.query(func.count(func.distinct(VoteToken.email))).filter(VoteToken.election_id == e.id).scalar() or 0
        total_tokens = db.session.query(func.count(VoteToken.id)).filter(VoteToken.election_id == e.id).scalar() or 0
        votes_cast = db.session.query(func.count(Vote.id)).filter(Vote.election_id == e.id).scalar() or 0
        total_candidates = db.session.query(func.count(Candidate.id)).filter(Candidate.election_id == e.id).scalar() or 0

        participation_rate = 0.0
        if total_voters:
            participation_rate = float(votes_cast) / float(total_voters)

        stats_list.append({
            'election_uid': e.uid,
            'title': e.title,
            'total_voters': int(total_voters),
            'total_tokens': int(total_tokens),
            'votes_cast': int(votes_cast),
            'total_candidates': int(total_candidates),
            'participation_rate': participation_rate
        })

    return jsonify(stats_list), 200


@admin_bp.route('/elections/<election_uid>/votants', methods=['GET'])
def list_voters(election_uid):
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    voters = VoteToken.query.filter_by(election_id=election.id).all()
    result = []
    for v in voters:
        result.append({'email': v.email, 'token': v.token, 'is_active': v.is_active})
    return jsonify(result)

@admin_bp.route('/elections/<election_uid>/votants/<email>', methods=['DELETE'])
def delete_voters(election_uid, email):
    """
    Delete a vote token by its token string for the specified election.
    """
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    vtoken = VoteToken.query.filter_by(email=email, election_id=election.id).first()
    if not vtoken:
        return jsonify({'error': 'token not found for this election'}), 404

    db.session.delete(vtoken)
    db.session.commit()
    return jsonify({'message': 'Token deleted'}), 200
