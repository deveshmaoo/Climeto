# HRMSV3_optimized/app/models/project.py
from datetime import datetime
from ..database import db
from .employee import Employee

project_members = db.Table('project_members',
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True)
)

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(db.String(50), nullable=False)  # Department identifier
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Active')  # Active, Completed, On Hold, Cancelled
    priority = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    
    # Project lead/manager
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    manager = db.relationship('Employee', foreign_keys=[manager_id])
    
    # Project members (many-to-many)
    members = db.relationship('Employee', secondary=project_members, lazy='dynamic',
                            backref=db.backref('projects', lazy='dynamic'))
    
    # Related entities
    tasks = db.relationship('Task', backref='project', lazy='dynamic')
    chats = db.relationship('ProjectChat', backref='project', lazy='dynamic')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Project {self.name}>'

    def add_member(self, employee):
        if employee not in self.members:
            self.members.append(employee)
            db.session.commit()

    def remove_member(self, employee):
        if employee in self.members:
            self.members.remove(employee)
            db.session.commit()

    def can_access(self, employee):
        """Check if employee can access this project."""
        # Project manager can access
        if self.manager_id == employee.id:
            return True
        # Project members can access
        if employee in self.members:
            return True
        # Admin or HR can access all projects
        if employee.user.has_role('Admin') or employee.user.has_role('HR'):
            return True
        return False

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Not Started')  # Not Started, In Progress, On Hold, Completed
    priority = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    due_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float)
    assigned_to = db.Column(db.Integer, db.ForeignKey('employees.id'))
    assigned_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    department = db.Column(db.String(50))  # Task department for cross-department assignments
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignee = db.relationship('Employee', foreign_keys=[assigned_to], backref='assigned_tasks')
    assigner = db.relationship('Employee', foreign_keys=[assigned_by], backref='created_tasks')
    queries = db.relationship('TaskQuery', backref='task', lazy='dynamic')
    ratings = db.relationship('TaskRating', backref='task', lazy='dynamic')

class TaskRating(db.Model):
    __tablename__ = 'task_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    rated_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    quality_rating = db.Column(db.Integer, nullable=False)  # 1-10 scale
    timeliness_rating = db.Column(db.Integer, nullable=False)  # 1-10 scale
    overall_rating = db.Column(db.Float)  # Calculated field
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rated_by = db.relationship('Employee', backref='given_ratings')
    
    def calculate_overall_rating(self):
        """Calculate overall rating based on quality and timeliness."""
        self.overall_rating = (self.quality_rating + self.timeliness_rating) / 2.0

class TaskQuery(db.Model):
    __tablename__ = 'task_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    raised_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    query_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Open')  # Open, Resolved, Closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    raised_by = db.relationship('Employee', backref='raised_queries')
    responses = db.relationship('QueryResponse', backref='query', lazy='dynamic')

class QueryResponse(db.Model):
    __tablename__ = 'query_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('task_queries.id'), nullable=False)
    responded_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    responded_by = db.relationship('Employee', backref='query_responses')

class ProjectDocument(db.Model):
    __tablename__ = 'project_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    document_type = db.Column(db.String(50))  # Specification, Design, Report, etc.
    created_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = db.relationship('Employee', backref='created_documents')
    versions = db.relationship('DocumentVersion', backref='document', lazy='dynamic')
    comments = db.relationship('DocumentComment', backref='document', lazy='dynamic')

class DocumentVersion(db.Model):
    __tablename__ = 'document_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('project_documents.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    change_summary = db.Column(db.Text)
    
    # Relationship
    uploaded_by = db.relationship('Employee', backref='uploaded_versions')

class DocumentComment(db.Model):
    __tablename__ = 'document_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('project_documents.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    commented_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    commented_by = db.relationship('Employee', backref='document_comments')

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False)  # Task Created, Project Created, Lead Added, etc.
    description = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(50), nullable=False)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    entity_type = db.Column(db.String(50))  # Task, Project, Lead, Employee, etc.
    entity_id = db.Column(db.Integer)  # ID of the related entity
    additional_data = db.Column(db.Text)  # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    performed_by = db.relationship('Employee', backref='activities')

class ProjectActivity(db.Model):
    __tablename__ = 'project_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # Task Created, Document Uploaded, etc.
    description = db.Column(db.Text, nullable=False)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    performed_by = db.relationship('Employee', backref='project_activities')

class ProjectChat(db.Model):
    __tablename__ = 'project_chats'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, image
    file_path = db.Column(db.String(255))  # For file attachments
    file_name = db.Column(db.String(100))  # Original filename
    file_size = db.Column(db.Integer)  # File size in bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    sender = db.relationship('Employee', backref='sent_messages')

class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50), nullable=False)  # Birthday, Deadline, Meeting, Holiday, etc.
    event_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    department = db.Column(db.String(50))
    created_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    related_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))  # For birthdays, joining dates, etc.
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))  # Daily, Weekly, Monthly, Yearly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_by = db.relationship('Employee', foreign_keys=[created_by_id], backref='created_events')
    related_employee = db.relationship('Employee', foreign_keys=[related_employee_id], backref='related_events')

# Sales Management Models
class Lead(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    industry = db.Column(db.String(50))
    source = db.Column(db.String(50))  # Website, Referral, Cold Call, etc.
    status = db.Column(db.String(20), default='New')  # New, Qualified, Proposal, Negotiation, Closed Won, Closed Lost
    priority = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    estimated_value = db.Column(db.Float)
    expected_close_date = db.Column(db.Date)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assigned_to = db.relationship('Employee', backref='assigned_leads')
    interactions = db.relationship('LeadInteraction', backref='lead', lazy='dynamic')

class LeadInteraction(db.Model):
    __tablename__ = 'lead_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    interaction_type = db.Column(db.String(50), nullable=False)  # Call, Email, Meeting, Demo, etc.
    description = db.Column(db.Text, nullable=False)
    interaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    next_follow_up = db.Column(db.Date)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Relationship
    performed_by = db.relationship('Employee', backref='lead_interactions')

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    industry = db.Column(db.String(50))
    client_since = db.Column(db.Date, default=datetime.utcnow)
    account_manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, Suspended
    total_value = db.Column(db.Float, default=0.0)
    created_from_lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    assigned_to_epr_id = db.Column(db.Integer, db.ForeignKey('employees.id'))  # EPR Compliance team assignment
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account_manager = db.relationship('Employee', foreign_keys=[account_manager_id], backref='managed_clients')
    created_from_lead = db.relationship('Lead', backref='converted_client')
    assigned_to_epr = db.relationship('Employee', foreign_keys=[assigned_to_epr_id], backref='epr_clients')
    projects = db.relationship('ClientProject', backref='client', lazy='dynamic')

class ClientProject(db.Model):
    __tablename__ = 'client_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    value = db.Column(db.Float)
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Training Management Model
class TrainingAssignment(db.Model):
    __tablename__ = 'training_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    training_title = db.Column(db.String(100), nullable=False)
    training_type = db.Column(db.String(50), nullable=False)  # Performance Improvement, Skill Development, etc.
    description = db.Column(db.Text)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    assigned_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Assigned')  # Assigned, In Progress, Completed, Overdue
    reason = db.Column(db.Text)  # Reason for training assignment
    completion_date = db.Column(db.Date)
    
    # Relationships
    employee = db.relationship('Employee', foreign_keys=[employee_id], backref='training_assignments')
    assigned_by = db.relationship('Employee', foreign_keys=[assigned_by_id], backref='assigned_trainings')