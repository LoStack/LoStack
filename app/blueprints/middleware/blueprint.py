"""
middleware blueprint - Andrew Spangler
Group-based endpoint access controller for LoStack
Compatible with Traefik+Authelia and possibly other auth systems
"""

import datetime
import fnmatch
import json
import logging
import os
import threading
import time
import traceback
import queue
import uuid
from queue import Queue, Empty
from collections import defaultdict
from flask import (
    Flask,
    Blueprint,
    request,
    Response,
    current_app,
    redirect,
    jsonify,
    render_template
)
from flask_login import current_user
from functools import wraps
from app.permissions import get_proxy_user_meta

from .session_manager import SessionManager, parse_duration

logger = logging.getLogger(__name__ + f'.ACCESS')


def register_blueprint(app: Flask) -> Blueprint:
    bp = blueprint = Blueprint(
        'middleware',
        __name__,
        url_prefix="/middleware",
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "templates")
    )

    with app.app_context():
        ADMIN_GROUP = app.config.get("ADMIN_GROUP")
        GROUPS_HEADER = app.config.get("GROUPS_HEADER")
        TRUSTED_PROXY_IPS = app.config.get("TRUSTED_PROXY_IPS")
        USERNAME_HEADER = app.config.get("USERNAME_HEADER")
        FORWARDED_FOR_HEADER = app.config.get("FORWARDED_FOR_HEADER")
        FORWARDED_HOST_HEADER = app.config.get("FORWARDED_HOST_HEADER")
        FORWARDED_METHOD_HEADER = app.config.get("FORWARDED_METHOD_HEADER")
        FORWARDED_URI_HEADER = app.config.get("FORWARDED_URI_HEADER")
        DOMAIN_NAME = app.config.get("DOMAIN_NAME")
        NAME_HEADER = app.config.get("NAME_HEADER")
        EMAIL_HEADER = app.config.get("EMAIL_HEADER")

    app.autostart_session_manager = session_manager = SessionManager(app)

    logger.debug(f"""
\nStarting Auth blueprint with configuration
\tUsername header: {USERNAME_HEADER}
\tName header: {NAME_HEADER}
\tEmail header: {EMAIL_HEADER}
\tGroups header: {GROUPS_HEADER}
\tAdmin group: {ADMIN_GROUP}
\tTrusted proxies: {TRUSTED_PROXY_IPS}
\tForwarded FOR header: {FORWARDED_FOR_HEADER}
\tForwarded HOST header: {FORWARDED_HOST_HEADER}
\tForwarded METHOD header: {FORWARDED_METHOD_HEADER}
\tForwarded URI header: {FORWARDED_URI_HEADER}
\tDomain Name: {DOMAIN_NAME}
""")

    def check_access(func):
        """Decorator to check a user's access to an endpoint"""
        @wraps(func)
        def wrapped(*args, **kwargs) -> Response:
            try:
                remote_addr = request.environ.get('REMOTE_ADDR')
                meta = get_proxy_user_meta(
                    request,
                    {
                        "user": USERNAME_HEADER,
                        "groups": GROUPS_HEADER,
                        "forwarded_for": FORWARDED_FOR_HEADER,
                        "forwarded_host": FORWARDED_HOST_HEADER,
                        "forwarded_method": FORWARDED_METHOD_HEADER,
                        "forwarded_uri": FORWARDED_URI_HEADER
                    }
                )
                username = meta["user"]
                user_groups = meta["groups"]
                forwarded_for = meta["forwarded_for"]
                forwarded_host = meta["forwarded_host"]
                forwarded_method = meta["forwarded_method"]
                forwarded_uri = meta["forwarded_uri"]

                if current_app.config.get("debug"):
                    logger.debug(f"DEBUG: From {remote_addr} for {forwarded_for} "
                    f"with headers: {json.dumps(dict(request.headers), indent=2)}")

                if not username:
                    logger.error(f"ERROR: Missing username header: {USERNAME_HEADER}")
                    return Response("Unauthorized", status=401)

                if not user_groups:
                    logger.error(f"ERROR: Missing groups header: {GROUPS_HEADER} for user: {username}")
                    return Response("Unauthorized", status=401)

                service_name = forwarded_host.split(".")[0]
                package_entry = current_app.models.PackageEntry.query.filter_by(name=service_name).first()

                if not package_entry:
                    logger.warning(f"WARNING: No package entry found for {service_name}")
                else:
                    logger.debug(f"Found package entry")

                if not package_entry and not ADMIN_GROUP in user_groups:
                    logger.warning(f"DENY (SERVICE NOT FOUND): {username}@{remote_addr}[{forwarded_for}] "
                        f"-> {forwarded_method}@{forwarded_host}{forwarded_uri}")
                    return Response("Forbidden", status=403)
                else:
                    if package_entry:
                        allowed_groups = package_entry.allowed_groups
                    else:
                        allowed_groups = [ADMIN_GROUP]

                if not any((g in allowed_groups for g in user_groups)):
                    if not ADMIN_GROUP in user_groups:
                        logger.warning(f"DENY: {username}@{remote_addr}[{forwarded_for}] "
                            f"-> {forwarded_method}@{forwarded_host}{forwarded_uri}")
                        return Response("Forbidden", status=403)

                if package_entry:
                    with current_app.app_context():
                        try:
                            for container in package_entry.docker_services:
                                current_app.logger.debug("Attempting service update")
                                current_app.autostart_session_manager.update_access(container, current_user)
                        except Exception as e:
                            logger.error(f"Failed to update session on access: {e}")


                logger.info(f"ALLOW: {username}@{remote_addr} [{forwarded_for}] "
                    f"-> {forwarded_method} {forwarded_host}{forwarded_uri}")

                return func(*args, **kwargs)

            except Exception as e:
                logger.error(f"ERROR: Error in access check: {str(e)}")
                traceback.print_exc()
                return Response("Internal Server Error", status=500)

        return wrapped

    @bp.route('/auth', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    @app.permission_required(app.models.PERMISSION_ENUM.EVERYBODY)  # Everyone can access check_access
    @check_access  # check_access limits by proxy group
    def auth() -> Response:
        try:
            try:
                meta = get_proxy_user_meta(
                    request,
                    {
                        "user": USERNAME_HEADER,
                        "groups": GROUPS_HEADER,
                        "name": NAME_HEADER,
                        "email": EMAIL_HEADER,
                        "forwarded_for": FORWARDED_FOR_HEADER,
                        "forwarded_host": FORWARDED_HOST_HEADER,
                        "forwarded_method": FORWARDED_METHOD_HEADER,
                        "forwarded_uri": FORWARDED_URI_HEADER
                    }
                )

                # Create response with headers
                resp = Response("OK", status=200)
                resp.headers[USERNAME_HEADER] = meta["user"]
                resp.headers[GROUPS_HEADER] = ",".join(meta["groups"])
                resp.headers[NAME_HEADER] = meta["name"]
                resp.headers[EMAIL_HEADER] = meta["email"]
                
                forwarded_host = meta["forwarded_host"]
                forwarded_for = meta["forwarded_for"]
                forwarded_uri = meta["forwarded_uri"]
                service_name = forwarded_host.split(".")[0]
                package_entry = current_app.models.PackageEntry.query.filter_by(name=service_name).first()
                
                if not package_entry:
                    # No package entry means no autostart needed
                    logger.info(f"No package entry found for {service_name} - skipping autostart")
                    return resp
                
                logger.debug(f"Checking autostart for service: {service_name}")
                task_id = session_manager.handle_autostart(package_entry, current_user, redirect=forwarded_host+forwarded_uri)
                if task_id:
                    stream_url = f"https://lostack.{DOMAIN_NAME}/middleware/autostart/task-stream-page/{task_id}"
                    logger.debug(f"Redirecting to task stream: {stream_url}")
                    return redirect(stream_url, code=302)
                else:
                    logger.debug(f"No task start needed for {service_name}")
                    return resp

            except Exception as e:
                logger.error(f"ERROR: Error in autostart: {str(e)}", exc_info=True)
                return Response("Internal Server Error", status=500)

        except Exception as e:
            logger.error(f"ERROR: Error in auth endpoint: {str(e)}", exc_info=True)
            return Response("Internal Server Error", status=500)

    def check_task_access(func):
        """Decorator to check user access to task endpoints"""
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                # Get user info from headers
                if not (username:=request.headers.get(USERNAME_HEADER)):
                    logger.error(f"ERROR: Missing username header: {USERNAME_HEADER}")
                    return Response("Unauthorized", status=401)
                
                groups_header = request.headers.get(GROUPS_HEADER, '')
                user_groups = [g.strip() for g in groups_header.split(',') if g.strip()] if groups_header else []
                if not user_groups:
                    logger.error(f"ERROR: Missing groups header: {GROUPS_HEADER} for user: {username}")
                    return Response("Unauthorized", status=401)
                
                if not (task_id:=kwargs.get('task_id')):
                    return Response("Bad Request - Missing task ID", status=400)
                
                if not session_manager.has_task_access(task_id, user_groups, ADMIN_GROUP):
                    logger.warning(f"DENY TASK ACCESS: {username} attempted to access task {task_id}")
                    return Response("Forbidden", status=403)
                
                logger.info(f"ALLOW TASK ACCESS: {username} accessing task {task_id}")
                return func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"ERROR: Error in task access check: {str(e)}")
                traceback.print_exc()
                return Response("Internal Server Error", status=500)
        
        return wrapped

    @bp.route('/autostart/task-stream/<task_id>')
    @app.permission_required(app.models.PERMISSION_ENUM.EVERYBODY)
    @check_task_access
    def task_stream(task_id):
        """Stream task progress updates"""
        logger.info(f"Client connecting to task stream: {task_id}")
        
        def generate():
            try:
                yield "data: " + json.dumps({"type": "connected", "task_id": task_id}) + "\n\n"
                for message in session_manager.get_task_stream(task_id):
                    yield f"data: {message}\n"
                yield "data: " + json.dumps({"type": "close"}) + "\n\n"
                
            except Exception as e:
                logger.error(f"Error in task stream generator: {e}")
                yield "data: " + json.dumps({
                    "type": "error", 
                    "message": f"Stream error: {str(e)}"
                }) + "\n\n"

        return Response(
            generate(), 
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    @bp.route('/autostart/task-status/<task_id>')
    @app.permission_required(app.models.PERMISSION_ENUM.EVERYBODY)
    @check_task_access
    def task_status(task_id):
        """Get task status as JSON"""
        status = session_manager.get_task_status(task_id)
        if not status:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(status)

    @bp.route('/autostart/task-stream-page/<task_id>')
    @app.permission_required(app.models.PERMISSION_ENUM.EVERYBODY)
    @check_task_access
    def task_stream_page(task_id):
        task = session_manager.tasks.get(task_id)
        redirect = task.task_redirect
        """Serve a simple HTML page that connects to the task stream"""
        return render_template(
            "autostart.html",
            task_id=task_id,
            redirect_url=redirect,
            refresh_frequency=parse_duration(task.refresh_frequency)
        )

    app.register_blueprint(bp)
    return bp