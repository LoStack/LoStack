import re

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget
from werkzeug.security import generate_password_hash


class MultiCheckboxField(SelectMultipleField):
    """Custom field for multiple checkboxes"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class UserForm(FlaskForm):
    """Form for creating/editing users"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50, message="Username must be between 3-50 characters")
    ], render_kw={'placeholder': 'Enter username'})
    
    password = PasswordField(
        'Password',
        validators=[],
        render_kw={'placeholder': 'Leave blank to keep current password'}
    )
    
    confirm_password = PasswordField(
        'Confirm Password', 
        render_kw={'placeholder': 'Confirm password'}
    )
    
    email = StringField('Email', validators=[
        # DataRequired(),
        # Email(message="Invalid email address")
    ], render_kw={'placeholder': 'user@lostack.internal'})
    
    first_name = StringField('First Name', validators=[
        DataRequired(),
        Length(max=100)
    ], render_kw={'placeholder': 'First name'})
    
    last_name = StringField('Last Name', validators=[
        DataRequired(),
        Length(max=100)
    ], render_kw={'placeholder': 'Last name'})
    
    phone = StringField('Phone', validators=[Optional()], 
                       render_kw={'placeholder': '+1-555-123-4567'})
    
    department = StringField('Department', validators=[Optional()],
                            render_kw={'placeholder': 'IT, HR, Sales, etc.'})
    
    title = StringField('Job Title', validators=[Optional()],
                       render_kw={'placeholder': 'Software Engineer, Manager, etc.'})
    
    groups = MultiCheckboxField('Groups', coerce=str)
    
    is_active = BooleanField('Active Account', default=True)
    
    def validate_password(self, field):
        """
        Custom password validation that:
        - Skips validation if both password fields are empty (for editing existing users)
        - Validates password strength if password is provided
        """
        # Skip validation if both password fields are empty
        if not self.password.data and not self.confirm_password.data:
            return
        
        if not self.password.data == self.confirm_password.data:
            raise ValueError(f'Passwords do not match {self.password.data} {self.confirm_password.data}')

        # If password is provided, validate it
        if self.password.data:
            password = self.password.data
            
            # Minimum length check
            if len(password) < 8:
                raise ValueError('Password must be at least 8 characters long')
            
            # Check for at least one uppercase letter
            if not re.search(r'[A-Z]', password):
                raise ValueError('Password must contain at least one uppercase letter')
            
            # Check for at least one lowercase letter
            if not re.search(r'[a-z]', password):
                raise ValueError('Password must contain at least one lowercase letter')
            
            # Check for at least one digit
            if not re.search(r'[0-9]', password):
                raise ValueError('Password must contain at least one number')
            
            # Check for at least one special character
            if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', password):
                raise ValueError('Password must contain at least one special character')
        
    def validate_username(self, field):
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValueError('Username can only contain letters, numbers, dots, hyphens, and underscores')


class GroupForm(FlaskForm):
    """Form for creating/editing groups"""
    name = StringField('Group Name', validators=[
        DataRequired(),
        Length(min=2, max=50, message="Group name must be between 2-50 characters")
    ], render_kw={'placeholder': 'Enter group name'})
    
    description = TextAreaField('Description', validators=[Optional()],
                               render_kw={'placeholder': 'Group description', 'rows': 3})
    
    members = MultiCheckboxField('Members', coerce=str)
    
    def validate_name(self, field):
        # Add custom validation for group name format if needed
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValidationError('Group name can only contain letters, numbers, dots, hyphens, and underscores')

class SearchForm(FlaskForm):
    """Form for searching users/groups"""
    search_type = SelectField('Search In', choices=[
        ('users', 'Users'),
        ('groups', 'Groups'),
        ('both', 'Users & Groups')
    ], default='users')
    
    search_query = StringField('Search', validators=[Optional()],
                              render_kw={'placeholder': 'Search by name, username, email...'})