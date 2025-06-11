# HRMSV3_optimized/app/services/employee_service.py
from typing import Optional, List, Tuple
from datetime import datetime
from ..models.employee import Employee, PerformanceReview, Leave
from ..models.attendance import Attendance, SalaryDetail
from ..models.users import User, Role
from ..database import db
from ..exceptions import ResourceNotFoundError, ValidationError

class EmployeeService:
    @staticmethod
    def create_employee(personal_data: dict, work_data: dict, salary_data: dict) -> Tuple[Employee, str]:
        """Create a new employee with associated user account."""
        # Create username from first name and last name
        username = f"{personal_data['first_name'].lower()}.{personal_data['last_name'].lower()}"
        base_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create user with temporary password
        temp_password = 'changeme123'
        user = User(
            username=username,
            email=work_data.get('work_email') or f"{username}@company.com"
        )
        user.set_password(temp_password)
        
        # Set default role as 'Employee'
        employee_role = Role.query.filter_by(name='Employee').first()
        if not employee_role:
            raise ValidationError('Employee role not found in the system.')
        user.role = employee_role
        
        # Create employee record
        employee = Employee(
            user=user,
            first_name=personal_data['first_name'],
            last_name=personal_data['last_name'],
            date_of_birth=personal_data.get('date_of_birth'),
            gender=personal_data.get('gender'),
            marital_status=personal_data.get('marital_status'),
            blood_group=personal_data.get('blood_group'),
            nationality=personal_data.get('nationality'),
            personal_email=personal_data.get('personal_email'),
            personal_mobile=personal_data.get('personal_mobile'),
            address=personal_data.get('address'),
            phone=personal_data.get('phone'),
            emergency_contact=personal_data.get('emergency_contact'),
            emergency_contact_name=personal_data.get('emergency_contact_name'),
            
            # Work details
            employee_id=work_data['employee_id'],
            department=work_data['department'],
            designation=work_data['designation'],
            joining_date=work_data['joining_date'],
            work_email=work_data.get('work_email'),
            work_phone=work_data.get('work_phone'),
            reporting_manager_id=work_data.get('reporting_manager_id'),
            is_manager=work_data.get('is_manager', False),
            employment_status=work_data.get('employment_status', 'Active'),
            employment_type=work_data.get('employment_type', 'Full-time'),
            probation_end_date=work_data.get('probation_end_date'),
            notice_period_days=work_data.get('notice_period_days', 30)
        )
        
        try:
            db.session.add(user)
            db.session.add(employee)
            db.session.commit()
            
            # Add salary details if provided
            if salary_data and 'basic_salary' in salary_data:
                salary = SalaryDetail(
                    employee=employee,
                    basic_salary=salary_data['basic_salary'],
                    allowances=salary_data.get('allowances', 0.0),
                    deductions=salary_data.get('deductions', 0.0),
                    effective_date=datetime.now().date(),
                    pf_contribution=salary_data.get('pf_contribution', 0.0),
                    medical_insurance=salary_data.get('medical_insurance', 0.0),
                    esic=salary_data.get('esic', 0.0),
                    casual_leaves_per_month=salary_data.get('casual_leaves_per_month', 0.0),
                    sick_leaves_per_month=salary_data.get('sick_leaves_per_month', 0.0),
                    travel_allowance_per_day=salary_data.get('travel_allowance_per_day', 0.0),
                    food_allowance_per_day=salary_data.get('food_allowance_per_day', 0.0)
                )
                db.session.add(salary)
                db.session.commit()
                
            return employee, temp_password
        except Exception as e:
            db.session.rollback()
            raise ValidationError(f"Error creating employee: {str(e)}")

    @staticmethod
    def get_employee_by_id(employee_id: int) -> Employee:
        """Get employee by ID."""
        employee = Employee.query.get(employee_id)
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {employee_id} not found")
        return employee

    @staticmethod
    def update_employee(employee_id: int, personal_data: dict = None, work_data: dict = None, salary_data: dict = None) -> Employee:
        """Update employee details."""
        employee = EmployeeService.get_employee_by_id(employee_id)
        
        try:
            # Update personal details
            if personal_data:
                for key, value in personal_data.items():
                    if hasattr(employee, key):
                        setattr(employee, key, value)
            
            # Update work details
            if work_data:
                for key, value in work_data.items():
                    if hasattr(employee, key):
                        setattr(employee, key, value)
            
            # Update salary details if provided
            if salary_data:
                salary = SalaryDetail.query.filter_by(employee_id=employee_id).order_by(SalaryDetail.effective_date.desc()).first()
                
                if salary:
                    for key, value in salary_data.items():
                        if hasattr(salary, key):
                            setattr(salary, key, value)
                else:
                    salary = SalaryDetail(
                        employee=employee,
                        basic_salary=salary_data.get('basic_salary', 0.0),
                        allowances=salary_data.get('allowances', 0.0),
                        deductions=salary_data.get('deductions', 0.0),
                        effective_date=datetime.now().date(),
                        pf_contribution=salary_data.get('pf_contribution', 0.0),
                        medical_insurance=salary_data.get('medical_insurance', 0.0),
                        esic=salary_data.get('esic', 0.0),
                        casual_leaves_per_month=salary_data.get('casual_leaves_per_month', 0.0),
                        sick_leaves_per_month=salary_data.get('sick_leaves_per_month', 0.0),
                        travel_allowance_per_day=salary_data.get('travel_allowance_per_day', 0.0),
                        food_allowance_per_day=salary_data.get('food_allowance_per_day', 0.0)
                    )
                    db.session.add(salary)
            
            db.session.commit()
            return employee
        except Exception as e:
            db.session.rollback()
            raise ValidationError(f"Error updating employee: {str(e)}")
    
    @staticmethod
    def get_all_employees() -> List[Employee]:
        """Get all employees."""
        return Employee.query.all()
    
    @staticmethod
    def get_employees_by_department(department: str) -> List[Employee]:
        """Get employees by department."""
        return Employee.query.filter_by(department=department).all()
    
    @staticmethod
    def get_employees_by_manager(manager_id: int) -> List[Employee]:
        """Get employees reporting to a specific manager."""
        return Employee.query.filter_by(reporting_manager_id=manager_id).all()

    @staticmethod
    def record_attendance(employee_id: int, date: datetime, status: str, in_time: datetime = None, 
                         out_time: datetime = None, notes: Optional[str] = None) -> Attendance:
        """Record attendance for an employee."""
        employee = EmployeeService.get_employee_by_id(employee_id)
        
        # Check if attendance record already exists for this date
        existing_attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=date.date() if isinstance(date, datetime) else date
        ).first()
        
        if existing_attendance:
            # Update existing record
            if in_time:
                existing_attendance.in_time = in_time.time() if isinstance(in_time, datetime) else in_time
            if out_time:
                existing_attendance.out_time = out_time.time() if isinstance(out_time, datetime) else out_time
            existing_attendance.status = status
            if notes:
                existing_attendance.notes = notes
            
            db.session.commit()
            return existing_attendance
        
        # Create new attendance record
        attendance = Attendance(
            employee_id=employee_id,
            date=date.date() if isinstance(date, datetime) else date,
            in_time=in_time.time() if in_time and isinstance(in_time, datetime) else in_time,
            out_time=out_time.time() if out_time and isinstance(out_time, datetime) else out_time,
            status=status,
            notes=notes
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return attendance

    @staticmethod
    def submit_performance_review(
        employee_id: int,
        reviewer_id: int,
        review_data: dict
    ) -> PerformanceReview:
        """Submit a performance review."""
        employee = EmployeeService.get_employee_by_id(employee_id)
        reviewer = EmployeeService.get_employee_by_id(reviewer_id)
        
        review = PerformanceReview(
            employee_id=employee_id,
            reviewer_id=reviewer_id,
            review_date=review_data.get('review_date', datetime.now().date()),
            period_start=review_data.get('period_start'),
            period_end=review_data.get('period_end'),
            job_knowledge=review_data.get('job_knowledge'),
            work_quality=review_data.get('work_quality'),
            attendance=review_data.get('attendance'),
            communication=review_data.get('communication'),
            teamwork=review_data.get('teamwork'),
            problem_solving=review_data.get('problem_solving'),
            management=review_data.get('management'),
            leadership=review_data.get('leadership'),
            overall_rating=review_data.get('overall_rating'),
            strengths=review_data.get('strengths'),
            areas_for_improvement=review_data.get('areas_for_improvement'),
            goals=review_data.get('goals'),
            employee_comments=review_data.get('employee_comments'),
            reviewer_comments=review_data.get('reviewer_comments')
        )
        
        db.session.add(review)
        db.session.commit()
        
        return review

    @staticmethod
    def submit_leave_request(employee_id: int, leave_data: dict) -> Leave:
        """Submit a leave request."""
        employee = EmployeeService.get_employee_by_id(employee_id)
        
        leave = Leave(
            employee_id=employee_id,
            start_date=leave_data['start_date'],
            end_date=leave_data['end_date'],
            leave_type=leave_data['leave_type'],
            reason=leave_data.get('reason'),
            status='Pending',
            is_half_day=leave_data.get('is_half_day', False),
            half_day_part=leave_data.get('half_day_part') if leave_data.get('is_half_day') else None,
            created_at=datetime.now()
        )
        
        db.session.add(leave)
        db.session.commit()
        
        return leave

    @staticmethod
    def process_leave_request(leave_id: int, approver_id: int, status: str, comments: str = None) -> Leave:
        """Process (approve/reject) a leave request."""
        leave = Leave.query.get(leave_id)
        if not leave:
            raise ResourceNotFoundError(f'Leave request with ID {leave_id} not found.')
        
        approver = EmployeeService.get_employee_by_id(approver_id)
        
        leave.status = status
        leave.approved_by = approver_id
        leave.approval_comments = comments
        leave.updated_at = datetime.now()
        
        db.session.commit()
        
        return leave
        
    @staticmethod
    def get_employee_leaves(employee_id: int, year: int = None) -> List[Leave]:
        """Get leave history for an employee."""
        employee = EmployeeService.get_employee_by_id(employee_id)
        
        query = Leave.query.filter_by(employee_id=employee_id)
        
        if year:
            query = query.filter(
                db.extract('year', Leave.start_date) == year
            )
            
        return query.order_by(Leave.start_date.desc()).all()
    
    @staticmethod
    def get_employee_performance_reviews(employee_id: int) -> List[PerformanceReview]:
        """Get performance review history for an employee."""
        employee = EmployeeService.get_employee_by_id(employee_id)
        
        return PerformanceReview.query.filter_by(employee_id=employee_id)\
            .order_by(PerformanceReview.review_date.desc()).all()