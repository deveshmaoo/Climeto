# HRMSV3_optimized/app/models/__init__.py

# This file makes the 'models' directory a Python package.
# Import models to make them easier to access
from . import users, employee, project, hr, attendance, calendar, notifications
from .users import User, Role
from .employee import Employee
from .project import Project
from .hr import (
    JobPosting, JobApplication, Interview, InterviewParticipant, JobRequest,
    Salary, Payroll, HREvent, Asset, AssetMaintenance, CleaningLog, PettyCash, 
    Appointment, AppointmentParticipant, ConferenceRoom, ConferenceBooking
)
from .attendance import Attendance, SalaryDetail
from .calendar import CalendarEvent
from .notifications import Notification, NotificationPreference, NotificationService