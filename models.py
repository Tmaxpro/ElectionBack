from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid
from flask import current_app as app

db = SQLAlchemy()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Public unique identifier (non-sequential) for safer external URLs
    uid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(140), nullable=False)
    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    candidates = db.relationship('Candidate', backref='election', lazy=True)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Public unique identifier (non-sequential) for safer external URLs
    uid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    prenom = db.Column(db.String(65), nullable=False)
    photo = db.Column(db.String(255), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    votes = db.relationship('Vote', backref='candidate', lazy=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    #user_id = db.Column(db.Integer, nullable=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VoteToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=False, nullable=False)
    token = db.Column(db.String(36), unique=True, nullable=False)

    def __init__(self, *args, **kwargs):
        """Gérer l'unicité"""
        super().__init__(*args, **kwargs)
        if not self.token:
            self.token = self._generate_unique_uuid()

    def _generate_unique_uuid(self):
        """Génère un UUID unique, retry"""
        while True:
            candidate = str(uuid.uuid4())
            if not VoteToken.query.filter_by(token=candidate).first():
                return candidate

    def __repr__(self):
        return f"<VoteToken {self.token}>"


class TokenBlocklist(db.Model):
    """Store revoked JWT `jti` values so tokens can be invalidated server-side.

    Simple blocklist model storing the token identifier (jti), token type
    (access or refresh), optional admin id for auditing, and revocation time.
    """
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), unique=True, nullable=False)
    token_type = db.Column(db.String(20), nullable=False)
    admin_id = db.Column(db.Integer, nullable=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def is_blocked(cls, jti: str) -> bool:
        if not jti:
            return False
        return cls.query.filter_by(jti=jti).first() is not None

    def __repr__(self):
        return f"<TokenBlocklist {self.jti} type={self.token_type}>"