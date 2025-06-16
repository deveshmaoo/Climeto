from flask import render_template, request, flash, redirect, url_for, jsonify, send_file, current_app
from flask_login import login_required, current_user
from ..models.hr import (
    JobPosting, JobApplication, Interview, InterviewParticipant, JobRequest,
    Salary, Payroll, HREvent, Asset, AssetMaintenance, CleaningLog, PettyCash,
    Appointment, AppointmentParticipant, ConferenceRoom, ConferenceBooking
)
from ..models.attendance import Attendance, AttendanceSetting
from ..models.employee import Leave
from ..models.employee import Employee
from ..models.calendar import CalendarEvent
from ..database import db
from . import bp
from ..utils.decorators import role_required
from datetime import datetime, date, timedelta
import io
import os
from werkzeug.utils import secure_filename

# Dashboard
@bp.route('/dashboard')
@login_required
@role_required('HR', 'Admin', 'Management')
def dashboard():
    """HR Dashboard with key metrics and quick actions."""
    # Quick stats
    total_employees = Employee.query.count()
    pending_applications = JobApplication.query.filter_by(status='Applied').count()
    pending_leaves = Leave.query.filter_by(status='Pending').count()
    active_job_postings = JobPosting.query.filter_by(status='Active').count()
    
    # Upcoming events (birthdays, anniversaries)
    today = date.today()
    next_30_days = today + timedelta(days=30)
    
    # Get birthdays in next 30 days
    upcoming_birthdays = db.session.query(Employee).filter(
        db.extract('month', Employee.date_of_birth) >= today.month,
        db.extract('day', Employee.date_of_birth) >= today.day
    ).limit(5).all()
    
    # Recent activities
    recent_applications = JobApplication.query.order_by(JobApplication.applied_date.desc()).limit(5).all()
    recent_leaves = Leave.query.order_by(Leave.created_at.desc()).limit(5).all()
    
    return render_template('hr/dashboard.html',
                         total_employees=total_employees,
                         pending_applications=pending_applications,
                         pending_leaves=pending_leaves,
                         active_job_postings=active_job_postings,
                         upcoming_birthdays=upcoming_birthdays,
                         recent_applications=recent_applications,
                         recent_leaves=recent_leaves)

# HIRING MANAGEMENT
@bp.route('/hiring/jobs')
@login_required
@role_required('HR', 'Admin', 'Management')
def job_postings():
    """List all job postings."""
    jobs = JobPosting.query.order_by(JobPosting.posted_date.desc()).all()
    return render_template('hr/job_postings.html', jobs=jobs)

@bp.route('/hiring/job/create', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def create_job_posting():
    """Create a new job posting."""
    if request.method == 'POST':
        try:
            job = JobPosting(
                title=request.form['title'],
                department=request.form['department'],
                description=request.form['description'],
                requirements=request.form['requirements'],
                salary_range_min=float(request.form['salary_range_min']) if request.form['salary_range_min'] else None,
                salary_range_max=float(request.form['salary_range_max']) if request.form['salary_range_max'] else None,
                employment_type=request.form['employment_type'],
                location=request.form['location'],
                posted_by=current_user.employee.id,
                application_deadline=datetime.strptime(request.form['application_deadline'], '%Y-%m-%d').date() if request.form['application_deadline'] else None,
                openings=int(request.form['openings'])
            )
            
            db.session.add(job)
            db.session.commit()
            flash('Job posting created successfully!', 'success')
            return redirect(url_for('hr.job_postings'))
        except Exception as e:
            flash(f'Error creating job posting: {str(e)}', 'danger')
    
    return render_template('hr/create_job_posting.html')

@bp.route('/hiring/applications')
@login_required
@role_required('HR', 'Admin', 'Management')
def job_applications():
    """List all job applications."""
    status_filter = request.args.get('status', 'all')
    job_filter = request.args.get('job', 'all')
    
    query = JobApplication.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if job_filter != 'all':
        query = query.filter_by(job_posting_id=job_filter)
    
    applications = query.order_by(JobApplication.applied_date.desc()).all()
    job_postings = JobPosting.query.filter_by(status='Active').all()
    
    return render_template('hr/job_applications.html', 
                         applications=applications,
                         job_postings=job_postings,
                         status_filter=status_filter,
                         job_filter=job_filter)

@bp.route('/hiring/application/<int:id>')
@login_required
@role_required('HR', 'Admin', 'Management')
def application_detail(id):
    """View detailed application information."""
    application = JobApplication.query.get_or_404(id)
    interviews = Interview.query.filter_by(application_id=id).order_by(Interview.scheduled_date.desc()).all()
    
    # Get available interviewers for scheduling
    employees = Employee.query.filter_by(employment_status='Active').all()
    conference_rooms = ConferenceRoom.query.filter_by(is_active=True).all()
    
    return render_template('hr/application_detail.html', 
                         application=application, 
                         interviews=interviews,
                         employees=employees,
                         conference_rooms=conference_rooms)

@bp.route('/hiring/application/<int:application_id>/download-resume')
@login_required
@role_required('HR', 'Admin', 'Management')
def download_resume(application_id):
    """Download applicant's resume."""
    application = JobApplication.query.get_or_404(application_id)
    
    if not application.resume_path:
        flash('No resume found for this application.', 'warning')
        return redirect(url_for('hr.application_detail', id=application_id))
    
    try:
        resume_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), application.resume_path)
        if os.path.exists(resume_path):
            return send_file(resume_path, 
                           as_attachment=True, 
                           download_name=application.resume_filename or f"{application.applicant_name}_resume.pdf")
        else:
            flash('Resume file not found on server.', 'danger')
            return redirect(url_for('hr.application_detail', id=application_id))
    except Exception as e:
        flash(f'Error downloading resume: {str(e)}', 'danger')
        return redirect(url_for('hr.application_detail', id=application_id))

@bp.route('/hiring/application/<int:application_id>/update-status', methods=['POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def update_application_status(application_id):
    """Update application status."""
    try:
        application = JobApplication.query.get_or_404(application_id)
        new_status = request.form['status']
        notes = request.form.get('notes', '')
        
        application.status = new_status
        application.reviewed_by = current_user.employee.id
        application.review_date = datetime.utcnow()
        if notes:
            application.notes = (application.notes or '') + f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {current_user.employee.full_name}: {notes}"
        
        if request.form.get('hr_rating'):
            application.hr_rating = int(request.form['hr_rating'])
        
        db.session.commit()
        flash(f'Application status updated to {new_status}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating application status: {str(e)}', 'danger')
    
    return redirect(url_for('hr.application_detail', id=application_id))

# SALARY MANAGEMENT
@bp.route('/salary/employees')
@login_required
@role_required('HR', 'Admin', 'Management')
def salary_management():
    """Employee salary management."""
    employees = Employee.query.all()
    salaries = {}
    
    for emp in employees:
        current_salary = Salary.query.filter_by(employee_id=emp.id, is_active=True).first()
        salaries[emp.id] = current_salary
    
    return render_template('hr/salary_management.html', employees=employees, salaries=salaries)

@bp.route('/salary/employee/<int:employee_id>/set', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def set_employee_salary(employee_id):
    """Set or update employee salary."""
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        try:
            # Deactivate current salary
            current_salary = Salary.query.filter_by(employee_id=employee_id, is_active=True).first()
            if current_salary:
                current_salary.is_active = False
                current_salary.effective_to = date.today()
            
            # Create new salary record
            new_salary = Salary(
                employee_id=employee_id,
                basic_salary=float(request.form['basic_salary']),
                hra=float(request.form['hra']),
                transport_allowance=float(request.form['transport_allowance']),
                medical_allowance=float(request.form['medical_allowance']),
                special_allowance=float(request.form['special_allowance']),
                bonus=float(request.form['bonus']),
                overtime_rate=float(request.form['overtime_rate']),
                effective_from=datetime.strptime(request.form['effective_from'], '%Y-%m-%d').date(),
                updated_by=current_user.employee.id
            )
            
            db.session.add(new_salary)
            db.session.commit()
            flash(f'Salary updated for {employee.first_name} {employee.last_name}!', 'success')
            return redirect(url_for('hr.salary_management'))
        except Exception as e:
            flash(f'Error updating salary: {str(e)}', 'danger')
    
    current_salary = Salary.query.filter_by(employee_id=employee_id, is_active=True).first()
    return render_template('hr/set_salary.html', employee=employee, current_salary=current_salary)

# ATTENDANCE MANAGEMENT
@bp.route('/attendance')
@login_required
@role_required('HR', 'Admin', 'Management')
def attendance_management():
    """Attendance overview and management."""
    today = date.today()
    month_start = today.replace(day=1)
    
    # Get attendance stats for current month
    total_employees = Employee.query.count()
    present_today = Attendance.query.filter(
        Attendance.date == today,
        Attendance.status == 'Present'
    ).count()
    
    # Recent attendance records
    recent_attendance = Attendance.query.filter(
        Attendance.date >= month_start
    ).order_by(Attendance.date.desc(), Attendance.in_time.desc()).limit(20).all()
    
    return render_template('hr/attendance_management.html',
                         total_employees=total_employees,
                         present_today=present_today,
                         recent_attendance=recent_attendance,
                         today=today)

@bp.route('/attendance/upload', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def upload_attendance():
    """Upload attendance data from Excel file."""
    if request.method == 'POST':
        try:
            file = request.files['file']
            if file and file.filename.endswith(('.csv')):
                # For now, we'll support CSV files instead of Excel
                # This can be enhanced later with proper Excel support
                flash('Excel upload feature will be implemented. Please use CSV format for now.', 'info')
                return redirect(url_for('hr.attendance_management'))
            else:
                flash('Please upload a valid CSV file (.csv)', 'danger')
        except Exception as e:
            flash(f'Error uploading attendance: {str(e)}', 'danger')
    
    return render_template('hr/upload_attendance.html')

# ENHANCED ATTENDANCE MANAGEMENT WITH HIERARCHY
@bp.route('/attendance/employee/<int:employee_id>')
@login_required
@role_required('HR', 'Admin', 'Management', 'General Manager', 'Department Manager')
def employee_attendance(employee_id):
    """View individual employee attendance records with hierarchy permissions."""
    target_employee = Employee.query.get_or_404(employee_id)
    current_employee = current_user.employee
    
    # Permission check based on hierarchy and role
    can_view = False
    
    if current_user.role in ['Admin', 'HR', 'Management', 'General Manager']:
        can_view = True
    elif current_user.role == 'Department Manager':
        # Department managers can only view their department employees
        if target_employee.department == current_employee.department:
            can_view = True
    elif current_employee.id == target_employee.reporting_manager_id:
        # Direct managers can view their reports
        can_view = True
    
    if not can_view:
        flash('You do not have permission to view this employee\'s attendance records.', 'danger')
        return redirect(url_for('hr.attendance_management'))
    
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = date.today().replace(day=1)  # First day of current month
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = date.today()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get attendance records
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).order_by(Attendance.date.desc()).all()
    
    # Get leave records for the same period
    leave_records = Leave.query.filter(
        Leave.employee_id == employee_id,
        Leave.start_date <= end_date,
        Leave.end_date >= start_date,
        Leave.status == 'Approved'
    ).all()
    
    # Calculate stats
    total_days = (end_date - start_date).days + 1
    present_days = len([a for a in attendance_records if a.status in ['Present', 'Late']])
    absent_days = len([a for a in attendance_records if a.status == 'Absent'])
    leave_days = sum([l.days for l in leave_records])
    
    return render_template('hr/employee_attendance.html',
                         employee=target_employee,
                         attendance_records=attendance_records,
                         leave_records=leave_records,
                         start_date=start_date,
                         end_date=end_date,
                         stats={
                             'total_days': total_days,
                             'present_days': present_days,
                             'absent_days': absent_days,
                             'leave_days': leave_days
                         })

@bp.route('/attendance/daily-status')
@login_required
@role_required('HR', 'Admin', 'Management', 'General Manager')
def daily_attendance_status():
    """Daily attendance status showing who's present, on leave, or missing."""
    target_date = request.args.get('date')
    if target_date:
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    else:
        target_date = date.today()
    
    # Get all active employees
    all_employees = Employee.query.filter_by(employment_status='Active').all()
    
    # Get attendance records for the target date
    attendance_today = Attendance.query.filter_by(date=target_date).all()
    attendance_dict = {a.employee_id: a for a in attendance_today}
    
    # Get approved leaves for the target date
    leaves_today = Leave.query.filter(
        Leave.start_date <= target_date,
        Leave.end_date >= target_date,
        Leave.status == 'Approved'
    ).all()
    leave_employee_ids = {l.employee_id for l in leaves_today}
    
    # Categorize employees
    present_employees = []
    on_leave_employees = []
    missing_employees = []
    
    for employee in all_employees:
        if employee.id in attendance_dict:
            # Employee has attendance record
            attendance = attendance_dict[employee.id]
            present_employees.append({
                'employee': employee,
                'attendance': attendance,
                'status': 'Present'
            })
        elif employee.id in leave_employee_ids:
            # Employee is on approved leave
            leave = next(l for l in leaves_today if l.employee_id == employee.id)
            on_leave_employees.append({
                'employee': employee,
                'leave': leave,
                'status': 'On Leave'
            })
        else:
            # Employee is missing
            missing_employees.append({
                'employee': employee,
                'status': 'Missing'
            })
    
    return render_template('hr/daily_attendance_status.html',
                         target_date=target_date,
                         present_employees=present_employees,
                         on_leave_employees=on_leave_employees,
                         missing_employees=missing_employees,
                         total_employees=len(all_employees))

# EMPLOYEE DETAILS MANAGEMENT
@bp.route('/employees')
@login_required
@role_required('HR', 'Admin', 'Management')
def employee_management():
    """Comprehensive employee management."""
    search = request.args.get('search', '')
    department_filter = request.args.get('department', 'all')
    status_filter = request.args.get('status', 'all')
    
    query = Employee.query
    
    if search:
        query = query.filter(
            db.or_(
                Employee.first_name.contains(search),
                Employee.last_name.contains(search),
                Employee.work_email.contains(search),
                Employee.employee_id.contains(search)
            )
        )
    
    if department_filter != 'all':
        query = query.filter_by(department=department_filter)
    
    if status_filter != 'all':
        if status_filter == 'active':
            query = query.filter_by(employment_status='Active')
        else:
            query = query.filter(Employee.employment_status != 'Active')
    
    employees = query.order_by(Employee.first_name).all()
    departments = db.session.query(Employee.department).distinct().all()
    
    return render_template('hr/employee_management.html',
                         employees=employees,
                         departments=departments,
                         search=search,
                         department_filter=department_filter,
                         status_filter=status_filter)

# ASSETS MANAGEMENT
@bp.route('/assets')
@login_required
@role_required('HR', 'Admin', 'Management')
def assets_management():
    """Asset management dashboard."""
    assets = Asset.query.order_by(Asset.created_at.desc()).all()
    return render_template('hr/assets_management.html', assets=assets)

@bp.route('/assets/create', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def create_asset():
    """Create new asset record."""
    if request.method == 'POST':
        try:
            asset = Asset(
                asset_tag=request.form['asset_tag'],
                name=request.form['name'],
                category=request.form['category'],
                brand=request.form.get('brand'),
                model=request.form.get('model'),
                serial_number=request.form.get('serial_number'),
                purchase_date=datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date() if request.form['purchase_date'] else None,
                purchase_price=float(request.form['purchase_price']) if request.form['purchase_price'] else None,
                supplier=request.form.get('supplier'),
                warranty_expiry=datetime.strptime(request.form['warranty_expiry'], '%Y-%m-%d').date() if request.form['warranty_expiry'] else None,
                location=request.form.get('location'),
                assigned_to=int(request.form['assigned_to']) if request.form['assigned_to'] else None,
                status=request.form['status'],
                condition=request.form['condition'],
                notes=request.form.get('notes')
            )
            
            db.session.add(asset)
            db.session.commit()
            flash('Asset created successfully!', 'success')
            return redirect(url_for('hr.assets_management'))
        except Exception as e:
            flash(f'Error creating asset: {str(e)}', 'danger')
    
    employees = Employee.query.filter_by(employment_status='Active').all()
    return render_template('hr/create_asset.html', employees=employees)

# PETTY CASH MANAGEMENT
@bp.route('/petty-cash')
@login_required
@role_required('HR', 'Admin', 'Management')
def petty_cash_management():
    """Petty cash management."""
    transactions = PettyCash.query.order_by(PettyCash.transaction_date.desc()).limit(50).all()
    
    # Calculate current balance
    total_additions = db.session.query(db.func.sum(PettyCash.amount)).filter_by(transaction_type='Addition').scalar() or 0
    total_expenses = db.session.query(db.func.sum(PettyCash.amount)).filter_by(transaction_type='Expense').scalar() or 0
    current_balance = total_additions - total_expenses
    
    # Calculate this month's total expenses
    today = date.today()
    month_start = today.replace(day=1)
    month_expenses = db.session.query(db.func.sum(PettyCash.amount)).filter(
        PettyCash.transaction_type == 'Expense',
        PettyCash.transaction_date >= month_start,
        PettyCash.transaction_date <= today
    ).scalar() or 0
    
    # Count pending transactions
    pending_count = PettyCash.query.filter_by(status='Pending').count()
    
    return render_template('hr/petty_cash_management.html',
                         transactions=transactions,
                         current_balance=current_balance,
                         month_total=month_expenses,
                         pending_transactions=pending_count)

@bp.route('/petty-cash/add', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def add_petty_cash():
    """Add petty cash transaction."""
    if request.method == 'POST':
        try:
            transaction = PettyCash(
                transaction_date=datetime.strptime(request.form['transaction_date'], '%Y-%m-%d').date(),
                transaction_type=request.form['transaction_type'],
                amount=float(request.form['amount']),
                category=request.form['category'],
                description=request.form['description'],
                receipt_number=request.form.get('receipt_number'),
                requested_by=current_user.employee.id,
                status='Approved' if current_user.is_admin() else 'Pending'
            )
            
            # Handle receipt upload
            if 'receipt_file' in request.files:
                file = request.files['receipt_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    receipt_path = f"receipts/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    full_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), receipt_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    file.save(full_path)
                    transaction.receipt_path = receipt_path
            
            db.session.add(transaction)
            db.session.commit()
            flash('Petty cash transaction added successfully!', 'success')
            return redirect(url_for('hr.petty_cash_management'))
        except Exception as e:
            flash(f'Error adding transaction: {str(e)}', 'danger')
    
    return render_template('hr/add_petty_cash.html')

# HR CALENDAR
@bp.route('/calendar')
@login_required
@role_required('HR', 'Admin', 'Management')
def hr_calendar():
    """HR calendar with birthdays, anniversaries, events."""
    today = date.today()
    
    # Get events for current month
    month_start = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    
    # HR Events
    hr_events = HREvent.query.filter(
        HREvent.event_date >= month_start,
        HREvent.event_date < next_month
    ).all()
    
    # Employee birthdays and anniversaries
    employees = Employee.query.filter_by(employment_status='Active').all()
    
    calendar_events = []
    
    # Add HR events
    for event in hr_events:
        calendar_events.append({
            'title': event.title,
            'date': event.event_date.date(),
            'type': event.event_type,
            'description': event.description
        })
    
    # Add birthdays
    for emp in employees:
        if emp.date_of_birth:
            birthday_this_year = emp.date_of_birth.replace(year=today.year)
            if month_start <= birthday_this_year < next_month:
                calendar_events.append({
                    'title': f"{emp.first_name} {emp.last_name}'s Birthday",
                    'date': birthday_this_year,
                    'type': 'Birthday',
                    'description': f'Birthday of {emp.first_name} {emp.last_name}'
                })
    
    # Add anniversaries
    for emp in employees:
        if emp.joining_date:
            anniversary_this_year = emp.joining_date.replace(year=today.year)
            if month_start <= anniversary_this_year < next_month:
                years = today.year - emp.joining_date.year
                calendar_events.append({
                    'title': f"{emp.first_name} {emp.last_name}'s {years} Year Anniversary",
                    'date': anniversary_this_year,
                    'type': 'Anniversary',
                    'description': f'{years} years with the company'
                })
    
    return render_template('hr/hr_calendar.html', calendar_events=calendar_events, today=today)

# APPOINTMENT SCHEDULING
@bp.route('/appointments')
@login_required
def appointments():
    """View all appointments for current user."""
    employee_id = current_user.employee.id
    
    # Get appointments where user is requester or participant
    requested_appointments = Appointment.query.filter_by(requested_by=employee_id).all()
    
    participated_appointments = db.session.query(Appointment)\
        .join(AppointmentParticipant)\
        .filter(AppointmentParticipant.employee_id == employee_id)\
        .all()
    
    all_appointments = list(set(requested_appointments + participated_appointments))
    all_appointments.sort(key=lambda x: (x.appointment_date, x.start_time), reverse=True)
    
    return render_template('hr/appointments.html', appointments=all_appointments)

@bp.route('/appointments/create', methods=['GET', 'POST'])
@login_required
def create_appointment():
    """Create new appointment."""
    if request.method == 'POST':
        try:
            appointment = Appointment(
                title=request.form['title'],
                description=request.form.get('description'),
                requested_by=current_user.employee.id,
                appointment_date=datetime.strptime(request.form['appointment_date'], '%Y-%m-%d').date(),
                start_time=datetime.strptime(request.form['start_time'], '%H:%M').time(),
                end_time=datetime.strptime(request.form['end_time'], '%H:%M').time(),
                location=request.form.get('location'),
                meeting_type=request.form['meeting_type'],
                notes=request.form.get('notes')
            )
            
            db.session.add(appointment)
            db.session.flush()  # Get the ID
            
            # Add participants
            participant_ids = request.form.getlist('participants')
            for participant_id in participant_ids:
                if participant_id:
                    participant = AppointmentParticipant(
                        appointment_id=appointment.id,
                        employee_id=int(participant_id)
                    )
                    db.session.add(participant)
            
            db.session.commit()
            flash('Appointment created successfully!', 'success')
            return redirect(url_for('hr.appointments'))
        except Exception as e:
            flash(f'Error creating appointment: {str(e)}', 'danger')
    
    employees = Employee.query.filter_by(employment_status='Active').all()
    return render_template('hr/create_appointment.html', employees=employees)

# CONFERENCE ROOM BOOKING
@bp.route('/conference-rooms')
@login_required
def conference_rooms():
    """View conference rooms and bookings."""
    rooms = ConferenceRoom.query.filter_by(is_active=True).all()
    today = date.today()
    
    # Get today's bookings and total bookings count for each room
    for room in rooms:
        room.today_bookings = ConferenceBooking.query.filter(
            ConferenceBooking.room_id == room.id,
            ConferenceBooking.booking_date == today,
            ConferenceBooking.status == 'Confirmed'
        ).order_by(ConferenceBooking.start_time).all()
        
        # Get all recent bookings for the room
        room.bookings = ConferenceBooking.query.filter(
            ConferenceBooking.room_id == room.id
        ).order_by(ConferenceBooking.booking_date.desc()).limit(10).all()
    
    # Count total bookings today across all rooms
    total_bookings_today = ConferenceBooking.query.filter(
        ConferenceBooking.booking_date == today,
        ConferenceBooking.status == 'Confirmed'
    ).count()
    
    return render_template('hr/conference_rooms.html', 
                         rooms=rooms, 
                         today=today,
                         total_bookings_today=total_bookings_today)

@bp.route('/conference-rooms/book', methods=['GET', 'POST'])
@login_required
def book_conference_room():
    """Book a conference room."""
    if request.method == 'POST':
        try:
            # Check for conflicts
            room_id = int(request.form['room_id'])
            booking_date = datetime.strptime(request.form['booking_date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
            end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
            
            # Check for overlapping bookings
            conflicts = ConferenceBooking.query.filter(
                ConferenceBooking.room_id == room_id,
                ConferenceBooking.booking_date == booking_date,
                ConferenceBooking.status == 'Confirmed',
                db.or_(
                    db.and_(ConferenceBooking.start_time <= start_time, ConferenceBooking.end_time > start_time),
                    db.and_(ConferenceBooking.start_time < end_time, ConferenceBooking.end_time >= end_time),
                    db.and_(ConferenceBooking.start_time >= start_time, ConferenceBooking.end_time <= end_time)
                )
            ).first()
            
            if conflicts:
                flash('This time slot is already booked. Please choose a different time.', 'danger')
                return redirect(url_for('hr.book_conference_room'))
            
            booking = ConferenceBooking(
                room_id=room_id,
                booked_by=current_user.employee.id,
                title=request.form['title'],
                description=request.form.get('description'),
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time,
                attendees_count=int(request.form.get('attendees_count', 1)),
                special_requirements=request.form.get('special_requirements')
            )
            
            db.session.add(booking)
            db.session.commit()
            flash('Conference room booked successfully!', 'success')
            return redirect(url_for('hr.conference_rooms'))
        except Exception as e:
            flash(f'Error booking room: {str(e)}', 'danger')
    
    rooms = ConferenceRoom.query.filter_by(is_active=True).all()
    return render_template('hr/book_conference_room.html', rooms=rooms)

# ATTENDANCE SETTINGS
@bp.route('/attendance-settings', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def attendance_settings():
    """Manage attendance clock-in settings."""
    if request.method == 'POST':
        try:
            setting_type = request.form.get('setting_type')
            value = request.form.get('value')
            description = request.form.get('description')

            if not setting_type or not value:
                flash('Setting Type and Value are required.', 'danger')
            else:
                new_setting = AttendanceSetting(
                    setting_type=setting_type,
                    value=value,
                    description=description
                )
                db.session.add(new_setting)
                db.session.commit()
                flash('New attendance setting has been added.', 'success')
            return redirect(url_for('hr.attendance_settings'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding setting: {str(e)}', 'danger')

    # For GET request
    allowed_ips = AttendanceSetting.query.filter_by(setting_type='allowed_ip', is_active=True).all()
    allowed_locations = AttendanceSetting.query.filter_by(setting_type='allowed_location', is_active=True).all()

    return render_template(
        'hr/attendance_settings.html',
        allowed_ips=allowed_ips,
        allowed_locations=allowed_locations
    )

@bp.route('/attendance-settings/delete/<int:setting_id>', methods=['POST'])
@login_required
@role_required('Admin')
def delete_attendance_setting(setting_id):
    """Delete an attendance setting."""
    try:
        setting = AttendanceSetting.query.get_or_404(setting_id)
        db.session.delete(setting)
        db.session.commit()
        flash('Setting deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting setting: {str(e)}', 'danger')
    
    return redirect(url_for('hr.attendance_settings'))

# JOB REQUEST MANAGEMENT
@bp.route('/job-requests')
@login_required
@role_required('HR', 'Admin', 'Management', 'General Manager', 'Manager')
def job_requests():
    """List all job requests with role-based filtering."""
    # Get requests based on user role
    if current_user.has_role('HR') or current_user.has_role('Admin'):
        # HR and Admin can see all requests
        requests = JobRequest.query.order_by(JobRequest.request_date.desc()).all()
    elif current_user.has_role('Management') or current_user.has_role('General Manager'):
        # Management can see all requests for approval
        requests = JobRequest.query.order_by(JobRequest.request_date.desc()).all()
    else:
        # Managers can only see their own requests
        requests = JobRequest.query.filter_by(requested_by=current_user.employee.id).order_by(JobRequest.request_date.desc()).all()
    
    return render_template('hr/job_requests.html', requests=requests)

@bp.route('/job-requests/create', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management', 'General Manager', 'Manager')
def create_job_request():
    """Create a new job request."""
    if request.method == 'POST':
        try:
            job_request = JobRequest(
                title=request.form['title'],
                department=request.form['department'],
                description=request.form['description'],
                requirements=request.form['requirements'],
                justification=request.form['justification'],
                budget_min=float(request.form['budget_min']) if request.form['budget_min'] else None,
                budget_max=float(request.form['budget_max']) if request.form['budget_max'] else None,
                employment_type=request.form['employment_type'],
                location=request.form['location'],
                openings=int(request.form['openings']),
                urgency=request.form['urgency'],
                expected_start_date=datetime.strptime(request.form['expected_start_date'], '%Y-%m-%d').date() if request.form['expected_start_date'] else None,
                application_deadline=datetime.strptime(request.form['application_deadline'], '%Y-%m-%d').date() if request.form['application_deadline'] else None,
                requested_by=current_user.employee.id
            )
            
            db.session.add(job_request)
            db.session.commit()
            flash('Job request submitted successfully! It will be reviewed by management.', 'success')
            return redirect(url_for('hr.job_requests'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating job request: {str(e)}', 'danger')
    
    return render_template('hr/create_job_request.html')

@bp.route('/job-requests/<int:request_id>')
@login_required
@role_required('HR', 'Admin', 'Management', 'General Manager', 'Manager')
def job_request_detail(request_id):
    """View detailed job request information."""
    job_request = JobRequest.query.get_or_404(request_id)
    
    # Check permissions
    if not (current_user.has_role('HR') or current_user.has_role('Admin') or 
            current_user.has_role('Management') or current_user.has_role('General Manager') or
            job_request.requested_by == current_user.employee.id):
        flash('You do not have permission to view this job request.', 'danger')
        return redirect(url_for('hr.job_requests'))
    
    return render_template('hr/job_request_detail.html', job_request=job_request)

@bp.route('/job-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@role_required('Management', 'General Manager', 'Admin')
def approve_job_request(request_id):
    """Approve a job request."""
    try:
        job_request = JobRequest.query.get_or_404(request_id)
        
        if job_request.status != 'Pending':
            flash('This request has already been processed.', 'warning')
            return redirect(url_for('hr.job_request_detail', request_id=request_id))
        
        job_request.status = 'Approved'
        job_request.approved_by = current_user.employee.id
        job_request.approval_date = datetime.utcnow()
        job_request.approval_notes = request.form.get('approval_notes', '')
        
        db.session.commit()
        flash('Job request approved successfully! HR can now create the job posting.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving job request: {str(e)}', 'danger')
    
    return redirect(url_for('hr.job_request_detail', request_id=request_id))

@bp.route('/job-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@role_required('Management', 'General Manager', 'Admin')
def reject_job_request(request_id):
    """Reject a job request."""
    try:
        job_request = JobRequest.query.get_or_404(request_id)
        
        if job_request.status != 'Pending':
            flash('This request has already been processed.', 'warning')
            return redirect(url_for('hr.job_request_detail', request_id=request_id))
        
        job_request.status = 'Rejected'
        job_request.approved_by = current_user.employee.id
        job_request.approval_date = datetime.utcnow()
        job_request.approval_notes = request.form.get('rejection_reason', '')
        
        db.session.commit()
        flash('Job request rejected.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting job request: {str(e)}', 'danger')
    
    return redirect(url_for('hr.job_request_detail', request_id=request_id))

@bp.route('/job-requests/<int:request_id>/create-posting', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin')
def create_posting_from_request(request_id):
    """Create a job posting from an approved job request."""
    job_request = JobRequest.query.get_or_404(request_id)
    
    if job_request.status != 'Approved':
        flash('Only approved job requests can be converted to job postings.', 'danger')
        return redirect(url_for('hr.job_request_detail', request_id=request_id))
    
    if job_request.job_posting_id:
        flash('A job posting has already been created for this request.', 'warning')
        return redirect(url_for('hr.job_postings'))
    
    if request.method == 'POST':
        try:
            job_posting = JobPosting(
                title=job_request.title,
                department=job_request.department,
                description=job_request.description,
                requirements=job_request.requirements,
                salary_range_min=job_request.budget_min,
                salary_range_max=job_request.budget_max,
                employment_type=job_request.employment_type,
                location=job_request.location,
                openings=job_request.openings,
                application_deadline=job_request.application_deadline,
                posted_by=current_user.employee.id
            )
            
            db.session.add(job_posting)
            db.session.flush()  # Get the ID
            
            # Link the job posting to the request
            job_request.job_posting_id = job_posting.id
            job_request.hr_assigned_to = current_user.employee.id
            job_request.hr_notes = request.form.get('hr_notes', '')
            
            db.session.commit()
            flash('Job posting created successfully from the approved request!', 'success')
            return redirect(url_for('hr.job_postings'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating job posting: {str(e)}', 'danger')
    
    return render_template('hr/create_posting_from_request.html', job_request=job_request)

# INTERVIEW MANAGEMENT
@bp.route('/interviews')
@login_required
@role_required('HR', 'Admin', 'Management')
def interviews():
    """List all interviews."""
    interviews = Interview.query.order_by(Interview.scheduled_date.desc()).all()
    return render_template('hr/interviews.html', interviews=interviews)

@bp.route('/interviews/create', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def create_interview():
    """Create a new interview."""
    if request.method == 'POST':
        try:
            interview = Interview(
                title=request.form['title'],
                description=request.form['description'],
                scheduled_date=datetime.strptime(request.form['scheduled_date'], '%Y-%m-%d').date() if request.form['scheduled_date'] else None,
                scheduled_time=datetime.strptime(request.form['scheduled_time'], '%H:%M').time() if request.form['scheduled_time'] else None,
                location=request.form['location'],
                interviewer_id=int(request.form['interviewer_id']) if request.form['interviewer_id'] else None,
                status=request.form['status']
            )
            
            db.session.add(interview)
            db.session.commit()
            flash('Interview created successfully!', 'success')
            return redirect(url_for('hr.interviews'))
        except Exception as e:
            flash(f'Error creating interview: {str(e)}', 'danger')
    
    employees = Employee.query.filter_by(employment_status='Active').all()
    return render_template('hr/create_interview.html', employees=employees)

@bp.route('/interviews/approve/<int:interview_id>', methods=['POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def approve_interview(interview_id):
    """Approve an interview."""
    try:
        interview = Interview.query.get_or_404(interview_id)
        interview.status = 'Approved'
        db.session.commit()
        flash('Interview approved successfully!', 'success')
        return redirect(url_for('hr.interviews'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving interview: {str(e)}', 'danger')
    
    return redirect(url_for('hr.interviews'))

@bp.route('/interviews/reject/<int:interview_id>', methods=['POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def reject_interview(interview_id):
    """Reject an interview."""
    try:
        interview = Interview.query.get_or_404(interview_id)
        interview.status = 'Rejected'
        db.session.commit()
        flash('Interview rejected successfully!', 'success')
        return redirect(url_for('hr.interviews'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting interview: {str(e)}', 'danger')
    
    return redirect(url_for('hr.interviews'))

# INTERVIEW PARTICIPANT MANAGEMENT
@bp.route('/interview-participants')
@login_required
@role_required('HR', 'Admin', 'Management')
def interview_participants():
    """List all interview participants."""
    participants = InterviewParticipant.query.order_by(InterviewParticipant.interview_id.desc()).all()
    return render_template('hr/interview_participants.html', participants=participants)

@bp.route('/interview-participants/create', methods=['GET', 'POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def create_interview_participant():
    """Create a new interview participant."""
    if request.method == 'POST':
        try:
            participant = InterviewParticipant(
                interview_id=int(request.form['interview_id']),
                employee_id=int(request.form['employee_id'])
            )
            
            db.session.add(participant)
            db.session.commit()
            flash('Interview participant created successfully!', 'success')
            return redirect(url_for('hr.interview_participants'))
        except Exception as e:
            flash(f'Error creating interview participant: {str(e)}', 'danger')
    
    interviews = Interview.query.filter_by(status='Scheduled').all()
    employees = Employee.query.filter_by(employment_status='Active').all()
    return render_template('hr/create_interview_participant.html', interviews=interviews, employees=employees)

@bp.route('/interview-participants/delete/<int:participant_id>', methods=['POST'])
@login_required
@role_required('HR', 'Admin', 'Management')
def delete_interview_participant(participant_id):
    """Delete an interview participant."""
    try:
        participant = InterviewParticipant.query.get_or_404(participant_id)
        db.session.delete(participant)
        db.session.commit()
        flash('Interview participant deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting interview participant: {str(e)}', 'danger')
    
    return redirect(url_for('hr.interview_participants')) 