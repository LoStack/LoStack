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

NAME_REGEX = r'^[a-zA-Z0-9- ]+$'
PREFIX_REGEX = r'^[a-z0-9-]+$'
PORT_REGEX = r'^\d{1,5}$'

class MultiCheckboxField(SelectMultipleField):
    """Custom field for multiple checkboxes"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class RouteEntryForm(FlaskForm):
    """Form for creating and editing Traefik routes"""
    
    id = HiddenField()
    
    name = StringField(
        'Route Name',
        validators=[
            DataRequired(message="Route name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
            Regexp(
                NAME_REGEX,
                message="Name can only contain letters, numbers, spaces. and hyphens"
            )
        ],
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Friendly route name"
    )

    prefix = StringField(
        'Route Prefix',
        validators=[
            DataRequired(message="Route prefix is required"),
            Length(min=1, max=100, message="Route prefix must be between 1 and 100 characters"),
            Regexp(
                PREFIX_REGEX,
                message="Prefix can only contain lowercase letters, numbers, and hyphens"
            )
        ],
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Unique router prefix (cannot overlap with a LoStack service name)"
    )

    homepage_icon = StringField(
        'Dashboard Icon',
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Homarr or MDI icon to use (prefix MDI with mdi-)"
    )

    middlewares = StringField(
        'Middlewares',
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Comma-separated list of Traefik Middleware. Do not add lostack-middleware to this field."
    )

    homepage_name = StringField(
        'Dashboard Name',
        validators=[
            DataRequired(message="Dashboard name is required"),
            Length(min=1, max=100, message="Dashboard name must be between 1 and 100 characters"),
        ],
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Friendly name for the dashboard"
    )

    homepage_group = StringField(
        'Dashboard Group',
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Dashboard group to sort into on the dashboard"
    )

    homepage_description = StringField(
        'Dashboard Description',
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Description to show on the dashboard"
    )

    host = StringField(
        'Server',
        validators=[
            DataRequired(message="Server is required"),
        ],
        render_kw={
            "placeholder": "192.168.1.50 or service.hostname.ext",
            "class": "form-control"
        },
        description="Hostname or IP"
    )

    port = StringField(
        'Target Port',
        validators=[
            DataRequired(message="Port is required"),
            Regexp(
                PORT_REGEX,
                message="Invalid port, must be between 1 and 65535"
            )
        ],
        render_kw={
            "placeholder": "80",
            "class": "form-control"
        },
        description="Port on the target server"
    )
    
    enabled = BooleanField(
        'Enabled',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Include this route in the generated configuration"
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

    use_https = BooleanField(
        'Use HTTPS',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Enable this if the server uses HTTPS"
    )

    use_insecure_transport = BooleanField(
        'Use Insecure Transport',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Enable this to connect to servers using old / self-signed certificates"
    )
    
    submit = SubmitField(
        'Save Route',
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
        """
        Validator to check for service and route name uniqueness
        """
        with current_app.app_context():
            if field.data:
                # Skip validation if this is an edit (has id) and name hasn't changed
                if self.id.data:
                    existing_service = current_app.models.Route.query.get(self.id.data)
                    if existing_service and existing_service.name == field.data:
                        return
                
                # Check for duplicate names
                existing = current_app.models.PackageEntry.query.filter_by(name=field.data).first()
                existing = existing or current_app.models.Route.query.filter_by(prefix=field.data).first()
                if existing:
                    raise ValidationError("A route with this prefix or service with this name already exists")

def populate_route_entry_form(form, route, all_groups):
    """Helper function to populate form with route data"""
    form.id.data = route.id
    form.name.data = route.name
    form.prefix.data = route.prefix
    form.host.data = route.host
    form.homepage_icon.data = route.homepage_icon
    form.homepage_name.data = route.homepage_name
    form.homepage_group.data = route.homepage_group
    form.homepage_description.data = route.homepage_description
    form.port.data = route.port
    form.enabled.data = route.enabled
    form.lostack_access_enabled.data = route.lostack_access_enabled
    form.use_https.data = route.use_https
    form.use_insecure_transport.data = route.use_insecure_transport
    form.middlewares.data = route.middlewares
    
    if route.access_groups:
        form.access_groups.data = route.allowed_groups
    else:
        form.access_groups.data = []