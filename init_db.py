#!/usr/bin/env python3
"""Database initialization script for production deployment."""

from app import create_app, db
from app.models.users import User, Role, insert_initial_roles
from app.models.employee import Employee

def init_database():
    """Initialize database with admin user."""
    app = create_app()
    with app.app_context():
        try:
            print("🔄 Creating database tables...")
            db.create_all()
            
            print("🔄 Creating initial roles...")
            insert_initial_roles()
            
            print("🔄 Checking for admin user...")
            if not User.query.filter_by(username='admin').first():
                print("🔄 Creating admin user...")
                admin_role = Role.query.filter_by(name='Admin').first()
                
                # Create admin user
                admin_user = User(username='admin', email='admin@company.com', role=admin_role)
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                
                # Create admin employee
                admin_employee = Employee(
                    first_name='Admin',
                    last_name='User',
                    email='admin@company.com',
                    department='Management',
                    role='Admin',
                    employment_status='Active'
                )
                db.session.add(admin_employee)
                db.session.commit()
                
                # Link user to employee
                admin_user.employee_id = admin_employee.id
                db.session.commit()
                
                print("✅ Admin user created successfully!")
                print("   Username: admin")
                print("   Password: admin123")
            else:
                print("✅ Admin user already exists")
                
            print("✅ Database initialization completed!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    init_database() 