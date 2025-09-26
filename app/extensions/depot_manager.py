import logging
import os
import queue
import yaml
from collections import defaultdict
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .git import RepoManager
from app.extensions.common.label_extractor import LabelExtractor as labext
from app.extensions.common.stream_handler import StreamHandler


def load_yaml(file:os.PathLike, required_sections:list[str]=[], encoding='utf-8',) -> dict:
    """Loads a YAML file into a Python dict"""
    if not os.path.exists(file):
        raise FileNotFoundError(f"YAML file doesn't exist - {file}")
    if not os.path.isfile(file):
        raise IsADirectoryError(f"Expected YAML file, found dir - {file}")
    try:
        with open(file, 'r', encoding=encoding) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")
    for sect in required_sections:
        if not sect in data:
            raise KeyError(f"YAML file missing expected key {sect}")
    return data    


class DepotManager(FileSystemEventHandler):
    def __init__(self, app, modified_callback=None):
        self.path = Path(app.config["DEPOT_DIR"]).resolve()
        self.dev_mode = app.config["DEPOT_DEV_MODE"]
        self.modified_callback = modified_callback
        self.packages = {}
        self.logger = app.logger

        self.repo_manager = RepoManager(
            self.path,
            repo_url = app.config["DEPOT_URL"],
            branch = app.config["DEPOT_BRANCH"],
        )
        if not self.dev_mode:
            self.logger.info("Ensuring depot is up to date...")
            self._update_repo()

        self.observer = Observer()
        self.observer.schedule(self, str(self.path), recursive=True)
        self.observer.start()
        self._scan()
        self.logger.info(f"Initialized Depot Handler")

    def _update_repo(self, result_queue=None) -> [None]:
        """Clone / pull depo git repo on background thread, pipes output to logs/stdout"""
        if result_queue is None:
            result_queue = queue.Queue()
        if self.dev_mode:
            return
        return self.repo_manager.ensure_repo(result_queue)

    def stream_update_repo(self) -> "Reponse":
        """Get flask response object to stream depot update to websocket"""
        if self.dev_mode:
            return StreamHandler.message_completion_stream("CAN'T UPDATE IN DEV MODE")
        def _update_repo(result_queue):
            return self.repo_manager.ensure_repo(result_queue)
        return StreamHandler.generic_stream(_update_repo, [])
    
    def on_modified(self, event) -> None:
        if not event.src_path.endswith(".yml"):
            return # Ignore non YAML files
        self.logger.info(f"Depot compose file modified: {event.src_path}")
        self._scan()
        if self.modified_callback:
            self.modified_callback(event.src_path)

    def _scan(self) -> dict[str:dict]:
        """Scans and loads depot"""
        self.logger.info(f"Scanning depot directory: {self.path}")
        packages = {}
        with os.scandir(os.path.join(os.path.abspath(str(self.path)), "packages")) as it:
            for entry in it:
                if os.path.isfile(entry.path):
                    continue
                if os.path.isdir(entry.path):
                    package_name = entry.name
                    package_compose = os.path.join(os.path.abspath(entry.path), "docker-compose.yml")
                    if os.path.isfile(package_compose):
                        packages[package_name] = load_yaml(Path(package_compose))
        self.logger.info(f"Found {len(packages)} packages in depot directory: {self.path}")
        self.packages = packages

    def format_packages_for_depot_page(self, package_names:list[str]) -> dict:
        """Collects and formats packages for depot page"""
        packages = {}
        for package_name in package_names:
            if package_name not in self.packages:
                continue

            package_services = self.packages[package_name].get("services")

            primary_config = package_services[package_name]
            primary_labels = labext.normalize_labels(primary_config.get('labels', {}))
            primary_group = primary_labels.get('lostack.group', package_name)

            packages[package_name] = primary_config.copy()
            packages[package_name]['dependencies'] = {}

            for service_name, service_config in package_services.items():
                if service_name == package_name or service_name in package_names:
                    continue
                service_labels = labext.normalize_labels(service_config.get('labels', {}))
                service_group = service_labels.get('lostack.group', service_name)

                if service_group == primary_group:
                    packages[package_name]['dependencies'][service_name] = service_config.copy()

        packages = {p: packages[p] for p in sorted(packages.keys())}
        packages = self._preprocess_packages_data_for_depot_page(packages)
        return packages

    def _preprocess_packages_data_for_depot_page(self, packages:dict) -> dict:
        """Process packages data to reduce template complexity"""
        processed_packages = {}
        group_counts = defaultdict(int)
        tag_counts = defaultdict(int)
        
        for package_name, package_data in packages.items():
            labels = package_data.get('labels', [])
            labels_dict = labext.normalize_labels(labels)
            # Pre-process labels (was messy/expensive in jinja)
            group = labext.get_by_prefix(labels, 'homepage.group')
            description = labext.get_by_prefix(labels, 'homepage.description')
            details = labext.get_by_prefix(labels, 'lostack.details')
            tags = labext.get_tags(labels)
            service_port = labext.get_lostack_port(labels)
            
            # Data for template
            processed_package = {
                'name': package_name,
                'title': package_name.replace('-', ' ').replace('_', ' ').title(),
                'image': package_data.get('image'),
                'volumes': package_data.get('volumes', []),
                'dependencies': package_data.get('dependencies', {}),
                'labels': labels,
                'labels_dict': labels_dict,
                'group': group,
                'description': description,
                'details': details,
                'tags': tags,
                'service_port': service_port,
                'search_data': {
                    'name': package_name.lower(),
                    'title': package_name.replace('-', ' ').replace('_', ' ').title().lower(),
                    'description': (description or '').lower(),
                    'group': (group or '').lower(),
                    'tags': ','.join(tag.lower() for tag in tags)
                }
            }
            processed_packages[package_name] = processed_package
            if group: group_counts[group] += 1
            for tag in tags: tag_counts[tag] += 1
        
        return {
            'packages': processed_packages,
            'groups': dict(sorted(group_counts.items())),
            'tags': dict(sorted(tag_counts.items())),
            'total_count': len(processed_packages)
        }

    def get_package_data(self, package_name:str) -> dict:
        """
        Get data for a given package
        self.packages might change in the future
        """
        return self.packages.get(package_name)