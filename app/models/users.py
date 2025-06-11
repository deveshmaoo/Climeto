# HRMSV3_optimized/app/models/users.py
from ..database import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# The user_loader callback is used to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    department = db.Column(db.String(50))  # New field for department assignment
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_login = db.Column(db.DateTime)
    # role relationship is defined in Role model via backref

    # Department constants
    DEPARTMENTS = [
        'Management',
        'General Manager', 
        'HR',
        'EPR Compliance',
        'Project Development',
        'Digital Marketing',
        'Business Development'
    ]

    def set_password(self, password):
        # Explicitly use pbkdf2:sha256 to avoid scrypt issues on some systems
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_role(self, role_name):
        """Set user role by role name."""
        role = Role.query.filter_by(name=role_name).first()
        if role:
            self.role = role
            db.session.commit()
            return True
        return False

    def has_role(self, role_name):
        """Check if user has a specific role."""
        return self.role and self.role.name == role_name

    def is_admin(self):
        """Check if user is an admin."""
        return self.has_role('Admin')

    def is_management(self):
        """Check if user is management level."""
        return self.has_role('Management') or self.department == 'Management'

    def is_general_manager(self):
        """Check if user is general manager."""
        return self.has_role('General Manager') or self.department == 'General Manager'

    def can_create_users(self):
        """Check if user can create other users (Admin or HR)."""
        return self.role and self.role.name in ['Admin', 'HR']

    def can_view_all_activities(self):
        """Check if user can view all department activities."""
        return self.is_management() or self.is_general_manager() or self.is_admin()

    def can_view_department_activities(self):
        """Check if user can view their department's activities."""
        return (self.has_role('Department Manager') and 
                self.department in ['Business Development', 'Digital Marketing', 'EPR Compliance', 'Project Development'])

    def can_manage_department_funnel(self):
        """Check if user can manage their department's sales funnel."""
        return (self.has_role('Department Manager') and 
                self.department in ['Business Development', 'Digital Marketing']) or self.can_view_all_activities()

    def can_assign_cross_department_tasks(self):
        """Check if user can assign tasks across departments."""
        if self.is_employee and self.employee:
            return self.employee.designation in ['Manager', 'Director', 'General Manager']
        return self.is_management() or self.is_general_manager()

    def can_manage_roles(self):
        """Check if user can manage roles (Admin or HR)."""
        return self.role and self.role.name in ['Admin', 'HR']

    def can_edit_user(self, target_user):
        """Check if current user can edit the target user."""
        # Admin can edit anyone
        if self.is_admin():
            return True
        
        # HR cannot edit Admin, Management, or General Manager users
        if self.has_role('HR'):
            restricted_roles = ['Admin', 'Management', 'General Manager']
            restricted_departments = ['Management', 'General Manager']
            
            if (target_user.role and target_user.role.name in restricted_roles) or \
               (target_user.department in restricted_departments):
                return False
            return True
        
        # Other users cannot edit anyone
        return False

    def can_delete_user(self, target_user):
        """Check if current user can delete the target user."""
        # Only Admin can delete users
        if self.is_admin():
            return True
        
        # HR and others cannot delete users
        return False

    def can_reset_password(self, target_user):
        """Check if current user can reset target user's password."""
        # Admin can reset anyone's password
        if self.is_admin():
            return True
        
        # HR cannot reset password for Admin, Management, or General Manager
        if self.has_role('HR'):
            restricted_roles = ['Admin', 'Management', 'General Manager']
            restricted_departments = ['Management', 'General Manager']
            
            if (target_user.role and target_user.role.name in restricted_roles) or \
               (target_user.department in restricted_departments):
                return False
            return True
        
        return False

    @property
    def is_employee(self):
        """Check if user has an associated employee record."""
        return hasattr(self, 'employee') and self.employee is not None

    @property
    def full_name(self):
        """Get the user's full name from employee record if available."""
        if self.is_employee:
            return f"{self.employee.first_name} {self.employee.last_name}"
        return self.username

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'

def insert_initial_roles():
    roles_data = [
        ('Employee', 'Regular employee access'),
        ('HR', 'Human Resources access'),
        ('Management', 'Management level access'),
        ('General Manager', 'General Manager access'),
        ('Admin', 'System administrator access'),
        ('Department Manager', 'Department manager access'),
        ('Team Lead', 'Team lead access')
    ]
    for r_name, r_desc in roles_data:
        role = Role.query.filter_by(name=r_name).first()
        if role is None:
            role = Role(name=r_name, description=r_desc)
            db.session.add(role)
    db.session.commit()