"""
Employee routes for the HRMS application.
"""

from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from . import bp
from ..models.employee import Employee
from ..database import db
from ..services.attendance_service import AttendanceService
from ..utils.decorators import role_required

@bp.route('/profile')
@login_required
def profile():
    """Employee profile route."""
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    return render_template('employee/profile.html', employee=employee)

@bp.route('/list')
@login_required
def list_employees():
    """List all employees route."""
    employees = Employee.query.all()
    return render_template('employee/list.html', employees=employees)

@bp.route('/attendance')
@login_required
def attendance():
    """Employee attendance page"""
    # Check if user has an employee record
    if not current_user.employee:
        # Create employee record if it doesn't exist
        try:
            employee = Employee(
                # Required fields
                email=current_user.email,
                first_name=current_user.username,
                last_name='',
                employee_id=f'EMP{current_user.id:03d}',
                designation='Staff',
                joining_date=datetime.utcnow().date(),
                
                # Optional fields with defaults
                department=current_user.department,
                position='Employee',
                role=current_user.role.name,
                is_active=True,
                work_email=current_user.email,
                employment_status='Active',
                employment_type='Full-time',
                notice_period_days=30,
                
                # Timestamps
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(employee)
            db.session.commit()
            
            # Link user to employee
            current_user.user_id = employee.id
            db.session.commit()
            
            flash('Employee profile created successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating employee profile: {str(e)}. Please contact HR.', 'error')
            return redirect(url_for('core.index'))
    
    # Get today's attendance
    today_record = AttendanceService.get_today_attendance(current_user.employee.id)
    
    # Get attendance summary for the current month
    today = datetime.utcnow().date()
    first_day = today.replace(day=1)
    summary = AttendanceService.get_attendance_summary(
        current_user.employee.id,
        first_day,
        today
    )
    
    return render_template('employee/attendance.html',
                         today_record=today_record,
                         summary=summary)

@bp.route('/attendance/clock-in', methods=['POST'])
@login_required
def clock_in():
    """Handle clock in request"""
    success, message = AttendanceService.clock_in(current_user.employee.id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('employee.attendance'))

@bp.route('/attendance/clock-out', methods=['POST'])
@login_required
def clock_out():
    """Handle clock out request"""
    success, message = AttendanceService.clock_out(current_user.employee.id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('employee.attendance'))

@bp.route('/attendance/history')
@login_required
def attendance_history():
    """View attendance history"""
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.utcnow().date() - timedelta(days=30)
        
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.utcnow().date()
    
    # Get attendance summary
    summary = AttendanceService.get_attendance_summary(
        current_user.employee.id,
        start_date,
        end_date
    )
    
    return render_template('employee/attendance_history.html',
                         summary=summary,
                         start_date=start_date,
                         end_date=end_date) 