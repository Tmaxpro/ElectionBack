from flask import jsonify, request
from . import admin_bp
from models import db, Election, Candidate


@admin_bp.route('/elections', methods=['GET'])
def list_elections():
    elections = Election.query.all()
    result = []
    for e in elections:
        result.append({'id': e.id, 'title': e.title, 'start_at': e.start_at, 'end_at': e.end_at})
    return jsonify(result)


@admin_bp.route('/elections', methods=['POST'])
def create_election():
    data = request.get_json() or {}
    title = data.get('title')
    candidates = data.get('candidates', [])
    if not title:
        return jsonify({'error': 'title is required'}), 400
    election = Election(title=title)
    db.session.add(election)
    db.session.flush()
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
    return jsonify({'id': election.id, 'title': election.title}), 201


@admin_bp.route('/elections/<int:election_id>/candidates', methods=['POST'])
def create_candidate(election_id):
    data = request.get_json() or {}
    name = data.get('name')
    prenom = data.get('prenom', '')
    if not name:
        return jsonify({'error': 'name required'}), 400
    election = Election.query.get_or_404(election_id)
    c = Candidate(name=name, prenom=prenom, election_id=election.id)
    db.session.add(c)
    db.session.commit()
    return jsonify({'id': c.id, 'name': c.name, 'prenom': c.prenom}), 201


@admin_bp.route('/elections/<int:election_id>/resultats', methods=['GET'])
def results(election_id):
    election = Election.query.get_or_404(election_id)
    results = []
    for candidate in election.candidates:
        vote_count = candidate.votes and len(candidate.votes) or 0
        results.append({
            'candidate_id': candidate.id,
            'name': candidate.name,
            'prenom': getattr(candidate, 'prenom', ''),
            'photo': getattr(candidate, 'photo', ''),
            'vote_count': vote_count
        })
    return jsonify({
        'election': {'id': election.id, 'title': election.title},
        'results': results
    })
