from flask import jsonify, request, current_app, url_for
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, date
from . import admin_bp
from models import db, Election, Candidate, Vote, VoteToken
from sqlalchemy import func

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _parse_datetime(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        # if date, convert to datetime at midnight
        return val if isinstance(val, datetime) else datetime(val.year, val.month, val.day)
    # essayer ISO / "YYYY-MM-DD HH:MM:SS"
    try:
        return datetime.fromisoformat(val)
    except Exception:
        try:
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        except Exception:
            raise ValueError(f"Invalid datetime format: {val}")


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


@admin_bp.route('/elections/<election_uid>/candidates', methods=['POST'])
def create_candidate(election_uid):
    # Support multipart/form-data uploads (photo file) and fallback to JSON
    photo = ''
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        name = request.form.get('name')
        prenom = request.form.get('prenom', '')
        file = request.files.get('photo')
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({'error': 'invalid file type'}), 400
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            new_filename = f"{uuid.uuid4()}.{ext}"
            upload_folder = os.path.join(current_app.root_path, 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, new_filename)
            file.save(file_path)
            # Build a public URL for the uploaded file. The application provides
            # an `/uploads/<filename>` route named `uploaded_file` (see app.py).
            photo = url_for('uploaded_file', filename=new_filename, _external=True)
        else:
            # allow photo to be provided as form field containing a URL or path
            photo = request.form.get('photo', '')
    else:
        data = request.get_json() or {}
        name = data.get('name')
        prenom = data.get('prenom', '')
        photo = data.get('photo', '')

    if not name:
        return jsonify({'error': 'name required'}), 400
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    # Bloquer la création de candidat si l'élection est en cours
    now = datetime.utcnow()
    if election.start_at and election.end_at and election.start_at <= now <= election.end_at:
        return jsonify({'error': "Cannot add candidate while election is in progress"}), 403
    c = Candidate(name=name, prenom=prenom, election_id=election.id, photo=photo)
    db.session.add(c)
    db.session.commit()
    return jsonify({'uid': c.uid, 'name': c.name, 'prenom': c.prenom}), 201

@admin_bp.route('/elections/<election_uid>/candidates/<candidate_uid>', methods=['DELETE'])
def delete_candidate(election_uid, candidate_uid):
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    candidate = Candidate.query.filter_by(uid=candidate_uid, election_id=election.id).first_or_404()
    # Bloquer la suppression de candidat si l'élection est en cours
    now = datetime.utcnow()
    if election.start_at and election.end_at and election.start_at <= now <= election.end_at:
        return jsonify({'error': "Cannot delete candidate while election is in progress"}), 403
    db.session.delete(candidate)
    db.session.commit()
    return jsonify({'message': 'Candidate deleted'}), 200

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
        result.append({'email': v.email, 'token': v.token})
    return jsonify(result)
