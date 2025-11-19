import os

class Config:
    # By default we use SQLite for local development. To use PostgreSQL,
    # set the environment variable `DATABASE_URL` to a PostgreSQL URI, for example:
    #   postgresql://myuser:mypassword@localhost:5432/electiondb
    # (leave the example commented out here so you can reuse it)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///electionapp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    # Frontend URL used to build public voting links (no trailing slash)
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

    # Mail settings (used by admin token importer to send voting links)
    MAIL_HOST = os.getenv('MAIL_HOST', '')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USER = os.getenv('MAIL_USER', '')
    MAIL_PASS = os.getenv('MAIL_PASS', '')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
    MAIL_FROM = os.getenv('MAIL_FROM', os.getenv('MAIL_USER', 'noreply@example.com'))
    # Admin credentials fallback (for initial setup). Prefer creating Admin rows in DB.
    ADMIN_USER = os.getenv('ADMIN_USER', '')
    ADMIN_PASS = os.getenv('ADMIN_PASS', '')
    # Session / cookie settings
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() in ('1', 'true', 'yes')
    # If frontend is on a different origin and you need cookies included, set to 'None' (requires HTTPS in browsers)
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = int(os.getenv('PERMANENT_SESSION_LIFETIME', '3600'))
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    # JWT settings for admin authentication
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'dev-secret'))
    JWT_EXP_DELTA_SECONDS = int(os.getenv('JWT_EXP_DELTA_SECONDS', '3600'))
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')