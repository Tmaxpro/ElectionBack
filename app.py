from flask import Flask, jsonify, request, send_from_directory
import os
# Load environment variables from a local .env file so Config reads them via os.getenv
from dotenv import load_dotenv
load_dotenv()
from config import Config
from models import db
from extensions import socketio
from flask_migrate import Migrate
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Configure upload folder (default: project/uploads) and ensure it exists
    app.config.setdefault('UPLOAD_FOLDER', os.path.join(app.root_path, 'uploads'))
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)
    socketio.init_app(app)
    Migrate(app, db)

    # Configure CORS to allow the configured frontend origin and support cookies (credentials).
    # Use the configured `FRONTEND_URL` so the browser accepts cookies (credentials must have a concrete origin).
    frontend_origin = app.config.get('FRONTEND_TEST_URL')
    #if frontend_origin:
        #CORS(app, resources={r"/api/*": {"origins": frontend_origin}}, supports_credentials=True)
    #else:
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

    # Serve uploaded files from the configured upload folder.
    # Endpoint name `uploaded_file` allows `url_for('uploaded_file', filename=...)` calls.
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    from admin import admin_bp
    from public import public_bp

    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')
    app.register_blueprint(public_bp, url_prefix='/api/v1')

    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

# Expose module-level `app` so `flask run` can discover the application
# when the CLI imports this module. This ensures the registered routes
# (including `/debug/routes` and `/api/v1/admin/...`) are available.
app = create_app()
