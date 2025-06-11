"""
Sales management routes for the HRMS application.
"""

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from . import bp
from ..models.project import Lead, LeadInteraction, Client, ClientProject, ActivityLog
from ..models.employee import Employee
from ..project.forms import LeadForm, LeadUpdateForm, LeadInteractionForm, ConvertLeadForm
from ..database import db
from ..utils.decorators import role_required
import json
from collections import defaultdict

@bp.route('/dashboard')
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager', 'Digital Marketing', 'Business Development')
def dashboard():
    """Sales dashboard showing leads, clients, and sales funnel."""
    employee = current_user.employee
    
    # Get leads based on user access
    if current_user.can_view_all_activities() or current_user.can_manage_department_funnel():
        leads = Lead.query.all()
        clients = Client.query.all()
    else:
        leads = Lead.query.filter_by(assigned_to_id=employee.id).all()
        clients = Client.query.filter_by(account_manager_id=employee.id).all()
    
    # Sales funnel data
    funnel_data = {
        'New': len([l for l in leads if l.status == 'New']),
        'Qualified': len([l for l in leads if l.status == 'Qualified']),
        'Proposal': len([l for l in leads if l.status == 'Proposal']),
        'Negotiation': len([l for l in leads if l.status == 'Negotiation']),
        'Closed Won': len([l for l in leads if l.status == 'Closed Won']),
        'Closed Lost': len([l for l in leads if l.status == 'Closed Lost'])
    }
    
    # Recent activities
    recent_activities = ActivityLog.query.filter(
        ActivityLog.entity_type.in_(['Lead', 'Client'])
    ).order_by(ActivityLog.created_at.desc()).limit(10).all()
    
    return render_template('sales/dashboard.html', 
                         leads=leads[:10],  # Latest 10 leads
                         clients=clients[:10],  # Latest 10 clients
                         funnel_data=funnel_data,
                         recent_activities=recent_activities)

@bp.route('/leads')
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager', 'Digital Marketing', 'Business Development')
def list_leads():
    """List all leads with filtering options."""
    employee = current_user.employee
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    source_filter = request.args.get('source', 'all')
    assigned_filter = request.args.get('assigned', 'all')
    
    # Base query
    if current_user.can_view_all_activities() or current_user.can_manage_department_funnel():
        query = Lead.query
    else:
        query = Lead.query.filter_by(assigned_to_id=employee.id)
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    if source_filter != 'all':
        query = query.filter_by(source=source_filter)
    if assigned_filter != 'all':
        query = query.filter_by(assigned_to_id=int(assigned_filter))
    
    leads = query.order_by(Lead.created_at.desc()).all()
    
    # Get unique values for filters
    all_sources = db.session.query(Lead.source).distinct().all()
    all_assignees = Employee.query.join(Lead, Lead.assigned_to_id == Employee.id).distinct().all()
    
    return render_template('sales/leads.html', 
                         leads=leads,
                         sources=[s[0] for s in all_sources],
                         assignees=all_assignees,
                         filters={
                             'status': status_filter,
                             'priority': priority_filter,
                             'source': source_filter,
                             'assigned': assigned_filter
                         })

@bp.route('/lead/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager', 'Digital Marketing', 'Business Development')
def create_lead():
    """Create a new lead."""
    form = LeadForm()
    
    # Populate assignee choices
    if current_user.can_view_all_activities():
        # Show all employees from sales departments
        employees = Employee.query.filter(
            Employee.department.in_(['Digital Marketing', 'Business Development'])
        ).all()
    else:
        employees = [current_user.employee]
    
    form.assigned_to.choices = [(e.id, f"{e.first_name} {e.last_name}") for e in employees]
    
    if form.validate_on_submit():
        lead = Lead(
            company_name=form.company_name.data,
            contact_person=form.contact_person.data,
            email=form.email.data,
            phone=form.phone.data,
            industry=form.industry.data,
            source=form.source.data,
            priority=form.priority.data,
            estimated_value=form.estimated_value.data,
            expected_close_date=form.expected_close_date.data,
            assigned_to_id=form.assigned_to.data,
            notes=form.notes.data
        )
        
        db.session.add(lead)
        db.session.commit()
        
        # Log activity
        activity = ActivityLog(
            activity_type='Lead Created',
            description=f'New lead created: {lead.company_name}',
            department=current_user.department,
            performed_by_id=current_user.employee.id,
            entity_type='Lead',
            entity_id=lead.id
        )
        db.session.add(activity)
        db.session.commit()
        
        flash('Lead created successfully!', 'success')
        return redirect(url_for('sales.lead_detail', id=lead.id))
    
    return render_template('sales/create_lead.html', form=form)

@bp.route('/lead/<int:id>')
@login_required
def lead_detail(id):
    """Show lead details."""
    lead = Lead.query.get_or_404(id)
    
    # Check access
    if not current_user.can_view_all_activities() and lead.assigned_to_id != current_user.employee.id:
        flash('You do not have permission to view this lead.', 'error')
        return redirect(url_for('sales.list_leads'))
    
    interactions = lead.interactions.order_by(LeadInteraction.interaction_date.desc()).all()
    
    return render_template('sales/lead_detail.html', lead=lead, interactions=interactions)

@bp.route('/lead/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(id):
    """Edit a lead."""
    lead = Lead.query.get_or_404(id)
    
    # Check access
    if not current_user.can_view_all_activities() and lead.assigned_to_id != current_user.employee.id:
        flash('You do not have permission to edit this lead.', 'error')
        return redirect(url_for('sales.list_leads'))
    
    form = LeadUpdateForm(obj=lead)
    
    if form.validate_on_submit():
        old_status = lead.status
        
        lead.status = form.status.data
        lead.priority = form.priority.data
        lead.estimated_value = form.estimated_value.data
        lead.expected_close_date = form.expected_close_date.data
        lead.notes = form.notes.data
        
        db.session.commit()
        
        # Log activity if status changed
        if old_status != lead.status:
            activity = ActivityLog(
                activity_type='Lead Status Changed',
                description=f'Lead {lead.company_name} status changed from {old_status} to {lead.status}',
                department=current_user.department,
                performed_by_id=current_user.employee.id,
                entity_type='Lead',
                entity_id=lead.id
            )
            db.session.add(activity)
            db.session.commit()
        
        flash('Lead updated successfully!', 'success')
        return redirect(url_for('sales.lead_detail', id=lead.id))
    
    return render_template('sales/edit_lead.html', form=form, lead=lead)

@bp.route('/lead/<int:id>/interaction', methods=['POST'])
@login_required
def add_interaction(id):
    """Add an interaction to a lead."""
    lead = Lead.query.get_or_404(id)
    
    # Check access
    if not current_user.can_view_all_activities() and lead.assigned_to_id != current_user.employee.id:
        flash('You do not have permission to add interactions to this lead.', 'error')
        return redirect(url_for('sales.list_leads'))
    
    form = LeadInteractionForm()
    
    if form.validate_on_submit():
        interaction = LeadInteraction(
            lead_id=lead.id,
            interaction_type=form.interaction_type.data,
            description=form.description.data,
            next_follow_up=form.next_follow_up.data,
            performed_by_id=current_user.employee.id
        )
        
        db.session.add(interaction)
        db.session.commit()
        
        flash('Interaction added successfully!', 'success')
    else:
        for error in form.errors:
            flash(f'Error: {form.errors[error][0]}', 'error')
    
    return redirect(url_for('sales.lead_detail', id=lead.id))

@bp.route('/lead/<int:id>/convert', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager', 'Digital Marketing', 'Business Development')
def convert_lead(id):
    """Convert a lead to a client."""
    lead = Lead.query.get_or_404(id)
    
    if lead.status == 'Closed Won':
        form = ConvertLeadForm()
        
        # Populate form choices
        account_managers = Employee.query.filter(
            Employee.department.in_(['Business Development', 'Management'])
        ).all()
        epr_employees = Employee.query.filter_by(department='EPR Compliance').all()
        
        form.account_manager.choices = [(e.id, f"{e.first_name} {e.last_name}") for e in account_managers]
        form.epr_assignee.choices = [(e.id, f"{e.first_name} {e.last_name}") for e in epr_employees]
        
        if form.validate_on_submit():
            # Create client
            client = Client(
                company_name=lead.company_name,
                contact_person=lead.contact_person,
                email=lead.email,
                phone=lead.phone,
                industry=lead.industry,
                account_manager_id=form.account_manager.data,
                created_from_lead_id=lead.id,
                assigned_to_epr_id=form.epr_assignee.data,
                total_value=form.project_value.data or 0
            )
            
            db.session.add(client)
            db.session.commit()
            
            # Create initial project if specified
            if form.project_name.data:
                project = ClientProject(
                    client_id=client.id,
                    project_name=form.project_name.data,
                    description=form.project_description.data,
                    value=form.project_value.data,
                    start_date=date.today()
                )
                db.session.add(project)
                db.session.commit()
            
            # Log activity
            activity = ActivityLog(
                activity_type='Lead Converted',
                description=f'Lead {lead.company_name} converted to client and assigned to EPR Compliance',
                department=current_user.department,
                performed_by_id=current_user.employee.id,
                entity_type='Client',
                entity_id=client.id
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Lead converted to client successfully!', 'success')
            return redirect(url_for('sales.client_detail', id=client.id))
        
        return render_template('sales/convert_lead.html', form=form, lead=lead)
    else:
        flash('Only leads with "Closed Won" status can be converted to clients.', 'error')
        return redirect(url_for('sales.lead_detail', id=lead.id))

@bp.route('/clients')
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager', 'EPR Compliance', 'Business Development')
def list_clients():
    """List all clients."""
    employee = current_user.employee
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    industry_filter = request.args.get('industry', 'all')
    
    # Base query
    if current_user.can_view_all_activities():
        query = Client.query
    elif current_user.department == 'EPR Compliance':
        query = Client.query.filter_by(assigned_to_epr_id=employee.id)
    else:
        query = Client.query.filter_by(account_manager_id=employee.id)
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if industry_filter != 'all':
        query = query.filter_by(industry=industry_filter)
    
    clients = query.order_by(Client.created_at.desc()).all()
    
    # Get unique values for filters
    all_industries = db.session.query(Client.industry).distinct().all()
    
    return render_template('sales/clients.html', 
                         clients=clients,
                         industries=[i[0] for i in all_industries],
                         filters={
                             'status': status_filter,
                             'industry': industry_filter
                         })

@bp.route('/client/<int:id>')
@login_required
def client_detail(id):
    """Show client details."""
    client = Client.query.get_or_404(id)
    
    # Check access
    if not current_user.can_view_all_activities():
        if (current_user.department == 'EPR Compliance' and client.assigned_to_epr_id != current_user.employee.id) or \
           (current_user.department != 'EPR Compliance' and client.account_manager_id != current_user.employee.id):
            flash('You do not have permission to view this client.', 'error')
            return redirect(url_for('sales.list_clients'))
    
    projects = client.projects.all()
    
    return render_template('sales/client_detail.html', client=client, projects=projects)

@bp.route('/analytics')
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager', 'Digital Marketing', 'Business Development')
def analytics():
    """Sales analytics and reports."""
    employee = current_user.employee
    
    # Get leads based on user access  
    if current_user.can_view_all_activities() or current_user.can_manage_department_funnel():
        leads = Lead.query.all()
        clients = Client.query.all()
    else:
        leads = Lead.query.filter_by(assigned_to_id=employee.id).all()
        clients = Client.query.filter_by(account_manager_id=employee.id).all()
    
    # Monthly lead generation trends
    monthly_leads = defaultdict(int)
    for lead in leads:
        month_key = lead.created_at.strftime('%Y-%m')
        monthly_leads[month_key] += 1
    
    # Conversion rates
    total_leads = len(leads)
    converted_leads = len([l for l in leads if l.status == 'Closed Won'])
    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Revenue by month
    monthly_revenue = defaultdict(float)
    for client in clients:
        if client.projects:
            for project in client.projects:
                if project.value:
                    month_key = project.created_at.strftime('%Y-%m')
                    monthly_revenue[month_key] += float(project.value)
    
    return render_template('sales/analytics.html',
                         leads=leads,
                         clients=clients,
                         monthly_leads=dict(monthly_leads),
                         monthly_revenue=dict(monthly_revenue),
                         conversion_rate=conversion_rate)

@bp.route('/funnel')
@login_required
@role_required('Admin', 'HR', 'Management', 'General Manager', 'Department Manager', 'Digital Marketing', 'Business Development')
def sales_funnel():
    """Interactive sales funnel view."""
    employee = current_user.employee
    
    # Get leads based on user access
    if current_user.can_view_all_activities() or current_user.can_manage_department_funnel():
        leads = Lead.query.all()
    else:
        leads = Lead.query.filter_by(assigned_to_id=employee.id).all()
    
    # Organize leads by status
    funnel_stages = {
        'New': [l for l in leads if l.status == 'New'],
        'Qualified': [l for l in leads if l.status == 'Qualified'], 
        'Proposal': [l for l in leads if l.status == 'Proposal'],
        'Negotiation': [l for l in leads if l.status == 'Negotiation'],
        'Closed Won': [l for l in leads if l.status == 'Closed Won'],
        'Closed Lost': [l for l in leads if l.status == 'Closed Lost']
    }
    
    # Calculate funnel metrics
    total_value_by_stage = {}
    for stage, stage_leads in funnel_stages.items():
        total_value_by_stage[stage] = sum(
            float(lead.estimated_value or 0) for lead in stage_leads
        )
    
    # Conversion rates between stages
    conversion_rates = {}
    stage_names = list(funnel_stages.keys())
    for i in range(len(stage_names) - 2):  # Exclude Closed Won/Lost
        current_stage = stage_names[i]
        next_stage = stage_names[i + 1]
        current_count = len(funnel_stages[current_stage])
        next_count = len(funnel_stages[next_stage])
        if current_count > 0:
            conversion_rates[f"{current_stage}_to_{next_stage}"] = (next_count / current_count) * 100
    
    return render_template('sales/funnel.html',
                         funnel_stages=funnel_stages,
                         total_value_by_stage=total_value_by_stage,
                         conversion_rates=conversion_rates)

@bp.route('/lead/<int:id>/update-status', methods=['POST'])
@login_required
def update_lead_status_api(id):
    """API endpoint to update lead status via AJAX."""
    lead = Lead.query.get_or_404(id)
    
    # Check access
    if not (current_user.can_view_all_activities() or current_user.can_manage_department_funnel()) and lead.assigned_to_id != current_user.employee.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        # Validate status
        valid_statuses = ['New', 'Qualified', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        old_status = lead.status
        lead.status = new_status
        db.session.commit()
        
        # Log activity
        activity = ActivityLog(
            activity_type='Lead Status Updated',
            description=f'Lead {lead.company_name} moved from {old_status} to {new_status}',
            department=current_user.department,
            performed_by_id=current_user.employee.id,
            entity_type='Lead',
            entity_id=lead.id
        )
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Lead status updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500 