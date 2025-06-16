# HRMSV3_optimized/app/__init__.py

from flask import Flask, render_template, request
from .config import config_by_name, get_config_name
import os
from datetime import datetime

# Import extensions
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .commands import register_commands
from .config import Config
from .database import db, migrate, login_manager
from .utils.logger import setup_logger
from .utils.module_permissions import get_accessible_modules, module_required
from .utils.timezone import to_ist
from app.models.employee import Employee
from app.models.users import User, Role, insert_initial_roles
from werkzeug.security import generate_password_hash

# Initialize CSRF protection
csrf = CSRFProtect()

def create_app(config_class=Config):
    """
    Application factory function.
    Creates and configures the Flask application instance.
    """
    app = Flask(__name__)
    
    config_name = get_config_name()
    app.config.from_object(config_by_name[config_name])

    # Initialize Flask extensions with the app instance here
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Initialize CSRF protection and error handler
    csrf.init_app(app)

    @app.errorhandler(400)
    def handle_csrf_error(e):
        app.logger.error(f'CSRF Error: {e.description}')
        app.logger.error(f'Request Method: {request.method}')
        app.logger.error(f'Request Headers: {dict(request.headers)}')
        app.logger.error(f'Request Form Data: {request.form}')
        return render_template('errors/403.html', reason=str(e.description)), 400

    # Configure logging
    setup_logger(app)

    # Import models here so that Flask-Migrate can detect them
    from .models import users, project, hr, employee, attendance, notifications

    register_commands(app) # Register CLI commands
    
    # Initialize notification scheduler
    from .services.notification_scheduler import notification_scheduler
    notification_scheduler.init_app(app)
    
    # Configure upload folder
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from .core import bp as core_bp
    app.register_blueprint(core_bp)
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from .employee import bp as employee_bp
    app.register_blueprint(employee_bp, url_prefix='/employee')
    from .project import bp as project_bp
    app.register_blueprint(project_bp, url_prefix='/project')
    from .sales import bp as sales_bp
    app.register_blueprint(sales_bp, url_prefix='/sales')
    from .hr import bp as hr_bp
    app.register_blueprint(hr_bp, url_prefix='/hr')

    @app.route('/hello') # Keep this for now to test app is running
    def hello():
        return "Hello, HR App with DB setup!"

    @app.route('/health')
    def health_check():
        """Health check endpoint for deployment monitoring."""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            return {"status": "healthy", "database": "connected"}, 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}, 500

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.error(f'Page not found: {error}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.error(f'Forbidden access: {error}')
        app.logger.error(f'Request Method: {request.method}')
        app.logger.error(f'Request Headers: {dict(request.headers)}')
        return render_template('errors/403.html', reason=str(error)), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500
    
    # Create database tables and initial data
    with app.app_context():
        try:
            db.create_all()
            
            # Insert initial roles
            insert_initial_roles()
            
            # Create admin role if it doesn't exist
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                admin_role = Role(name='Admin', description='System administrator access')
                db.session.add(admin_role)
                db.session.commit()
            
            # Create admin user if it doesn't exist
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash=generate_password_hash('admin123'),
                    role=admin_role,
                    is_active=True,
                    department='Management'
                )
                db.session.add(admin)
                db.session.commit()
                app.logger.info("Admin user created successfully")
            
            # Create admin employee if it doesn't exist
            admin_employee = Employee.query.filter_by(email='admin@example.com').first()
            if not admin_employee:
                admin_employee = Employee(
                    email='admin@example.com',
                    first_name='Admin',
                    last_name='User',
                    department='Management',
                    position='Administrator',
                    role='Admin',
                    employee_id='EMP001',
                    designation='Director',
                    joining_date=datetime.utcnow().date(),
                    work_email='admin@example.com',
                    is_active=True,
                    employment_status='Active'
                )
                db.session.add(admin_employee)
                db.session.commit()
                
                # Link user and employee
                admin.user_id = admin_employee.id
                db.session.commit()
                app.logger.info("Admin employee created and linked successfully")
            
            app.logger.info("Database initialization completed successfully")
            
        except Exception as e:
            app.logger.error(f"Error during database initialization: {e}")
            # Don't fail the app startup for database issues in production
            pass
    
    # Add template context processor for module permissions
    @app.context_processor
    def inject_modules():
        return dict(get_accessible_modules=get_accessible_modules)
    
    # Register custom template filters
    app.jinja_env.filters['to_ist'] = to_ist
    
    return app