"""
Project management module for the HR application.
This module handles project creation, task management, document versioning,
and performance tracking.
"""

from flask import Blueprint

bp = Blueprint('project', __name__)

from . import routes