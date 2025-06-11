import os
from datetime import datetime
from flask import render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from ..models.project import (
    Project, Task, TaskQuery, QueryResponse, 
    ProjectDocument, DocumentVersion, DocumentComment, ProjectActivity, ProjectChat
)
from ..models.employee import Employee
from .forms import (
    ProjectForm, TaskForm, TaskRatingForm, TaskQueryForm, 
    QueryResponseForm, DocumentUploadForm, DocumentCommentForm
)
from ..database import db
from . import bp
from ..utils.decorators import role_required
from ..services.project_service import ProjectService

@bp.route('/dashboard')
@login_required
def dashboard():
    """Employee dashboard showing all assigned tasks across projects"""
    employee = current_user.employee
    assigned_tasks = ProjectService.get_tasks_by_assignee(employee.id)
    created_tasks = ProjectService.get_tasks_by_creator(employee.id)
    projects = ProjectService.get_accessible_projects(employee.id)
    
    return render_template('project/dashboard.html',
                         assigned_tasks=assigned_tasks,
                         created_tasks=created_tasks,
                         projects=projects)

@bp.route('/list')
@login_required
def list_projects():
    """List all projects the current user has access to"""
    employee = current_user.employee
    projects = ProjectService.get_accessible_projects(employee.id)
    
    return render_template('project/list.html', projects=projects)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Management')
def create_project():
    """Create a new project"""
    if request.method == 'POST':
        try:
            member_ids = request.form.getlist('members') if 'members' in request.form else []
            
            # Parse dates
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None
            
            project = ProjectService.create_project(
                name=request.form['name'],
                description=request.form.get('description', ''),
                department_id=request.form['department'],
                start_date=start_date,
                end_date=end_date,
                priority=request.form['priority'],
                manager_id=int(request.form['manager_id']),
                member_ids=[int(id) for id in member_ids if id]
            )
            
            flash('Project created successfully!', 'success')
            return redirect(url_for('project.view_project', id=project.id))
            
        except Exception as e:
            flash(f'Error creating project: {str(e)}', 'danger')
    
    # Get employees for member selection
    employees = Employee.query.all()
    departments = db.session.query(Employee.department).distinct().all()
    
    return render_template('project/create.html', 
                         employees=employees,
                         departments=departments)

@bp.route('/<int:id>')
@login_required
def view_project(id):
    """View project details"""
    try:
        project = ProjectService.get_project_by_id(id)
        return render_template('project/view.html', project=project)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))

@bp.route('/<int:id>/tasks')
@login_required
def project_tasks(id):
    """View project tasks"""
    try:
        project = ProjectService.get_project_by_id(id)
        tasks = ProjectService.get_project_tasks(id)
        return render_template('project/tasks.html', project=project, tasks=tasks)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))

@bp.route('/<int:id>/chat', methods=['GET', 'POST'])
@login_required
def project_chat(id):
    """View project chat"""
    try:
        project = ProjectService.get_project_by_id(id)
        
        if request.method == 'POST':
            message = request.form.get('message', '').strip()
            file = request.files.get('file')
            
            if file and file.filename:
                # Handle file upload
                filename = secure_filename(file.filename)
                file_path = f"chat_files/{id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                full_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), file_path)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                file.save(full_path)
                
                # Determine message type
                message_type = 'image' if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'file'
                chat_message = message if message else f"Shared a file: {filename}"
                
                ProjectService.add_chat_message(
                    project_id=id,
                    sender_id=current_user.employee.id,
                    message=chat_message,
                    message_type=message_type,
                    file_path=file_path,
                    file_name=filename,
                    file_size=len(file.read())
                )
                file.seek(0)  # Reset file pointer
            elif message:
                # Handle text message
                ProjectService.add_chat_message(
                    project_id=id,
                    sender_id=current_user.employee.id,
                    message=message
                )
            
            return redirect(url_for('project.project_chat', id=id))
        
        chats = ProjectService.get_project_chats(id)
        return render_template('project/chat.html', project=project, chats=chats)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))

@bp.route('/<int:id>/chat/send', methods=['POST'])
@login_required
def send_chat(id):
    """Send a chat message"""
    try:
        message = request.form.get('message')
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        chat = ProjectService.add_chat_message(
            project_id=id,
            sender_id=current_user.employee.id,
            message=message
        )
        
        return jsonify({
            'id': chat.id,
            'message': chat.message,
            'sender_name': f"{chat.sender.first_name} {chat.sender.last_name}",
            'created_at': chat.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/tasks/all')
@login_required
def all_tasks():
    """View all tasks across projects"""
    employee = current_user.employee
    tasks = ProjectService.get_accessible_tasks(employee.id)
    
    return render_template('project/all_tasks.html', tasks=tasks)

@bp.route('/chats/all')
@login_required
def all_chats():
    """View all chats across projects"""
    employee = current_user.employee
    filter_type = request.args.get('filter', 'all')
    
    chats = ProjectService.get_accessible_chats(employee.id)
    
    # Apply filters
    if filter_type == 'files':
        chats = [chat for chat in chats if chat.message_type in ['file', 'image']]
    elif filter_type == 'today':
        from datetime import date
        today = date.today()
        chats = [chat for chat in chats if chat.created_at.date() == today]
    elif filter_type == 'week':
        from datetime import date, timedelta
        week_ago = date.today() - timedelta(days=7)
        chats = [chat for chat in chats if chat.created_at.date() >= week_ago]
    
    return render_template('project/all_chats.html', chats=chats, filter_type=filter_type)

@bp.route('/project/<int:project_id>/task/new', methods=['GET', 'POST'])
@login_required
def create_task(project_id):
    """Create a new task in the project"""
    try:
        project = ProjectService.get_project_by_id(project_id)
        
        if request.method == 'POST':
            task = ProjectService.create_task(
                project_id=project_id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                assigned_to=request.form.get('assigned_to'),
                assigned_by=current_user.employee.id,
                deadline=datetime.strptime(request.form.get('deadline'), '%Y-%m-%d').date(),
                priority=request.form.get('priority', 'Medium'),
                estimated_hours=request.form.get('estimated_hours')
            )
            
            flash('Task created successfully.', 'success')
            return redirect(url_for('project.project_tasks', id=project_id))
        
        # GET request - show form
        form = TaskForm()
        participants = Employee.query.join(Employee.projects).filter_by(id=project_id).all()
        form.assigned_to.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in participants]
        
        return render_template('project/task_form.html', form=form, project=project)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))

@bp.route('/task/<int:task_id>/rate', methods=['GET', 'POST'])
@login_required
def rate_task(task_id):
    """Rate a completed task"""
    try:
        task = ProjectService.get_task_by_id(task_id)
        
        # Only task assigner can rate it
        if task.assigned_by != current_user.employee.id:
            flash('You do not have permission to rate this task.', 'danger')
            return redirect(url_for('project.project_tasks', id=task.project_id))
        
        form = TaskRatingForm()
        if form.validate_on_submit():
            ProjectService.rate_task(
                task_id=task_id,
                quality_rating=int(form.quality_rating.data),
                timeliness_rating=int(form.timeliness_rating.data),
                feedback=form.feedback.data
            )
            
            flash('Task rated successfully.', 'success')
            return redirect(url_for('project.project_tasks', id=task.project_id))
        
        return render_template('project/rate_task.html', form=form, task=task)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.all_tasks'))

@bp.route('/task/<int:task_id>/query', methods=['POST'])
@login_required
def create_query(task_id):
    """Create a new query on a task"""
    try:
        query_text = request.form.get('query_text')
        if not query_text:
            flash('Query text is required.', 'danger')
            return redirect(url_for('project.task_detail', task_id=task_id))
        
        query = ProjectService.create_task_query(
            task_id=task_id,
            raised_by=current_user.employee.id,
            query_text=query_text
        )
        
        flash('Query raised successfully.', 'success')
        return redirect(url_for('project.task_detail', task_id=task_id))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.all_tasks'))

@bp.route('/query/<int:query_id>/respond', methods=['POST'])
@login_required
def respond_to_query(query_id):
    """Respond to a task query"""
    try:
        response_text = request.form.get('response_text')
        if not response_text:
            flash('Response text is required.', 'danger')
            return redirect(url_for('project.task_detail', task_id=query.task_id))
        
        response = ProjectService.respond_to_query(
            query_id=query_id,
            responded_by=current_user.employee.id,
            response_text=response_text
        )
        
        flash('Response added successfully.', 'success')
        return redirect(url_for('project.task_detail', task_id=response.query.task_id))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.all_tasks'))

@bp.route('/project/<int:project_id>/document/upload', methods=['GET', 'POST'])
@login_required
def upload_document(project_id):
    """Upload a new document to the project"""
    try:
        project = ProjectService.get_project_by_id(project_id)
        form = DocumentUploadForm()
        
        if form.validate_on_submit():
            file = form.file.data
            filename = secure_filename(file.filename)
            
            document = ProjectService.create_document(
                project_id=project_id,
                name=form.name.data,
                description=form.description.data,
                created_by=current_user.employee.id,
                file=file,
                filename=filename,
                upload_folder=current_app.config['UPLOAD_FOLDER']
            )
            
            flash('Document uploaded successfully.', 'success')
            return redirect(url_for('project.view_project', id=project_id))
        
        return render_template('project/upload_document.html', form=form, project=project)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))

@bp.route('/document/<int:doc_id>/version/new', methods=['POST'])
@login_required
def upload_new_version(doc_id):
    """Upload a new version of an existing document"""
    try:
        document = ProjectService.get_document_by_id(doc_id)
        
        if 'file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('project.view_project', id=document.project_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('project.view_project', id=document.project_id))
        
        if file:
            filename = secure_filename(file.filename)
            
            version = ProjectService.add_document_version(
                document_id=doc_id,
                uploaded_by=current_user.employee.id,
                file=file,
                filename=filename,
                upload_folder=current_app.config['UPLOAD_FOLDER']
            )
            
            flash('New version uploaded successfully.', 'success')
        
        return redirect(url_for('project.view_project', id=document.project_id))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))

@bp.route('/version/<int:version_id>/comment', methods=['POST'])
@login_required
def add_comment(version_id):
    """Add a comment to a document version"""
    try:
        version = ProjectService.get_document_version(version_id)
        form = DocumentCommentForm()
        
        if form.validate_on_submit():
            comment = ProjectService.add_document_comment(
                version_id=version_id,
                commented_by=current_user.employee.id,
                comment_text=form.comment_text.data
            )
            
            flash('Comment added successfully.', 'success')
        
        return redirect(url_for('project.view_project', id=version.document.project_id))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))

@bp.route('/task/<int:task_id>')
@login_required
def task_detail(task_id):
    """Show task details"""
    try:
        task = ProjectService.get_task_by_id(task_id)
        return render_template('project/task_detail.html', task=task)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.all_tasks'))

@bp.route('/task/<int:task_id>/update-status', methods=['POST'])
@login_required
def update_task_status(task_id):
    """Update task status"""
    try:
        task = ProjectService.get_task_by_id(task_id)
        
        # Check if user is assigned to this task
        if task.assigned_to != current_user.employee.id:
            flash('You do not have permission to update this task.', 'danger')
            return redirect(url_for('project.task_detail', task_id=task_id))
        
        new_status = request.form.get('status')
        if new_status in ['Not Started', 'In Progress', 'On Hold', 'Completed']:
            ProjectService.update_task_status(
                task_id=task_id,
                status=new_status,
                updated_by=current_user.employee.id
            )
            flash('Task status updated successfully.', 'success')
        else:
            flash('Invalid status.', 'danger')
        
        return redirect(url_for('project.task_detail', task_id=task_id))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.all_tasks'))

@bp.route('/project/<int:project_id>/member/add', methods=['POST'])
@login_required
def add_member(project_id):
    """Add a team member to the project"""
    try:
        employee_id = request.form.get('employee_id')
        role = request.form.get('role', 'Team Member')
        
        if not employee_id:
            flash('Please select an employee.', 'danger')
            return redirect(url_for('project.view_project', id=project_id))
        
        ProjectService.add_project_member(
            project_id=project_id,
            employee_id=employee_id,
            role=role,
            added_by=current_user.employee.id
        )
        
        flash('Team member added successfully.', 'success')
        return redirect(url_for('project.view_project', id=project_id))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('project.list_projects'))