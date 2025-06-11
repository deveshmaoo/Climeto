# HRMSV3_optimized/app/services/project_service.py
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
import os
from werkzeug.utils import secure_filename

from ..database import db
from ..models.project import (
    Project, Task, TaskQuery, QueryResponse, 
    ProjectDocument, DocumentVersion, DocumentComment, 
    ProjectActivity, ProjectChat
)
from ..models.employee import Employee
from ..exceptions import ResourceNotFoundError, ValidationError, AuthorizationError


class ProjectService:
    @staticmethod
    def create_project(
        name: str,
        description: str,
        department_id: str,
        start_date: datetime,
        end_date: Optional[datetime],
        priority: str,
        manager_id: int,
        member_ids: List[int] = None
    ) -> Project:
        """Create a new project with initial members."""
        # Validate manager exists
        manager = Employee.query.get(manager_id)
        if not manager:
            raise ResourceNotFoundError(f"Manager with ID {manager_id} not found")
            
        project = Project(
            name=name,
            description=description,
            department_id=department_id,
            start_date=start_date,
            end_date=end_date,
            status='Active',
            priority=priority,
            manager_id=manager_id
        )
        
        db.session.add(project)
        
        # Add members if provided
        if member_ids:
            for member_id in member_ids:
                employee = Employee.query.get(member_id)
                if employee:
                    project.members.append(employee)
        
        # Add manager as a member if not already included
        if manager not in project.members:
            project.members.append(manager)
            
        # Record project creation activity
        activity = ProjectActivity(
            project_id=project.id,
            activity_type='Project Created',
            description=f"Project '{name}' was created",
            performed_by_id=manager_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return project
    
    @staticmethod
    def get_project_by_id(project_id: int) -> Project:
        """Get project by ID."""
        project = Project.query.get(project_id)
        if not project:
            raise ResourceNotFoundError(f"Project with ID {project_id} not found")
        return project
    
    @staticmethod
    def update_project(
        project_id: int,
        data: Dict[str, Any],
        updated_by_id: int
    ) -> Project:
        """Update project details."""
        project = ProjectService.get_project_by_id(project_id)
        
        # Update fields if provided
        if 'name' in data:
            project.name = data['name']
        if 'description' in data:
            project.description = data['description']
        if 'department_id' in data:
            project.department_id = data['department_id']
        if 'start_date' in data:
            project.start_date = data['start_date']
        if 'end_date' in data:
            project.end_date = data['end_date']
        if 'status' in data:
            project.status = data['status']
        if 'priority' in data:
            project.priority = data['priority']
        if 'manager_id' in data:
            # Validate manager exists
            manager = Employee.query.get(data['manager_id'])
            if not manager:
                raise ResourceNotFoundError(f"Manager with ID {data['manager_id']} not found")
            project.manager_id = data['manager_id']
        
        # Record project update activity
        activity = ProjectActivity(
            project_id=project.id,
            activity_type='Project Updated',
            description=f"Project '{project.name}' was updated",
            performed_by_id=updated_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return project
    
    @staticmethod
    def delete_project(project_id: int) -> None:
        """Delete a project."""
        project = ProjectService.get_project_by_id(project_id)
        db.session.delete(project)
        db.session.commit()
    
    @staticmethod
    def add_project_member(project_id: int, employee_id: int, added_by_id: int) -> Project:
        """Add a member to the project."""
        project = ProjectService.get_project_by_id(project_id)
        employee = Employee.query.get(employee_id)
        
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {employee_id} not found")
        
        if employee in project.members:
            raise ValidationError(f"Employee is already a member of this project")
        
        project.add_member(employee)
        
        # Record member addition activity
        activity = ProjectActivity(
            project_id=project.id,
            activity_type='Member Added',
            description=f"{employee.full_name} was added to the project",
            performed_by_id=added_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return project
    
    @staticmethod
    def remove_project_member(project_id: int, employee_id: int, removed_by_id: int) -> Project:
        """Remove a member from the project."""
        project = ProjectService.get_project_by_id(project_id)
        employee = Employee.query.get(employee_id)
        
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {employee_id} not found")
        
        if employee not in project.members:
            raise ValidationError(f"Employee is not a member of this project")
        
        # Cannot remove the project manager
        if project.manager_id == employee_id:
            raise ValidationError(f"Cannot remove the project manager from the project")
        
        project.remove_member(employee)
        
        # Record member removal activity
        activity = ProjectActivity(
            project_id=project.id,
            activity_type='Member Removed',
            description=f"{employee.full_name} was removed from the project",
            performed_by_id=removed_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return project
    
    @staticmethod
    def get_accessible_projects(employee_id: int) -> List[Project]:
        """Get all projects accessible to an employee."""
        employee = Employee.query.get(employee_id)
        if not employee:
            return []
            
        if employee.user.has_role('Admin') or employee.user.has_role('HR'):
            return Project.query.all()
        
        # Get projects where user is either manager, member, or in same department
        department_projects = Project.query.filter_by(department_id=employee.department).all()
        managed_projects = Project.query.filter_by(manager_id=employee.id).all()
        member_projects = employee.projects.all()
        
        # Combine and remove duplicates
        all_projects = set()
        for project in department_projects + managed_projects + member_projects:
            all_projects.add(project)
        
        return list(all_projects)
    
    @staticmethod
    def get_tasks_by_assignee(employee_id: int) -> List[Task]:
        """Get all tasks assigned to an employee."""
        return Task.query.filter_by(assigned_to=employee_id).all()
    
    @staticmethod
    def get_tasks_by_creator(employee_id: int) -> List[Task]:
        """Get all tasks created by an employee."""
        return Task.query.filter_by(assigned_by=employee_id).all()
    
    @staticmethod
    def get_accessible_tasks(employee_id: int) -> List[Task]:
        """Get all tasks accessible to an employee (assigned, created, or in their projects)."""
        employee = Employee.query.get(employee_id)
        if not employee:
            return []
        
        # Get tasks assigned to or created by the employee
        assigned_tasks = Task.query.filter_by(assigned_to=employee_id).all()
        created_tasks = Task.query.filter_by(assigned_by=employee_id).all()
        
        # Get tasks from projects they're part of
        project_tasks = []
        for project in employee.projects:
            project_tasks.extend(project.tasks)
        
        # Combine and remove duplicates
        all_tasks = set()
        for task in assigned_tasks + created_tasks + project_tasks:
            all_tasks.add(task)
        
        return list(all_tasks)
    
    @staticmethod
    def get_accessible_chats(employee_id: int) -> List[ProjectChat]:
        """Get all chats accessible to an employee from their projects."""
        employee = Employee.query.get(employee_id)
        if not employee:
            return []
        
        # Managers/Directors can see all chats
        if employee.user.has_role('Admin') or employee.user.has_role('HR') or employee.designation in ['Manager', 'Director']:
            return ProjectChat.query.order_by(ProjectChat.created_at.desc()).limit(100).all()
        
        all_chats = []
        for project in employee.projects:
            chats = ProjectChat.query.filter_by(project_id=project.id).order_by(ProjectChat.created_at.desc()).limit(10).all()
            all_chats.extend(chats)
        
        # Sort by creation time
        all_chats.sort(key=lambda x: x.created_at, reverse=True)
        return all_chats[:50]  # Return latest 50 chats
    
    @staticmethod
    def get_project_completion_rate(project_id: int) -> float:
        """Calculate project completion rate based on completed tasks."""
        project = ProjectService.get_project_by_id(project_id)
        total_tasks = project.tasks.count()
        
        if total_tasks == 0:
            return 0.0
            
        completed_tasks = project.tasks.filter_by(status='Done').count()
        return (completed_tasks / total_tasks) * 100
    
    # Task Management Methods
    @staticmethod
    def create_task(
        project_id: int,
        title: str,
        description: str,
        assigned_to: int,
        assigned_by: int,
        due_date: datetime,
        priority: str = 'Medium',
        estimated_hours: float = None
    ) -> Task:
        """Create a new task in the project."""
        project = ProjectService.get_project_by_id(project_id)
        assignee = Employee.query.get(assigned_to)
        assigner = Employee.query.get(assigned_by)
        
        if not assignee:
            raise ResourceNotFoundError(f"Assignee with ID {assigned_to} not found")
        
        if not assigner:
            raise ResourceNotFoundError(f"Assigner with ID {assigned_by} not found")
        
        # Validate that assignee is a project member
        if assignee not in project.members:
            raise ValidationError(f"Assignee must be a member of the project")
        
        task = Task(
            project_id=project_id,
            title=title,
            description=description,
            status='To Do',
            priority=priority,
            due_date=due_date,
            estimated_hours=estimated_hours,
            assigned_to=assigned_to,
            assigned_by=assigned_by
        )
        
        db.session.add(task)
        
        # Record task creation activity
        activity = ProjectActivity(
            project_id=project_id,
            activity_type='Task Created',
            description=f"Task '{title}' was created and assigned to {assignee.full_name}",
            performed_by_id=assigned_by
        )
        db.session.add(activity)
        
        db.session.commit()
        return task
    
    @staticmethod
    def update_task_status(
        task_id: int,
        new_status: str,
        actual_hours: float = None,
        updated_by_id: int = None
    ) -> Task:
        """Update task status and record actual hours if completed."""
        task = Task.query.get(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task with ID {task_id} not found")
        
        old_status = task.status
        task.status = new_status
        
        # If task is marked as done, record actual hours
        if new_status == 'Done' and actual_hours is not None:
            task.actual_hours = actual_hours
        
        # Record task status update activity
        activity = ProjectActivity(
            project_id=task.project_id,
            activity_type='Task Status Updated',
            description=f"Task '{task.title}' status changed from '{old_status}' to '{new_status}'",
            performed_by_id=updated_by_id or task.assigned_to
        )
        db.session.add(activity)
        
        db.session.commit()
        return task
    
    @staticmethod
    def get_task_by_id(task_id: int) -> Task:
        """Get task by ID."""
        task = Task.query.get(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task with ID {task_id} not found")
        return task
    
    @staticmethod
    def get_employee_tasks(employee_id: int, status: str = None) -> List[Task]:
        """Get all tasks assigned to an employee, optionally filtered by status."""
        query = Task.query.filter_by(assigned_to=employee_id)
        
        if status:
            query = query.filter_by(status=status)
            
        return query.order_by(Task.due_date).all()
    
    @staticmethod
    def get_project_tasks(project_id: int, status: str = None) -> List[Task]:
        """Get all tasks in a project, optionally filtered by status."""
        project = ProjectService.get_project_by_id(project_id)
        query = project.tasks
        
        if status:
            query = query.filter_by(status=status)
            
        return query.order_by(Task.due_date).all()
    
    @staticmethod
    def get_overdue_tasks(project_id: int = None, employee_id: int = None) -> List[Task]:
        """Get overdue tasks, optionally filtered by project or employee."""
        query = Task.query.filter(
            Task.due_date < datetime.utcnow().date(),
            Task.status != 'Done'
        )
        
        if project_id:
            query = query.filter_by(project_id=project_id)
            
        if employee_id:
            query = query.filter_by(assigned_to=employee_id)
            
        return query.order_by(Task.due_date).all()
    
    # Task Query Methods
    @staticmethod
    def create_task_query(
        task_id: int,
        raised_by_id: int,
        query_text: str
    ) -> TaskQuery:
        """Create a new query on a task."""
        task = ProjectService.get_task_by_id(task_id)
        employee = Employee.query.get(raised_by_id)
        
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {raised_by_id} not found")
        
        query = TaskQuery(
            task_id=task_id,
            raised_by_id=raised_by_id,
            query_text=query_text,
            status='Open'
        )
        
        db.session.add(query)
        
        # Record query creation activity
        activity = ProjectActivity(
            project_id=task.project_id,
            activity_type='Query Raised',
            description=f"Query raised on task '{task.title}'",
            performed_by_id=raised_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return query
    
    @staticmethod
    def respond_to_query(
        query_id: int,
        responded_by_id: int,
        response_text: str
    ) -> QueryResponse:
        """Respond to a task query."""
        query = TaskQuery.query.get(query_id)
        if not query:
            raise ResourceNotFoundError(f"Query with ID {query_id} not found")
        
        employee = Employee.query.get(responded_by_id)
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {responded_by_id} not found")
        
        response = QueryResponse(
            query_id=query_id,
            responded_by_id=responded_by_id,
            response_text=response_text
        )
        
        db.session.add(response)
        
        # Update query status to Resolved
        query.status = 'Resolved'
        
        # Record response activity
        task = Task.query.get(query.task_id)
        activity = ProjectActivity(
            project_id=task.project_id,
            activity_type='Query Responded',
            description=f"Response provided to query on task '{task.title}'",
            performed_by_id=responded_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return response
    
    # Document Management Methods
    @staticmethod
    def create_document(
        project_id: int,
        title: str,
        description: str,
        document_type: str,
        created_by_id: int,
        file_path: str,
        change_summary: str = "Initial version"
    ) -> Tuple[ProjectDocument, DocumentVersion]:
        """Create a new document with initial version."""
        project = ProjectService.get_project_by_id(project_id)
        employee = Employee.query.get(created_by_id)
        
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {created_by_id} not found")
        
        document = ProjectDocument(
            project_id=project_id,
            title=title,
            description=description,
            document_type=document_type,
            created_by_id=created_by_id
        )
        
        db.session.add(document)
        db.session.flush()  # To get the document ID
        
        # Create initial version
        version = DocumentVersion(
            document_id=document.id,
            version_number=1,
            file_path=file_path,
            uploaded_by_id=created_by_id,
            change_summary=change_summary
        )
        
        db.session.add(version)
        
        # Record document creation activity
        activity = ProjectActivity(
            project_id=project_id,
            activity_type='Document Created',
            description=f"Document '{title}' was created",
            performed_by_id=created_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return document, version
    
    @staticmethod
    def add_document_version(
        document_id: int,
        uploaded_by_id: int,
        file_path: str,
        change_summary: str
    ) -> DocumentVersion:
        """Add a new version to an existing document."""
        document = ProjectDocument.query.get(document_id)
        if not document:
            raise ResourceNotFoundError(f"Document with ID {document_id} not found")
        
        employee = Employee.query.get(uploaded_by_id)
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {uploaded_by_id} not found")
        
        # Get the latest version number
        latest_version = DocumentVersion.query.filter_by(document_id=document_id).order_by(
            DocumentVersion.version_number.desc()).first()
        new_version_number = (latest_version.version_number + 1) if latest_version else 1
        
        version = DocumentVersion(
            document_id=document_id,
            version_number=new_version_number,
            file_path=file_path,
            uploaded_by_id=uploaded_by_id,
            change_summary=change_summary
        )
        
        db.session.add(version)
        
        # Record document version activity
        activity = ProjectActivity(
            project_id=document.project_id,
            activity_type='Document Updated',
            description=f"New version {new_version_number} added to document '{document.title}'",
            performed_by_id=uploaded_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return version
    
    @staticmethod
    def add_document_comment(
        document_id: int,
        commented_by_id: int,
        comment_text: str
    ) -> DocumentComment:
        """Add a comment to a document."""
        document = ProjectDocument.query.get(document_id)
        if not document:
            raise ResourceNotFoundError(f"Document with ID {document_id} not found")
        
        employee = Employee.query.get(commented_by_id)
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {commented_by_id} not found")
        
        comment = DocumentComment(
            document_id=document_id,
            comment_text=comment_text,
            commented_by_id=commented_by_id
        )
        
        db.session.add(comment)
        
        # Record document comment activity
        activity = ProjectActivity(
            project_id=document.project_id,
            activity_type='Document Commented',
            description=f"Comment added to document '{document.title}'",
            performed_by_id=commented_by_id
        )
        db.session.add(activity)
        
        db.session.commit()
        return comment
    
    @staticmethod
    def get_project_documents(project_id: int, document_type: str = None) -> List[ProjectDocument]:
        """Get all documents in a project, optionally filtered by type."""
        project = ProjectService.get_project_by_id(project_id)
        query = ProjectDocument.query.filter_by(project_id=project_id)
        
        if document_type:
            query = query.filter_by(document_type=document_type)
            
        return query.order_by(ProjectDocument.created_at.desc()).all()
    
    # Project Chat Methods
    @staticmethod
    def add_chat_message(
        project_id: int,
        sender_id: int,
        message: str,
        message_type: str = 'text',
        file_path: str = None,
        file_name: str = None,
        file_size: int = None
    ) -> ProjectChat:
        """Add a chat message to the project."""
        project = ProjectService.get_project_by_id(project_id)
        employee = Employee.query.get(sender_id)
        
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {sender_id} not found")
        
        # Validate that sender is a project member
        if not project.can_access(employee):
            raise AuthorizationError(f"Employee does not have access to this project")
        
        chat = ProjectChat(
            project_id=project_id,
            sender_id=sender_id,
            message=message,
            message_type=message_type,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size
        )
        
        db.session.add(chat)
        db.session.commit()
        return chat
    
    @staticmethod
    def get_project_chats(project_id: int, limit: int = 50) -> List[ProjectChat]:
        """Get chat messages for a project, limited to the most recent ones."""
        project = ProjectService.get_project_by_id(project_id)
        return project.chats.order_by(ProjectChat.created_at.desc()).limit(limit).all()
    
    # Project Activity Methods
    @staticmethod
    def get_project_activities(project_id: int, limit: int = 50) -> List[ProjectActivity]:
        """Get activity log for a project, limited to the most recent ones."""
        project = ProjectService.get_project_by_id(project_id)
        return ProjectActivity.query.filter_by(project_id=project_id).order_by(
            ProjectActivity.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def log_project_activity(
        project_id: int,
        activity_type: str,
        description: str,
        performed_by_id: int
    ) -> ProjectActivity:
        """Log a custom activity for a project."""
        project = ProjectService.get_project_by_id(project_id)
        employee = Employee.query.get(performed_by_id)
        
        if not employee:
            raise ResourceNotFoundError(f"Employee with ID {performed_by_id} not found")
        
        activity = ProjectActivity(
            project_id=project_id,
            activity_type=activity_type,
            description=description,
            performed_by_id=performed_by_id
        )
        
        db.session.add(activity)
        db.session.commit()
        return activity