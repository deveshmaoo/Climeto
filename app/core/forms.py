from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, SubmitField, DateTimeField, BooleanField
from wtforms.validators import DataRequired, Optional

class EventForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    start = DateTimeField('Start Time', validators=[DataRequired()], format='%Y-%m-%dT%H:%M:%S')
    end = DateTimeField('End Time', validators=[Optional()], format='%Y-%m-%dT%H:%M:%S')
    all_day = BooleanField('All Day')
    submit = SubmitField('Create Event')

class TrainingForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
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
    reason = TextAreaField('Reason for Assignment')
    submit = SubmitField('Assign Training') 