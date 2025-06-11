# HRMSV3_optimized/app/utils/decorators.py
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from ..exceptions import HRMSError, AuthorizationError, ResourceNotFoundError, ValidationError

def role_required(*roles):
    """Decorator to check if user has any of the required roles."""
    def decorator(view_function):
        @wraps(view_function)
        def decorated_function(*args, **kwargs):
            if not any(current_user.has_role(role) for role in roles):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('core.index'))
            return view_function(*args, **kwargs)
        return decorated_function
    return decorator

def handle_errors(view_function):
    """Decorator to handle common exceptions."""
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        try:
            return view_function(*args, **kwargs)
        except ResourceNotFoundError as e:
            flash(str(e), 'danger')
            return redirect(url_for('core.index'))
        except ValidationError as e:
            flash(str(e), 'danger')
            return redirect(url_for('core.index'))
        except AuthorizationError as e:
            flash(str(e), 'danger')
            return redirect(url_for('core.index'))
        except HRMSError as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('core.index'))
        except Exception as e:
            flash('An unexpected error occurred. Please try again later.', 'danger')
            # Here you might want to log the error
            return redirect(url_for('core.index'))
    return decorated_function