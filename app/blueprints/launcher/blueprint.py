import functools
import logging
import os
from flask import (
    Blueprint,
    Response,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)
from flask_login import current_user

logger = logging.getLogger(__name__)

def register_blueprint(app):
    blueprint = bp = Blueprint(
        'launcher', __name__, 
        url_prefix='/launcher',
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    @bp.route('/')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def launcher() -> Response:
        """List all containers from compose files"""
        compose_file = request.args.get('file', 'docker-compose.yml', type=str)
        highlight_container = request.args.get('container', '', type=str)
        containers_data = []
        file_path = f"/docker/{compose_file}"

        existing_containers = current_app.docker_manager.api_client.containers(all=True)
        
        container_status = {}
        for container in existing_containers:
            names = container.get('Names', [])
            state = container.get('State', 'unknown')
            for name in names:
                container_status[name.lstrip('/')] = state

        try:
            if file_path not in current_app.docker_manager.compose_file_handlers:
                flash(f'Compose file not found: {compose_file}', 'error')
                return render_template('docker_containers.html', containers=[], compose_files=[], selected_file=compose_file)
            
            handler = current_app.docker_manager.compose_file_handlers[file_path]
            services = handler.content.get('services', {})
            
            for name, config in services.items():
                labels = config.get('labels', [])
                group = None
                is_primary = False
                
                if isinstance(labels, list):
                    for label in labels:
                        if isinstance(label, str):
                            if label.startswith('lostack.group='):
                                group = label.split('=', 1)[1].strip()
                            elif label.startswith('lostack.primary='):
                                is_primary = label.split('=', 1)[1].strip().lower() == 'true'
                elif isinstance(labels, dict):
                    group = labels.get('lostack.group')
                    is_primary = str(labels.get('lostack.primary', '')).lower() == 'true'
                                
                status = container_status.get(name, 'not_launched')
                is_running = status.lower() == 'running'
                is_stopped = status.lower() in ['exited', 'stopped', 'dead']
                is_not_launched = name not in container_status

                container_info = {
                    'name': name,
                    'image': config.get('image', 'N/A'),
                    'group': group or 'None',
                    'config': config,
                    'status': status,
                    'is_running': is_running,
                    'is_stopped': is_stopped,
                    'is_not_launched': is_not_launched,
                    'is_primary': is_primary
                }
                containers_data.append(container_info)
                
        except Exception as e:
            flash(f'Failed to retrieve containers: {str(e)}', 'error')
            logger.error(f"Error retrieving containers: {e}")

        # Get list of available compose files
        compose_files = [
            {'name': 'docker-compose', 'path': 'docker-compose.yml'},
            {'name': 'lostack-compose', 'path': 'lostack-compose.yml'}
        ]

        return render_template(
            'launcher.html', 
            containers=containers_data,
            compose_files=compose_files,
            selected_file=compose_file,
            selected_container=highlight_container
        )

    @bp.route('/action/<mode>/<name>/<action>/stream', methods=['GET', 'POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def action(mode, name, action) -> Response:
        """Start a container from compose"""
        compose_file = request.args.get('file', 'docker-compose', type=str)
        file_path = f"/docker/{compose_file}"
        
        if file_path not in current_app.docker_manager.compose_file_handlers:
            return "Not found", 404
                
        handler = current_app.docker_manager.compose_file_handlers.get(file_path)

        if mode == 'group':
            group_data = handler.get_service_group_data(name)
            names = list(group_data.keys())
        elif mode == 'container':
            names = name
        else:
            raise ValueError(f"Unknown mode - {mode}")

        act = {
            "up": handler.stream_compose_up,
            "stop": handler.stream_compose_stop,
        }.get(action)

        return act( current_app._get_current_object(), names)

    app.register_blueprint(blueprint)
    return blueprint