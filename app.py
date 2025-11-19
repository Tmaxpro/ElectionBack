from flask import Flask, jsonify
from flask import request
# Load environment variables from a local .env file so Config reads them via os.getenv
from dotenv import load_dotenv
load_dotenv()
from config import Config
from models import db
from flask_migrate import Migrate
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    Migrate(app, db)

    # Configure CORS to allow the configured frontend origin and support cookies (credentials).
    # Use the configured `FRONTEND_URL` so the browser accepts cookies (credentials must have a concrete origin).
    frontend_origin = app.config.get('FRONTEND_TEST_URL')
    if frontend_origin:
        CORS(app, resources={r"/api/*": {"origins": frontend_origin}}, supports_credentials=True)
    else:
        # Fallback to enabling CORS for all origins if FRONTEND_URL is not set."""
        CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # simple root
    @app.route('/')
    def index():
        return jsonify({'message': 'ElectionApp Backend running'})

    # Debug: list registered routes (development helper)
    @app.route('/debug/routes')
    def debug_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({'endpoint': rule.endpoint, 'methods': sorted(list(rule.methods)), 'rule': str(rule)})
        return jsonify({'routes': routes})

    # Debug: echo request headers to help diagnose missing Authorization header
    @app.route('/debug/request-headers', methods=['GET', 'POST', 'OPTIONS'])
    def debug_request_headers():
        # Return headers as a simple dict (values may be lists or single strings)
        headers = {k: v for k, v in request.headers.items()}
        return jsonify({'headers': headers})

    from admin import admin_bp
    from public import public_bp

    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')
    app.register_blueprint(public_bp, url_prefix='/api/v1')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

# Expose module-level `app` so `flask run` can discover the application
# when the CLI imports this module. This ensures the registered routes
# (including `/debug/routes` and `/api/v1/admin/...`) are available.
app = create_app()
