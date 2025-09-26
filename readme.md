# LoStack - Easy Docker Service Management

An opinionated, highly integrated service for deploying, and managing Docker services. Automates the hard parts of deploying a multi-user environment with SSO, easy group-based access control, automatic service discovery, routing, and more.


![LoStack Architecture](docs/images/architecture.png?raw=true "LoStack Architecture")

## Dependencies

LoStack is highly integrated with its dependencies
```
Host OS (Ubuntu, Raspbian recommended)
├── Docker + Compose
└── Service Stack
    ├── Traefik (Reverse Proxy, routing, and middleware)
    ├── Authelia (Authentication)
    ├── OpenLDAP (Users and groups backend)
    ├── MariaDB (DB for Authelia and LoStack)
    ├── LoStack (Container Management and configuration)
    ├── CoreDNS (DNS Resolution) [Optional]
    └── Application Services
```

## Goals

- **Easy Configuration**:
    - Configure your services either through simple Docker labels, or through the web UI
    - Automatically route services over HTTPS through Traefik without exposing ports on your local network.
    - Automatically generate self-signed certs on initial deployment for easy setup. Optionally supply your own
    - Automatically shut down services when not in use
- **Web-Based Management**:
    - Depot, container, and service-group manager. Customizable dashbord only shows what users have access to.
    - UI Developed in Bootstrap, with attention to mobile support
    - Per-user theme system, over a dozen built-in UI themes, customizable CSS, and dozens of text-editor themes
    - A growing, community-driven depot of pre-configured services
    - Integrated file editor, live log viewer, and more planned (SSH and FTP clients coming soon) 
- **User Management**:
    - Create and manage system Users and Groups
    - Easily configure which groups have access to which services
    - SSO through Authelia Auth + LoStack RBAC and Auto-Login features



See the [LoStack Setup](https://github.com/LoStack/LoStack-Setup) repo for a detailed setup guide.


## Automated Dashboard

LoStack automatically generates a dashboard that only shows services a user has access to. Admin users will be shown all services, and only admins will be shown the management links in the navigation bar.

![LoStack Dashboard](docs/images/dashboard.png?raw=true "LoStack Dashboard")


## Service Management

LoStacks revolves around the idea of "services," groups of docker containers needed to support an endpoint. LoStack provides features to easily manage these groups with simple button presses.

![LoStack Services](docs/images/services.png?raw=true "LoStack Services")

## Containers

In addition to services, LoStack allows basic management of Docker containers through the UI.

![LoStack Containers](docs/images/containers.png?raw=true "LoStack Containers")


## Depot

LoStack uses a git repo as the backend for its depot, by default it points to https://github.com/LoStack/LoStack-Depot. LoStack depots are generally fairly small as they consist of just a collection of YAML files.

Depot packages are just Docker Compose files with labeling, and a consistent container naming scheme. Depot containers are added to a separate `lostack-compose.yml` file, next to your core `docker-compose.yml` file, so that if something breaks during the installation / uninstalliation of a service, your primary services file will remain intact and usable.

Currently, all containers are added to the same `traefik_network` Docker network, however future releases will automatically generate bridge networks to segment different services.

![LoStack Depot](docs/images/depot.png?raw=true "LoStack Depot")


## File Editor

LoStack includes a basic built-in text editor / file explorer.
It currently only supports for file editing, and lacks features for creating new files, and downloading files. It supports CodeMirror themes, with linting and syntax highlighting for most common languages.

![LoStack Files](docs/images/files.png?raw=true "LoStack Files")


# Contributors:
 - None yet, make a PR!

# Special Thanks:
 - Ultimaterez (alpha tester / feedback)
 - Olaf (feedback / ideas)
 - Machstem (feedback / ideas)
 - [David C.](https://github.com/CheeseCake87) (feedback / ideas)
 - [Flask Discord](https://discord.gg/B6AGZRP)
 - [Homepage Discord](https://discord.com/invite/k4ruYNrudu)
 - [Authelia Discord](https://discord.authelia.com/)