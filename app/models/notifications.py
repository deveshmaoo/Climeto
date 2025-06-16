# HRMSV3_optimized/app/models/notifications.py

from ..database import db
from datetime import datetime, timedelta
from sqlalchemy import event
import re

class Notification(db.Model):
    """Notification system for users"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    
    # Notification content
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # mention, meeting, task, system, etc.
    
    # Status and priority
    is_read = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Related entities
    related_entity_type = db.Column(db.String(50))  # project, task, meeting, chat, etc.
    related_entity_id = db.Column(db.Integer)
    
    # Mention specific fields
    mentioned_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    mention_context = db.Column(db.Text)  # The text where the mention occurred
    
    # Meeting reminder fields
    meeting_id = db.Column(db.Integer, db.ForeignKey('calendar_events.id'), nullable=True)
    reminder_time = db.Column(db.DateTime)  # When to send the reminder
    is_reminder_sent = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    employee = db.relationship('Employee', foreign_keys=[employee_id], backref='received_notifications')
    mentioned_by = db.relationship('Employee', foreign_keys=[mentioned_by_id], backref='sent_mentions')
    meeting = db.relationship('CalendarEvent', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    @property
    def time_ago(self):
        """Get human-readable time since notification was created"""
        now = datetime.utcnow()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @property
    def icon_class(self):
        """Get icon class based on notification type"""
        icons = {
            'mention': 'fas fa-at',
            'meeting': 'fas fa-calendar-alt',
            'task': 'fas fa-tasks',
            'project': 'fas fa-project-diagram',
            'system': 'fas fa-cog',
            'reminder': 'fas fa-bell',
            'assignment': 'fas fa-user-plus',
            'deadline': 'fas fa-clock',
            'approval': 'fas fa-check-circle',
            'message': 'fas fa-comment'
        }
        return icons.get(self.notification_type, 'fas fa-info-circle')
    
    @property
    def color_class(self):
        """Get color class based on priority and type"""
        if self.priority == 'urgent':
            return 'text-danger'
        elif self.priority == 'high':
            return 'text-warning'
        elif self.notification_type == 'meeting':
            return 'text-info'
        elif self.notification_type == 'mention':
            return 'text-primary'
        else:
            return 'text-secondary'

class NotificationPreference(db.Model):
    """User notification preferences"""
    __tablename__ = 'notification_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Notification type preferences
    mentions_enabled = db.Column(db.Boolean, default=True)
    meeting_reminders_enabled = db.Column(db.Boolean, default=True)
    task_notifications_enabled = db.Column(db.Boolean, default=True)
    project_notifications_enabled = db.Column(db.Boolean, default=True)
    system_notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Timing preferences
    meeting_reminder_minutes = db.Column(db.Integer, default=15)  # Minutes before meeting
    daily_digest_enabled = db.Column(db.Boolean, default=False)
    daily_digest_time = db.Column(db.Time, default=datetime.strptime('09:00', '%H:%M').time())
    
    # Email preferences
    email_notifications_enabled = db.Column(db.Boolean, default=False)
    email_mentions_only = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notification_preferences', uselist=False))
    
    def __repr__(self):
        return f'<NotificationPreference {self.user_id}>'

# Utility functions for creating notifications
class NotificationService:
    """Service class for managing notifications"""
    
    @staticmethod
    def create_notification(user_id, title, message, notification_type, 
                          related_entity_type=None, related_entity_id=None,
                          mentioned_by_id=None, mention_context=None,
                          priority='normal', meeting_id=None):
        """Create a new notification"""
        notification = Notification(
            user_id=user_id,
            employee_id=user_id,  # Assuming user_id maps to employee_id
            title=title,
            message=message,
            notification_type=notification_type,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            mentioned_by_id=mentioned_by_id,
            mention_context=mention_context,
            priority=priority,
            meeting_id=meeting_id
        )
        
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def create_mention_notification(mentioned_user_id, mentioner_id, context, 
                                  entity_type, entity_id, title=None):
        """Create a notification for @mentions"""
        from ..models.employee import Employee
        
        mentioner = Employee.query.get(mentioner_id)
        mentioner_name = mentioner.full_name if mentioner else "Someone"
        
        if not title:
            title = f"{mentioner_name} mentioned you"
        
        message = f"You were mentioned by {mentioner_name} in {entity_type}"
        
        return NotificationService.create_notification(
            user_id=mentioned_user_id,
            title=title,
            message=message,
            notification_type='mention',
            related_entity_type=entity_type,
            related_entity_id=entity_id,
            mentioned_by_id=mentioner_id,
            mention_context=context,
            priority='high'
        )
    
    @staticmethod
    def create_meeting_reminder(user_id, meeting_id, minutes_before=15):
        """Create a meeting reminder notification"""
        from ..models.calendar import CalendarEvent
        
        meeting = CalendarEvent.query.get(meeting_id)
        if not meeting:
            return None
        
        reminder_time = meeting.start - timedelta(minutes=minutes_before)
        
        notification = Notification(
            user_id=user_id,
            employee_id=user_id,
            title=f"Meeting Reminder: {meeting.title}",
            message=f"You have a meeting '{meeting.title}' starting in {minutes_before} minutes",
            notification_type='meeting',
            related_entity_type='meeting',
            related_entity_id=meeting_id,
            meeting_id=meeting_id,
            reminder_time=reminder_time,
            priority='high'
        )
        
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def create_task_assignment_notification(user_id, task_id, assigner_id):
        """Create notification for task assignment"""
        from ..models.project import Task
        from ..models.employee import Employee
        
        task = Task.query.get(task_id)
        assigner = Employee.query.get(assigner_id)
        
        if not task or not assigner:
            return None
        
        title = f"New Task Assigned: {task.title}"
        message = f"{assigner.full_name} assigned you a new task in project {task.project.name}"
        
        return NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type='assignment',
            related_entity_type='task',
            related_entity_id=task_id,
            mentioned_by_id=assigner_id,
            priority='normal'
        )
    
    @staticmethod
    def create_project_notification(user_id, project_id, title, message, 
                                  notification_type='project', priority='normal'):
        """Create a project-related notification"""
        return NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_entity_type='project',
            related_entity_id=project_id,
            priority=priority
        )
    
    @staticmethod
    def parse_mentions(text):
        """Parse @mentions from text and return list of mentioned usernames/emails"""
        # Pattern to match @username or @email
        mention_pattern = r'@([a-zA-Z0-9._-]+(?:@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})?)'
        mentions = re.findall(mention_pattern, text)
        return mentions
    
    @staticmethod
    def process_mentions_in_text(text, author_id, entity_type, entity_id):
        """Process mentions in text and create notifications"""
        from ..models.employee import Employee
        from ..models.users import User
        
        mentions = NotificationService.parse_mentions(text)
        created_notifications = []
        
        for mention in mentions:
            # Try to find user by email first, then by username
            user = None
            if '@' in mention:
                user = User.query.filter_by(email=mention).first()
            else:
                # Try to find by employee name or username
                employee = Employee.query.filter(
                    db.or_(
                        Employee.first_name.ilike(f'%{mention}%'),
                        Employee.last_name.ilike(f'%{mention}%'),
                        Employee.email.ilike(f'%{mention}%')
                    )
                ).first()
                if employee:
                    user = employee.user
            
            if user and user.id != author_id:
                notification = NotificationService.create_mention_notification(
                    mentioned_user_id=user.id,
                    mentioner_id=author_id,
                    context=text,
                    entity_type=entity_type,
                    entity_id=entity_id
                )
                created_notifications.append(notification)
        
        return created_notifications
    
    @staticmethod
    def get_unread_count(user_id):
        """Get count of unread notifications for user"""
        return Notification.query.filter_by(
            user_id=user_id, 
            is_read=False
        ).count()
    
    @staticmethod
    def get_recent_notifications(user_id, limit=10):
        """Get recent notifications for user"""
        return Notification.query.filter_by(
            user_id=user_id
        ).order_by(
            Notification.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications as read for user"""
        notifications = Notification.query.filter_by(
            user_id=user_id, 
            is_read=False
        ).all()
        
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        db.session.commit()
        return len(notifications) 