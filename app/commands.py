# HRMSV3_optimized/app/commands.py
import click
from flask.cli import with_appcontext
from .models.users import User, Role, insert_initial_roles
from .database import db
from werkzeug.security import generate_password_hash
from datetime import datetime
from .models.employee import Employee

def register_commands(app):
    """Register custom Flask CLI commands."""
    app.cli.add_command(create_admin_command)
    app.cli.add_command(create_roles)
    app.cli.add_command(init_admin)
    app.cli.add_command(reset_db)

@click.command('create-roles')
@with_appcontext
def create_roles():
    """Create initial roles in the database."""
    try:
        insert_initial_roles()
        click.echo('Roles created successfully.')
    except Exception as e:
        click.echo(f'Error creating roles: {e}')

@click.command('create-admin')
@click.option('--username', prompt=True, help='Admin username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--email', prompt=True, help='Admin email')
@with_appcontext
def create_admin_command(username, password, email):
    """Create an admin user."""
    try:
        # Check if user already exists
        user = User.query.filter_by(username=username).first()
        if user:
            click.echo(f'User {username} already exists.')
            return
        
        # Get admin role
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            click.echo('Admin role not found. Creating roles first.')
            insert_initial_roles()
            admin_role = Role.query.filter_by(name='Admin').first()
        
        # Create user
        user = User(username=username, email=email, role=admin_role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f'Admin user {username} created successfully.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating admin user: {e}')

@click.command('init-admin')
@with_appcontext
def init_admin():
    """Initialize admin user and roles."""
    try:
        # Create roles
        insert_initial_roles()
        click.echo('Roles created successfully.')
        
        # Check if admin exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            click.echo('Admin user already exists.')
            return
        
        # Get admin role
        admin_role = Role.query.filter_by(name='Admin').first()
        
        # Create admin user
        admin = User(username='admin', email='admin@example.com', role=admin_role)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        click.echo('Default admin user created with username: admin and password: admin')
        click.echo('IMPORTANT: Change the default password immediately in production!')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error initializing admin: {e}')

@click.command('reset-db')
@click.confirmation_option(prompt='Are you sure you want to reset the database? This will delete all data!')
@with_appcontext
def reset_db():
    """Reset the database and create new tables."""
    try:
        db.drop_all()
        db.create_all()
        insert_initial_roles()
        click.echo('Database has been reset successfully.')
    except Exception as e:
        click.echo(f'Error resetting database: {e}')