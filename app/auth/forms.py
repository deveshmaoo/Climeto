from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from ..models.users import User

class LoginForm(FlaskForm):
    email = StringField('Email or Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=1, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=1, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', validators=[DataRequired()], coerce=int)
    department = SelectField('Department', validators=[DataRequired()], 
                           choices=[(dept, dept) for dept in User.DEPARTMENTS])
    position = StringField('Position', validators=[DataRequired()], default='Employee')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Create User')

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', validators=[DataRequired()], coerce=int)
    department = SelectField('Department', validators=[DataRequired()], 
                           choices=[(dept, dept) for dept in User.DEPARTMENTS])
    is_active = BooleanField('Active')
    submit = SubmitField('Update User') 