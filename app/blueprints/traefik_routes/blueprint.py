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

from .forms import RouteEntryForm, populate_route_entry_form
from .models import init_db

def register_blueprint(app:Flask) -> Blueprint:
    bp = blueprint = Blueprint(
        'traefik_routes',
        __name__,
        url_prefix="/routes",
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    @bp.route("/")
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def routes() -> Response:
        """List all configured routes"""
        routes = current_app.models.Route.query.order_by(
            current_app.models.Route.name
        ).all()

        return render_template(
            "routes.html",
            routes=routes,
        )

    @bp.route("/new", methods=["GET", "POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def route_new():
        """Create a new route"""
        form = RouteEntryForm()
            
        try:
            all_groups = current_app.get_all_ldap_groups()
            form.access_groups.choices = [(group, group) for group in all_groups]
        except Exception as e:
            current_app.logger.error(f"Failed to fetch LDAP groups: {e}")
            form.access_groups.choices = []
            if request.method == "GET":
                flash("Warning: Could not load LDAP groups", "warning")

        if request.method == "GET":
            form.enabled.data = True
            form.use_https.data = False
            form.use_insecure_transport.data = False
            form.lostack_access_enabled.data = True
            form.port.data = "80"
            form.homepage_icon.data = "mdi-application"
            form.homepage_group.data = "Apps"
            form.middlewares.data = ""
        
        if form.validate_on_submit():
            try:
                route = current_app.models.Route()
                route.name = form.name.data
                route.prefix = form.prefix.data
                route.host = form.host.data
                route.port = form.port.data
                route.use_insecure_transport = form.use_insecure_transport.data
                route.enabled = form.enabled.data
                route.use_https = form.use_https.data
                route.homepage_icon = form.homepage_icon.data
                route.homepage_name = form.homepage_name.data
                route.homepage_group = form.homepage_group.data
                route.homepage_description = form.homepage_description.data
                route.lostack_access_enabled = form.lostack_access_enabled.data
                route.middlewares = form.middlewares.data

                current_app.db.session.add(route)
                current_app.db.session.commit()
                flash(f"Route '{route.name}' created successfully!", "success")
                
                if current_app.models.save_traefik_routes_config():
                    flash("Traefik configuration updated!", "info")
                
                return redirect(url_for("traefik_routes.routes"))
            except Exception as e:
                current_app.db.session.rollback()
                flash(f"Error creating route: {str(e)}", "error")
                
        return render_template("route_form.html", form=form, route=None, action="New")

    @bp.route("/action/<int:route_id>/edit", methods=["GET", "POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def route_edit(route_id):
        """Edit an existing route"""
        route = current_app.models.Route.query.get_or_404(route_id)
        form = RouteEntryForm()
        
        try:
            all_groups = current_app.get_all_ldap_groups()
            form.access_groups.choices = [(group, group) for group in all_groups]
        except Exception as e:
            current_app.logger.error(f"Failed to fetch LDAP groups: {e}")
            form.access_groups.choices = []
            if request.method == "GET":
                flash("Warning: Could not load LDAP groups", "warning")

        if request.method == "GET":
            populate_route_entry_form(form, route, all_groups)
        
        if form.validate_on_submit():
            route.name = form.name.data
            route.prefix = form.prefix.data
            route.host = form.host.data
            route.port = form.port.data
            route.use_insecure_transport = form.use_insecure_transport.data
            route.enabled = form.enabled.data
            route.use_https = form.use_https.data
            route.homepage_icon = form.homepage_icon.data
            route.homepage_name = form.homepage_name.data
            route.homepage_group = form.homepage_group.data
            route.homepage_description = form.homepage_description.data
            route.lostack_access_enabled = form.lostack_access_enabled.data
            route.middlewares = form.middlewares.data

            try:
                current_app.db.session.commit()
                flash(f"Route '{route.name}' updated successfully!", "success")
                
                if current_app.models.save_traefik_routes_config():
                    flash("Traefik configuration updated!", "info")
                
                return redirect(url_for("traefik_routes.routes"))
            except Exception as e:
                current_app.db.session.rollback()
                flash(f"Error updating route: {str(e)}", "error")

        return render_template("route_form.html", form=form, route=route, action="Edit")

    @bp.route("/action/<int:route_id>/delete", methods=["POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def route_delete(route_id):
        """Delete a route"""
        route = current_app.models.Route.query.get_or_404(route_id)
        route_name = route.name
        
        try:
            current_app.db.session.delete(route)
            current_app.db.session.commit()
            
            config_updated = current_app.models.save_traefik_routes_config()
            
            return jsonify({
                "success": True,
                "config_updated": config_updated,
                "message": f"Route '{route_name}' deleted successfully"
            })
        except Exception as e:
            current_app.db.session.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/action/<int:route_id>/toggle", methods=["POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def route_toggle(route_id):
        """AJAX endpoint to toggle route enabled status"""
        route = current_app.models.Route.query.get_or_404(route_id)
        
        try:
            route.enabled = not route.enabled
            current_app.db.session.commit()
            
            config_updated = current_app.models.save_traefik_routes_config()
            
            return jsonify({
                "success": True,
                "enabled": route.enabled,
                "config_updated": config_updated,
                "message": f"Route {'enabled' if route.enabled else 'disabled'} successfully"
            })
        except Exception as e:
            current_app.db.session.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    init_db(app)
    app.register_blueprint(bp)
    return bp