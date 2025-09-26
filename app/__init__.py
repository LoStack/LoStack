import json
import ldap
import logging
import logging.config
import os
import platform
import sys
from flask import (
    Flask,
    Blueprint,
    current_app,
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
from app.permissions import setup_permissions


def _require_config(app, var_name):
    if (value := app.config.get(var_name)) is None:
        logging.error((msg := f"{var_name} environment variable cannot be empty"))
        raise ValueError(msg)
    return value


def setup_config(app: Flask) -> None:
    for k, v in ENV_DEFAULTS.items():
        val = os.environ.get(k, v)
        if (parser := ENV_PARSING.get(k)):
            val = parser(val)
        app.config.update({k:val})
        if k in ENV_NON_REQUIRED:
            continue
        _require_config(app, k)
    # Blueprint can populate this to add to context provider
    app.config["PROVIDED_CONTEXT"] = {}
    trusted_proxies_string = app.config.get("TRUSTED_PROXY_IPS", None)
    if not trusted_proxies_string:
        raise ValueError("TRUSTED_PROXY_IPS var cannot be empty")
    app.config["TRUSTED_PROXY_IPS"] = [i.strip() for i in trusted_proxies_string.split(",")]
    if app.config.get("DEPOT_DEV_MODE"):
        app.config["DEPOT_DIR"] = app.config.get("DEPOT_DIR_DEV")
    
    if not os.path.exists("/docker/lostack-compose.yml"):
        with open("/docker/lostack-compose.yml", "w+") as f:
            f.write(app.config["DEFAULT_LOSTACK_COMPOSE"])
        
    if not os.path.exists("/docker/docker-compose.yml"):
        raise FileNotFoundError("Could not locate docker-compose.yml, do you have /docker mounted properly?")

def setup_logging(app: Flask) -> None:
    logging.basicConfig(
        level=logging.DEBUG
        if labext.parse_boolean(app.config.get("DEBUG"))
        else logging.INFO
    )
    logging.config.dictConfig(app.config["LOG_CONFIG"])

def setup_media_folders(app: Flask) -> None:
    if app.config.get("SETUP_MEDIA_FOLDERS"):
        for subdir in app.config["MEDIA_FOLDERS"].split(","):
            d = os.path.join("/media", subdir.strip())
            if not os.path.exists(d):
                app.logger.info(f"Creating media folder media/{subdir.strip()}")
                os.makedirs(d, exist_ok=True)
                os.chmod(d, 0o755)

def setup_certificates(app: Flask):
    if app.config["CREATE_SELF_SIGNED_CERT"]:
        if not check_certificates_exist(app.config["DOMAIN_NAME"], "/certs"):
            app.logger.info("Generating self-signed cert...")
            generate_certificates(app.config["DOMAIN_NAME"], "/certs", app.logger)
        else:
            app.logger.info("Self-signed cert already exists")
    else:
        app.logger.info("Self-signed cert generation is disabled")


def setup_user_login(app: Flask) -> None:
    def user_loader(user_id:int|str) -> "User":
        """User Loader for Flask-Login"""
        return current_app.models.User.query.get(int(user_id))

    login_manager = LoginManager()
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id):
        return user_loader(user_id)


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
        
        return {
            "themes": app.config.get("BOOTSWATCH_THEMES"),
            "editor_themes": app.config.get("CODEMIRROR_THEMES"),
            "selected_theme": selected_theme,
            "selected_editor_theme" : selected_editor_theme,
            "depot_url" : app.config["DEPOT_URL"],
            "custom_css_data" : app.models.sanitize_css(current_user.custom_css),
            **app.config.get("PROVIDED_CONTEXT")
        }


def create_app(*args, **kw) -> Flask:
    print(args)
    app = Flask(
        __name__,
        static_folder='static', 
        static_url_path='/static',
        **kw
    )

    setup_config(app)    
    setup_logging(app)
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
    
    setup_media_folders(app)
    setup_certificates(app)

    if not os.path.exists("/config/lostack-dynamic.yml"):
        with open("/config/lostack-dynamic.yml", "w+") as f:
            app.logger.info("Creating traefik dynamic config file")
            f.write("http:\n") # Empty traefik config

    app.ldap_manager = setup_ldap_manager(app)
    with app.ldap_manager:
        initialized = True
        try:
            grps = app.ldap_manager.get_all_groups()
        except ldap.NO_SUCH_OBJECT:
            initialized = False
        if not initialized: # Not set up
            # Setup LDAP structure
            app.ldap_manager.setup_ldap_structure()
                        

    app.db = setup_db(app)
    with app.app_context():
        init_db(app)

    app.docker_manager = DockerManagerStreaming(
        (
            "/docker/lostack-compose.yml",
            "/docker/docker-compose.yml"
        )
    )

    with app.app_context():
        app.docker_handler = init_service_manager(app)
        app.docker_manager.modified_callback = app.docker_handler.refresh

    setup_user_login(app)
    setup_permissions(app)
    setup_context_provider(app)


    # Must be imported here 
    from app.blueprints import register_blueprints
    register_blueprints(app)
    
    return app


if __name__ == '__main__':
    create_app().run(debug=True)