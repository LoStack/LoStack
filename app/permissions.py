import logging
from fnmatch import fnmatch
from flask import Flask, abort, g, request, Response
from flask_login import current_user, login_user
from functools import wraps

def get_proxy_user_meta(
    req, conf:dict
) -> dict:
    meta = {
        k : req.headers.get(v, "")
        for k,v in conf.items()
    }
    if "groups" in meta:
        groups = meta.get("groups")
        if len(groups):
            groups = groups.split(",")
        if len(groups) == 1 and groups[0] == "":
            groups = []
        meta["groups"] = groups
    return meta

def is_trusted_ip(remote_addr: str, trusted_ips: list[str]) -> bool:
    """Checks to see if the host router / proxy is trusted"""
    for ip in trusted_ips:
        if fnmatch(remote_addr, ip):
            return True
    return False

def setup_permissions(app:Flask) -> None:
    # THIS FUNCTION HANDLES ACCESS TO THE APP ITSELF
    # FOR THE FORWARD-AUTH MIDDLEWARE SEE ./blueprints/access
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

    logger = logging.getLogger(__name__ + f'.PERMISSIONS')

    def permission_required(required_permission):
        """
        SSO / Authelia Integration
        This decorator function is used to limit access to Flask endpoints 
        based on users' groups as supplied by the reverse-proxy.
        """
        def decorator(func):
            @wraps(func)
            def wrapped(*args, **kwargs) -> Response:
                # Validate proxy trust
                remote_addr = request.remote_addr
                logging.info("Request from: %s", remote_addr)
                
                if not is_trusted_ip(remote_addr, app.config["TRUSTED_PROXY_IPS"]):
                    logging.warning("Untrusted proxy: %s", remote_addr)
                    abort(403)

                meta = get_proxy_user_meta(
                    request,
                    {
                        "user" : USERNAME_HEADER,
                        "groups" : GROUPS_HEADER,
                    }
                )

                username = meta.get("user").strip()
                if not username:
                    logging.warning("No Remote-User header provided")
                    abort(403)
                    
                groups = meta.get("groups")
                permission = app.models.get_permission_from_groups(groups)

                # Get or create user 
                user = app.models.User.query.filter_by(name=username).first()

                if user is None:
                    # Create new user
                    user = app.models.User(name=username, permission_integer=permission)
                    app.db.session.add(user)
                    app.db.session.commit()
                    logging.info("Created new user: %s with permission %s", username, permission)
                elif user.permission_integer != permission:
                    # Update existing user's permissions if changed
                    user.permission_integer = permission
                    app.db.session.commit()
                    logging.info("Updated permission for user %s: %s", username, permission)
                
                # Ensure user is logged in
                if not current_user.is_authenticated:
                    login_user(user)

                # Check permission level
                if permission < required_permission:
                    logging.warning(
                        "[403] User '%s' (permission %s) attempted to access endpoint "
                        "requiring permission %s", 
                        username, permission, required_permission
                    )
                    abort(403)
                g.user = username
                g.groups = groups
                g.permission = permission
                return func(*args, **kwargs)
                
            return wrapped
        return decorator

    # For use in blueprints etc
    app.permission_required = permission_required