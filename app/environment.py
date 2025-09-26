from app.extensions.common.label_extractor import LabelExtractor as labext 

DEFAULT_LOSTACK_COMPOSE = """
networks:
  traefik_network:
    driver: bridge
    name: traefik_network
    external: true
services: {}
"""

LOG_CONFIG = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s \
            %(name)s %(threadName)s in %(module)s: %(message)s",
        }
    },
    "handlers": {
        "wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "default",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "loggers": {
        "__main__": {
            "level": "INFO",
            "handlers": ["wsgi", "console"],
            # "handlers": ["console"],
            "propagate": False,
        },
        "werkzeug": {
            "level": "INFO",
            "handlers": ["wsgi", "console"],
            # "handlers": ["console"],
            "propagate": False,
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
        # "handlers": ["wsgi", "console"]
    }
}

MEDIA_FOLDERS = [
    "audiobooks",
    "books",
    "comics",
    "documents",
    "downloads",
    "images",
    "manga",
    "models",
    "movies",
    "music",
    "podcasts",
    "recordings",
    "tv",
    "www",
    "youtube",
    "youtube/general",
    "youtube/music",
    "youtube/podcasts",
    "youtube/temp",
    "downloads/audiobooks",
    "downloads/books",
    "downloads/comics",
    "downloads/documents",
    "downloads/general",
    "downloads/images",
    "downloads/manga",
    "downloads/models",
    "downloads/movies",
    "downloads/music",
    "downloads/podcasts",
    "downloads/recordings",
    "downloads/temp",
    "downloads/tv",
    "downloads/www",
    "downloads/youtube",
    "downloads/youtube/general",
    "downloads/youtube/music",
    "downloads/youtube/podcasts",
    "downloads/youtube/temp",
]

ENV_DEFAULTS = {
    "AUTHOR" : "Andrew Spangler",
    "APPLICATION_NAME" : "LoStack Admin",
    "APPLICATION_DESCRIPTION" : "Welcome to LoStack",
    "APPLICATION_DETAILS" : "Easily configure Traefik, GetHomePage, \
    and Sablier and install prebuilt services with a few clicks.",
    "CREATE_SELF_SIGNED_CERT"       : "true",
    "DEPOT_URL" : "https://github.com/AndrewSpangler/LoStack-Depot.git",
    "DEPOT_BRANCH"                  : "main",
    "DEPOT_DIR"                     : "/appdata/LoStack-Depot",
    "DEPOT_DIR_DEV"                 : "/docker/LoStack-Depot",
    "DEPOT_DEV_MODE"                : "false",
    "TRUSTED_PROXY_IPS"             : "172.*",
    "DOMAIN_NAME"                   : "lostack.internal",
    "AUTOSTART_DEFAULT_SESSION_DURATION": "5m",
    "AUTOSTART_REFRESH_FREQUENCY"   : "3s",
    "DB_HOST"                       : "lostack-db",
    "DB_PORT"                       : "3306",
    "DB_USER"                       : "lostack",
    "DB_PASSWORD"                   : "", # Required External
    "DB_NAME"                       : "lostack-db",
    "SQLALCHEMY_POOL_SIZE"          : 24,
    "SQLALCHEMY_MAX_OVERFLOW"       : 5,
    "SQLALCHEMY_POOL_RECYCLE"       : 3600,
    "SQLALCHEMY_TRACK_MODIFICATIONS": "false",
    "DEBUG"                         : "false",
    "TIMEZONE"                      : "US/Pacific",
    "LOG_CONFIG"                    : LOG_CONFIG,
    "ADMIN_GROUP"                   : "admins",
    "GROUPS_HEADER"                 : "Remote-Groups",
    "USERNAME_HEADER"               : "Remote-User",
    "FORWARDED_FOR_HEADER"          : "X-Forwarded-For",
    "FORWARDED_HOST_HEADER"         : "X-Forwarded-Host",
    "FORWARDED_METHOD_HEADER"       : "X-Forwarded-Method",
    "FORWARDED_URI_HEADER"          : "X-Forwarded-Uri",
    "LOSTACK_DEFAULT_PACKAGE_PORT"  : 80,
    "LDAP_HOST"                     : "ldap",
    "LDAP_PORT_NUMBER"              : 389,
    "LDAP_LDAPS_PORT_NUMBER"        : 636,
    "LDAP_USE_LDAPS"                : "false",
    "LDAP_BASE_DN"                  : "dc=lostack,dc=internal",
    "LDAP_ORGANISATION"             : "lostack.internal",
    "LDAP_ADMIN_USERNAME"           : "admin",
    "LDAP_ADMIN_BIND_DN"            : "cn=admin,dc=lostack,dc=internal",
    "LDAP_ADMIN_PASSWORD"           : "one_time_login_password_i_made_this_long_so_you_will_change_it",
    "LDAP_TLS_VERIFY_CLIENT"        : "never",
    "LDAP_IGNORE_CERT_ERRORS"       : "true",
    "LDAP_REQUIRE_STARTTLS"         : "false",
    "LDAP_ADMINS_GROUP"             : "admins",
    "EMAIL_DOMAIN"                  : "lostack.internal",
    "MEDIA_FOLDERS"                 : ",".join(MEDIA_FOLDERS),
    "SETUP_MEDIA_FOLDERS"           : "true",
    "DEFAULT_LOSTACK_COMPOSE"       : DEFAULT_LOSTACK_COMPOSE
}

ENV_PARSING = {
    "CREATE_SELF_SIGNED_CERT" : labext.parse_boolean,
    "DEPOT_DEV_MODE" : labext.parse_boolean,
    "SQLALCHEMY_POOL_SIZE" : int,
    "SQLALCHEMY_MAX_OVERFLOW" : int,
    "SQLALCHEMY_POOL_RECYCLE" : int,
    "SQLALCHEMY_TRACK_MODIFICATIONS" : labext.parse_boolean,
    "SETUP_MEDIA_FOLDERS" : labext.parse_boolean,
    "DEBUG" : labext.parse_boolean,
    "LOSTACK_DEFAULT_PACKAGE_PORT" : int
}

ENV_NON_REQUIRED  = [
    "AUTHOR", "APPLICATION_NAME", "APPLICATION_DETAILS"
]