"""
Employee routes for the HRMS application.
"""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import bp
from ..models.employee import Employee
from ..database import db

@bp.route('/profile')
@login_required
def profile():
    """Employee profile route."""
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    return render_template('employee/profile.html', employee=employee)

@bp.route('/list')
@login_required
def list_employees():
    """List all employees route."""
    employees = Employee.query.all()
    return render_template('employee/list.html', employees=employees)

@bp.route('/attendance')
@login_required
def attendance():
    """Employee attendance route."""
    return render_template('employee/attendance.html') 