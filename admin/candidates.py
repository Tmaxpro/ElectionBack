import logging

# module-level logger
log = logging.getLogger(__name__)
from flask import jsonify, request, current_app, url_for
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from . import admin_bp
from models import db, Candidate, Election
from .utils import allowed_file


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
            log.info(f"Uploaded candidate photo saved to {file_path}, accessible at {photo}")
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


@admin_bp.route('/elections/<election_uid>/candidates/<candidate_uid>', methods=['PUT', 'PATCH'])
def update_candidate(election_uid, candidate_uid):
    election = Election.query.filter_by(uid=election_uid).first_or_404()
    candidate = Candidate.query.filter_by(uid=candidate_uid, election_id=election.id).first_or_404()
    data = request.get_json(silent=True) or {}

    # Bloquer la modification de candidat si l'élection est en cours
    now = datetime.utcnow()
    if election.start_at and election.end_at and election.start_at <= now <= election.end_at:
        return jsonify({'error': "Cannot update candidate while election is in progress"}), 403

    # Support both `multipart/form-data` (file upload + form fields) and JSON body
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        form = request.form
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
            photo_url = url_for('uploaded_file', filename=new_filename, _external=True)
            log.info(f"Uploaded candidate photo saved to {file_path}, accessible at {photo_url}")
            candidate.photo = photo_url
        else:
            # allow photo to be provided as form field containing a URL or path
            photo_field = form.get('photo', '')
            if photo_field:
                candidate.photo = photo_field

        # Update name/prenom from form if provided
        name = form.get('name', None)
        prenom = form.get('prenom', None)
        if name:
            candidate.name = name
        if prenom is not None:
            candidate.prenom = prenom
    else:
        # JSON payload
        name = data.get('name', None)
        prenom = data.get('prenom', None)
        photo_field = data.get('photo', '')
        if name:
            candidate.name = name
        if prenom is not None:
            candidate.prenom = prenom
        if photo_field:
            candidate.photo = photo_field

    db.session.commit()
    return jsonify({'uid': candidate.uid, 'name': candidate.name, 'prenom': candidate.prenom, 'photo': candidate.photo}), 200

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