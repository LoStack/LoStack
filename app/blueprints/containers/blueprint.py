import os
from flask import (
    Flask,
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template
)


def register_blueprint(app:Flask) -> Blueprint:
    bp = blueprint = Blueprint(
        'containers',
        __name__,
        url_prefix="/containers",
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "templates")
    )

    @bp.route("/")
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def containers() -> Response:
        """List of all containers"""
        containers = current_app.docker_manager.api_client.containers(all=True)
        return render_template(
            "containers.html",
            containers=containers
        )

    @bp.route("/action/<id>/<action>")
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def containers_action(id:str, action:str) -> Response:
        """Docker container management"""
        actions = {
            "start" : current_app.docker_manager.stream_shell_start,
            "stop" : current_app.docker_manager.stream_shell_stop,
            "remove" : current_app.docker_manager.stream_shell_remove,
            "logs" : current_app.docker_manager.stream_shell_logs,
            "follow" : current_app.docker_manager.stream_shell_follow,
        }
        act = actions.get(action)
        if not act:
            raise ValueError(f"Invalid container action")

        return act(id)

    @bp.route('/api/all')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def api_containers() -> Response:
        """Get containers for JS page refresh"""
        containers = current_app.docker_manager.api_client.containers(all=True)
        return jsonify({ 'containers': containers})
    
    app.register_blueprint(bp)
    return bp