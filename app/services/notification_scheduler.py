# HRMSV3_optimized/app/services/notification_scheduler.py

import threading
import time
from datetime import datetime, timedelta
from ..database import db
from ..models.notifications import Notification, NotificationService, NotificationPreference
from ..models.calendar import CalendarEvent
from ..models.users import User
import logging

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """Background scheduler for notifications"""
    
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.thread = None
        
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
    def start(self):
        """Start the notification scheduler"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("Notification scheduler started")
    
    def stop(self):
        """Stop the notification scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Notification scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                with self.app.app_context():
                    self._check_meeting_reminders()
                    self._check_overdue_tasks()
                    self._cleanup_old_notifications()
                
                # Sleep for 1 minute before next check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in notification scheduler: {str(e)}")
                time.sleep(60)  # Continue after error
    
    def _check_meeting_reminders(self):
        """Check for upcoming meetings and send reminders"""
        try:
            now = datetime.utcnow()
            
            # Get all upcoming meetings in the next hour
            upcoming_meetings = CalendarEvent.query.filter(
                CalendarEvent.start > now,
                CalendarEvent.start <= now + timedelta(hours=1),
                CalendarEvent.event_type.in_(['Meeting', 'Interview', 'Appointment'])
            ).all()
            
            for meeting in upcoming_meetings:
                # Get all participants
                participants = []
                
                # Add creator
                if meeting.created_by_id:
                    participants.append(meeting.created_by_id)
                
                # Add assigned employee if exists
                if hasattr(meeting, 'employee_id') and meeting.employee_id:
                    participants.append(meeting.employee_id)
                
                # Add interview participants if it's an interview
                if meeting.event_type == 'Interview':
                    from ..models.hr import InterviewParticipant
                    interview_participants = InterviewParticipant.query.filter_by(
                        interview_id=meeting.id
                    ).all()
                    for participant in interview_participants:
                        if participant.employee_id:
                            participants.append(participant.employee_id)
                
                # Remove duplicates
                participants = list(set(participants))
                
                for participant_id in participants:
                    # Get user's notification preferences
                    user = User.query.join(User.employee).filter(
                        User.employee.has(id=participant_id)
                    ).first()
                    
                    if not user:
                        continue
                    
                    preferences = NotificationPreference.query.filter_by(
                        user_id=user.id
                    ).first()
                    
                    if not preferences:
                        # Create default preferences
                        preferences = NotificationPreference(user_id=user.id)
                        db.session.add(preferences)
                        db.session.commit()
                    
                    if not preferences.meeting_reminders_enabled:
                        continue
                    
                    # Check if we should send reminder now
                    reminder_time = meeting.start - timedelta(
                        minutes=preferences.meeting_reminder_minutes
                    )
                    
                    if now >= reminder_time:
                        # Check if reminder already sent
                        existing_reminder = Notification.query.filter_by(
                            user_id=user.id,
                            meeting_id=meeting.id,
                            notification_type='meeting',
                            is_reminder_sent=True
                        ).first()
                        
                        if not existing_reminder:
                            # Create meeting reminder notification
                            minutes_until = int((meeting.start - now).total_seconds() / 60)
                            
                            notification = NotificationService.create_notification(
                                user_id=user.id,
                                title=f"Meeting Reminder: {meeting.title}",
                                message=f"You have a meeting '{meeting.title}' starting in {minutes_until} minutes at {meeting.location or 'TBD'}",
                                notification_type='meeting',
                                related_entity_type='meeting',
                                related_entity_id=meeting.id,
                                meeting_id=meeting.id,
                                priority='high'
                            )
                            
                            notification.is_reminder_sent = True
                            notification.reminder_time = reminder_time
                            db.session.commit()
                            
                            logger.info(f"Meeting reminder sent to user {user.id} for meeting {meeting.id}")
            
        except Exception as e:
            logger.error(f"Error checking meeting reminders: {str(e)}")
    
    def _check_overdue_tasks(self):
        """Check for overdue tasks and send notifications"""
        try:
            from ..models.project import Task
            from ..models.employee import Employee
            
            now = datetime.utcnow().date()
            
            # Get overdue tasks
            overdue_tasks = Task.query.filter(
                Task.due_date < now,
                Task.status != 'Completed'
            ).all()
            
            for task in overdue_tasks:
                if not task.assigned_to:
                    continue
                
                # Get assigned employee
                employee = Employee.query.get(task.assigned_to)
                if not employee or not employee.user:
                    continue
                
                # Check if overdue notification already sent today
                existing_notification = Notification.query.filter(
                    Notification.user_id == employee.user.id,
                    Notification.related_entity_type == 'task',
                    Notification.related_entity_id == task.id,
                    Notification.notification_type == 'deadline',
                    db.func.date(Notification.created_at) == now
                ).first()
                
                if not existing_notification:
                    days_overdue = (now - task.due_date).days
                    
                    NotificationService.create_notification(
                        user_id=employee.user.id,
                        title=f"Overdue Task: {task.title}",
                        message=f"Task '{task.title}' in project '{task.project.name}' is {days_overdue} day{'s' if days_overdue != 1 else ''} overdue",
                        notification_type='deadline',
                        related_entity_type='task',
                        related_entity_id=task.id,
                        priority='urgent'
                    )
                    
                    logger.info(f"Overdue task notification sent for task {task.id}")
        
        except Exception as e:
            logger.error(f"Error checking overdue tasks: {str(e)}")
    
    def _cleanup_old_notifications(self):
        """Clean up old read notifications"""
        try:
            # Delete read notifications older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            old_notifications = Notification.query.filter(
                Notification.is_read == True,
                Notification.created_at < cutoff_date
            ).all()
            
            for notification in old_notifications:
                db.session.delete(notification)
            
            if old_notifications:
                db.session.commit()
                logger.info(f"Cleaned up {len(old_notifications)} old notifications")
        
        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {str(e)}")
    
    def create_meeting_reminders_for_event(self, event_id):
        """Create meeting reminders for a specific event"""
        try:
            with self.app.app_context():
                meeting = CalendarEvent.query.get(event_id)
                if not meeting:
                    return
                
                # Get all users who should receive reminders
                participants = []
                
                if meeting.created_by_id:
                    participants.append(meeting.created_by_id)
                
                if hasattr(meeting, 'employee_id') and meeting.employee_id:
                    participants.append(meeting.employee_id)
                
                # Add interview participants if it's an interview
                if meeting.event_type == 'Interview':
                    from ..models.hr import InterviewParticipant
                    interview_participants = InterviewParticipant.query.filter_by(
                        interview_id=meeting.id
                    ).all()
                    for participant in interview_participants:
                        if participant.employee_id:
                            participants.append(participant.employee_id)
                
                participants = list(set(participants))
                
                for participant_id in participants:
                    user = User.query.join(User.employee).filter(
                        User.employee.has(id=participant_id)
                    ).first()
                    
                    if user:
                        NotificationService.create_meeting_reminder(
                            user_id=user.id,
                            meeting_id=meeting.id,
                            minutes_before=15  # Default 15 minutes
                        )
                
                logger.info(f"Meeting reminders created for event {event_id}")
        
        except Exception as e:
            logger.error(f"Error creating meeting reminders: {str(e)}")

# Global scheduler instance
notification_scheduler = NotificationScheduler() 