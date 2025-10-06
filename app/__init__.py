import json
import ldap
import logging
import logging.config
import os
import platform
import secrets
import sys
from flask import (
    Flask,
    Blueprint,
    current_app,
    request,
    __version__ as flask_version
)
from flask_login import LoginManager, current_user
from app.version import __version__
from app.environment import ENV_DEFAULTS, ENV_PARSING, ENV_NON_REQUIRED
from app.extensions import setup_db
from app.extensions.docker import DockerManagerStreaming
from app.extensions.ezldap import setup_ldap_manager
from app.extensions.service_manager import init_service_manager
from app.extensions.certificate_generator import check_certificates_exist, generate_certificates
from app.extensions.common.label_extractor import LabelExtractor as labext
from app.models import init_db
from app.permissions import setup_permissions, get_proxy_user_meta

def _require_config(app, var_name):
    if (value := app.config.get(var_name)) is None:
        logging.error((msg := f"{var_name} environment variable cannot be empty"))
        raise ValueError(msg)
    return value

def _if_not_exists_write(dest, content, conditional=True) -> bool:
    if not conditional:
        return False # Do nothing
    if os.path.exists(dest):
        return False # Do nothing
    parent = os.path.dirname(dest)
    if not os.path.exists(parent):
        os.makedirs(parent)
    with open(dest, "w+") as f:
        f.write(content)
    return True

def setup_app_config(app: Flask) -> None:
    for k, v in ENV_DEFAULTS.items():
        val = os.environ.get(k, v)
        if (parser := ENV_PARSING.get(k)):
            val = parser(val)
        app.config.update({k:val})
        if k in ENV_NON_REQUIRED:
            continue
        _require_config(app, k)
    # Blueprints can populate this to add to context provider
    app.config["PROVIDED_CONTEXT"] = {}
    trusted_proxies_string = app.config.get("TRUSTED_PROXY_IPS", None)
    if not trusted_proxies_string:
        raise ValueError("TRUSTED_PROXY_IPS var cannot be empty")
    app.config["TRUSTED_PROXY_IPS"] = [i.strip() for i in trusted_proxies_string.split(",")]
    if app.config.get("DEPOT_DEV_MODE"):
        app.config["DEPOT_DIR"] = app.config.get("DEPOT_DIR_DEV")

    # Configure NAV_LINKS with adjusted groups  
    app.config["NAV_LINKS"][app.config["USER_GROUP"]] = app.config["NAV_LINKS"].pop("users")
    app.config["NAV_LINKS"][app.config["ADMIN_GROUP"]] = app.config["NAV_LINKS"].pop("admins")

def setup_logging(app: Flask) -> None:
    logging.basicConfig(
        level=logging.DEBUG
        if labext.parse_boolean(app.config.get("DEBUG"))
        else logging.INFO
    )
    logging.config.dictConfig(app.config["LOG_CONFIG"])

def setup_spew(app: Flask) -> None:
    if app.config.get("DEBUG"):
            logging.info(
                "SYSTEM INFO:\n"
                +json.dumps(
                    {
                        "OS": (platform.system(), platform.release(), platform.version()),
                        "Python Version": sys.version,
                        "Flask Version": flask_version,
                    },
                    indent=2
                )
            )

def setup_media_folders(app: Flask) -> None:
    if not app.config.get("FIRST_RUN_SETUP_MEDIA_FOLDERS"):
        return
    for subdir in app.config["MEDIA_FOLDERS"].split(","):
        d = os.path.join("/media", subdir.strip())
        if os.path.exists(d):
            continue
        app.logger.info(f"Creating media folder media/{subdir.strip()}")
        os.makedirs(d, exist_ok=True)
        os.chmod(d, 0o755)

def setup_compose(app: Flask):
    if not os.path.exists("/docker/docker-compose.yml"):
        raise FileNotFoundError("Could not locate docker-compose.yml, do you have /docker mounted properly?")

def setup_certificates(app: Flask):
    if app.config["FIRST_RUN_CREATE_SELF_SIGNED_CERT"]:
        if not check_certificates_exist(app.config["DOMAIN_NAME"], "/certs"):
            app.logger.info("Generating self-signed cert...")
            generate_certificates(app.config["DOMAIN_NAME"], "/certs", app.logger)
        else:
            app.logger.info("Cert already exists")
    else:
        app.logger.info("Cert generation is disabled")

def setup_user_login(app: Flask) -> None:
    def user_loader(user_id:int|str) -> "User":
        """User Loader for Flask-Login"""
        return current_app.models.User.query.get(int(user_id))

    login_manager = LoginManager()
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id):
        return user_loader(user_id)

def setup_ldap(app: Flask) -> None:
    app.ldap_manager = setup_ldap_manager(app)
    app.ldap_manager.await_connection()
    with app.ldap_manager:
        initialized = True
        try:
            grps = app.ldap_manager.get_all_groups()
        except ldap.NO_SUCH_OBJECT:
            initialized = False
        if not initialized: # Not set up
            # Setup LDAP structure
            if app.config.get("FIRST_RUN_SETUP_LDAP"):
                app.ldap_manager.setup_ldap_structure()
            else:
                raise ValueError("FIRST_RUN_SETUP_LDAP set to false and LDAP not initialized")

def setup_docker_manager(app: Flask) -> None:
    app.docker_manager = DockerManagerStreaming(
        (
            "/docker/lostack-compose.yml",
            "/docker/docker-compose.yml"
        )
    )

def setup_docker_handler(app):
    with app.app_context():
        app.docker_handler = init_service_manager(app)
        app.docker_manager.modified_callback = app.docker_handler.refresh

def setup_secrets(app):
    app.logger.info("Loading secrets keys")
    secrets_files = (
        ("SECRET_KEY", "/config/lostack/secrets/secret_key"),
        ("WTF_CSRF_SECRET_KEY", "/config/lostack/secrets/wtf_secret_key"),
    )
    for conf_name, file in secrets_files:
        with open(file, "r") as f:
            app.config[conf_name] = f.read()
    app.secret_key = app.config["SECRET_KEY"]

def handle_first_run(app):
    # Config file creation
    config_files = (
        ( # User-managed Traefik dynamic config file
            "/config/traefik/dynamic.yml",
            app.config["DEFAULT_TRAEFIK_CONFIG"],
            app.config.get("FIRST_RUN_CREATE_TRAEFIK_CONFIG")
        ),
        ( # Auto-generated LoStack Service Traefik dynamic config file
            "/config/traefik/lostack-dynamic.yml",
            "http:\n",
            True
        ),
        ( # Auto-generated LoStack Routes Traefik dynamic config file
            "/config/traefik/lostack-routes-dynamic.yml",
            "http:\n",
            True
        ),
        ( # User-managed Authelia static configuration file
            "/config/authelia/configuration.yml",
            app.config["DEFAULT_AUTHELIA_CONFIG"],
            app.config.get("FIRST_RUN_CREATE_AUTHELIA_CONFIG")
        ),
        ( # LoStack-managed, with used-edits, LoStack Service compose file
            "/docker/lostack-compose.yml",
            app.config["DEFAULT_LOSTACK_COMPOSE"],
            True
        ),
        ( # Static CoreDNS config file
            "/config/coredns/resolv.conf",
            app.config["DEFAULT_COREDNS_CONFIG"],
            app.config.get("FIRST_RUN_CREATE_COREDNS_CONFIG")
        ),
        ( # LoStack autostart session tracking file
            "/config/lostack/sessions.json",
            "{}",
            True
        ),
        ( # LoStack Flask Secret Key
            "/config/lostack/secrets/secret_key",
            secrets.token_urlsafe(32),
            app.config.get("FIRST_RUN_CREATE_FLASK_SECRET_KEY")
        ),
        ( # LoStack Flask WTF Secret Key
            "/config/lostack/secrets/wtf_secret_key",
            secrets.token_urlsafe(32),
            app.config.get("FIRST_RUN_CREATE_WTF_SECRET_KEY")
        )
    )

    for args in config_files:
        if not _if_not_exists_write(*args):
            app.logger.info(f"Skipped {args[0]} - already exists or disabled")

    setup_media_folders(app)
    setup_compose(app)
    setup_certificates(app)

def setup_and_init_db(app: Flask) -> None:
    app.db = setup_db(app)
    with app.app_context():
        init_db(app)

def setup_context_provider(app: Flask) -> None:
    @app.context_processor
    def provide_selection() -> dict[str:any]:
        """
        Context processor which runs before any template is rendered
        Provides access to these values in all templates
        """
        selected_theme = "default"
        if hasattr(current_user, 'theme'):
            selected_theme = current_user.theme or "default"
        
        selected_editor_theme = "default"
        if hasattr(current_user, 'editor_theme'):
            selected_editor_theme = current_user.editor_theme or "default"
        
        nav_links = current_app.config["NAV_LINKS"]
        allowed_links = {}
        user_groups = get_proxy_user_meta(request,{"groups": app.config["GROUPS_HEADER"]})["groups"]
        for group, config in nav_links.items():
            if group in user_groups:
                allowed_links[group] = config

        return {
            "nav_links": allowed_links,
            "themes": app.config.get("BOOTSWATCH_THEMES"),
            "editor_themes": app.config.get("CODEMIRROR_THEMES"),
            "selected_theme": selected_theme,
            "selected_editor_theme" : selected_editor_theme,
            "depot_url" : app.config["DEPOT_URL"],
            "custom_css_data" : app.models.sanitize_css(current_user.custom_css),
            **app.config.get("PROVIDED_CONTEXT")
        }


def create_app(*args, **kw) -> Flask:
    app = Flask(
        __name__,
        static_folder='static', 
        static_url_path='/static',
        **kw
    )

    setup_app_config(app)
    setup_logging(app)
    setup_spew(app)
    
    if app.config.get("FIRST_RUN"):
        app.logger.info("Running first run tasks...")
        handle_first_run(app)

    setup_secrets(app)
    setup_ldap(app)
    setup_and_init_db(app)
    setup_docker_manager(app)
    setup_docker_handler(app)
    setup_user_login(app)
    setup_permissions(app)
    setup_context_provider(app)

    if app.config.get("FIRST_RUN"):
        app.logger.info("First run setup completed successfully!")
        sys.exit(0) # Don't start app on setup, exit happily

    # Must be imported here.
    # Some blueprints need db to be initialized before importing.
    from app.blueprints import register_blueprints
    register_blueprints(app)
    
    return app

if __name__ == '__main__':
    create_app().run(debug=True)