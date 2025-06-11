# HRMSV3_optimized/app/services/attendance_service.py
import pandas as pd
from datetime import datetime, time
from typing import List, Dict, Optional
from ..models.attendance import Attendance, SalaryDetail
from ..models.employee import Employee
from ..database import db
from ..exceptions import ValidationError, ResourceNotFoundError

class AttendanceService:
    @staticmethod
    def process_attendance_excel(file_path: str) -> int:
        """Process attendance Excel file and update database.
        
        Args:
            file_path: Path to the Excel file containing attendance data
            
        Returns:
            Number of attendance records processed
            
        Raises:
            ValidationError: If the Excel file is invalid or processing fails
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Expected columns: employee_id, date, in_time, out_time
            required_columns = ['employee_id', 'date', 'in_time', 'out_time']
            if not all(col in df.columns for col in required_columns):
                raise ValidationError("Excel file must contain all required columns: employee_id, date, in_time, out_time")
            
            attendance_records = []
            
            for _, row in df.iterrows():
                employee_id = int(row['employee_id'])
                date = pd.to_datetime(row['date']).date()
                in_time = pd.to_datetime(row['in_time']).time()
                out_time = pd.to_datetime(row['out_time']).time() if pd.notna(row['out_time']) else None
                
                # Calculate attendance status and deductions
                status, deduction_hours = AttendanceService.calculate_attendance_status(
                    employee_id, in_time
                )
                
                attendance = Attendance(
                    employee_id=employee_id,
                    date=date,
                    in_time=in_time,
                    out_time=out_time,
                    status=status,
                    deduction_hours=deduction_hours
                )
                attendance_records.append(attendance)
            
            # Bulk insert attendance records
            db.session.bulk_save_objects(attendance_records)
            db.session.commit()
            
            return len(attendance_records)
            
        except Exception as e:
            db.session.rollback()
            raise ValidationError(f"Error processing attendance Excel file: {str(e)}")

    @staticmethod
    def calculate_attendance_status(employee_id: int, in_time: time) -> tuple:
        """Calculate attendance status and deductions based on in_time.
        
        Args:
            employee_id: ID of the employee
            in_time: Time when employee checked in
            
        Returns:
            Tuple of (status, deduction_hours)
        """
        # Get employee's grace period from salary details
        salary_detail = SalaryDetail.query.filter_by(employee_id=employee_id).order_by(SalaryDetail.effective_date.desc()).first()
        grace_period = 15  # Default grace period in minutes
        
        # Standard office start time (10:00 AM)
        standard_start = time(10, 0)
        
        # Calculate grace period end time
        max_grace_time = time(10, grace_period)
        
        if in_time <= standard_start:
            return 'Present', 0
        elif in_time <= max_grace_time:
            return 'Present', 0
        else:
            # Late arrival
            return 'Late', 2  # 2 hours deduction for late arrival
            
    @staticmethod
    def get_monthly_attendance(employee_id: int, year: int, month: int) -> List[Attendance]:
        """Get monthly attendance report for an employee.
        
        Args:
            employee_id: ID of the employee
            year: Year to filter by
            month: Month to filter by (1-12)
            
        Returns:
            List of attendance records for the specified month
        """
        # Verify employee exists
        employee = Employee.query.get(employee_id)
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {employee_id} not found")
            
        return Attendance.query.filter(
            Attendance.employee_id == employee_id,
            db.extract('year', Attendance.date) == year,
            db.extract('month', Attendance.date) == month
        ).order_by(Attendance.date).all()

    @staticmethod
    def get_total_deductions(employee_id: int, year: int, month: int) -> float:
        """Calculate total deduction hours for an employee in a month.
        
        Args:
            employee_id: ID of the employee
            year: Year to filter by
            month: Month to filter by (1-12)
            
        Returns:
            Total deduction hours for the month
        """
        attendance_records = AttendanceService.get_monthly_attendance(employee_id, year, month)
        return sum(record.deduction_hours for record in attendance_records)
        
    @staticmethod
    def mark_attendance(employee_id: int, date: datetime.date, status: str, 
                       in_time: Optional[time] = None, out_time: Optional[time] = None) -> Attendance:
        """Mark attendance for an employee manually.
        
        Args:
            employee_id: ID of the employee
            date: Date of attendance
            status: Attendance status (Present, Late, Absent, etc.)
            in_time: Check-in time
            out_time: Check-out time
            
        Returns:
            Created or updated attendance record
        """
        # Check if attendance already exists for this date
        existing = Attendance.query.filter_by(
            employee_id=employee_id,
            date=date
        ).first()
        
        if existing:
            # Update existing record
            if in_time:
                existing.in_time = in_time
            if out_time:
                existing.out_time = out_time
            existing.status = status
            
            # Recalculate deduction if status changed
            if status == 'Present' and existing.deduction_hours > 0:
                existing.deduction_hours = 0
            elif status == 'Late' and in_time:
                _, deduction_hours = AttendanceService.calculate_attendance_status(employee_id, in_time)
                existing.deduction_hours = deduction_hours
            elif status == 'Absent':
                existing.deduction_hours = 8  # Full day deduction
                
            db.session.commit()
            return existing
        else:
            # Create new attendance record
            attendance = Attendance(
                employee_id=employee_id,
                date=date,
                in_time=in_time,
                out_time=out_time,
                status=status,
                deduction_hours=8 if status == 'Absent' else (2 if status == 'Late' else 0)
            )
            
            db.session.add(attendance)
            db.session.commit()
            return attendance
            
    @staticmethod
    def record_partial_leave(employee_id: int, date: datetime.date, 
                           start_time: time, end_time: time, reason: str) -> Attendance:
        """Record a partial leave for an employee.
        
        Args:
            employee_id: ID of the employee
            date: Date of partial leave
            start_time: Start time of leave
            end_time: End time of leave
            reason: Reason for partial leave
            
        Returns:
            Updated attendance record
        """
        # Get attendance record for the day
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=date
        ).first()
        
        if not attendance:
            # Create a new attendance record with partial leave
            attendance = Attendance(
                employee_id=employee_id,
                date=date,
                in_time=time(9, 0),  # Default check-in time
                status='Partial',
                partial_leave_start=start_time,
                partial_leave_end=end_time,
                partial_leave_reason=reason
            )
            db.session.add(attendance)
        else:
            # Update existing record with partial leave details
            attendance.status = 'Partial'
            attendance.partial_leave_start = start_time
            attendance.partial_leave_end = end_time
            attendance.partial_leave_reason = reason
            
            # Calculate deduction hours based on leave duration
            leave_duration = (
                datetime.combine(date, end_time) - 
                datetime.combine(date, start_time)
            ).total_seconds() / 3600  # Convert to hours
            
            attendance.deduction_hours = min(leave_duration, 4)  # Cap at half day
            
        db.session.commit()
        return attendance
        
    @staticmethod
    def get_department_attendance(department: str, start_date: datetime.date, end_date: datetime.date) -> Dict:
        """Get attendance summary for a department.
        
        Args:
            department: Department name
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Dictionary with attendance statistics
        """
        # Get all employees in the department
        employees = Employee.query.filter_by(department=department).all()
        employee_ids = [emp.id for emp in employees]
        
        # Get attendance records for these employees in the date range
        attendance_records = Attendance.query.filter(
            Attendance.employee_id.in_(employee_ids),
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()
        
        # Calculate statistics
        stats = {
            'total_employees': len(employees),
            'total_days': (end_date - start_date).days + 1,
            'present_count': sum(1 for a in attendance_records if a.status == 'Present'),
            'late_count': sum(1 for a in attendance_records if a.status == 'Late'),
            'absent_count': sum(1 for a in attendance_records if a.status == 'Absent'),
            'partial_count': sum(1 for a in attendance_records if a.status == 'Partial'),
            'total_deduction_hours': sum(a.deduction_hours for a in attendance_records)
        }
        
        return stats