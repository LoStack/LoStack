"""Handler to manager a compose file and mirror compose file contents as data"""

import atexit
import logging
import os
import yaml
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def write_compose(compose_file_path: os.PathLike, compose_data: dict) -> None:
    yaml_content = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)
    with open(compose_file_path, 'w') as f:
        f.write(yaml_content)


def load_yaml(file:os.PathLike, required_sections:list[str]=[], encoding='utf-8',) -> dict:
    """Loads a YAML file into a Python dict"""
    print(f"Loading {file}")
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


class ComposeFileManager(FileSystemEventHandler):
    """
    Object to handle compose file updates and reload automatically on change
    """
    def __init__(self, file:os.PathLike, modified_callback=None):
        self.file = Path(file).resolve()
        self.modified_callback = modified_callback
        self.content = None
        self.services = []
        self.logger = logging.getLogger(__name__ + f'.ComposeManager.{self.file}')
        self.observer = Observer()
        self.observer.schedule(self, str(self.file.parent), recursive=False)
        self.observer.start()
        self._load()
        self.logger.info(f"Initialized Compose File handler for {self.file}")

        atexit.register(self._exit)

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        if Path(event.src_path).resolve() == self.file:
            self.logger.info(f"Compose file modified: {event.src_path}")
            self.logger.info(f"Reloading...")
            self._load()
            self.logger.info(f"Done updating compose services")
            if self.modified_callback:
                self.modified_callback()

    def _load(self) -> dict:
        self.logger.info(f"Reloading compose file at {self.file}")
        self.content = load_yaml(self.file, ["services"])
        self.services = list(self.content.get("services", {}).keys())
        self.logger.info(f"Found services - {self.services} in {str(self.file)}")
        return self.content

    def write(self, content:dict) -> None:
        self.logger.info(f"Writing compose file at {self.file}")
        if not content:
            raise ValueError("No content in compose file.")
        self.content = content
        write_compose(self.file, content)
        # No need to reload, FileSystemEventHandler will catch the change

    def check_if_service_exists(self, service_name:str) -> bool:
        """Check if a service is defined in compose file. Returns True if it exists.""" 
        return service_name in self.services
    
    def get_service_data(self, service_name:str) -> dict:
        """Get data for a given service by name. Returns a dict."""
        return self.content.get("services", {}).get(service_name)
    
    def get_services_data(self, service_names:list[str], result:dict = {}) -> dict[str:dict]:
        """Get data for a list of services by name. Returns a dict of names mapped to service data"""
        for service_name in service_names:
            result[service_name] = self.get_service_data(service_name)
        return result

    def get_service_group_details(self, group_names:str, result:dict = {}) -> dict[str:dict]:
        services = self.content['services']     

        for group_name in group_names:
            if group_name not in services:
                continue

            primary_config = services[group_name]
            primary_labels = LabelExtractor.normalize_labels(primary_config.get('labels', {}))
            primary_group = primary_labels.get('lostack.group', group_name)

            result[group_name] = primary_config.copy()
            result[group_name]['dependencies'] = {}

            for service_name, service_config in services.items():
                if service_name == group_name or service_name in group_names:
                    continue
                service_labels = LabelExtractor.normalize_labels(service_config.get('labels', {}))
                service_group = service_labels.get('lostack.group', service_name)

                if service_group == primary_group:
                    result[group_name]['dependencies'][service_name] = service_config.copy()

        return result

    def get_service_group_data(self, group_name:str, result:dict = None) -> dict[str:dict]:
        """
        Gets data for a given Sablier group.
        Returns a dict of dicts mapped by package name.
        """
        result = result or {}
        for name, config in self.content.get("services", {}).items():
            labels = config.get("labels", [])
            for label in labels:
                if label.startswith("lostack.group="):
                    _, value = label.split("=", 1)
                    if value.strip() == group_name:
                        result[name] = config
        return result

    def update_services(self, services_data:dict[str:dict]) -> None:
        """
        Updates services from a dict in form {name:{:}, name2:{:}, ...}.
        Raises an error if a service doesn't exist already
        """ 
        # Ensure services exists first
        for name, config in services_data.items():
            if not self.check_if_service_exists(name):
                raise KeyError(f"Service '{name}' not found in compose data")
        # Update services
        for name, config in services_data.items():
            self.content["services"][name].update(config)
    
    def add_services_from_package_data(self, package_data: dict, save=True) -> None:
        """Adds services to compose data. Raises an error if services already exist."""
        if self.content is None:
            raise ValueError(f"File content is None!")

        if "services" not in self.content or self.content.get("services") is None:
            self.content["services"] = {}
        if "services" not in package_data or package_data.get("services") is None:
            raise ValueError(f"No service data found in services")

        existing = set(self.content["services"].keys())
        incoming = set(package_data["services"].keys())
        conflict = existing.intersection(incoming)

        if conflict:
            raise KeyError(f"Service(s) already exist in compose: {', '.join(conflict)}")

        for name, config in package_data["services"].items():
            self.content["services"][name] = config
        
        if save:
            self.save()

    def save(self) -> None:
        """
        Save any changes made to content
        File handler will automatically reload file after
        """
        if self.content is None:
            raise ValueError("Compose file data cannot be None!")
        self.write(self.content)

    def _exit(self) -> None:
        self.logger.info("Stopping observer")
        self.observer.stop()
        self.observer.join(timeout=5)