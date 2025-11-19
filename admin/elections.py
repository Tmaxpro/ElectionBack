from flask import jsonify, request
from datetime import datetime
from . import admin_bp
from models import db, Election, Candidate


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
    start_at = data.get('start_datetime', False)
    end_at = data.get('end_datetime', False)
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
            else:
                name = cand
                prenom = ''
            c = Candidate(name=name, prenom=prenom, election_id=election.id)
            db.session.add(c)
    db.session.commit()
    return jsonify({'uid': election.uid, 'title': election.title}), 201


@admin_bp.route('/elections/<election_uid>/candidates', methods=['POST'])
def create_candidate(election_uid):
    data = request.get_json() or {}
    name = data.get('name')
    prenom = data.get('prenom', '')
    if not name:
        return jsonify({'error': 'name required'}), 400
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    # Bloquer la création de candidat si l'élection est en cours
    now = datetime.utcnow()
    if election.start_at and election.end_at and election.start_at <= now <= election.end_at:
        return jsonify({'error': "Cannot add candidate while election is in progress"}), 403
    c = Candidate(name=name, prenom=prenom, election_id=election.id)
    db.session.add(c)
    db.session.commit()
    return jsonify({'uid': c.uid, 'name': c.name, 'prenom': c.prenom}), 201

@admin_bp.route('/elections/<election_uid>/candidates', methods=['GET'])
def list_candidates(election_uid):
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    candidates = []
    for candidate in election.candidates:
        candidates.append({
            'uid': candidate.uid,
            'name': candidate.name,
            'prenom': getattr(candidate, 'prenom', ''),
            'photo': getattr(candidate, 'photo', '')
        })
    return jsonify(candidates)


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
