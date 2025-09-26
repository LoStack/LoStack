from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, 
    HiddenField,
    SelectField, 
    StringField, 
    SubmitField,
    SelectMultipleField
)
from wtforms.validators import (
    DataRequired, 
    Length, 
    Optional, 
    Regexp, 
    ValidationError
)
from wtforms.widgets import CheckboxInput, ListWidget

SERVICE_NAME_REGEX = r'^[a-z0-9-]+$'
SERVICE_DEPENDENCIES_REGEX = r'^[a-z0-9-,]*$'
REFRESH_FREQUENCY_REGEX = r'^\d+[s]s?$'
PORT_REGEX = r'^\d{1,5}$'
SESSION_DURTION_REGEX =  r'^\d+[smh]$'
ACCESS_GROUPS_REGEX = r'^[a-zA-Z0-9,._\s-]+$'


class MultiCheckboxField(SelectMultipleField):
    """Custom field for multiple checkboxes"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class PackageEntryForm(FlaskForm):
    """Form for creating and editing LoStack Package entries"""
    
    id = HiddenField()
    
    name = StringField(
        'Container Name',
        validators=[
            DataRequired(message="Container name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
            Regexp(
                SERVICE_NAME_REGEX,
                message="Name can only contain lowercase letters, numbers, and hyphens"
            )
        ],
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Unique service name"
    )

    service_names = StringField(
        'Service Names',
        validators=[
            Length(min=0, max=400, message="Name must be between 0 and 400 characters"),
            Regexp(
                SERVICE_DEPENDENCIES_REGEX,
                message="Separate with commas. Names can only contain lowercase letters, numbers, and hyphens."
            )
        ],
        render_kw={
            "placeholder": "service-db,service-redis",
            "class": "form-control"
        },
        description="Startup containers, use commas, no spaces."
    )
    
    display_name = StringField(
        'Display Name',
        validators=[
            Optional(),
            Length(max=200, message="Display name cannot exceed 200 characters")
        ],
        render_kw={
            "placeholder": "My Service",
            "class": "form-control"
        },
        description="Custom name shown on loading page (optional)"
    )
    
    port = StringField(
        'Internal Port',
        validators=[
            DataRequired(message="Port is required"),
            Regexp(
                PORT_REGEX,
                message="Invalid port, must be between 1 and 65535"
            )
        ],
        render_kw={
            "placeholder": "8080",
            "class": "form-control"
        },
        description="Port the service runs on"
    )
    
    session_duration = StringField(
        'Session Duration',
        validators=[
            DataRequired(message="Session duration is required"),
            Regexp(
               SESSION_DURTION_REGEX,
                message="Duration must be in format like '5m', '30s', or '2h'"
            )
        ],
        render_kw={
            "placeholder": "5m",
            "class": "form-control"
        },
        description="Idle time until container shutdown (e.g., 45s, 5m, 1h)"
    )
        
    refresh_frequency = StringField(
        'Refresh Frequency',
        validators=[
            DataRequired(message="Refresh frequency is required"),
            Regexp(
                REFRESH_FREQUENCY_REGEX,
                message="Frequency must be in format like '3s', '500ms', or '1s'"
            )
        ],
        render_kw={
            "placeholder": "3s",
            "class": "form-control"
        },
        description="Loading page refresh interval (e.g., 3s, 10s)"
    )
    
    show_details = BooleanField(
        'Show Details',
        render_kw={"class": "form-check-input"},
        description="Show service details on the loading page"
    )
    
    enabled = BooleanField(
        'Enabled',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Include this service in the generated configuration"
    )

    lostack_autostart_enabled = BooleanField(
        'Auto-Start',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Enable container auto-start/stop"
    )

    lostack_autoupdate_enabled = BooleanField(
        'Auto-Update',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Enable container auto update"
    )

    lostack_access_enabled = BooleanField(
        'Access Control',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Enable LoStack group access control"
    )

    access_groups = MultiCheckboxField(
        'Allowed Groups',
        choices=[],  # Will be populated dynamically
        validators=[Optional()],
        description=""
    )

    
    
    submit = SubmitField(
        'Save Service',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_port(self, field):
        """Custom validator for port range"""
        try:
            port_num = int(field.data)
            if not (1 <= port_num <= 65535):
                raise ValidationError("Port must be between 1 and 65535")
        except ValueError:
            raise ValidationError("Port must be a valid number")
    
    def validate_name(self, field):
        """Custom validator to check for service name uniqueness"""
        with current_app.app_context():
            if field.data:
                # Skip validation if this is an edit (has id) and name hasn't changed
                if self.id.data:
                    existing_service = current_app.models.PackageEntry.query.get(self.id.data)
                    if existing_service and existing_service.name == field.data:
                        return
                
                # Check for duplicate names
                existing = current_app.models.PackageEntry.query.filter_by(name=field.data).first()
                if existing:
                    raise ValidationError("A service with this name already exists")

def populate_package_entry_form(form, service, all_groups):
    """Helper function to populate form with service data"""
    form.id.data = service.id
    form.name.data = service.name
    form.service_names.data = service.service_names
    form.display_name.data = service.display_name
    form.port.data = service.port
    form.session_duration.data = service.session_duration
    form.refresh_frequency.data = service.refresh_frequency
    form.show_details.data = service.show_details
    form.enabled.data = service.enabled
    form.lostack_autostart_enabled.data = service.lostack_autostart_enabled
    form.lostack_autoupdate_enabled.data = service.lostack_autoupdate_enabled
    form.lostack_access_enabled.data = service.lostack_access_enabled
    
    if service.access_groups:
        form.access_groups.data = service.allowed_groups
    else:
        form.access_groups.data = []