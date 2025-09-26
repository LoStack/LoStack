import docker
import logging
import traceback

class DockerHandler:
    def __init__(self):
        self.client = docker.from_env()
        self.logger = logging.getLogger(__name__ + ".DockerHandler")

    def _handle_env_action(
        self,
        action,
        container_id:str,
        result_queue=None,
        complete=False
    ) -> None:
        actions = "start", "stop", "kill", "restart", "logs"
        if not action in actions:
            raise ValueError("Invalid API action")
        
        msg = f"Running {action} on {container_id}"
        if result_queue:
            result_queue.put_nowait(msg)
        self.logger.info(msg)

        container = self.client.containers.get(container_id)

        try:
            act = getattr(container, action)
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

    def env_start(self,container_id:str,result_queue:bool=None, complete=True) -> None:
        return self._handle_env_action("start", container_id, result_queue, complete=complete)
    def env_stop(self,container_id:str,result_queue:bool=None, complete=True) -> None:
        return self._handle_env_action("stop", container_id, result_queue, complete=complete)
    def env_kill(self, container_id:str, result_queue:bool=None, complete=True) -> None:
        return self._handle_env_action("kill", container_id, result_queue, complete=complete)
    def env_restart(self,container_id:str,result_queue:bool=None, complete=True) -> None:
        return self._handle_env_action("restart", container_id, result_queue, complete=complete)
    def env_logs(self,container_id:str,result_queue:bool=None, complete=True) -> None:
        return self._handle_env_action("logs", container_id, result_queue, complete=complete)