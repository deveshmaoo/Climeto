from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, FileField, IntegerField, FloatField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email
from flask_wtf.file import FileRequired, FileAllowed
from datetime import date

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    department = SelectField('Department', validators=[DataRequired()], 
                           choices=[('Management', 'Management'),
                                  ('General Manager', 'General Manager'),
                                  ('HR', 'HR'),
                                  ('EPR Compliance', 'EPR Compliance'),
                                  ('Project Development', 'Project Development'),
                                  ('Digital Marketing', 'Digital Marketing'),
                                  ('Business Development', 'Business Development')])
    start_date = DateField('Start Date', validators=[DataRequired()], default=date.today)
    end_date = DateField('End Date', validators=[Optional()])
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')
    manager_id = SelectField('Project Manager', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Create Project')

class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    assigned_to = SelectField('Assign To', validators=[DataRequired()], coerce=int)
    department = SelectField('Department', validators=[Optional()], 
                           choices=[('', 'Select Department'),
                                  ('Management', 'Management'),
                                  ('General Manager', 'General Manager'),
                                  ('HR', 'HR'),
                                  ('EPR Compliance', 'EPR Compliance'),
                                  ('Project Development', 'Project Development'),
                                  ('Digital Marketing', 'Digital Marketing'),
                                  ('Business Development', 'Business Development')])
    deadline = DateField('Deadline', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')
    estimated_hours = FloatField('Estimated Hours', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Create Task')

class TaskRatingForm(FlaskForm):
    quality_rating = SelectField('Quality Rating', 
                               choices=[(i, str(i)) for i in range(1, 11)], 
                               validators=[DataRequired()], coerce=int)
    timeliness_rating = SelectField('Timeliness Rating', 
                                  choices=[(i, str(i)) for i in range(1, 11)], 
                                  validators=[DataRequired()], coerce=int)
    feedback = TextAreaField('Feedback', validators=[DataRequired()])
    submit = SubmitField('Submit Rating')

class TaskQueryForm(FlaskForm):
    query_text = TextAreaField('Query', validators=[DataRequired()])
    submit = SubmitField('Raise Query')

class QueryResponseForm(FlaskForm):
    response_text = TextAreaField('Response', validators=[DataRequired()])
    submit = SubmitField('Submit Response')

class DocumentUploadForm(FlaskForm):
    name = StringField('Document Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    file = FileField('Upload File', validators=[FileRequired(), FileAllowed(['pdf', 'doc', 'docx', 'txt', 'xlsx', 'pptx'], 'Document files only!')])
    submit = SubmitField('Upload Document')

class DocumentCommentForm(FlaskForm):
    comment_text = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Add Comment')

# Sales Management Forms
class LeadForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired()])
    contact_person = StringField('Contact Person', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    industry = StringField('Industry', validators=[Optional()])
    source = SelectField('Source', choices=[
        ('Website', 'Website'),
        ('Referral', 'Referral'),
        ('Cold Call', 'Cold Call'),
        ('Social Media', 'Social Media'),
        ('Email Campaign', 'Email Campaign'),
        ('Trade Show', 'Trade Show'),
        ('Other', 'Other')
    ], default='Website')
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')
    estimated_value = FloatField('Estimated Value', validators=[Optional(), NumberRange(min=0)])
    expected_close_date = DateField('Expected Close Date', validators=[Optional()])
    assigned_to = SelectField('Assign To', validators=[DataRequired()], coerce=int)
    notes = TextAreaField('Notes')
    submit = SubmitField('Create Lead')

class LeadUpdateForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('New', 'New'),
        ('Qualified', 'Qualified'),
        ('Proposal', 'Proposal'),
        ('Negotiation', 'Negotiation'),
        ('Closed Won', 'Closed Won'),
        ('Closed Lost', 'Closed Lost')
    ], validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')])
    estimated_value = FloatField('Estimated Value', validators=[Optional(), NumberRange(min=0)])
    expected_close_date = DateField('Expected Close Date', validators=[Optional()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Update Lead')

class LeadInteractionForm(FlaskForm):
    interaction_type = SelectField('Interaction Type', choices=[
        ('Call', 'Phone Call'),
        ('Email', 'Email'),
        ('Meeting', 'Meeting'),
        ('Demo', 'Demo'),
        ('Proposal', 'Proposal'),
        ('Follow-up', 'Follow-up'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    next_follow_up = DateField('Next Follow-up Date', validators=[Optional()])
    submit = SubmitField('Add Interaction')

class ConvertLeadForm(FlaskForm):
    account_manager = SelectField('Account Manager', validators=[DataRequired()], coerce=int)
    epr_assignee = SelectField('EPR Compliance Assignee', validators=[DataRequired()], coerce=int)
    project_name = StringField('Initial Project Name', validators=[DataRequired()])
    project_description = TextAreaField('Project Description')
    project_value = FloatField('Project Value', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Convert to Client')

class CalendarEventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    event_type = SelectField('Event Type', choices=[
        ('Meeting', 'Meeting'),
        ('Deadline', 'Deadline'),
        ('Birthday', 'Birthday'),
        ('Holiday', 'Holiday'),
        ('Training', 'Training'),
        ('Review', 'Review'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    event_date = DateField('Event Date', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[Optional()])
    start_time = StringField('Start Time', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    end_time = StringField('End Time', validators=[Optional()])
    location = StringField('Location', validators=[Optional()])
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')
    is_recurring = SelectField('Recurring', choices=[('No', 'No'), ('Yes', 'Yes')], default='No')
    send_reminders = SelectField('Send Reminders', choices=[('No', 'No'), ('Yes', 'Yes')], default='No')
    department = SelectField('Department', validators=[Optional()], 
                           choices=[('', 'All Departments'),
                                  ('Management', 'Management'),
                                  ('General Manager', 'General Manager'),
                                  ('HR', 'HR'),
                                  ('EPR Compliance', 'EPR Compliance'),
                                  ('Project Development', 'Project Development'),
                                  ('Digital Marketing', 'Digital Marketing'),
                                  ('Business Development', 'Business Development')])
    submit = SubmitField('Create Event')

class TrainingAssignmentForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], coerce=int)
    training_title = StringField('Training Title', validators=[DataRequired()])
    training_type = SelectField('Training Type', choices=[
        ('Performance Improvement', 'Performance Improvement'),
        ('Skill Development', 'Skill Development'),
        ('Compliance Training', 'Compliance Training'),
        ('Leadership Development', 'Leadership Development'),
        ('Technical Training', 'Technical Training'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description')
    due_date = DateField('Due Date', validators=[DataRequired()])
    reason = TextAreaField('Reason for Assignment', validators=[DataRequired()])
    submit = SubmitField('Assign Training')