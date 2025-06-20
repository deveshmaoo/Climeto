"""
Core routes for the HRMS application.
"""

from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from . import bp
from ..models.project import Task, ActivityLog, Lead, Client
from ..models.employee import Employee
from ..models.project import TrainingAssignment
from ..project.forms import CalendarEventForm, TrainingAssignmentForm
from ..database import db
from ..utils.decorators import role_required
from ..models.project import ProjectActivity
from ..models.calendar import CalendarEvent
from .forms import EventForm, TrainingForm
from ..models.notifications import Notification, NotificationPreference, NotificationService

@bp.route('/')
def index():
    """Landing page route."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    return render_template('core/index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard route - customized based on user role."""
    employee = current_user.employee
    
    # Debug: Let's see what's happening
    print(f"DEBUG: User: {current_user.username}")
    print(f"DEBUG: Department: {current_user.department}")
    print(f"DEBUG: Role: {current_user.role.name if current_user.role else None}")
    print(f"DEBUG: can_view_all_activities(): {current_user.can_view_all_activities()}")
    print(f"DEBUG: Department in sales: {current_user.department in ['Digital Marketing', 'Business Development']}")
    
    # Get user-specific data based on role and department
    if current_user.can_view_all_activities():
        # Management/General Manager dashboard
        print("DEBUG: Routing to management_dashboard")
        return management_dashboard()
    elif current_user.department in ['EPR Compliance', 'Project Development']:
        # Department-specific dashboard
        print("DEBUG: Routing to department_dashboard")
        return department_dashboard()
    elif current_user.department in ['Digital Marketing', 'Business Development']:
        # Sales dashboard
        print("DEBUG: Routing to sales_dashboard")
        return sales_dashboard()
    else:
        # Regular employee dashboard
        print("DEBUG: Routing to employee_dashboard")
        return employee_dashboard()

def management_dashboard():
    """Dashboard for Management and General Manager users."""
    # Activity log - all departments
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    
    # Department-wise task statistics
    dept_stats = {}
    for dept in current_user.DEPARTMENTS:
        dept_tasks = Task.query.join(Employee, Task.assigned_to == Employee.id).filter(
            Employee.department == dept
        ).all()
        dept_stats[dept] = {
            'total': len(dept_tasks),
            'completed': len([t for t in dept_tasks if t.status == 'Completed']),
            'in_progress': len([t for t in dept_tasks if t.status == 'In Progress']),
            'overdue': len([t for t in dept_tasks if t.due_date and t.due_date < date.today() and t.status != 'Completed'])
        }
    
    # Recent chats from all projects
    from ..models.project import ProjectChat
    all_chats = ProjectChat.query.order_by(ProjectChat.created_at.desc()).limit(15).all()
    
    # Calendar events for the next 30 days
    end_date = date.today() + timedelta(days=30)
    upcoming_events = CalendarEvent.query.filter(
        db.func.date(CalendarEvent.start).between(date.today(), end_date)
    ).order_by(CalendarEvent.start).all()
    
    # Employee birthdays this month
    current_month = date.today().month
    birthday_events = CalendarEvent.query.filter(
        CalendarEvent.event_type == 'Birthday'
    ).filter(
        db.extract('month', CalendarEvent.start) == current_month
    ).all()
    
    # Sales metrics
    total_leads = Lead.query.count()
    total_clients = Client.query.count()
    
    return render_template('core/dashboard.html',
                         recent_activities=recent_activities,
                         dept_stats=dept_stats,
                         all_chats=all_chats,
                         upcoming_events=upcoming_events,
                         birthday_events=birthday_events,
                         total_leads=total_leads,
                         total_clients=total_clients)

def department_dashboard():
    """Dashboard for EPR Compliance and Project Development departments."""
    employee = current_user.employee
    department = current_user.department
    
    # Department-specific tasks
    dept_employees = Employee.query.filter_by(department=department).all()
    dept_employee_ids = [e.id for e in dept_employees]
    
    my_tasks = Task.query.filter_by(assigned_to=employee.id).all()
    dept_tasks = Task.query.filter(Task.assigned_to.in_(dept_employee_ids)).all()
    
    # Task statistics
    task_stats = {
        'my_total': len(my_tasks),
        'my_completed': len([t for t in my_tasks if t.status == 'Completed']),
        'my_in_progress': len([t for t in my_tasks if t.status == 'In Progress']),
        'dept_total': len(dept_tasks),
        'dept_completed': len([t for t in dept_tasks if t.status == 'Completed'])
    }
    
    # Recent department activities
    dept_activities = ActivityLog.query.filter_by(department=department).order_by(
        ActivityLog.created_at.desc()
    ).limit(10).all()
    
    # Training assignments
    training_assignments = TrainingAssignment.query.filter_by(
        employee_id=employee.id,
        status='Assigned'
    ).all()
    
    # If EPR Compliance, show assigned clients
    assigned_clients = []
    if department == 'EPR Compliance':
        assigned_clients = Client.query.filter_by(assigned_to_epr_id=employee.id).all()
    
    return render_template('core/dashboard.html',
                         my_tasks=my_tasks[:10],
                         task_stats=task_stats,
                         dept_activities=dept_activities,
                         training_assignments=training_assignments,
                         assigned_clients=assigned_clients,
                         department=department)

def sales_dashboard():
    """Dashboard for Digital Marketing and Business Development departments."""
    employee = current_user.employee
    
    # Sales metrics
    my_leads = Lead.query.filter_by(assigned_to_id=employee.id).all()
    my_clients = Client.query.filter_by(account_manager_id=employee.id).all()
    
    # Lead statistics
    lead_stats = {
        'total': len(my_leads),
        'new': len([l for l in my_leads if l.status == 'New']),
        'qualified': len([l for l in my_leads if l.status == 'Qualified']),
        'won': len([l for l in my_leads if l.status == 'Closed Won']),
        'lost': len([l for l in my_leads if l.status == 'Closed Lost'])
    }
    
    # Recent lead interactions
    from ..models.project import LeadInteraction
    recent_interactions = LeadInteraction.query.filter_by(
        performed_by_id=employee.id
    ).order_by(LeadInteraction.interaction_date.desc()).limit(10).all()
    
    # Upcoming follow-ups
    upcoming_followups = LeadInteraction.query.filter(
        LeadInteraction.performed_by_id == employee.id,
        LeadInteraction.next_follow_up >= date.today()
    ).order_by(LeadInteraction.next_follow_up).limit(10).all()
    
    return render_template('core/dashboard.html',
                         my_leads=my_leads[:10],
                         my_clients=my_clients[:10],
                         lead_stats=lead_stats,
                         recent_interactions=recent_interactions,
                         upcoming_followups=upcoming_followups)

def employee_dashboard():
    """Dashboard for regular employees."""
    employee = current_user.employee
    
    # My tasks
    my_tasks = Task.query.filter_by(assigned_to=employee.id).all()
    
    # Task statistics
    task_stats = {
        'total': len(my_tasks),
        'completed': len([t for t in my_tasks if t.status == 'Completed']),
        'in_progress': len([t for t in my_tasks if t.status == 'In Progress']),
        'overdue': len([t for t in my_tasks if t.due_date and t.due_date < date.today() and t.status != 'Completed'])
    }
    
    # Training assignments
    training_assignments = TrainingAssignment.query.filter_by(
        employee_id=employee.id,
        status='Assigned'
    ).all()
    
    # My recent activities
    my_activities = ActivityLog.query.filter_by(
        performed_by_id=employee.id
    ).order_by(ActivityLog.created_at.desc()).limit(10).all()
    
    return render_template('core/dashboard.html',
                         my_tasks=my_tasks,
                         task_stats=task_stats,
                         training_assignments=training_assignments,
                         my_activities=my_activities)

@bp.route('/activity-log')
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager')
def activity_log():
    """View all system activities."""
    # Get filter parameters
    department_filter = request.args.get('department', 'all')
    activity_type_filter = request.args.get('activity_type', 'all')
    
    # Base query
    query = ActivityLog.query
    
    # Apply filters
    if department_filter != 'all':
        query = query.filter_by(department=department_filter)
    if activity_type_filter != 'all':
        query = query.filter_by(activity_type=activity_type_filter)
    
    activities = query.order_by(ActivityLog.created_at.desc()).limit(100).all()
    
    # Get unique values for filters
    all_departments = db.session.query(ActivityLog.department).distinct().all()
    all_activity_types = db.session.query(ActivityLog.activity_type).distinct().all()
    
    return render_template('core/activity_log.html',
                         activities=activities,
                         departments=[d[0] for d in all_departments],
                         activity_types=[a[0] for a in all_activity_types],
                         filters={
                             'department': department_filter,
                             'activity_type': activity_type_filter
                         })

@bp.route('/calendar')
@login_required
def calendar():
    """Renders the unified calendar view."""
    return render_template('core/calendar.html')

@bp.route('/api/calendar/events')
@login_required
def get_events():
    """API endpoint to fetch calendar events for the logged-in user."""
    start = request.args.get('start')
    end = request.args.get('end')
    
    if not start or not end:
        return jsonify({'error': 'Start and end dates are required.'}), 400

    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))

        # Get events for the current user
        events = CalendarEvent.query.filter(
            CalendarEvent.user_id == current_user.id,
            CalendarEvent.start < end_dt,
            CalendarEvent.start >= start_dt
        ).all()
        
        return jsonify([event.to_dict() for event in events])
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {e}'}), 400

@bp.route('/api/calendar/events', methods=['POST'])
@login_required
def create_event_api():
    """API endpoint to create a new calendar event."""
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('start'):
        return jsonify({'error': 'Title and start date are required.'}), 400
    
    try:
        # Set employee_id if user has an employee profile
        employee_id = None
        if hasattr(current_user, 'employee') and current_user.employee:
            employee_id = current_user.employee.id
            
        event = CalendarEvent(
            title=data['title'],
            start=datetime.fromisoformat(data['start'].replace('Z', '+00:00')),
            end=datetime.fromisoformat(data['end'].replace('Z', '+00:00')) if data.get('end') else None,
            all_day=data.get('allDay', False),
            description=data.get('description'),
            event_type=data.get('event_type', 'Personal'),
            priority=data.get('priority', 'Medium'),
            user_id=current_user.id,
            employee_id=employee_id
        )
        db.session.add(event)
        db.session.commit()
        return jsonify(event.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/calendar/events/<int:event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    """API endpoint to update an existing event (e.g., drag and drop)."""
    event = CalendarEvent.query.get_or_404(event_id)
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    try:
        event.title = data.get('title', event.title)
        event.start = datetime.fromisoformat(data['start'].replace('Z', '+00:00')) if data.get('start') else event.start
        event.end = datetime.fromisoformat(data['end'].replace('Z', '+00:00')) if data.get('end') else event.end
        event.all_day = data.get('allDay', event.all_day)
        event.description = data.get('description', event.description)
        event.event_type = data.get('event_type', event.event_type)
        event.priority = data.get('priority', event.priority)
        
        db.session.commit()
        return jsonify(event.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/calendar/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    """API endpoint to delete an event."""
    event = CalendarEvent.query.get_or_404(event_id)
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': 'Event deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/training/assign', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager')
def assign_training():
    """Assign training to employees."""
    form = TrainingAssignmentForm()
    
    # Get employees based on user access
    if current_user.can_view_all_activities():
        employees = Employee.query.all()
    else:
        # Department managers can assign to their department
        employees = Employee.query.filter_by(department=current_user.department).all()
    
    form.employee_id.choices = [(e.id, f"{e.first_name} {e.last_name} ({e.department})") for e in employees]
    
    if form.validate_on_submit():
        assignment = TrainingAssignment(
            employee_id=form.employee_id.data,
            training_title=form.training_title.data,
            training_type=form.training_type.data,
            description=form.description.data,
            assigned_by_id=current_user.employee.id,
            due_date=form.due_date.data,
            reason=form.reason.data
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        # Log activity
        employee = Employee.query.get(form.employee_id.data)
        activity = ActivityLog(
            activity_type='Training Assigned',
            description=f'Training assigned to {employee.first_name} {employee.last_name}: {assignment.training_title}',
            department=current_user.department,
            performed_by_id=current_user.employee.id,
            entity_type='Training',
            entity_id=assignment.id
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Training assigned successfully!', 'success')
        return redirect(url_for('core.dashboard'))
    
    return render_template('core/assign_training.html', form=form)

@bp.route('/training/my-assignments')
@login_required
def my_training_assignments():
    """View my training assignments."""
    employee = current_user.employee
    assignments = TrainingAssignment.query.filter_by(employee_id=employee.id).order_by(
        TrainingAssignment.assigned_date.desc()
    ).all()
    
    return render_template('core/my_training.html', assignments=assignments)

@bp.route('/training/<int:id>/complete', methods=['POST'])
@login_required
def complete_training(id):
    """Mark training as completed."""
    assignment = TrainingAssignment.query.get_or_404(id)
    
    if assignment.employee_id != current_user.employee.id:
        flash('You can only complete your own training assignments.', 'error')
        return redirect(url_for('core.my_training_assignments'))
    
    assignment.status = 'Completed'
    assignment.completion_date = date.today()
    db.session.commit()
    
    flash('Training marked as completed!', 'success')
    return redirect(url_for('core.my_training_assignments'))

@bp.route('/all-chats')
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager')
def all_chats():
    """View all project chats across the organization."""
    from ..models.project import ProjectChat
    
    # Get filter parameters
    filter_type = request.args.get('filter', 'all')
    project_filter = request.args.get('project', 'all')
    
    # Base query
    query = ProjectChat.query
    
    # Apply filters
    if filter_type == 'files':
        query = query.filter(ProjectChat.message_type.in_(['file', 'image']))
    elif filter_type == 'today':
        today = date.today()
        query = query.filter(db.func.date(ProjectChat.created_at) == today)
    elif filter_type == 'week':
        week_ago = date.today() - timedelta(days=7)
        query = query.filter(ProjectChat.created_at >= week_ago)
    
    if project_filter != 'all':
        query = query.filter_by(project_id=int(project_filter))
    
    chats = query.order_by(ProjectChat.created_at.desc()).limit(100).all()
    
    # Get all projects for filter
    from ..models.project import Project
    all_projects = Project.query.all()
    
    return render_template('core/all_chats.html',
                         chats=chats,
                         projects=all_projects,
                         filters={
                             'filter_type': filter_type,
                             'project': project_filter
                         })

@bp.route('/calendar/add', methods=['GET', 'POST'])
@login_required
def add_calendar_event():
    """Add a new event to the calendar."""
    if request.method == 'POST':
        try:
            # Parse date and time
            event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d').date()
            start_time = None
            end_time = None
            
            if request.form.get('start_time'):
                start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
                start_datetime = datetime.combine(event_date, start_time)
            else:
                start_datetime = datetime.combine(event_date, datetime.min.time())
                
            if request.form.get('end_time'):
                end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
                end_datetime = datetime.combine(event_date, end_time)
            else:
                end_datetime = None
            
            # Set employee_id if user has an employee profile
            employee_id = None
            if hasattr(current_user, 'employee') and current_user.employee:
                employee_id = current_user.employee.id
                
            event = CalendarEvent(
                user_id=current_user.id,
                employee_id=employee_id,
                title=request.form['title'],
                description=request.form.get('description'),
                start=start_datetime,
                end=end_datetime,
                event_type=request.form['event_type'],
                priority=request.form['priority'],
                all_day=bool(request.form.get('is_all_day')),
                reminder_minutes=int(request.form.get('reminder_minutes', 15))
            )
            
            db.session.add(event)
            db.session.commit()
            flash('Event added to your calendar!', 'success')
            return redirect(url_for('core.calendar'))
        except Exception as e:
            flash(f'Error adding event: {str(e)}', 'danger')
    
    return render_template('core/add_calendar_event.html')

@bp.route('/notifications')
@login_required
def notifications():
    """View all notifications for the current user."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications_query = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc())
    
    notifications_paginated = notifications_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unread count
    unread_count = NotificationService.get_unread_count(current_user.id)
    
    return render_template('core/notifications.html',
                         notifications=notifications_paginated.items,
                         pagination=notifications_paginated,
                         unread_count=unread_count)

@bp.route('/notifications/api/recent')
@login_required
def api_recent_notifications():
    """API endpoint for recent notifications (for real-time updates)."""
    limit = request.args.get('limit', 10, type=int)
    notifications = NotificationService.get_recent_notifications(current_user.id, limit)
    unread_count = NotificationService.get_unread_count(current_user.id)
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'is_read': notification.is_read,
            'time_ago': notification.time_ago,
            'icon_class': notification.icon_class,
            'color_class': notification.color_class,
            'created_at': notification.created_at.isoformat()
        })
    
    return jsonify({
        'notifications': notifications_data,
        'unread_count': unread_count
    })

@bp.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a specific notification as read."""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    
    notification.mark_as_read()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Notification marked as read'})
    
    flash('Notification marked as read.', 'success')
    return redirect(url_for('core.notifications'))

@bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current user."""
    count = NotificationService.mark_all_as_read(current_user.id)
    
    if request.is_json:
        return jsonify({'success': True, 'message': f'{count} notifications marked as read'})
    
    flash(f'{count} notifications marked as read.', 'success')
    return redirect(url_for('core.notifications'))

@bp.route('/notifications/preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    """Manage notification preferences."""
    preferences = NotificationPreference.query.filter_by(
        user_id=current_user.id
    ).first()
    
    if not preferences:
        preferences = NotificationPreference(user_id=current_user.id)
        db.session.add(preferences)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            # Update preferences from form
            preferences.mentions_enabled = 'mentions_enabled' in request.form
            preferences.meeting_reminders_enabled = 'meeting_reminders_enabled' in request.form
            preferences.task_notifications_enabled = 'task_notifications_enabled' in request.form
            preferences.project_notifications_enabled = 'project_notifications_enabled' in request.form
            preferences.system_notifications_enabled = 'system_notifications_enabled' in request.form
            
            preferences.meeting_reminder_minutes = int(request.form.get('meeting_reminder_minutes', 15))
            preferences.daily_digest_enabled = 'daily_digest_enabled' in request.form
            
            if request.form.get('daily_digest_time'):
                preferences.daily_digest_time = datetime.strptime(
                    request.form['daily_digest_time'], '%H:%M'
                ).time()
            
            preferences.email_notifications_enabled = 'email_notifications_enabled' in request.form
            preferences.email_mentions_only = 'email_mentions_only' in request.form
            
            preferences.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Notification preferences updated successfully!', 'success')
            return redirect(url_for('core.notification_preferences'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating preferences: {str(e)}', 'danger')
    
    return render_template('core/notification_preferences.html', preferences=preferences)

@bp.route('/notifications/test-mention', methods=['POST'])
@login_required
def test_mention():
    """Test endpoint for creating mention notifications (for development)."""
    if not current_user.has_role('Admin'):
        abort(403)
    
    text = request.form.get('text', '@admin test mention')
    NotificationService.process_mentions_in_text(
        text=text,
        author_id=current_user.employee.id,
        entity_type='test',
        entity_id=1
    )
    
    flash('Test mention notification created!', 'success')
    return redirect(url_for('core.notifications')) 