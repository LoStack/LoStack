from flask import current_app
import yaml

def _init_db(app):
    db = app.db

    class Route(db.Model):
        """Traefik Route Entry"""
        __tablename__ = "Route"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        # Route name, must be unique for searchability
        name = db.Column(db.String(100), unique=True, nullable=False)
        # Enable Route in generated config
        enabled = db.Column(db.Boolean, nullable=False, default=True)
        # Subdomain/prefix, must be unique from any other prefix or PackageEntry name
        prefix = db.Column(db.String(100), unique=True, nullable=False)
        # What internal port Traefik should connect to
        port = db.Column(db.String(10), nullable=False, default=80)
        # Host (target server)
        host = db.Column(db.String(512), nullable=False)
        # Custom Traefik rule (overrides prefix)
        custom_rule = db.Column(db.String(512), nullable=True)
        # Enables LoStack forward-auth for role checking
        lostack_access_enabled = db.Column(db.Boolean, nullable=False, default=True)
        # Ldap groups allowed to access route
        access_groups = db.Column(db.String(1024), nullable=False, default=app.config["ADMIN_GROUP"])
        # Enable https instead of http for route
        use_https = db.Column(db.Boolean, nullable=False, default=True)
        # Enable insecure transport to servers with self-signed certs
        use_insecure_transport = db.Column(db.Boolean, nullable=False, default=True)
        # List of middlewares to add to traefik router
        middlewares= db.Column(db.String(1024), nullable=True)
        # Homepage icon / icon path
        homepage_icon = db.Column(db.String(100), unique=False, nullable=False, default="mdi-application")
        # Homepage name
        homepage_name = db.Column(db.String(100), unique=False, nullable=False, default="CHANGE ME")
        # Homepage group
        homepage_group = db.Column(db.String(100), unique=False, nullable=False, default="Apps")
        # Homepage Description
        homepage_description = db.Column(db.String(100), unique=False, nullable=False, default="")

        @property
        def allowed_groups(self) -> list[str]:
            return [g.strip() for g in self.access_groups.split(",") if g.strip()]


    def export_routes_config_to_file() -> str:
        routes = current_app.models.Route.query.filter_by(enabled=True).all()
        defaults = current_app.models.LoStackDefaults.get_defaults()

        config = {
            "http": {
                "middlewares": {},
                "services": {},
                "routers": {}
            }
        }

        for route in routes:
            route_name = route.prefix
            proto = "https" if route.use_https else "http"

            config["http"]["services"][route_name] = {
                "loadBalancer": {
                    "servers": [
                        {"url": f"{proto}://{route.host}:{route.port}/"}
                    ]
                }
            }

            if not (rule := route.custom_rule):
                rule =  f"Host(`{route_name}.{defaults.domain}`)"

            router_conf = {
                "rule": rule,
                "entryPoints": ["https"],
                "service": route_name,
                "middlewares": []
            }

            if any((
                route.lostack_access_enabled,
            )):
                router_conf["middlewares"].append("lostack-middleware@docker")
            
            if route.middlewares:
                for middleware in route.middlewares.split(","):
                    router_conf["middlewares"].append(middleware)

            config["http"]["routers"][route_name] = router_conf

        if not config["http"]["middlewares"]:
            config["http"].pop("middlewares")
        
        return yaml.dump(config, default_flow_style=False, sort_keys=False)
    
    def save_traefik_routes_config(filename="/config/traefik/lostack-routes-dynamic.yml") -> bool:
        """
        Export Traefik configuration and save to file
        Returns True if successful, False otherwise
        """
        try:
            yaml_content = export_routes_config_to_file()
            with open(filename, 'w') as f:
                f.write(yaml_content)
            return True
        except Exception as e:
            print(f"Error saving config to {filename}: {e}")
            return False

    app.logger.info("Initializing Trafik Routes table...")
    db.create_all(bind_key="lostack-db")
    db.session.commit()
    for obj in (
        Route,
        export_routes_config_to_file,
        save_traefik_routes_config
    ):
        setattr(app.models, obj.__name__, obj)

def init_db(app):
    with app.app_context():
        _init_db(app)