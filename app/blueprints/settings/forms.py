from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, 
    SelectField, 
    StringField, 
    SubmitField
)
from wtforms.validators import (
    DataRequired, 
    Length, 
    Regexp
)

DOMAIN_REGEX = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
URL_REGEX = r'^https?://.+'
DURATION_REGEX = r'^\d+[smh]$'

class LoStackDefaultsForm(FlaskForm):
    """Form for editing Sablier default configuration"""
    
    domain = StringField(
        'Domain',
        validators=[
            DataRequired(message="Domain is required"),
            Length(min=3, max=255, message="Domain must be between 3 and 255 characters"),
            Regexp(
                DOMAIN_REGEX,
                message="Please enter a valid domain name"
            )
        ],
        render_kw={
            "placeholder": "example.com",
            "class": "form-control"
        },
        description="Base domain for LoStack services"
    )

    session_duration = StringField(
        'Default Session Duration',
        validators=[
            DataRequired(message="Session duration is required"),
            Regexp(
                DURATION_REGEX,
                message="Duration must be in format like '5m', '30s', or '2h'"
            )
        ],
        render_kw={
            "placeholder": "5m",
            "class": "form-control"
        },
        description="Default session duration (e.g., 5m, 30s, 2h)"
    )

    refresh_frequency = StringField(
        'Refresh Frequency',
        validators=[
            DataRequired(message="Refresh frequency is required"),
            Regexp(
                DURATION_REGEX,
                message="Frequency must be in format like '3s', '500ms', or '1s'"
            )
        ],
        render_kw={
            "placeholder": "3s",
            "class": "form-control"
        },
        description="How often to refresh the loading page (e.g., 3s, 500ms)"
    )
    
    show_details = BooleanField(
        'Show Details by Default',
        render_kw={"class": "form-check-input"},
        description="Show service details on loading pages by default"
    )
    
    submit = SubmitField(
        'Update Defaults',
        render_kw={"class": "btn btn-primary"}
    )