# HRMSV3_optimized/app/__init__.py

from flask import Flask, render_template, request
from .config import config_by_name, get_config_name
import os

# Import extensions
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .commands import register_commands
from .config import Config
from .database import db, migrate, login_manager
from .utils.logger import setup_logger

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
    from .models import users, project, hr

    register_commands(app) # Register CLI commands
    
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
    
    # Create database tables
    with app.app_context():
        db.create_all()
        from .models.users import insert_initial_roles
        insert_initial_roles()
    
    return app