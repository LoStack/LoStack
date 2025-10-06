import docker
import logging
import os
from collections import defaultdict
from queue import Queue
from flask import (
    Flask,
    current_app,
    render_template,
    Response,
    Blueprint,
    g
)

from app.permissions import get_proxy_user_meta


def check_user_access(user_groups:list[str], package_groups:list[str]):
    print(user_groups, package_groups)
    for g in user_groups:
        if g in package_groups:
            return True

def register_blueprint(app:Flask) -> Blueprint:

    bp = blueprint = Blueprint(
        'dashboard',
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    logger = logging.getLogger(__name__ + f'.DASHBOARD')

    @bp.route("/")  # App root
    @app.permission_required(app.models.PERMISSION_ENUM.EVERYBODY)
    def dashboard() -> Response:
        """Show per-user dashboard"""
        logger.info("Showing dashboard")
        
        # Get all installed packages
        installed_packages = current_app.models.PackageEntry.query.all()

        all_routes = current_app.models.Route.query.all()        
        logger.info(f"Installed packages {installed_packages}")

        user_groups = g.groups
        
        logger.info(f"Showing dashboard with groups {user_groups}")

        # Filter packages based on user access
        if app.config.get("ADMIN_GROUP") in user_groups:
            allowed_packages = installed_packages
            allowed_routes = all_routes
        else:
            allowed_packages = []
            for package in installed_packages:
                package_groups = [g.strip() for g in package.access_groups.split(',') if g.strip()]
                if check_user_access(user_groups, package_groups):
                    allowed_packages.append(package)
            allowed_routes = []
            for route in all_routes:
                route_groups = [g.strip() for g in route.access_groups.split(',') if g.strip()]
                if check_user_access(user_groups, route_groups):
                    allowed_routes.append(route)
        
        logger.info(f"Showing dashboard with allowed packages {allowed_packages}")

        # Get Docker client for container status
        docker_client = current_app.docker_manager.client
        
        # Group services by homepage group
        service_groups = defaultdict(list)
        
        for package in allowed_packages:
            try:
                # Initialize service data with package defaults
                service_data = {
                    'name': package.name,
                    'homepage_name': package.homepage_name,
                    'homepage_icon': package.homepage_icon,
                    'homepage_description': package.homepage_description,
                    'homepage_url': package.homepage_url.replace('${service}', package.name),
                    'homepage_group': package.homepage_group,
                    'container_status': 'unknown',
                    'exit_code': None,
                    'item_type': 'service'
                }
                
                service_names = [s.strip() for s in package.service_names.split(',') if s.strip()]
                
                running_containers = []
                for service_name in service_names:
                    try:
                        container = docker_client.containers.get(service_name)
                        running_containers.append(container)
                        container_state = container.attrs['State']
                        status = container.status.lower()
                        
                        if status == 'running':
                            if container_state.get('Health', {}).get('Status') == 'healthy':
                                service_data['container_status'] = 'healthy'
                            elif container_state.get('Health', {}).get('Status') == 'unhealthy':
                                service_data['container_status'] = 'unhealthy'
                            else:
                                service_data['container_status'] = 'running'
                        elif status == 'exited':
                            service_data['container_status'] = 'exited'
                            service_data['exit_code'] = container_state.get('ExitCode', 0)
                        elif status == 'restarting':
                            service_data['container_status'] = 'restarting'
                        elif status == 'paused':
                            service_data['container_status'] = 'paused'
                        elif status == 'dead':
                            service_data['container_status'] = 'dead'
                        elif status == 'created':
                            service_data['container_status'] = 'created'
                        else:
                            service_data['container_status'] = status
                        
                        if container.status == 'running':
                            labels = container.labels
                            if 'homepage.name' in labels:
                                service_data['homepage_name'] = labels['homepage.name']
                            if 'homepage.icon' in labels:
                                service_data['homepage_icon'] = labels['homepage.icon']
                            if 'homepage.description' in labels:
                                service_data['homepage_description'] = labels['homepage.description']
                            if 'homepage.group' in labels:
                                service_data['homepage_group'] = labels['homepage.group']
                            if 'homepage.url' in labels:
                                service_data['homepage_url'] = labels['homepage.url']
                            break
                            
                    except docker.errors.NotFound:
                        continue
                    except Exception as e:
                        logger.warning(f"Error checking container {service_name}: {e}")
                        continue
                
                # If no running containers found, check compose files for labels
                if service_data['container_status'] == 'unknown' and service_names:
                    try:
                        # Determine which compose file to check
                        if package.core_service:
                            # Check main compose file
                            compose_handler = current_app.docker_handler.compose_file_handlers("/docker/docker-compose.yml")
                        else:
                            # Check lostack compose file
                            compose_handler = current_app.docker_handler.compose_file_handlers("/docker/lostack-compose.yml")
                        
                        # Extract labels
                        for service_name in service_names:
                            service_config = compose_handler.get_service_data(service_name)
                            if service_config and 'labels' in service_config:
                                labels = service_config['labels']
                                
                                # Handle both list and dict format labels
                                if isinstance(labels, list):
                                    label_dict = {}
                                    for label in labels:
                                        if '=' in label:
                                            key, value = label.split('=', 1)
                                            label_dict[key] = value
                                    labels = label_dict
                                
                                # Update service data with compose labels
                                if 'homepage.name' in labels:
                                    service_data['homepage_name'] = labels['homepage.name']
                                if 'homepage.icon' in labels:
                                    service_data['homepage_icon'] = labels['homepage.icon']
                                if 'homepage.description' in labels:
                                    service_data['homepage_description'] = labels['homepage.description']
                                if 'homepage.group' in labels:
                                    service_data['homepage_group'] = labels['homepage.group']
                                if 'homepage.url' in labels:
                                    service_data['homepage_url'] = labels['homepage.url']
                                
                                break
                        
                        # Check if any containers are stopped
                        if running_containers:
                            # Some containers exist but may not be running
                            statuses = [c.status for c in running_containers]
                            if 'running' in statuses:
                                service_data['container_status'] = 'running'
                            elif 'paused' in statuses:
                                service_data['container_status'] = 'paused'
                            else:
                                service_data['container_status'] = 'stopped'
                                # Get exit code from the first stopped container
                                for container in running_containers:
                                    if container.status in ['exited', 'stopped']:
                                        service_data['exit_code'] = container.attrs['State'].get('ExitCode', 0)
                                        break
                        else:
                            service_data['container_status'] = 'stopped'
                            
                    except Exception as e:
                        logger.warning(f"Error reading compose data for {package.name}: {e}")
                        service_data['container_status'] = 'stopped'
                
                # Add to appropriate group
                service_groups[service_data['homepage_group']].append(service_data)
                
            except Exception as e:
                logger.error(f"Error processing package {package.name}: {e}")
                continue
        
        for route in allowed_routes:
            try:
                if not route.enabled:
                    continue
                    
                if route.custom_rule:
                    route_url = f"https://{route.prefix}.{current_app.config.get('DOMAIN_NAME', 'lostack.internal')}/"
                else:
                    route_url = f"https://{route.prefix}.{current_app.config.get('DOMAIN_NAME', 'lostack.internal')}/"
                
                route_data = {
                    'name': route.prefix,
                    'homepage_name': route.homepage_name,
                    'homepage_icon': route.homepage_icon,
                    'homepage_description': route.homepage_description,
                    'homepage_url': route_url,
                    'homepage_group': route.homepage_group,
                    'item_type': 'route'
                }
                
                service_groups[route_data['homepage_group']].append(route_data)
                
            except Exception as e:
                logger.error(f"Error processing route {route.name}: {e}")
                continue
        
        sorted_groups = dict(sorted(service_groups.items()))
        for group_name in sorted_groups:
            sorted_groups[group_name].sort(key=lambda x: x['homepage_name'].lower())

        return render_template("dashboard.html", service_groups=sorted_groups)
    
    app.register_blueprint(bp)