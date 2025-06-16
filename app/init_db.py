import os
from app import create_app, db
from app.models.users import User, Role, insert_initial_roles
from werkzeug.security import generate_password_hash

def init_db():
    app = create_app()
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
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
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")

if __name__ == '__main__':
    # Remove the database file if it exists
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'hrms.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Existing database removed.")
    
    init_db() 