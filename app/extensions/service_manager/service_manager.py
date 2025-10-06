import docker
import logging
import os
import time
from flask import current_app
from queue import Queue
from app.extensions.common.label_extractor import LabelExtractor as labext
from app.extensions.depot_manager import DepotManager
from app.extensions.docker.compose_file_manager import ComposeFileManager

parse_bool = labext.parse_boolean

class ServiceManager:
    """
    Service and Package Manager
    """
    def __init__(
        self,
        app,
        compose_file:os.PathLike="/docker/docker-compose.yml",
        lostack_file:os.PathLike="/docker/lostack-compose.yml",
    ) -> None:
        self.app = app
        self.compose_file = compose_file
        self.lostack_file = lostack_file
        self.depot_dir = app.config["DEPOT_DIR"]
        self.client = docker.from_env()
        self.api_client = docker.APIClient()
        self.depot_handler = DepotManager(app)
        self.logger = app.logger
        self.refresh()

    def refresh(self, event=None) -> None:
        if self.app.config.get("FIRST_RUN"):
            return # Don't register container on first run
        try:
            # CURRENT_APP WILL NOT WORK HERE | Proxy expires before this is reached due to threading
            with self.app.app_context():
                # Get all containers with Sablier labels
                lostack_groups = self.get_running_service_groups()
                existing_services = {s.name: s for s in self.app.models.PackageEntry.query.all()}
                
                # Track which services should exist
                should_exist = set()
                
                # Create or update services based on Docker containers
                for group_name, group_data in lostack_groups.items():
                    should_exist.add(group_name)
                
                    compose_file_manager = current_app.docker_manager.compose_file_handlers.get("/docker/docker-compose.yml")
                    if not group_name in existing_services:
                        core_service = False
                        if compose_file_manager.check_if_service_exists(group_name):
                            # If file is a core service
                            core_service = True

                        # Create new service
                        service = self.create_service_from_labels(group_name, group_data, core_service)
                        existing_services[group_name] = service
                
                # Disable services that no longer have containers
                for service_name, service in existing_services.items():
                    if service_name not in should_exist and service.enabled:
                        service.enabled = False
                        self.logger.info(f"Disabled service: {service_name} (no containers found)")
                
                current_app.db.session.commit()
                
                if self.app.models.save_traefik_config():
                    self.logger.info("Traefik configuration updated successfully")
                else:
                    self.logger.error("Failed to update Traefik configuration file")
                    
        except Exception as e:
            self.logger.error(f"Error syncing containers: {e}")
            try:
                self.app.db.session.rollback()
            except Exception:
                pass
    
    def create_service_from_labels(
        self,
        group_name:str,
        group_data:dict,
        core_service:bool=False
    ) -> "PackageEntry":
        """Create a new PackageEntry from container labels"""
        defaults = current_app.models.LoStackDefaults.get_defaults()
        labels = group_data['labels']
        lb_get = labels.get 
        def get_bool(key, default="true"): return parse_bool(labels.get(key, default))
        service = current_app.models.PackageEntry(
            name                         = group_name,
            core_service                 = core_service,
            service_names                = ','.join(group_data['service_names']),
            display_name                 = labext.get_friendly_name(labels, group_name),
            port                         = lb_get(  'lostack.port', None),
            session_duration             = lb_get(  'lostack.default_duration', defaults.session_duration),
            refresh_frequency            = lb_get(  'lostack.refresh_frequency', defaults.refresh_frequency),
            show_details                 = get_bool('lostack.show_details', defaults.show_details),
            enabled                      = get_bool('lostack.enable'),
            lostack_access_enabled       = get_bool('lostack.access_control'),
            lostack_autostart_enabled    = get_bool('lostack.autostart'),
            lostack_autoupdate_enabled   = get_bool('lostack.autoupdate'),
            automatic                    = get_bool('lostack.automatic', "false"),
            mount_to_root                = get_bool('lostack.root', 'false'),
            homepage_icon                = lb_get(  'homepage.icon', "mdi-application"),
            homepage_name                = lb_get(  'homepage.name', group_name),
            homepage_description         = lb_get(  'homepage.description', ""),
            homepage_url                 = lb_get(  'homepage.href', "https://"+group_name+"."+current_app.config.get("DOMAIN_NAME")),
            homepage_group               = lb_get(  'homepage.group', "Apps"),
            force_disable_autostart      = get_bool('lostack.force_disable_autostart','false'),
            force_disable_access_control = get_bool('lostack.force_disable_access_control','false'),
            force_disable_autoupdate     = get_bool('lostack.force_disable_autoupdate','false'),
            force_compose_edit           = get_bool('lostack.force_compose_edit','false'),
        )
        
        current_app.db.session.add(service)
        self.logger.info(f"Created new service: {group_name}")
        return service
            
    def get_running_service_groups(self) -> dict:
        """Gets a list of running services from docker groups sorted by group"""
        groups = {}
        try:
            client = current_app.docker_manager.client
            containers = client.containers.list(all=True)
            groups = {}
            for container in containers:
                labels = labext.normalize_labels(container.labels or {})
                if not parse_bool(labels.get('lostack.enable', "false")):
                    continue

                group = labels.get('lostack.group')
                if not group:
                    continue
                
                if not group in groups:
                    groups[group] = {
                        'containers': [],
                        'main_container': None,
                        'labels': {},
                        'service_names': []
                    }

                groups[group]['containers'].append(container)
                groups[group]['service_names'].append(container.name)
                
                # Check if this is the primary container
                if parse_bool(labels.get('lostack.primary', "false")):
                    groups[group]['main_container'] = container

            # After collecting all containers, set labels with primary taking precedence
            for group_name, group_data in groups.items():
                # First, merge labels from all containers
                merged_labels = {}
                for container in group_data['containers']:
                    container_labels = labext.normalize_labels(container.labels or {})
                    merged_labels.update(container_labels)
                
                # Then, if there's a primary container, let its labels override
                if group_data['main_container']:
                    primary_labels = labext.normalize_labels(group_data['main_container'].labels or {})
                    merged_labels.update(primary_labels)
                
                group_data['labels'] = merged_labels

        except Exception as e:
            self.logger.error(f"Error getting service groups: {e}")
        return groups

    def get_installed_packages(self) -> list[str]:
        """Gets a list of installed packages by looking at compose file labels."""
        packages = []

        for handler in current_app.docker_manager.compose_file_handlers.values():
            for name, service in handler.content.get("services", {}).items():
                if not isinstance(service, dict):
                    continue
                labels = labext.normalize_labels(service.get('labels', []))
                primary = parse_bool(labext.get_label("lostack.primary"))
                if primary:
                    packages.append(name)
        return packages

    def get_installable_packages(self) -> list[str]:
        """
        Gets a list of installable LoStack packages.
        Excludes currently installed packages.
        """
        packages = self.get_all_depot_packages()
        installed = self.get_installed_packages()
        installable = []
        for p in packages:
            if p in installed:
                continue
            installable.append(p)
        return installable
    
    def add_depot_package(self, package_name:str, result_queue, complete=False) -> list[str]:
        """
        Adds a depot package to the dynamic compose.
        Returns the list of docker services added.
        """
        result_queue.put_nowait(f"Adding depot package...")
        package_data = self.depot_handler.get_package_data(package_name)
        if not package_data:
            msg = f"DEPOT: Failed to get package data for {package_name}"
            result_queue.put_nowait(msg)
            raise FileNotFoundError(msg)
        result_queue.put_nowait(f"Got package data")
        service_names = list(package_data.get("services", {}).keys())
        lostack_file_handler = current_app.docker_manager.compose_file_handlers.get("/docker/lostack-compose.yml")
        try: 
            result_queue.put_nowait(f"Adding services {', '.join(service_names)}")
            lostack_file_handler.add_services_from_package_data(package_data)
        except Exception as e:
            result_queue.put_nowait(f"Error adding services to dynamic compose - {e}")
            result_queue.put_nowait(f"Aborting...")
            time.sleep(1) # Ensure result queue gets pushed to user before context ends
            raise e
        
        if complete:
            result_queue.put_nowait("__COMPLETE__")
            self.force_sync()

        result_queue.put_nowait(f"Added services: {service_names}")
        return service_names
    
    def remove_depot_package(self, service_db_id:str, result_queue: Queue, complete=False) -> Queue:
        """
        Remove a package.
        Stops containers
        Removes package entry from the DB
        Removes containers
        Updates compose file
        """
        result_queue.put_nowait(f"Removing depot package...")
        with self.app.app_context():
            print(service_db_id)
            service = current_app.models.PackageEntry.query.get_or_404(service_db_id)

            package_name = service.name
            docker_service_names = service.docker_services
            if service and not docker_service_names:
                """Fix in case of broken db entry"""
                current_app.db.session.delete(service)
                current_app.db.session.commit()
                return StreamHandler.message_completion_stream("No services to handle, deleted db entry.")
            
            docker_manager = current_app.docker_manager

            try:
                result_queue.put_nowait(f"Starting removal of services: {', '.join(docker_service_names)}")
                containers = docker_manager.get_services_info(docker_service_names)
                running_containers = [
                    name for name, info in containers.items()
                    if info and info.get("State") in ["running", "starting"]
                ]

                lostack_file_handler = docker_manager.compose_file_handlers.get(self.lostack_file)

                if running_containers:
                    result_queue.put_nowait(f"Stopping running containers: {', '.join(running_containers)}")
                    lostack_file_handler.compose_stop(running_containers, result_queue, complete=False)
                else:
                    result_queue.put_nowait("No running containers found to stop")
                existing_containers = [name for name, info in containers.items() if info is not None]
                if existing_containers:
                    result_queue.put_nowait(f"Removing containers: {', '.join(existing_containers)}")
                    docker_manager.shell_remove(existing_containers, result_queue, complete=False)
                else:
                    result_queue.put_nowait("No containers found to remove")

                # Update compose file
                result_queue.put_nowait(f"Updating {lostack_file_handler.file}...")
                try:
                    compose_data = lostack_file_handler.content.copy()
                    services_to_remove = []
                    for service_name in docker_service_names:
                        if service_name in compose_data.get("services", {}):
                            services_to_remove.append(service_name)
                            del compose_data["services"][service_name]

                    if services_to_remove:
                        lostack_file_handler.write(compose_data)
                        result_queue.put_nowait(f"Removed services from LoStack compose file: {', '.join(services_to_remove)}")
                    else:
                        result_queue.put_nowait("No services found in LoStack compose file to remove")
                except Exception as e:
                    result_queue.put_nowait(f"Warning: Could not update LoStack compose file: {str(e)}")

                result_queue.put_nowait("Removing database entries...")

                # Delete db services
                services_to_delete = current_app.models.PackageEntry.query.filter(
                    current_app.models.PackageEntry.service_names.in_(docker_service_names)
                ).all()

                all_services = current_app.models.PackageEntry.query.all()
                for service in all_services:
                    service_docker_names = service.docker_services
                    if any(name in docker_service_names for name in service_docker_names):
                        if service not in services_to_delete:
                            services_to_delete.append(service)
                
                deleted_count = 0
                for service in services_to_delete:
                    current_app.db.session.delete(service)
                    deleted_count += 1
                
                if deleted_count > 0:
                    current_app.db.session.commit()
                    result_queue.put_nowait(f"Removed {deleted_count} database entries")
                else:
                    result_queue.put_nowait("No database entries found to remove")

                # Regenerate Traefik config
                result_queue.put_nowait("Regenerating Traefik configuration...")
                try:
                    if current_app.models.save_traefik_config():
                        result_queue.put_nowait("Traefik dynamic configuration updated successfully")
                    else:
                        result_queue.put_nowait("Warning: Could not update Traefik dynamic configuration")
                except Exception as e:
                    result_queue.put_nowait(f"Warning: Error updating Traefik dynamic config: {str(e)}")

                result_queue.put_nowait("Package removal completed successfully")
            except Exception as e:
                result_queue.put_nowait(f"Error handling package removal - {e}")
            finally:
                if complete:
                    result_queue.put_nowait("__COMPLETE__")
                self.force_sync()
        return result_queue

    def force_sync(self) -> None:
        """Refresh configs"""
        self.refresh()