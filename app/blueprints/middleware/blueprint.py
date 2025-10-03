"""
middleware blueprint - Andrew Spangler
Group-based endpoint access controller for LoStack
Compatible with Traefik+Authelia and possibly other auth systems
"""

import json
import logging
import os
import time
import traceback
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


class PermissionCache:
    """Cache for user permissions and route/package lookups"""
    def __init__(self, ttl=15):
        self.ttl = ttl
        self.cache = {}
        
    def _is_expired(self, timestamp):
        return time.time() - timestamp > self.ttl
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if not self._is_expired(timestamp):
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
    
    def clear(self):
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            k for k, (_, ts) in self.cache.items() 
            if current_time - ts > self.ttl
        ]
        for k in expired_keys:
            del self.cache[k]


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
    permission_cache = PermissionCache(ttl=15)

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

    def get_target_info(service_name):
        """Get target info with caching"""
        cache_key = f"target:{service_name}"
        cached = permission_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache HIT for target: {service_name}")
            return cached
        
        logger.debug(f"Cache MISS for target: {service_name}")
        target = None
        is_package = False
        
        package_entry = current_app.models.PackageEntry.query.filter_by(name=service_name).first()
        if package_entry:
            target = package_entry
            is_package = True
        else:
            route_entry = current_app.models.Route.query.filter_by(name=service_name).first()
            if route_entry:
                target = route_entry
        
        result = {
            'target': target,
            'is_package': is_package,
            'allowed_groups': target.allowed_groups if target else []
        }
        
        permission_cache.set(cache_key, result)
        return result

    def check_user_access(username, user_groups, service_name):
        """Check if user has access to service with caching"""
        groups_key = ",".join(sorted(user_groups))
        cache_key = f"access:{username}:{groups_key}:{service_name}"
        
        cached = permission_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache HIT for access check: {username}@{service_name}")
            return cached
        
        logger.debug(f"Cache MISS for access check: {username}@{service_name}")
        
        if ADMIN_GROUP in user_groups:
            result = {'allowed': True, 'is_admin': True, 'target_info': None}
            permission_cache.set(cache_key, result)
            return result
        
        target_info = get_target_info(service_name)
        
        if not target_info['target']:
            result = {'allowed': False, 'reason': 'TARGET_NOT_FOUND', 'target_info': None}
            permission_cache.set(cache_key, result)
            return result
        
        allowed = any((g in target_info['allowed_groups'] for g in user_groups))
        result = {
            'allowed': allowed,
            'is_admin': False,
            'reason': None if allowed else 'NOT_IN_GROUPS',
            'target_info': target_info
        }
        
        permission_cache.set(cache_key, result)
        return result

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
                if not service_name:
                    logger.error(f"ERROR: Invalid service name.")
                    return Response("Unauthorized", status=404)
                
                # Check access with caching
                access_result = check_user_access(username, user_groups, service_name)
                
                if not access_result['allowed']:
                    reason = access_result['reason']
                    logger.info(f"DENY ({reason}): {username}@{remote_addr}[{forwarded_for}] "
                        f"-> {forwarded_method}@{forwarded_host}{forwarded_uri}")
                    return Response("Forbidden", status=403)
                
                # Handle autostart for packages
                target_info = access_result.get('target_info')
                if target_info and target_info['is_package']:
                    with current_app.app_context():
                        try:
                            target = target_info['target']
                            for container in target.docker_services:
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
                
                # Use cached lookup
                target_info = get_target_info(service_name)
                package_entry = target_info['target'] if target_info['is_package'] else None
                
                if not package_entry:
                    logger.debug(f"No package entry found for {service_name} - skipping autostart")
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
                
                logger.debug(f"ALLOW TASK ACCESS: {username} accessing task {task_id}")
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
        """Stream task progress updates to web terminal"""
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
    
    @bp.route('/cache/clear', methods=['POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def clear_cache():
        """Clear the permission cache (admin only)"""
        permission_cache.clear()
        logger.info("Permission cache cleared")
        return jsonify({"message": "Cache cleared successfully"})
    
    @bp.route('/cache/stats', methods=['GET'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def cache_stats():
        """Get cache statistics (admin only)"""
        permission_cache.cleanup_expired()
        return jsonify({
            "entries": len(permission_cache.cache),
            "ttl": permission_cache.ttl
        })

    app.register_blueprint(bp)
    return bp