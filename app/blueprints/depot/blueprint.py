from flask import (
    Flask,
    current_app,
    render_template,
    Response,
    Blueprint
)
import os
from queue import Queue
from app.extensions.common.stream_handler import StreamHandler


def stream_depot_package_install(package_name: os.PathLike) -> Response:
    return StreamHandler.generic_context_stream(
        depot_package_install,
        current_app._get_current_object(),
        package_name
    )

def stream_remove_package(package_db_id: int) -> Response:
    with current_app.app_context():
        callback = current_app.docker_handler.remove_depot_package

    return StreamHandler.generic_context_stream(
        callback,
        current_app._get_current_object(),
        package_db_id
    )

def register_blueprint(app:Flask) -> Blueprint:
    bp = blueprint = Blueprint(
        'depot',
        __name__,
        url_prefix="/depot",
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    @bp.route("/")
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def depot() -> Response:
        """Show depot page"""
        all_packages = current_app.docker_handler.depot_handler.packages.keys()
        installed_packages = [s.name for s in current_app.models.PackageEntry.query.all()]
        available_packages = [s for s in all_packages if not s in installed_packages]
        depot_data = current_app.docker_handler.depot_handler.format_packages_for_depot_page(available_packages)
        # Passes pre-formatted data / arguments to template:
        # Pre-processing litterally halved the size of the template file
        # I wasted so much time writing all that jinja filtering 
        # trying to process the data directly lol
        # {
        #     'packages': processed_packages,
        #     'groups': dict(sorted(group_counts.items())),
        #     'tags': dict(sorted(tag_counts.items())),
        #     'total_count': len(processed_packages)
        # }
        return render_template(
            "depot.html",
            **depot_data,
            depot_repo=current_app.config.get("DEPOT_URL"),
            depot_branch=current_app.config.get("DEPOT_BRANCH")
        )


    @bp.route("/update/stream")
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def depot_update() -> Response:
        resp = app.docker_handler.depot_handler.stream_update_repo()
        return resp


    @bp.route('/launch/<package>/stream')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def depot_launch(package:str) -> Response:
        result_queue = Queue()
        result_queue.put_nowait("Adding depot package to lostack compose file.")

        with current_app.app_context():
            try:
                services = current_app.docker_handler.add_depot_package(package, result_queue)
            except Exception as e:
                import traceback
                result_queue.put_nowait(f"Error adding package services to compose: {traceback.print_exc()}")
                time.sleep(1) # Wait for queue flush before context exit
                return

            compose_handler = current_app.docker_manager.compose_file_handlers.get("/docker/lostack-compose.yml")

            return compose_handler.stream_compose_up(
                current_app._get_current_object(),
                services, 
                result_queue=result_queue, 
                complete=True
            )


    @bp.route('/remove/<int:service_id>/stream')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def depot_remove(service_id:int) -> Response:
        service = current_app.models.PackageEntry.query.get_or_404(service_id)
        package_name = service.name
        docker_service_names = service.docker_services
        if service and not docker_service_names:
            current_app.db.session.delete(service)
            current_app.db.session.commit()
            return StreamHandler.message_completion_stream("No services to handle, deleted db entry,")
        else:
            return stream_remove_package(service_id)


    @bp.route("/depot_info")
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def depot_info() -> Response:
        return "OK", 200

    app.register_blueprint(bp)
    return bp