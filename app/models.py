import datetime
import logging
import yaml
import cssutils
from flask import current_app
from flask_login import UserMixin
from random import choice as random_choice
from string import ascii_lowercase
from werkzeug.datastructures import ImmutableDict

def sanitize_css(css_input: str) -> str:
    sheet = cssutils.parseString(css_input)
    safe_css = []
    for rule in sheet:
        if rule.type == rule.STYLE_RULE:
            safe_props = []
            for p in rule.style:
                value = p.value
                if p.priority:  # e.g. "important"
                    value += f" !{p.priority}"
                safe_props.append(f"{p.name}: {value};")
            if safe_props:
                safe_css.append(f"{rule.selectorText} {{ {' '.join(safe_props)} }}")
    return "\n".join(safe_css)

def _init_db(app):
    db = app.db

    class PERMISSION_ENUM:
        _NAMES = {
            (EVERYBODY := 5) : app.config["USER_GROUP"],
            (ADMIN := 10)   : app.config["ADMIN_GROUP"],
            (OWNER := 15)   : "owners",
            (NOACCESS := 99): "NOACCESS"
        } 
        _LOOKUP = {v:k for k,v in _NAMES.items()}

    class User(UserMixin, db.Model):
        """User object with flask_login UserMixin"""
        __tablename__ = "User"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        # Permission integer, calculated from user groups
        permission_integer = db.Column(db.Integer, default=PERMISSION_ENUM.EVERYBODY)
        # User primary name
        name = db.Column(db.String(100), unique=True, nullable=False)
        # Date user was added to LoStack db
        date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        # Selected UI themes
        theme = db.Column(db.String(100), nullable=False, default="default")
        # Selected Editor Theme
        editor_theme = db.Column(db.String(100), nullable=False, default="default")
        # custom css
        custom_css = db.Column(db.Text, nullable=False, default="")
        

    class SecretKey(db.Model):
        """Table to store Flask and FlaskWTF secret keys"""
        __tablename__ = "SecretKey"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        key = db.Column(db.String(24), nullable=False)


    class LoStackDefaults(db.Model):
        """Default configuration for LoStack package entry"""
        __tablename__ = "LoStackDefaults"
        __bind_key__ = "lostack-db"
        
        id = db.Column(db.Integer, primary_key=True)
        domain = db.Column(db.String(255), nullable=False, default=app.config["DOMAIN_NAME"])
        session_duration = db.Column(db.String(10), nullable=False, default=app.config["AUTOSTART_DEFAULT_SESSION_DURATION"])
        refresh_frequency = db.Column(db.String(10), nullable=False, default=app.config["AUTOSTART_REFRESH_FREQUENCY"])
        show_details = db.Column(db.Boolean, default=True)

        @classmethod
        def get_defaults(cls):
            """Get the current defaults (create if none exist)"""
            defaults = cls.query.first()
            if not defaults:
                defaults = cls()
                db.session.add(defaults)
                db.session.commit()
            return defaults


    class PackageEntry(db.Model):
        """Individual installed Package configuration"""
        __tablename__ = "PackageEntry"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        # Package name, must be uniqe for searchability
        name = db.Column(db.String(100), unique=True, nullable=False)
        # List of docker container names to up / down
        service_names = db.Column(db.String(400), nullable=True, default="")
        # What internal port Traefik should connect to
        port = db.Column(db.String(10), nullable=False, default=app.config["LOSTACK_DEFAULT_PACKAGE_PORT"])
        # How long the autostart session should last without inactivity
        session_duration = db.Column(db.String(10), nullable=False, default=app.config["AUTOSTART_DEFAULT_SESSION_DURATION"])
        # What name to show on the autostart loading screen
        display_name = db.Column(db.String(200), nullable=True)
        # How often sablier loading screen retries connections
        refresh_frequency = db.Column(db.String(10), nullable=False, default=app.config["AUTOSTART_REFRESH_FREQUENCY"])
        # Show container details on Sablier loading screen
        show_details = db.Column(db.Boolean, nullable=False, default=False)
        # Not used anymore, kept for future
        automatic = db.Column(db.Boolean, nullable=False, default=False)
        # If in main docker compose
        core_service = db.Column(db.Boolean, nullable=False, default=False)
        # Enables Traefik Route
        enabled = db.Column(db.Boolean, nullable=False, default=True)
        # Enables middleware autostart
        lostack_autostart_enabled = db.Column(db.Boolean, nullable=False, default=True)
        # Enable automatic container update
        lostack_autoupdate_enabled = db.Column(db.Boolean, nullable=False, default=False)
        # Enables LoStack forward-auth for role checking
        lostack_access_enabled = db.Column(db.Boolean, nullable=False, default=True)
        # List of middlewares to add to traefik router
        middlewares= db.Column(db.String(1024), nullable=True, default="")
        # Ldap groups allowed to access end service
        access_groups = db.Column(db.String(1024), nullable=False, default=app.config["ADMIN_GROUP"])
        # If service should be mounted to ${DOMAINNAME} - onle one service should have this 
        mount_to_root = db.Column(db.Boolean, nullable=False, default=False)
        # Homepage icon / icon path
        homepage_icon = db.Column(db.String(100), unique=False, nullable=False, default="mdi-application")
        # Homepage name
        homepage_name = db.Column(db.String(100), unique=False, nullable=False, default="CHANGE ME")
        # Homepage group
        homepage_group = db.Column(db.String(100), unique=False, nullable=False, default="Apps")
        # Homepage Description
        homepage_description = db.Column(db.String(100), unique=False, nullable=False, default="Homepage Description")
        # Homepage URL
        homepage_url = db.Column(db.String(100), unique=False, nullable=False, default="${service}."+app.config["DOMAIN_NAME"])
        # Last time accessed via auth middleware
        last_accessed = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        # Disable service autostart in GUI and Middleware
        force_disable_autostart = db.Column(db.Boolean, nullable=False, default=False)
        # Disable service access control in GUI and Middleware
        force_disable_access_control = db.Column(db.Boolean, nullable=False, default=False)
        # Disable service autoupdate in GUI and Middleware
        force_disable_autoupdate = db.Column(db.Boolean, nullable=False, default=False)
        # Disable editing in GUI
        force_compose_edit = db.Column(db.Boolean, nullable=False, default=False)

        @property
        def display_name_or_name(self) -> str:
            """Return display_name if set, otherwise use name"""
            return self.display_name or self.name.title()

        @property
        def docker_services(self) -> list[str]:
            return [n.strip() for n in self.service_names.split(",") if n.strip()]
        
        @property
        def allowed_groups(self) -> list[str]:
            return [g.strip() for g in self.access_groups.split(",") if g.strip()]


    class ContainerSession(db.Model):
        """Tracks container sessions and usage by users"""
        __tablename__ = "ContainerSession"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        container_name = db.Column(db.String(100), nullable=False)
        start_user_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
        start_user = db.relationship("User", foreign_keys=[start_user_id])
        users = db.Column(db.String(400), nullable=False, default="")
        started_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        last_accessed = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        total_length = db.Column(db.Integer, nullable=False, default=0)
        session_duration = db.Column(db.Integer, nullable=False, default=3600)

        @property
        def user_list(self):
            return [u.strip() for u in self.users.split(",") if u.strip()]

        def add_user(self, user: "User"):
            """Add a user to the session, updating last_accessed"""
            current_users = set(self.user_list)
            current_users.add(user.name)
            self.users = ",".join(current_users)
            self.last_accessed = datetime.datetime.utcnow()


    def export_services_config_to_file() -> str:
        """
        Export all enabled Sablier services to Traefik dynamic YAML format
        Returns the YAML string
        """
        defaults = current_app.models.LoStackDefaults.get_defaults()

        # Get all enabled services
        services = current_app.models.PackageEntry.query.filter_by(enabled=True).all()
        
        config = {
            "http": {
                "middlewares": {},
                "services": {},
                "routers": {}
            }
        }
        
        for service in services:
            service_name = service.name
            names = [s.strip() for s in [service_name, *service.service_names.split(",")]]
            names = [s for s in set(names) if s]
            names = ",".join(names).strip(",")
            
            # Create Traefik service
            config["http"]["services"][service_name] = {
                "loadBalancer": {
                    "servers": [
                        {"url": f"http://{service_name}:{service.port}/"}
                    ]
                }
            }
            
            router_conf = {
                "rule": f"Host(`{service_name}.{defaults.domain}`)",
                "entryPoints": ["https"],
                "service": service_name,
                "middlewares": []
            }

            if service.mount_to_root:
                router_conf["rule"] = f"Host(`{defaults.domain}`)"

            router_name = f"{service_name}-lostack"
                
            if any((
                service.lostack_autostart_enabled,
                service.lostack_autoupdate_enabled,
                service.lostack_access_enabled
            )):
                router_conf["middlewares"].append("lostack-middleware@docker")
            
            if service.middlewares:
                for middleware in service.middlewares.split(","):
                    router_conf["middlewares"].append(middleware)
            
            config["http"]["routers"][router_name] = router_conf
        
        if not config["http"]["middlewares"]:
            config["http"].pop("middlewares")

        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    def save_traefik_config(filename="/config/traefik/lostack-dynamic.yml") -> bool:
        """
        Export Traefik configuration and save to file
        Returns True if successful, False otherwise
        """
        try:
            yaml_content = export_services_config_to_file()
            with open(filename, 'w') as f:
                f.write(yaml_content)
            return True
        except Exception as e:
            print(f"Error saving config to {filename}: {e}")
            return False

    def update_defaults(**kwargs) -> LoStackDefaults:
        """Update default configuration"""
        defaults = LoStackDefaults.get_defaults()
        for key, value in kwargs.items():
            if hasattr(defaults, key):
                setattr(defaults, key, value)
        defaults.date_modified = datetime.datetime.utcnow()
        db.session.commit()
        return defaults

    def get_permission_from_groups(groups:list[str]) -> int:
        """Assigns the highest permission level from group memberships"""
        return max([PERMISSION_ENUM._LOOKUP.get(grp.strip(), 0) for grp in groups], default=0)

    logging.info("Initializing db...")
    db.create_all(bind_key="lostack-db")
    if not User.query.get(1):
        logging.info("Creating default (admin) user with id=1")
        user = User(id=1, name=app.config.get("LDAP_ADMIN_USERNAME"), permission_integer=PERMISSION_ENUM.ADMIN)
        db.session.add(user)
        db.session.commit()
    db.session.commit()
    app.models = ImmutableDict()
    for obj in (
        User,
        LoStackDefaults,
        PackageEntry,
        ContainerSession,
        PERMISSION_ENUM,            
        export_services_config_to_file,
        get_permission_from_groups,
        save_traefik_config,
        update_defaults,
        sanitize_css
    ):
        setattr(app.models, obj.__name__, obj)

def init_db(app):
    with app.app_context():
        _init_db(app)