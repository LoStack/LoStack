from app.extensions.common.label_extractor import LabelExtractor as labext 

DEFAULT_LOSTACK_COMPOSE = r"""
networks:
  traefik_network:
    driver: bridge
    name: traefik_network
    external: true
services: {}
"""

DEFAULT_AUTHELIA_CONFIG = r"""
authentication_backend:
  ldap:
    password: '{{ env "LDAP_ADMIN_PASSWORD" }}'
server:
  endpoints:
    authz:
      forward-auth:
        implementation: ForwardAuth
identity_validation:
  reset_password:
    jwt_secret: |
      {{- fileContent "/lostack_secrets/jwt_secret" | nindent 6 }}

session:
  secret: |
    {{- fileContent "/lostack_secrets/session_secret" | nindent 4 }}
  cookies:
  - name: authelia_session
    domain: '{{ env "DOMAINNAME" }}'
    authelia_url: 'https://{{ env "CUST_AUTHELIA_PREFIX" }}.{{ env "DOMAINNAME" }}/'
    expiration: '{{ env "CUST_AUTHELIA_EXPIRATION" }}'
    inactivity: '{{ env "CUST_AUTHELIA_INACTIVITY" }}'
    default_redirection_url: 'https://{{ env "DOMAINNAME" }}/'
storage:
  encryption_key: |
    {{- fileContent "/lostack_secrets/storage_encryption_key" | nindent 4 }}
  mysql:
    address: 'tcp://lostack-db:3306'
    database: lostack-db
    username: '{{ env "CUST_AUTHELIA_MYSQL_USERNAME" }}'
    password: '{{ env "CUST_AUTHELIA_MYSQL_PASSWORD" }}'

notifier:
  filesystem:
    filename: /config/notification.txt

access_control:
  # Default policy - LoStack has secondary forward-auth for group-based limits
  default_policy: one_factor

  # Authelia - must bypass for users to log in
  rules:
  - domain: authelia.{{ env "DOMAINNAME" }}
    policy: bypass
"""

DEFAULT_TRAEFIK_CONFIG = r"""
tls:
  options:
    modern:
      minVersion: VersionTLS13
    intermediate:
      minVersion: VersionTLS12
      cipherSuites:
      - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
      - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
      - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
      - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
      - TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305
      - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
  certificates:
    - certFile: '/certs/_wildcard.{{ env "DOMAINNAME" }}.pem'
      keyFile: '/certs/_wildcard.{{ env "DOMAINNAME" }}-key.pem'
      stores:
        - default
  stores:
    default:
      defaultCertificate:
        certFile: '/certs/_wildcard.{{ env "DOMAINNAME" }}.pem'
        keyFile: '/certs/_wildcard.{{ env "DOMAINNAME" }}-key.pem'

http:
  # Not yet uses, allows services to bypass tls check
  # Useful for servers with self-signed certs
  serversTransports:
    insecureTransport: 
      insecureSkipVerify: true

  middlewares:
    # Headers for Authelia / LoStack
    securityHeaders:
      headers:
        customResponseHeaders:
          X-Robots-Tag: none,noarchive,nosnippet,notranslate,noimageindex
          X-Forwarded-Proto: https
          server: ''
        customRequestHeaders:
          X-Forwarded-Proto: https
          X-Forwarded-Ssl: true
          X-Forwarded-Port: 443
          X-Forwarded-Host: '{{ env "DOMAINNAME" }}'
        sslProxyHeaders:
          X-Forwarded-Proto: https
        referrerPolicy: same-origin
        hostsProxyHeaders:
        - X-Forwarded-Host
        contentTypeNosniff: true
        browserXssFilter: true
        forceSTSHeader: true
        stsIncludeSubdomains: true
        stsSeconds: 63072000
        stsPreload: true
"""

DEFAULT_COREDNS_CONFIG = r"""
.:53 {
    log
    errors

    template IN A {
        match "^{$HOSTNAME}\.{$DOMEXT}\.$"
        answer "{{ .Name }} 30 IN A {$HOST_IP}"
        fallthrough
    }

    template IN A {
        match "^(.*)\.{$HOSTNAME}\.{$DOMEXT}\.$"
        answer "{{ .Name }} 30 IN A {$HOST_IP}"
        fallthrough
    }

    # Forward all other queries to upstream servers
    forward . {$DNS_IP} {
        policy sequential
        max_fails 1
        expire {$DNS_EXPIRATION_TIME}
    }

    cache 30
    loop
    reload
    bind 0.0.0.0
}
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
    "FIRST_RUN"                     : "false",
    "FIRST_RUN_SETUP_LDAP"          : "true",
    "FIRST_RUN_SETUP_MEDIA_FOLDERS" : "true",
    "DEFAULT_LOSTACK_COMPOSE"       : DEFAULT_LOSTACK_COMPOSE,
    "FIRST_RUN_CREATE_AUTHELIA_CONFIG"  : "true",
    "DEFAULT_AUTHELIA_CONFIG"       : DEFAULT_AUTHELIA_CONFIG,
    "FIRST_RUN_CREATE_TRAEFIK_CONFIG"   : "true", 
    "DEFAULT_TRAEFIK_CONFIG"        : DEFAULT_TRAEFIK_CONFIG,
    "FIRST_RUN_CREATE_COREDNS_CONFIG"   : "false",
    "DEFAULT_COREDNS_CONFIG"        : DEFAULT_COREDNS_CONFIG,
    "FIRST_RUN_CREATE_SELF_SIGNED_CERT" : "true",
    "DEPOT_URL" : "https://github.com/LoStack/LoStack-Depot.git",
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
    "SQLALCHEMY_MAX_OVERFLOW"       : 10,
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
    # "ENABLE_DNS"                    : "true",
    # "HOST_IP"                       : "", # Required External
    # "DNS_IP"                        : "", # Required External
    # "DNS_PORT"                      : 5353,
    # "UPSTREAM_DNS_PORT"             : 53, 
    # "DNS_EXPIRATION_TIME"           : 600,
}

ENV_PARSING = {
    "FIRST_RUN" : labext.parse_boolean,
    "FIRST_RUN_SETUP_LDAP" : labext.parse_boolean,
    "FIRST_RUN_CREATE_SELF_SIGNED_CERT" : labext.parse_boolean,
    "FIRST_RUN_CREATE_AUTHELIA_CONFIG" : labext.parse_boolean,
    "FIRST_RUN_CREATE_TRAEFIK_CONFIG" : labext.parse_boolean,
    "FIRST_RUN_CREATE_COREDNS_CONFIG" : labext.parse_boolean,
    "FIRST_RUN_CREATE_SELF_SIGNED_CERT": labext.parse_boolean,
    "FIRST_RUN_SETUP_MEDIA_FOLDERS" :  labext.parse_boolean,
    "DEPOT_DEV_MODE" : labext.parse_boolean,
    "SQLALCHEMY_POOL_SIZE" : int,
    "SQLALCHEMY_MAX_OVERFLOW" : int,
    "SQLALCHEMY_POOL_RECYCLE" : int,
    "SQLALCHEMY_TRACK_MODIFICATIONS" : labext.parse_boolean,
    "DEBUG" : labext.parse_boolean,
    "LOSTACK_DEFAULT_PACKAGE_PORT" : int,
}

ENV_NON_REQUIRED  = [
    "AUTHOR", "APPLICATION_NAME", "APPLICATION_DETAILS"
]