from datetime import datetime
from ..database import db

class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Date and time fields - supporting both datetime and separate date/time
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime)
    all_day = db.Column(db.Boolean, default=False)
    
    # Event categorization
    event_type = db.Column(db.String(50), nullable=False, default='Personal')  # Personal, Work, Meeting, Task, etc.
    priority = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    status = db.Column(db.String(20), default='Planned')  # Planned, In Progress, Completed, Cancelled
    
    # Reminder and notification
    reminder_minutes = db.Column(db.Integer, default=15)  # Minutes before event to remind
    
    # Ownership - supporting both user and employee relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)  # Optional for employee-specific events
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('calendar_events', lazy='dynamic'))
    employee = db.relationship('Employee', backref=db.backref('calendar_events', lazy='dynamic'))

    def to_dict(self):
        """Serialize the object to a dictionary for FullCalendar."""
        
        EVENT_TYPE_COLORS = {
            'Personal': '#007bff',
            'Work': '#28a745',
            'Meeting': '#ffc107',
            'Task': '#dc3545',
            'Training': '#17a2b8',
            'Appointment': '#6f42c1',
            'Deadline': '#fd7e14',
            'Holiday': '#20c997',
            'Birthday': '#e83e8c',
            'Other': '#6c757d',
        }
        
        return {
            'id': self.id,
            'title': self.title,
            'start': self.start.isoformat(),
            'end': self.end.isoformat() if self.end else None,
            'allDay': self.all_day,
            'description': self.description,
            'extendedProps': {
                'eventType': self.event_type,
                'priority': self.priority,
                'status': self.status,
                'reminderMinutes': self.reminder_minutes
            },
            'color': EVENT_TYPE_COLORS.get(self.event_type, '#6c757d'),
            'borderColor': EVENT_TYPE_COLORS.get(self.event_type, '#6c757d')
        }

    def __repr__(self):
        return f'<CalendarEvent {self.title}>' 