"""
Authentication routes for the HRMS application.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime
from . import bp
from .forms import LoginForm, CreateUserForm, EditUserForm
from ..models.users import User, Role
from ..models.employee import Employee
from ..database import db
from ..utils.decorators import role_required

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by email first, then by username
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            user = User.query.filter_by(username=form.email.data).first()
        
        if user and user.check_password(form.password.data) and user.is_active:
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('core.dashboard'))
        else:
            flash('Invalid email/username or password, or account is inactive', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/create-user', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def create_user():
    """Create a new user account."""
    form = CreateUserForm()
    
    # Populate role choices
    form.role.choices = [(role.id, role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists.', 'error')
            return render_template('auth/create_user.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'error')
            return render_template('auth/create_user.html', form=form)
        
        try:
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                role_id=form.role.data,
                department=form.department.data,
                is_active=form.is_active.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.flush()  # Flush to get user.id
            
            # Create associated employee record
            employee = Employee(
                user_id=user.id,
                employee_id=f"EMP{user.id:04d}",
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                work_email=form.email.data,
                department=form.department.data,
                designation=form.position.data,
                joining_date=datetime.utcnow().date()
            )
            
            db.session.add(employee)
            db.session.commit()
            
            flash(f'User {user.username} and employee record created successfully!', 'success')
            return redirect(url_for('auth.manage_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
            return render_template('auth/create_user.html', form=form)
    
    return render_template('auth/create_user.html', form=form)

@bp.route('/manage-users')
@login_required
@role_required('Admin', 'HR')
def manage_users():
    """Manage users page."""
    users = User.query.all()
    return render_template('auth/manage_users.html', users=users)

@bp.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def edit_user(user_id):
    """Edit a user account."""
    user = User.query.get_or_404(user_id)
    
    # Check if current user can edit target user
    if not current_user.can_edit_user(user):
        flash('You do not have permission to edit this user.', 'error')
        return redirect(url_for('auth.manage_users'))
    
    form = EditUserForm(obj=user)
    
    # Populate role choices
    form.role.choices = [(role.id, role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        # Check if username or email already exists (excluding current user)
        if User.query.filter(User.username == form.username.data, User.id != user_id).first():
            flash('Username already exists.', 'error')
            return render_template('auth/edit_user.html', form=form, user=user)
        
        if User.query.filter(User.email == form.email.data, User.id != user_id).first():
            flash('Email already exists.', 'error')
            return render_template('auth/edit_user.html', form=form, user=user)
        
        # Update user
        user.username = form.username.data
        user.email = form.email.data
        user.role_id = form.role.data
        user.department = form.department.data
        user.is_active = form.is_active.data
        
        db.session.commit()
        
        flash(f'User {user.username} updated successfully!', 'success')
        return redirect(url_for('auth.manage_users'))
    
    return render_template('auth/edit_user.html', form=form, user=user)

@bp.route('/deactivate-user/<int:user_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def deactivate_user(user_id):
    """Deactivate a user account."""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('auth.manage_users'))
    
    # Check if current user can edit target user
    if not current_user.can_edit_user(user):
        flash('You do not have permission to deactivate this user.', 'error')
        return redirect(url_for('auth.manage_users'))
    
    user.is_active = False
    db.session.commit()
    
    flash(f'User {user.username} deactivated successfully!', 'success')
    return redirect(url_for('auth.manage_users'))

@bp.route('/activate-user/<int:user_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def activate_user(user_id):
    """Activate a user account."""
    user = User.query.get_or_404(user_id)
    
    # Check if current user can edit target user
    if not current_user.can_edit_user(user):
        flash('You do not have permission to activate this user.', 'error')
        return redirect(url_for('auth.manage_users'))
    
    user.is_active = True
    db.session.commit()
    
    flash(f'User {user.username} activated successfully!', 'success')
    return redirect(url_for('auth.manage_users'))

@bp.route('/reset-password/<int:user_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def reset_password(user_id):
    """Reset user password."""
    user = User.query.get_or_404(user_id)
    
    # Check if current user can reset target user's password
    if not current_user.can_reset_password(user):
        flash('You do not have permission to reset this user\'s password.', 'error')
        return redirect(url_for('auth.manage_users'))
    
    # Generate temporary password
    temp_password = 'TempPass123!'
    user.set_password(temp_password)
    db.session.commit()
    
    flash(f'Password reset for {user.username}. Temporary password: {temp_password}', 'info')
    return redirect(url_for('auth.manage_users'))

@bp.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def register():
    """User registration route for Admin/HR to create new users."""
    return redirect(url_for('auth.create_user'))

@bp.route('/public-register', methods=['GET', 'POST'])
def public_register():
    """Public registration route - disabled for security."""
    flash('Public user registration is disabled. Please contact your administrator.', 'info')
    return redirect(url_for('auth.login')) 