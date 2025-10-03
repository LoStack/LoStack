# LoStack - Easy Docker Service Management

A *"One Container to Rule Them All"* approach to create a multi-user Docker ecosystem in minutes.

LoStack serves as a simple way to automate and standardize service installation, and provide a friendly way to handle user management, group-based access control, service discovery, routing, log inspection, Docker container actions, and more.

![LoStack Architecture](docs/images/architecture.png?raw=true "LoStack Architecture")

```
Host OS (Ubuntu, Raspbian recommended)
├── Docker + Compose
└── Service Stack
    ├── Traefik (Reverse Proxy, routing, and middleware)
    ├── Authelia (Universal authentication and SSO)
    ├── OpenLDAP (Users and groups backend)
    ├── MariaDB (Database services for Authelia and LoStack)
    ├── LoStack (Container Management and configuration)
    └── CoreDNS (DNS Resolution) [Optional]
```

## Setup

While not terribly complicated, LoStack's setup can take several paths depending on how you plan on using it. To simplify setup, LoStack provides several setup scripts, a preconfigured docker-compose.yml file, and template env file in the
[**LoStack/LoStack-Setup**](https://github.com/LoStack/LoStack-Setup) repo.

## Features

- **Easy Configuration**:
    - Configure all of your services either through simple, easy-to-understand Docker labels, or through the simple and intuitive web UI
    - Automatically route services over HTTPS through Traefik without exposing ports on your local network.
    - Automatically generate self-signed certs on initial deployment for easy setup. Or if you'd rather, you can also just supply your own!
    - Automatically shut down services when not in use for power-saving, and start them as needed by accessing their URL.
- **Scale-To-Zero**:
    - Services can be configured to automatically start / stop automatically after user inactiviy.
- **Web-Based Management**:
    - Application depot, container, and service-group manager. Customizable dashbord only shows what a user has permissions to access.
    - UI Developed in Bootstrap with attention to mobile support
    - Per-user theme system, over a dozen built-in UI themes, customizable CSS, and dozens of text-editor themes
    - A growing, community-driven depot of pre-configured services including music library managers, ebook readers, chat clients, file servers, and plenty more!
    - Integrated file editor, live log viewer, and more planned (SSH and FTP clients coming soon) 
    - Depot, container, and service-group manager. Customizable dashbord only shows what users have access to.
    - UI Developed in Bootstrap, with attention to mobile support
    - Per-user theme system, over a dozen built-in UI themes, customizable CSS, and dozens of text-editor themes.
    - Integrated file editor, live log viewer, and more planned (SSH and FTP clients coming soon).
- **User Management**:
    - Create and manage system Users and Groups.
    - Easily configure which groups have access to which services.
    - SSO through Authelia Auth + LoStack RBAC and Auto-Login features.
- **Easy Installs**:
    - A growing, community-driven depot of pre-configured services.
    - See [LoStack-Depot](https://github.com/LoStack/LoStack-Depot) for a full list of Packages.
- **Integrations**:
    - Compatible with getHomePage! Services installed through the depot will appear on the getHomePage dashboard automatically.
    - WIP plugin system coming soon - will allow the community to write plugins that add new functionality to LoStack.
    - WIP API system coming soon.

In order for your service groups to show up in LoStack, you must name and label them appropriately.
This process is fairly simple, see the guide in the [LoStack-Depot](https://github.com/LoStack/LoStack-Depot) repo.

## Automated Dashboard

LoStack automatically generates a dashboard that only shows the services a user has permission to access. Admin users will be shown all services, and only admins will be shown the management links in the navigation bar.

![LoStack Dashboard](docs/images/dashboard.png?raw=true "LoStack Dashboard")


## Service Management

LoStack revolves around the idea of "services," groups of Docker containers needed to support an endpoint. LoStack provides features to easily manage these groups with simple button presses.

![LoStack Services](docs/images/services.png?raw=true "LoStack Services")


## Easy Reverse Proxy Routing

LoStack provides an easy way to handle basic Traefik routing. Routes appear on the automated dashboard based on group access controls (if enabled).

![LoStack Routes](docs/images/routes.png?raw=true "Routing")

![LoStack Routes](docs/images/route_editor.png?raw=true "Route Editor")


## Containers

In addition to services, LoStack allows basic management of Docker containers through the UI.

![LoStack Containers](docs/images/containers.png?raw=true "LoStack Containers")


## Depot

LoStack uses a git repo as the backend for its depot. By default it points to https://github.com/LoStack/LoStack-Depot. LoStack depots are generally fairly small as they consist of just a collection of YAML files.

Depot packages are just Docker Compose files with labeling, and a consistent container naming scheme. Depot containers are added to a separate `lostack-compose.yml` file, next to your core `docker-compose.yml` file, so that if something breaks during the installation / uninstalliation of a service, your primary services file will remain intact and usable.

Currently, all containers are added to the same `traefik_network` Docker network, however future releases will automatically generate bridge networks to segment different services.

![LoStack Depot](docs/images/depot.png?raw=true "LoStack Depot")


## File Editor

LoStack includes a basic text editor / file explorer.
It currently only has support for text-file editing, and lacks features for creating new files, and downloading files. It supports CodeMirror themes, with linting and syntax highlighting for most common languages.

![LoStack Files](docs/images/files.png?raw=true "LoStack Files")

### Planned features

#### Roadmap
![LoStack Roadmap](docs/images/roadmap.png?raw=true "LoStack Roadmap")

#### Coming Soon

- **Automatic Container Segregation**:
    - LoStack will automatically create Docker networks for services:
        - A bridge network from the primary container to Traefik
        - A bridge network to connect container to its dependencies if more than one container exists in the group 
- **Multi-Compose System**:
    - Support creating a compose file per-package, or select existing compose files to add the service to.
- **Multi-Depot System**:
    - Support multiple depots, and create depots targeting specific architectures (not all packages work on arm for example).
- **Traefik Routing**:
    - GUI menu similar to the service menu for creating external routes (need to figure out how to cleanly handle inscure transport, and other use cases, as well as ACL handling).
- **File Browser Improvements**:
    - Add support for downloading / uploading files.
    - Add support for changing a file's permissions with a right-click menu.
- **First-time-setup**:
    - Change many settings currently supplied via ENV to a first-time-setup ui flow when the admin first connects.
- **Integrated Console / SSH Client**:
    - Admins will be able to create SSH credentials, and specify groups / users that have access to the SSH session. Available SSH will show up in a tab on the dashboard.
- **Package Templater / Depot Editor**:
    - Admin tool to easily create new packages from existing docker compose files, and save them into a depot for easy depot creation.
- **Container Auto-Update**:
    - Partially implemented / commented. Will implement when stable.
    - Automatically update containers before auto-start.
- **Container Scheduling**:
    - Specify downtimes when containers will be stopped and cannot be auto-started (return 403).
- **Access Scheduling**:
    - Specify when groups have access to container.

# Technologies / Licensing:

### LoStack WebUI
- **[ANSI Up](https://github.com/drudru/ansi_up)** [MIT]
- **[Bootstrap](https://getbootstrap.com/)** [MIT]
- **[Bootstrap Icons](https://icons.getbootstrap.com/)** [MIT]
- **[Bootswatch Themes](https://bootswatch.com/)** [MIT]
- **[CodeMirror 5](https://github.com/codemirror/codemirror5)** [MIT]
- **[Homarr Icons](https://github.com/homarr-labs/dashboard-icons)** [Apache 2]
- **[JS-YAML](https://www.npmjs.com/package/js-yaml)** [MIT]
- **[Pictogrammers Material Design Icons](https://pictogrammers.com/library/mdi/)** [[Pictogrammers Free License + MIT](https://pictogrammers.com/docs/general/license/)]

### LoStack Backend
- **[Flask](https://flask.palletsprojects.com/en/stable/)** [BSD-3]
- **[Python](https://docs.python.org/)** [[Python Software License](https://docs.python.org/3/license.html)]
- **[Docker](https://www.docker.com/)** 
- **[Docker Compose Plugin](https://docs.docker.com/compose/install/linux/)** [Apache 2]

### Integrated Containers
- **[Authelia](https://github.com/authelia/authelia)** [Apache 2]
- **[Traefik](https://github.com/traefik/traefik)** [MIT]
- **[OpenLDAP](https://www.openldap.org/)** [[OpenLDAP Public License](https://www.openldap.org/software/release/license.html)]
- **[MariaDB](https://mariadb.com/)** [[MariaDB License](https://mariadb.com/docs/general-resources/community/community/faq/licensing-questions/licensing-faq)]

# Contributors:
 - [Ultimaterez](https://github.com/ultimaterez) (alpha tester / feedback / depot / readme)

# Special Thanks:
 - Olaf (feedback / ideas / he's good people)
 - Machstem (feedback / ideas)
 - [David C.](https://github.com/CheeseCake87) (feedback / ideas / code review)
 - [Flask Discord](https://discord.gg/B6AGZRP)
 - [Homepage Discord](https://discord.com/invite/k4ruYNrudu)
 - [Authelia Discord](https://discord.authelia.com/)

# Questions / Comments:
 - [**Join us in the LoStack Discord**](https://discord.gg/MnXcKqfjQB)
 - Pull Requests wanted!
 