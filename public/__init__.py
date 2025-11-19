from flask import Blueprint

public_bp = Blueprint('public', __name__)

from . import vote  # noqa: F401
