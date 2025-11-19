from app import create_app
from models import db, Admin
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    a = Admin(username='admin', password_hash=generate_password_hash('admin'))
    db.session.add(a)
    db.session.commit()

    
"""
with app.app_context():
    a = Admin.query.filter_by(username='admin').first()
    db.session.delete(a)
    db.session.commit()
"""