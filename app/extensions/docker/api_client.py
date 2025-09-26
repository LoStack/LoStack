import docker
import logging
import traceback
from queue import Queue

class DockerApiHandler:
    def __init__(self):
        self.api_client = docker.APIClient()
        self.logger = logging.getLogger(__name__ + ".DockerApiHandler")

    def get_services_info(
        self,
        service_names:list[str]|str|None,
        include_stopped:bool=True
    ) -> dict:
        """
        Gets a list of running services from docker groups using the api client
        Set service_names to "all" to include non-running containers
        """
        try:
            containers = {}
            for c in self.api_client.containers(all=include_stopped):
                name = c["Names"][0].strip("/")
                containers[name] = c

            if service_names is None:
                return containers

            if isinstance(service_names, str):
                if service_names.lower() == "all":
                    return containers
            
            result = {}
            for n in service_names:
                result[n] = containers.get(n)
            return result
        except Exception as e:
            self.logger.error(traceback.print_exc(e))

    def _handle_api_action(
        self,
        action,
        container_id:str,
        result_queue:Queue=None,
        complete:bool=True
    ) -> None:
        actions = "start", "stop", "kill", "restart", "logs"
        if not action in actions:
            raise ValueError("Invalid API action")
        
        act = getattr(self.api_client, action)
        
        msg = f"Running {action} on {container_id}"
        if result_queue:
            result_queue.put_nowait(msg)
        self.logger.info(msg)

        try:
            act()
        except Exception as e:
            msg = (
                f"Error running {action} on "
                f"{container_id} - {traceback.print_exc()}"
            )
            if result_queue:
                result_queue.put_nowait(msg)
            self.logger.info(msg)
        
        if complete and result_queue:
            result_queue.put_nowait("__COMPLETE__")

    def api_start(self,container_id:str,result_queue:Queue=None, complete:bool=True) -> None:
        return self._handle_api_action("start", container_id, result_queue, complete=complete)
    def api_stop(self,container_id:str,result_queue:Queue=None, complete:bool=True) -> None:
        return self._handle_api_action("stop", container_id, result_queue, complete=complete)
    def api_kill(self, container_id:str, result_queue:Queue=None, complet:bool=True) -> None:
        return self._handle_api_action("kill", container_id, result_queue, complete=complete)
    def api_restart(self,container_id:str,result_queue:Queue=None, complete:bool=True) -> None:
        return self._handle_api_action("restart", container_id, result_queue, complete=complete)
    def api_logs(self,container_id:str,result_queue:Queue=None, complete:bool=True) -> None:
        return self._handle_api_action("logs", container_id, result_queue, complete=complete)