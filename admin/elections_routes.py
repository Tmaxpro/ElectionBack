from flask import jsonify, request
from datetime import datetime
from . import admin_bp
from models import db, Election, Candidate
from .utils import _parse_datetime


@admin_bp.route('/elections', methods=['GET'])
def list_elections():
    elections = Election.query.all()
    result = []
    for e in elections:
        result.append({'uid': e.uid, 'title': e.title, 'start_at': e.start_at, 'end_at': e.end_at})
    return jsonify(result)


@admin_bp.route('/elections', methods=['POST'])
def create_election():
    data = request.get_json() or {}
    title = data.get('title')
    candidates = data.get('candidates', [])
    try:
        start_at = _parse_datetime(data.get('start_at', False))
        end_at = _parse_datetime(data.get('end_at', False))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    if not title:
        return jsonify({'error': 'title is required'}), 400
    election = Election(title=title, start_at=start_at, end_at=end_at)
    db.session.add(election)
    db.session.flush()
    if candidates:
        for cand in candidates:
            if isinstance(cand, dict):
                name = cand.get('name')
                prenom = cand.get('prenom', '')
                photo = cand.get('photo', '')
            else:
                name = cand
                prenom = ''
                photo = ''
            c = Candidate(name=name, prenom=prenom, election_id=election.id, photo=photo)
            db.session.add(c)
    db.session.commit()
    return jsonify({'uid': election.uid, 'title': election.title}), 201


@admin_bp.route('/elections/<election_uid>', methods=['DELETE'])
def delete_election(election_uid):
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    db.session.delete(election)
    db.session.commit()
    return jsonify({'message': 'Election deleted'}), 200


@admin_bp.route('/elections/<election_uid>', methods=['PUT', 'PATCH'])
def update_election(election_uid):
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    data = request.get_json() or {}
    title = data.get('title', None)
    start_at = data.get('start_at', None)
    end_at = data.get('end_at', None)

    try:
        if start_at is not None:
            start_at = _parse_datetime(start_at)
        if end_at is not None:
            end_at = _parse_datetime(end_at)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if title:
        election.title = title
    if start_at is not None:
        election.start_at = start_at
    if end_at is not None:
        election.end_at = end_at

    db.session.commit()
    return jsonify({'uid': election.uid, 'title': election.title, 'start_at': election.start_at, 'end_at': election.end_at}), 200


@admin_bp.route('/elections/<election_uid>/results', methods=['GET'])
def results(election_uid):
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    results = []
    for candidate in election.candidates:
        vote_count = candidate.votes and len(candidate.votes) or 0
        results.append({
            'candidate_uid': candidate.uid,
            'name': candidate.name,
            'prenom': getattr(candidate, 'prenom', ''),
            'photo': getattr(candidate, 'photo', ''),
            'vote_count': vote_count
        })
    return jsonify({
        'election': {'uid': election.uid, 'title': election.title},
        'results': results
    })
