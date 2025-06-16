from functools import wraps
from flask import abort
from flask_login import current_user

# Module Categories with their route names
PERSONAL_MODULES = {
    'dashboard': {'label': 'Personal Dashboard', 'route': 'core.dashboard'},
    'my_profile': {'label': 'My Profile', 'route': 'employee.profile'},
    'my_attendance': {'label': 'My Attendance', 'route': 'employee.attendance'},
    'my_trainings': {'label': 'My Trainings', 'route': 'core.my_training_assignments'}
}

WORK_MODULES = {
    'projects': {'label': 'Projects', 'route': 'project.dashboard'},
    'project_list': {'label': 'Project List', 'route': 'project.list_projects'},
    'create_project': {'label': 'Create Project', 'route': 'project.create_project'},
    'activity_log': {'label': 'Activity Log', 'route': 'core.activity_log'},
    'calendar_events': {'label': 'My Calendar', 'route': 'core.calendar'},
    'notifications': {'label': 'Notifications', 'route': 'core.notifications'},
    'appointments': {'label': 'Appointments', 'route': 'hr.appointments'},
    'conference_rooms': {'label': 'Conference Rooms', 'route': 'hr.conference_rooms'},
    'team_chats': {'label': 'Team Chats', 'route': 'project.all_chats'}
}

HR_MODULES = {
    'create_user': {'label': 'Create User', 'route': 'auth.create_user'},
    'hr_dashboard': {'label': 'HR Dashboard', 'route': 'hr.dashboard'},
    'employee_management': {'label': 'Employee Management', 'route': 'hr.employee_management'},
    'salary_management': {'label': 'Salary Management', 'route': 'hr.salary_management'},
    'attendance': {'label': 'Attendance', 'route': 'hr.attendance_management'},
    'assets': {'label': 'Assets', 'route': 'hr.assets_management'},
    'petty_cash': {'label': 'Petty Cash', 'route': 'hr.petty_cash_management'},
    'hr_calendar': {'label': 'HR Calendar', 'route': 'hr.hr_calendar'}
}

MANAGEMENT_MODULES = {
    'daily_status': {'label': 'Daily Status', 'route': 'hr.daily_attendance_status'},
    'training_programs': {'label': 'Training Programs', 'route': 'core.assign_training'},
    'job_requests': {'label': 'Job Requests', 'route': 'hr.job_requests'},
    'job_postings': {'label': 'Job Postings', 'route': 'hr.job_postings'},
    'applications': {'label': 'Applications', 'route': 'hr.job_applications'},
    'interviews': {'label': 'Interviews', 'route': 'hr.interviews'}
}

# Module Access Control
MODULE_PERMISSIONS = {
    # Personal Modules - Available to all employees
    'dashboard': lambda user: True,
    'my_profile': lambda user: True,
    'my_attendance': lambda user: True,
    'my_trainings': lambda user: True,
    
    # Work Modules - Available to all employees
    'projects': lambda user: True,
    'project_list': lambda user: True,
    'create_project': lambda user: True,
    'activity_log': lambda user: True,
    'calendar_events': lambda user: True,
    'notifications': lambda user: True,
    'appointments': lambda user: True,
    'conference_rooms': lambda user: True,
    'team_chats': lambda user: True,
    
    # HR Modules - Available to HR, Admin, and Management
    'create_user': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    'hr_dashboard': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    'employee_management': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    'salary_management': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    'attendance': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    'assets': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    'petty_cash': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    'hr_calendar': lambda user: user.has_role('HR') or user.has_role('Admin') or user.has_role('Management'),
    
    # Management Modules
    'daily_status': lambda user: (
        user.has_role('HR') or 
        user.has_role('Admin') or 
        user.has_role('Management') or 
        user.has_role('General Manager') or 
        user.has_role('Manager')
    ),
    'training_programs': lambda user: (
        user.has_role('HR') or 
        user.has_role('Admin') or 
        user.has_role('Management') or 
        user.has_role('General Manager') or 
        user.has_role('Manager')
    ),
    'job_requests': lambda user: (
        user.has_role('HR') or 
        user.has_role('Admin') or 
        user.has_role('Management') or 
        user.has_role('General Manager') or
        user.has_role('Manager')
    ),
    'job_postings': lambda user: (
        user.has_role('HR') or 
        user.has_role('Admin') or 
        user.has_role('Management') or 
        user.has_role('General Manager')
    ),
    'applications': lambda user: (
        user.has_role('HR') or 
        user.has_role('Admin') or 
        user.has_role('Management') or 
        user.has_role('General Manager')
    ),
    'interviews': lambda user: (
        user.has_role('HR') or 
        user.has_role('Admin') or 
        user.has_role('Management') or 
        user.has_role('General Manager')
    )
}

def module_required(module_name):
    """Decorator to check if user has access to a specific module."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if module_name not in MODULE_PERMISSIONS:
                abort(404)
            
            if not MODULE_PERMISSIONS[module_name](current_user):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_accessible_modules(user):
    """Get all modules accessible to the user."""
    accessible_modules = {}
    
    # Add personal modules
    accessible_modules['personal'] = {
        name: data for name, data in PERSONAL_MODULES.items()
        if MODULE_PERMISSIONS[name](user)
    }
    
    # Add work modules
    accessible_modules['work'] = {
        name: data for name, data in WORK_MODULES.items()
        if MODULE_PERMISSIONS[name](user)
    }
    
    # Add HR modules
    accessible_modules['hr'] = {
        name: data for name, data in HR_MODULES.items()
        if MODULE_PERMISSIONS[name](user)
    }
    
    # Add management modules
    accessible_modules['management'] = {
        name: data for name, data in MANAGEMENT_MODULES.items()
        if MODULE_PERMISSIONS[name](user)
    }
    
    return accessible_modules 