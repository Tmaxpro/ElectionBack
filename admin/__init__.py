
from flask import Blueprint

# Define the admin blueprint without an internal url_prefix.
# The application will register it under `/api/v1/admin` so final
# routes become `/api/v1/admin/...`.
admin_bp = Blueprint('admin', __name__)

# import submodules to register routes on the blueprint
from . import auth, elections, tokens  # noqa: F401
