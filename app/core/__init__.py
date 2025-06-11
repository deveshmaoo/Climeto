"""
Core blueprint for the HRMS application.
Contains the main dashboard and common functionality.
"""

from flask import Blueprint

bp = Blueprint('core', __name__)

from . import routes 