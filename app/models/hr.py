from ..database import db
from datetime import datetime, date

class JobPosting(db.Model):
    __tablename__ = 'job_postings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    salary_range_min = db.Column(db.Float)
    salary_range_max = db.Column(db.Float)
    employment_type = db.Column(db.String(50), default='Full-time')  # Full-time, Part-time, Contract, Intern
    location = db.Column(db.String(200))
    posted_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    application_deadline = db.Column(db.Date)
    status = db.Column(db.String(50), default='Active')  # Active, Closed, On Hold
    openings = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    poster = db.relationship('Employee', foreign_keys=[posted_by])
    applications = db.relationship('JobApplication', backref='job_posting', lazy='dynamic')

class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'), nullable=False)
    applicant_name = db.Column(db.String(200), nullable=False)
    applicant_email = db.Column(db.String(120), nullable=False)
    applicant_phone = db.Column(db.String(20))
    
    # Enhanced resume and document handling
    resume_filename = db.Column(db.String(500))  # Original filename
    resume_path = db.Column(db.String(500))      # Stored file path
    resume_size = db.Column(db.Integer)          # File size in bytes
    cover_letter = db.Column(db.Text)
    portfolio_url = db.Column(db.String(500))    # Portfolio/LinkedIn URL
    
    # Experience and compensation
    experience_years = db.Column(db.Integer)
    current_salary = db.Column(db.Float)
    expected_salary = db.Column(db.Float)
    notice_period = db.Column(db.String(50))
    current_company = db.Column(db.String(200))
    current_position = db.Column(db.String(200))
    
    # Application details
    status = db.Column(db.String(50), default='Applied')  # Applied, Screening, Interview, Rejected, Hired, On Hold
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(100))  # How they found the job (Website, LinkedIn, Referral, etc.)
    
    # Review and processing
    reviewed_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    review_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    hr_rating = db.Column(db.Integer)  # 1-10 scale
    
    # Interview scheduling preferences
    preferred_interview_time = db.Column(db.String(100))  # Morning, Afternoon, Evening
    available_dates = db.Column(db.Text)  # JSON string of available dates
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviewer = db.relationship('Employee', foreign_keys=[reviewed_by])
    interviews = db.relationship('Interview', backref='application', lazy='dynamic')

class Interview(db.Model):
    __tablename__ = 'interviews'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    interview_type = db.Column(db.String(50), nullable=False)  # Phone, Video, In-person, Technical, HR, Panel
    scheduled_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    
    # Primary interviewer (required)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Location and meeting details
    location = db.Column(db.String(200))  # Meeting room or video link
    meeting_link = db.Column(db.String(500))  # Video conference link
    conference_room_id = db.Column(db.Integer, db.ForeignKey('conference_rooms.id'))
    
    # Interview status and results
    status = db.Column(db.String(50), default='Scheduled')  # Scheduled, Completed, Cancelled, Rescheduled, No Show
    feedback = db.Column(db.Text)
    rating = db.Column(db.Integer)  # 1-10 scale
    recommendation = db.Column(db.String(50))  # Hire, Reject, Next Round, On Hold
    
    # Calendar integration
    calendar_event_id = db.Column(db.Integer, db.ForeignKey('calendar_events.id'))  # Link to calendar event
    
    # Scheduling details
    interview_round = db.Column(db.Integer, default=1)  # 1st round, 2nd round, etc.
    preparation_notes = db.Column(db.Text)  # Notes for interviewer preparation
    candidate_instructions = db.Column(db.Text)  # Instructions sent to candidate
    
    # Rescheduling tracking
    original_date = db.Column(db.DateTime)  # Original scheduled date if rescheduled
    reschedule_reason = db.Column(db.Text)
    reschedule_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interviewer = db.relationship('Employee', foreign_keys=[interviewer_id])
    conference_room = db.relationship('ConferenceRoom', foreign_keys=[conference_room_id])
    calendar_event = db.relationship('CalendarEvent', foreign_keys=[calendar_event_id])
    participants = db.relationship('InterviewParticipant', backref='interview', lazy='dynamic', cascade='all, delete-orphan')

class InterviewParticipant(db.Model):
    """Additional participants in an interview (for panel interviews)"""
    __tablename__ = 'interview_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    role = db.Column(db.String(50), default='Interviewer')  # Interviewer, Observer, Technical Expert, HR Representative
    is_required = db.Column(db.Boolean, default=True)  # Whether this person's presence is required
    response = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Declined
    response_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Individual feedback from this participant
    individual_rating = db.Column(db.Integer)  # 1-10 scale
    individual_feedback = db.Column(db.Text)
    individual_recommendation = db.Column(db.String(50))  # Hire, Reject, Next Round
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='interview_participations')

class Salary(db.Model):
    __tablename__ = 'salaries'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    hra = db.Column(db.Float, default=0)  # House Rent Allowance
    transport_allowance = db.Column(db.Float, default=0)
    medical_allowance = db.Column(db.Float, default=0)
    special_allowance = db.Column(db.Float, default=0)
    bonus = db.Column(db.Float, default=0)
    overtime_rate = db.Column(db.Float, default=0)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', foreign_keys=[employee_id])
    updater = db.relationship('Employee', foreign_keys=[updated_by])
    
    @property
    def gross_salary(self):
        return (self.basic_salary + self.hra + self.transport_allowance + 
                self.medical_allowance + self.special_allowance + self.bonus)

class Payroll(db.Model):
    __tablename__ = 'payroll'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    salary_id = db.Column(db.Integer, db.ForeignKey('salaries.id'), nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    basic_pay = db.Column(db.Float, nullable=False)
    allowances = db.Column(db.Float, default=0)
    overtime_pay = db.Column(db.Float, default=0)
    gross_pay = db.Column(db.Float, nullable=False)
    tax_deduction = db.Column(db.Float, default=0)
    pf_deduction = db.Column(db.Float, default=0)  # Provident Fund
    esi_deduction = db.Column(db.Float, default=0)  # Employee State Insurance
    other_deductions = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    net_pay = db.Column(db.Float, nullable=False)
    days_worked = db.Column(db.Integer, default=0)
    leaves_taken = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Generated')  # Generated, Approved, Paid
    generated_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    paid_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', foreign_keys=[employee_id])
    salary = db.relationship('Salary', foreign_keys=[salary_id])
    generator = db.relationship('Employee', foreign_keys=[generated_by])
    approver = db.relationship('Employee', foreign_keys=[approved_by])

# Using existing Attendance model from attendance.py
# Extended attendance features will be added to that model

# Using existing Leave model from employee.py
# Additional leave management features will work with the existing model

class HREvent(db.Model):
    __tablename__ = 'hr_events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50), nullable=False)  # Birthday, Anniversary, Team Building, Training, Meeting
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    organizer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    participants = db.Column(db.Text)  # Comma-separated employee IDs or 'all'
    budget = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='Planned')  # Planned, Ongoing, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organizer = db.relationship('Employee', foreign_keys=[organizer_id])

class Asset(db.Model):
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Laptop, Desktop, Monitor, Furniture, etc.
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    purchase_price = db.Column(db.Float)
    supplier = db.Column(db.String(200))
    warranty_expiry = db.Column(db.Date)
    location = db.Column(db.String(200))
    assigned_to = db.Column(db.Integer, db.ForeignKey('employees.id'))
    status = db.Column(db.String(50), default='Available')  # Available, Assigned, Maintenance, Disposed
    condition = db.Column(db.String(50), default='Good')  # Good, Fair, Poor, Damaged
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignee = db.relationship('Employee', foreign_keys=[assigned_to])
    maintenance_logs = db.relationship('AssetMaintenance', backref='asset', lazy='dynamic')

class AssetMaintenance(db.Model):
    __tablename__ = 'asset_maintenance'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False)  # Repair, Service, Cleaning, Upgrade
    description = db.Column(db.Text, nullable=False)
    maintenance_date = db.Column(db.Date, nullable=False)
    cost = db.Column(db.Float, default=0)
    vendor = db.Column(db.String(200))
    performed_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    next_maintenance_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Completed')  # Scheduled, In Progress, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    performer = db.relationship('Employee', foreign_keys=[performed_by])

class CleaningLog(db.Model):
    __tablename__ = 'cleaning_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(200), nullable=False)  # Office Floor, Washroom, Kitchen, Conference Room
    cleaning_date = db.Column(db.Date, nullable=False)
    cleaning_time = db.Column(db.Time)
    cleaner_name = db.Column(db.String(200), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    items_cleaned = db.Column(db.Text)  # Checklist of cleaned items
    supplies_used = db.Column(db.Text)
    notes = db.Column(db.Text)
    rating = db.Column(db.Integer)  # 1-5 rating
    photo_path = db.Column(db.String(500))  # Photo evidence
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    supervisor = db.relationship('Employee', foreign_keys=[supervisor_id])

class PettyCash(db.Model):
    __tablename__ = 'petty_cash'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.Date, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # Addition, Expense
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Office Supplies, Refreshments, Transportation, etc.
    description = db.Column(db.Text, nullable=False)
    receipt_number = db.Column(db.String(100))
    receipt_path = db.Column(db.String(500))  # Scanned receipt
    requested_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    status = db.Column(db.String(50), default='Pending')  # Pending, Approved, Rejected, Reimbursed
    balance_after = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requester = db.relationship('Employee', foreign_keys=[requested_by])
    approver = db.relationship('Employee', foreign_keys=[approved_by])

# Leave types are handled by the existing Leave model in employee.py 

class Appointment(db.Model):
    """Appointment scheduling between employees"""
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    requested_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(100))
    meeting_type = db.Column(db.String(50), default='General')  # General, Review, Interview, etc.
    status = db.Column(db.String(20), default='Pending')  # Pending, Confirmed, Cancelled, Completed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requester = db.relationship('Employee', foreign_keys=[requested_by], backref='requested_appointments')
    participants = db.relationship('AppointmentParticipant', back_populates='appointment', cascade='all, delete-orphan')

class AppointmentParticipant(db.Model):
    """Participants in an appointment"""
    __tablename__ = 'appointment_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    response = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Declined
    response_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Relationships
    appointment = db.relationship('Appointment', back_populates='participants')
    employee = db.relationship('Employee', backref='appointment_participations')

class ConferenceRoom(db.Model):
    """Conference room management"""
    __tablename__ = 'conference_rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    capacity = db.Column(db.Integer, default=10)
    facilities = db.Column(db.Text)  # JSON string of available facilities
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('ConferenceBooking', back_populates='room', cascade='all, delete-orphan')

class ConferenceBooking(db.Model):
    """Conference room bookings"""
    __tablename__ = 'conference_bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('conference_rooms.id'), nullable=False)
    booked_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Confirmed')  # Confirmed, Cancelled
    attendees_count = db.Column(db.Integer, default=1)
    special_requirements = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    room = db.relationship('ConferenceRoom', back_populates='bookings')
    organizer = db.relationship('Employee', backref='conference_bookings')

# PersonalCalendar model removed - now using unified CalendarEvent in app.models.calendar 

class JobRequest(db.Model):
    """Job requests from managers/departments to HR for new positions"""
    __tablename__ = 'job_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    justification = db.Column(db.Text, nullable=False)  # Why this position is needed
    
    # Budget and compensation
    budget_min = db.Column(db.Float)
    budget_max = db.Column(db.Float)
    employment_type = db.Column(db.String(50), default='Full-time')
    location = db.Column(db.String(200))
    openings = db.Column(db.Integer, default=1)
    urgency = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    
    # Timeline
    expected_start_date = db.Column(db.Date)
    application_deadline = db.Column(db.Date)
    
    # Request details
    requested_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Pending')  # Pending, Approved, Rejected, In Review
    
    # Approval workflow
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    approval_date = db.Column(db.DateTime)
    approval_notes = db.Column(db.Text)
    
    # HR processing
    hr_assigned_to = db.Column(db.Integer, db.ForeignKey('employees.id'))
    hr_notes = db.Column(db.Text)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'))  # Link to created job posting
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requester = db.relationship('Employee', foreign_keys=[requested_by], backref='job_requests')
    approver = db.relationship('Employee', foreign_keys=[approved_by])
    hr_assignee = db.relationship('Employee', foreign_keys=[hr_assigned_to])
    job_posting = db.relationship('JobPosting', backref='job_request')