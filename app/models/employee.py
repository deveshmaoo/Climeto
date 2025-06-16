# HRMSV3_optimized/app/models/employee.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from ..database import db
from .users import User

class Employee(UserMixin, db.Model):
    __tablename__ = 'employees'

    # Management and Regular Employee Types
    MANAGEMENT_ROLES = ['Director', 'Country Head', 'General Manager', 'Department Manager']
    
    # Hierarchy Levels (in descending order)
    HIERARCHY_LEVELS = {
        'Director': 10,
        'Country Head': 9,
        'General Manager': 8,
        'Department Manager': 7,
        'Team Lead': 6,
        'Senior Executive': 5,
        'Executive': 4,
        'Junior Executive': 3,
        'Special Role': 2,
        'Intern': 1
    }

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50))
    position = db.Column(db.String(50))
    role = db.Column(db.String(20), default='Employee')  # Admin, HR, Management, Employee
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Personal Details
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    marital_status = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    nationality = db.Column(db.String(50))
    personal_email = db.Column(db.String(120), unique=True)
    personal_mobile = db.Column(db.String(20))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(20))
    emergency_contact_name = db.Column(db.String(100))
    
    # Work Details
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    designation = db.Column(db.String(50), nullable=False)
    joining_date = db.Column(db.Date, nullable=False)
    resignation_date = db.Column(db.Date)
    last_working_date = db.Column(db.Date)
    work_email = db.Column(db.String(120), unique=True)
    work_phone = db.Column(db.String(20))
    reporting_manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    is_manager = db.Column(db.Boolean, default=False)
    employment_status = db.Column(db.String(20), default='Active')  # Active, Resigned, Terminated, On Leave
    employment_type = db.Column(db.String(20), default='Full-time')  # Full-time, Part-time, Contract, Intern
    probation_end_date = db.Column(db.Date)
    notice_period_days = db.Column(db.Integer, default=30)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    user = db.relationship('User', back_populates='employee', uselist=False)
    reporting_manager = db.relationship('Employee', remote_side=[id], backref='direct_reports')
    attendance = db.relationship('Attendance', back_populates='employee', lazy='dynamic')
    salary_history = db.relationship('SalaryDetail', back_populates='employee', lazy='dynamic')
    performance_reviews = db.relationship('PerformanceReview', 
                                        foreign_keys='PerformanceReview.employee_id',
                                        backref='employee', lazy='dynamic')
    leaves = db.relationship('Leave', 
                           foreign_keys='Leave.employee_id',
                           backref='employee', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_management(self):
        return self.designation in self.MANAGEMENT_ROLES

    @property
    def hierarchy_level(self):
        return self.HIERARCHY_LEVELS.get(self.designation, 0)

    def can_manage(self, other_employee):
        """Check if this employee can manage another employee based on hierarchy."""
        if self.id == other_employee.id:
            return False
        return self.hierarchy_level > other_employee.hierarchy_level

    def get_current_salary(self):
        """Get the current salary details."""
        from .attendance import SalaryDetail
        return SalaryDetail.query.filter_by(employee_id=self.id, end_date=None).first()

    def get_leave_balance(self, year=None):
        """Get leave balance for the current year or specified year."""
        if year is None:
            year = datetime.now().year
        # Implementation depends on your leave tracking system
        return {'annual': 20, 'sick': 10, 'casual': 5}  # Example

    def __repr__(self):
        return f'<Employee {self.email}>'

class PerformanceReview(db.Model):
    __tablename__ = 'performance_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    review_date = db.Column(db.Date, nullable=False)
    review_period_start = db.Column(db.Date, nullable=False)
    review_period_end = db.Column(db.Date, nullable=False)
    performance_score = db.Column(db.Float)  # Overall score
    strengths = db.Column(db.Text)
    areas_for_improvement = db.Column(db.Text)
    goals_set = db.Column(db.Text)
    comments = db.Column(db.Text)
    status = db.Column(db.String(20), default='Draft')  # Draft, Submitted, Acknowledged, Finalized
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    reviewer = db.relationship('Employee', foreign_keys=[reviewer_id])

class Leave(db.Model):
    __tablename__ = 'leaves'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)  # Annual, Sick, Casual, Unpaid
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Float, nullable=False)  # Can be fractional for half-days
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected, Cancelled
    approved_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    approved_by = db.relationship('Employee', foreign_keys=[approved_by_id])