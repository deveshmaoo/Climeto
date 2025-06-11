# HRMSV3_optimized/app/models/attendance.py
from datetime import datetime, time
from ..database import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    in_time = db.Column(db.Time, nullable=False)
    out_time = db.Column(db.Time)
    status = db.Column(db.String(20), default='Present')  # Present, Late, Absent, Half-Day, Partial
    deduction_hours = db.Column(db.Float, default=0.0)
    partial_leave_start = db.Column(db.Time)  # For tracking partial day leave start
    partial_leave_end = db.Column(db.Time)    # For tracking partial day leave end
    partial_leave_reason = db.Column(db.String(200))  # Reason for partial leave
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    employee = db.relationship('Employee', back_populates='attendance_records')

    def __repr__(self):
        return f'<Attendance {self.employee.first_name} {self.date}>'

    def calculate_hours_worked(self):
        """Calculate total hours worked in a day, accounting for partial leaves."""
        if not self.out_time:
            return 0
            
        total_seconds = (
            datetime.combine(self.date, self.out_time) - 
            datetime.combine(self.date, self.in_time)
        ).total_seconds()
        
        # Subtract partial leave duration if exists
        if self.partial_leave_start and self.partial_leave_end:
            leave_seconds = (
                datetime.combine(self.date, self.partial_leave_end) - 
                datetime.combine(self.date, self.partial_leave_start)
            ).total_seconds()
            total_seconds -= leave_seconds
            
        return round(total_seconds / 3600, 2)  # Convert to hours

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