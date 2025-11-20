from app import create_app
from models import db, Admin
from werkzeug.security import generate_password_hash

app = create_app()

username = app.config.get('ADMIN_USER')
password = app.config.get('ADMIN_PASS')
with app.app_context():
    a = Admin(username=username, password_hash=generate_password_hash(password))
    db.session.add(a)
    db.session.commit()

    
"""
with app.app_context():
    a = Admin.query.filter_by(username=username).first()
    db.session.delete(a)
    db.session.commit()
"""