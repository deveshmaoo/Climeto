# HRMSV3_optimized/app/services/attendance_service.py
from datetime import datetime, time
from flask import request, flash
from ..models.attendance import Attendance, AttendanceSetting
from ..database import db
from ..utils.geolocation import get_location_from_ip
from ..utils.device_fingerprint import get_device_fingerprint

class AttendanceService:
    @staticmethod
    def clock_in(employee_id):
        """Handle employee clock in with security checks"""
        ip_address = request.remote_addr
        flash(f"Attempting clock-in from IP: {ip_address}", "info") # Temporary debug flash
        
        # --- Attendance Restriction Check ---
        # Fetch active IP and location restrictions
        allowed_ips = {s.value for s in AttendanceSetting.query.filter_by(setting_type='allowed_ip', is_active=True).all()}
        allowed_locations = {s.value for s in AttendanceSetting.query.filter_by(setting_type='allowed_location', is_active=True).all()}

        # If there are IP restrictions, enforce them
        if allowed_ips and ip_address not in allowed_ips:
            return False, "Clock-in failed: Your IP address is not authorized."

        # If there are location restrictions, enforce them
        if allowed_locations:
            location = get_location_from_ip(ip_address)
            if location not in allowed_locations:
                return False, f"Clock-in failed: Your location ({location}) is not authorized."
        # --- End of Restriction Check ---

        # Check if already clocked in today
        today = datetime.utcnow().date()
        existing_record = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()

        if existing_record and existing_record.clock_in:
            return False, "Already clocked in today"

        # Get current time and location
        current_time = datetime.utcnow()
        device_id = get_device_fingerprint(request)
        location = get_location_from_ip(ip_address)

        # Create or update attendance record
        if not existing_record:
            attendance = Attendance(
                employee_id=employee_id,
                date=today,
                clock_in=current_time,
                clock_in_ip=ip_address,
                clock_in_device=device_id,
                clock_in_location=location,
                work_mode='Office'  # Default to office for most employees
            )
            db.session.add(attendance)
        else:
            existing_record.clock_in = current_time
            existing_record.clock_in_ip = ip_address
            existing_record.clock_in_device = device_id
            existing_record.clock_in_location = location

        # Update status based on time
        if current_time.time() > time(9, 30):
            attendance.status = 'Late'
        else:
            attendance.status = 'Present'

        db.session.commit()
        return True, "Successfully clocked in"

    @staticmethod
    def clock_out(employee_id):
        """Handle employee clock out with security checks"""
        today = datetime.utcnow().date()
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()

        if not attendance or not attendance.clock_in:
            return False, "No clock in record found for today"

        if attendance.clock_out:
            return False, "Already clocked out today"

        # Get current time and location
        current_time = datetime.utcnow()
        ip_address = request.remote_addr
        device_id = get_device_fingerprint(request)
        location = get_location_from_ip(ip_address)

        # Update attendance record
        attendance.clock_out = current_time
        attendance.clock_out_ip = ip_address
        attendance.clock_out_device = device_id
        attendance.clock_out_location = location

        # Update status if leaving early
        if current_time.time() < time(18, 0):
            attendance.status = 'Early Leave'

        db.session.commit()
        return True, "Successfully clocked out"

    @staticmethod
    def get_today_attendance(employee_id):
        """Get today's attendance record for an employee"""
        today = datetime.utcnow().date()
        return Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()

    @staticmethod
    def get_attendance_summary(employee_id, start_date, end_date):
        """Get attendance summary for an employee within a date range"""
        records = Attendance.get_employee_attendance(employee_id, start_date, end_date)
        
        summary = {
            'total_days': len(records),
            'present_days': sum(1 for r in records if r.status == 'Present'),
            'late_days': sum(1 for r in records if r.status == 'Late'),
            'early_leaves': sum(1 for r in records if r.is_early_leave),
            'total_hours': sum(r.total_hours for r in records),
            'records': records
        }
        
        return summary

    @staticmethod
    def get_department_summary(department, date=None):
        """Get attendance summary for a department"""
        if not date:
            date = datetime.utcnow().date()
            
        records = Attendance.get_department_attendance(department, date)
        
        summary = {
            'total_employees': len(records),
            'present': sum(1 for r in records if r.status == 'Present'),
            'late': sum(1 for r in records if r.status == 'Late'),
            'absent': sum(1 for r in records if not r.clock_in),
            'early_leaves': sum(1 for r in records if r.is_early_leave),
            'records': records
        }
        
        return summary

    @staticmethod
    def clock_in_with_user(current_user):
        if not current_user.employee:
            print(f"Creating employee for user: {current_user.email}")
            # ... rest of the code