"""
Employee blueprint for the HRMS application.
Handles employee management, profiles, and HR operations.
"""

from flask import Blueprint

bp = Blueprint('employee', __name__)

from . import routes 