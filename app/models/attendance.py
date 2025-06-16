# HRMSV3_optimized/app/models/attendance.py
from datetime import datetime, time
from ..database import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Present')  # Present, Late, Early Leave, Absent
    work_mode = db.Column(db.String(20), default='Office')  # Office, Remote
    
    # Clock in details
    clock_in_ip = db.Column(db.String(50))
    clock_in_device = db.Column(db.String(100))
    clock_in_location = db.Column(db.String(200))
    
    # Clock out details
    clock_out_ip = db.Column(db.String(50))
    clock_out_device = db.Column(db.String(100))
    clock_out_location = db.Column(db.String(200))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', back_populates='attendance')
    
    @property
    def total_hours(self):
        """Calculate total hours worked"""
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            return round(duration.total_seconds() / 3600, 2)
        return 0
    
    @property
    def is_early_leave(self):
        """Check if employee left early"""
        if self.clock_out:
            return self.clock_out.time() < time(18, 0)  # Before 6 PM
        return False
    
    @classmethod
    def get_employee_attendance(cls, employee_id, start_date, end_date):
        """Get attendance records for an employee within a date range"""
        return cls.query.filter(
            cls.employee_id == employee_id,
            cls.date >= start_date,
            cls.date <= end_date
        ).order_by(cls.date.desc()).all()
    
    @classmethod
    def get_department_attendance(cls, department, date):
        """Get attendance records for a department on a specific date"""
        return cls.query.join(cls.employee).filter(
            cls.employee.has(department=department),
            cls.date == date
        ).all()

class SalaryDetail(db.Model):
    __tablename__ = 'salary_details'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    allowances = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    effective_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # Null if current
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    employee = db.relationship('Employee', back_populates='salary_history')

class AttendanceSetting(db.Model):
    __tablename__ = 'attendance_settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_type = db.Column(db.String(50), nullable=False)  # e.g., 'allowed_ip', 'allowed_location'
    value = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AttendanceSetting {self.setting_type}: {self.value}>'