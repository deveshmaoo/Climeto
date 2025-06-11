from flask import Blueprint

bp = Blueprint('hr', __name__, url_prefix='/hr')

from . import routes 