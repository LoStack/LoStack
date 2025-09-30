import os
from flask import (
    Flask,
    Blueprint,
    Response,
    current_app,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify
)

from .forms import PackageEntryForm, populate_package_entry_form

def register_blueprint(app:Flask) -> Blueprint:
    bp = blueprint = Blueprint(
        'services',
        __name__,
        url_prefix="/services",
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    @bp.route("/")
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def services() -> Response:
        """List all installed Packages groups"""
        services = current_app.models.PackageEntry.query.order_by(
            current_app.models.PackageEntry.name
        ).all()

        all_names = []
        for s in services:
            for n in [
                _n.strip()
                for _n in s.service_names.split(",")
                if _n.strip()
            ]:
                all_names.append(n)
        container_names = all_names

        containers = current_app.docker_manager.get_services_info(container_names)

        return render_template(
            "services.html",
            services=services,
            containers=containers,
        )
    
    @bp.route("/action/<int:service_id>/edit", methods=["GET", "POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def service_edit(service_id):
        """Edit an existing LoStack Package Entry"""
        service = current_app.models.PackageEntry.query.get_or_404(service_id)
        form = PackageEntryForm()
        
        try:
            all_groups = current_app.get_all_ldap_groups()
            form.access_groups.choices = [(group, group) for group in all_groups]
        except Exception as e:
            current_app.logger.error(f"Failed to fetch LDAP groups: {e}")
            form.access_groups.choices = []
            if request.method == "GET":
                flash("Warning: Could not load LDAP groups", "warning")
        
        if request.method == "GET":
            populate_package_entry_form(form, service, all_groups)
        
        if form.validate_on_submit():
            service.name = form.name.data
            service.service_names = form.service_names.data
            service.display_name = form.display_name.data or None
            service.port = form.port.data
            service.session_duration = form.session_duration.data
            service.refresh_frequency = form.refresh_frequency.data
            service.show_details = form.show_details.data
            service.enabled = form.enabled.data
            service.lostack_autostart_enabled = form.lostack_autostart_enabled.data
            service.lostack_autoupdate_enabled = form.lostack_autoupdate_enabled.data
            service.lostack_access_enabled = form.lostack_access_enabled.data
            service.middlewares = form.middlewares.data
            
            if form.access_groups.data:
                service.access_groups = ','.join(form.access_groups.data)
            else:
                service.access_groups = ""
            
            try:
                current_app.db.session.commit()
                flash(f"Service '{service.display_name_or_name}' updated successfully!", "success")
                
                if current_app.models.save_traefik_config():
                    flash("Configuration file updated!", "info")
                
                return redirect(url_for("services.services"))
            except Exception as e:
                current_app.db.session.rollback()
                flash(f"Error updating service: {str(e)}", "error")
        
        return render_template("service_form.html", form=form, service=service, action="Edit")

    @bp.route("/action/<int:service_id>/toggle", methods=["POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def service_toggle(service_id):
        """AJAX endpoint to toggle service enabled status"""
        service = current_app.models.PackageEntry.query.get_or_404(service_id)
        
        try:
            service.enabled = not service.enabled
            current_app.db.session.commit()
            
            config_updated = current_app.models.save_traefik_config()
            
            return jsonify({
                "success": True,
                "enabled": service.enabled,
                "config_updated": config_updated,
                "message": f"Service {'enabled' if service.enabled else 'disabled'} successfully"
            })
        except Exception as e:
            current_app.db.session.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/action/<int:service_id>/toggle_access", methods=["POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def service_toggle_access_control(service_id):
        """AJAX endpoint to toggle service access control"""
        service = current_app.models.PackageEntry.query.get_or_404(service_id)
        
        try:
            service.lostack_access_enabled = not service.lostack_access_enabled
            current_app.db.session.commit()
            
            config_updated = current_app.models.save_traefik_config()
            
            return jsonify({
                "success": True,
                "enabled": service.enabled,
                "config_updated": config_updated,
                "message": f"LoStack group check {'enabled' if service.enabled else 'disabled'} successfully"
            })
        except Exception as e:
            current_app.db.session.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/action/<int:service_id>/toggle_autostart", methods=["POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def service_toggle_autostart(service_id):
        """AJAX endpoint to toggle service autostart"""
        service = current_app.models.PackageEntry.query.get_or_404(service_id)
        
        try:
            service.lostack_autostart_enabled = not service.lostack_autostart_enabled
            current_app.db.session.commit()
            
            config_updated = current_app.models.save_traefik_config()
            
            return jsonify({
                "success": True,
                "enabled": service.enabled,
                "config_updated": config_updated,
                "message": f"Sablier autoStart {'enabled' if service.enabled else 'disabled'} successfully"
            })
        except Exception as e:
            current_app.db.session.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/action/<int:service_id>/toggle_autoupdate", methods=["POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def service_toggle_autoupdate(service_id):
        """AJAX endpoint to toggle service autoupdate"""
        service = current_app.models.PackageEntry.query.get_or_404(service_id)
        
        try:
            service.lostack_autoupdate_enabled = not service.lostack_autoupdate_enabled
            current_app.db.session.commit()
            
            config_updated = current_app.models.save_traefik_config()
            
            return jsonify({
                "success": True,
                "enabled": service.enabled,
                "config_updated": config_updated,
                "message": f"Sablier autoStart {'enabled' if service.enabled else 'disabled'} successfully"
            })
        except Exception as e:
            current_app.db.session.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route('/action/<int:service_id>/containers/<action>')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def service_action(service_id, action):
        service = current_app.models.PackageEntry.query.get_or_404(service_id)
        docker_service_names = service.docker_services

        if not action in ["up", "stop", "remove", "logs"]:
            abort(404)
            
        if action in ["up", "stop"]:
            compose_file = "/docker/docker-compose.yml" if service.core_service else "/docker/lostack-compose.yml"
            handler = current_app.docker_manager.compose_file_handlers.get(compose_file)
            act = {
                "up": handler.stream_compose_up,
                "stop": handler.stream_compose_stop,
            }.get(action)

            return act(
                current_app._get_current_object(),
                docker_service_names
            )
        elif action in ["remove"]:
            return current_app.docker_manager.stream_shell_remove(
                current_app._get_current_object(),
                docker_service_names,
            )
        else:
            raise ValueError("How did we even get here?")

    app.register_blueprint(bp)
    return bp