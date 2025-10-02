from .middleware import register_blueprint as register_middleware_blueprint
from .file_browser import register_blueprint as register_browser_blueprint
from .containers import register_blueprint as register_containers_blueprint
from .dashboard import register_blueprint as register_dashboard_blueprint
from .depot import register_blueprint as register_depot_blueprint
from .launcher import register_blueprint as register_launcher_blueprint
from .ldap import register_blueprint as register_ldap_blueprint
from .services import register_blueprint as register_services_blueprint
from .settings import register_blueprint as register_settings_blueprint
from .traefik_routes import register_blueprint as register_traefik_routes_blueprint
from .user import register_blueprint as register_user_blueprint 

def register_blueprints(app):
    for callback in [
        register_middleware_blueprint,
        register_browser_blueprint,
        register_containers_blueprint,
        register_dashboard_blueprint,
        register_depot_blueprint,
        register_launcher_blueprint,
        register_ldap_blueprint,
        register_traefik_routes_blueprint,
        register_services_blueprint,
        register_settings_blueprint,
        register_user_blueprint
    ]:
        callback(app)