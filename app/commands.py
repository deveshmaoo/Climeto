# HRMSV3_optimized/app/commands.py
import click
from flask.cli import with_appcontext
from .models.users import User, Role, insert_initial_roles
from .database import db
from werkzeug.security import generate_password_hash
from datetime import datetime
from .models.employee import Employee
from sqlalchemy import text

@click.command("reset-db")
@with_appcontext
def reset_db_command():
    """Drops and recreates the database and stamps it as up-to-date."""
    click.echo("Resetting database...")
    try:
        # Drop alembic_version table if it exists
        with db.engine.connect() as connection:
            connection.execute(text('DROP TABLE IF EXISTS alembic_version;'))
        click.echo("Dropped alembic_version table.")

        # Drop all tables
        db.drop_all()
        click.echo("Dropped all tables.")

        # Create all tables
        db.create_all()
        click.echo("Created all tables.")
        
        # Re-seed initial data
        insert_initial_roles()
        click.echo("Inserted initial roles.")

        click.echo("Database has been reset successfully.")

    except Exception as e:
        click.echo(f"An error occurred: {e}")
        db.session.rollback()

@click.command('create-roles')
@with_appcontext
def create_roles_command():
    """Create initial roles in the database."""
    try:
        insert_initial_roles()
        click.echo('Roles created successfully.')
    except Exception as e:
        click.echo(f'Error creating roles: {e}')

@click.command('create-admin')
@click.option('--username', help='Admin username')
@click.option('--password', help='Admin password')
@click.option('--email', help='Admin email')
@with_appcontext
def create_admin_command(username, password, email):
    """Create an admin user and an associated employee record."""
    try:
        if User.query.filter((User.username == username) | (User.email == email)).first():
            click.echo(f"User with username '{username}' or email '{email}' already exists.")
            return

        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            click.echo("Admin role not found. Please run 'flask create-roles' first.")
            return

        # Create an employee record for the admin user
        employee = Employee(
            first_name=username.capitalize(),
            last_name='Admin',
            email=email,
            work_email=email,
            department='Management',
            position='System Administrator',
            designation='System Administrator',
            role='Admin',
            employee_id=f"ADM{int(datetime.now().timestamp())}",
            joining_date=datetime.utcnow().date(),
            is_active=True,
            employment_status='Active'
        )
        db.session.add(employee)
        db.session.flush()

        user = User(username=username, email=email, role=admin_role)
        user.set_password(password)
        user.employee_id = employee.id
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user '{username}' created successfully and linked to new employee record.")

    except Exception as e:
        db.session.rollback()
        click.echo(f'An error occurred: {e}')

@click.command('init-admin')
@with_appcontext
def init_admin_command():
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

@click.command('delete-user')
@click.option('--username', help='Username of the user to delete')
@with_appcontext
def delete_user_command(username):
    """Deletes a user and their associated employee record from the database."""
    user = User.query.filter_by(username=username).first()
    if user:
        if user.employee:
            db.session.delete(user.employee)
        db.session.delete(user)
        db.session.commit()
        click.echo(f'User {username} and associated employee deleted successfully.')
    else:
        # If user is not found, check for an orphaned employee with the same email.
        # This is because the username and email for the admin are the same in this context.
        employee = Employee.query.filter_by(email=f'{username}@example.com').first()
        if employee:
            db.session.delete(employee)
            db.session.commit()
            click.echo(f"Orphaned employee for {username} deleted.")
        else:
            click.echo(f'User {username} not found.')

def register_commands(app):
    """Register all custom commands."""
    app.cli.add_command(reset_db_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(create_roles_command)
    app.cli.add_command(init_admin_command)
    app.cli.add_command(delete_user_command)