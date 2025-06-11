"""
Authentication blueprint for the HRMS application.
Handles login, logout, registration, and user management.
"""

from flask import Blueprint

bp = Blueprint('auth', __name__)

from . import routes 