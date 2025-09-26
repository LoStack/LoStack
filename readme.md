# LoStack - Easy Docker Service Management

![LoStack Dashboard](docs/images/dashboard.png?raw=true "LoStack Dashboard")

An opinionated, highly integrated service for deploying, and managing Docker services. Automates the hard parts of deploying a multi-user environment with SSO, easy group-based access control, automatic service discovery, routing, and more.    

![Sablier UI](docs/images/architecture.png?raw=true "LoStack Architecture")

- **Easy Configuration**: Configure your services either through simple Docker labels, or through the web UI
- **Web-Based Management**: Depot, container, and service-group manager.Customizable dashbord only shows what users have access to
- **Scale to Zero**: Shut down services automatically when not in use
- **User Management**: Create and manage system Users and Groups
- **Centralized Authentication**: SSO through Authelia Auth + LoStack RBAC and Auto-Login features
- **Two-Click Install**: Includes a growing, community-driven depot of pre-configured services
- **Simple Self-Signed SSL**: Automataically generates self-signed certs on initial deployment for easy setup. Optionally supply your own
- **Automatic Reverse Proxy**: Automatically routes services over HTTPS thorugh Traefik
- **RBAC**: Easily configure which groups have access to which services
- **Tools**: Integrated file editor, live log viewer, and more planned (SSH and FTP clients coming soon) 
- **Theme Support**: Per-user, over a dozen built-in UI themes, customizable CSS, and dozens of text-editor themes

See the [LoStack Setup](https://github.com/LoStack/LoStack-Setup) repo for a detailed setup guide.


## Dependencies

LoStack is highly integrated with its dependencies, while planned for the future

- **Traefik**: Reverse-Proxy, routing, and middleware management
- **Authelia**: Authentication
- **OpenLDAP**: Users and groups backend for Authelia and LoStack
- **MariaDB**: Authelia and LoStack data 


## Architecture

```
Host OS (Ubuntu, Raspbian recommended)
├── Docker + Compose
└── Service Stack
    ├── Traefik (Reverse Proxy)
    ├── Authelia (Authentication)
    ├── OpenLDAP (User Directory)
    ├── MariaDB (DB for Authelia and LoStack)
    ├── LoStack (Container Management and configuration)
    ├── CoreDNS (DNS Resolution) [Optional]
    └── Application Services
```


```bash
# Navigate to docker directory
sudo mkdir /docker && cd /docker

# Clone the repository
git clone https://github.com/LoStack/LoStack-Setup .
```

If you're running Ubuntu
```bash
sudo bash ./setup-ubuntu.sh
```

If you're running Raspbian
```bash
sudo bash ./setup-arm.sh
```

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