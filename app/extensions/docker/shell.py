import logging
import traceback
from .shell_actions import DockerShellActions

class DockerShellHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".DockerShellHandler")

    def _handle_shell_action(
        self,
        action,
        container_id:str|list[str],
        result_queue=None,
        complete=True
    ) -> None:
        actions = list(DockerShellActions.ACTIONS.keys())
        if not action in actions:
            raise ValueError("Invalid API action")
        
        msg = f"Running {action} on {container_id}"
        if result_queue:
            result_queue.put_nowait(msg)
        self.logger.info(msg)

        try:
            act = DockerShellActions.ACTIONS[action]
            act(container_id, result_queue=result_queue, complete=complete)
        except Exception as e:
            msg = (
                f"Error running {action} on "
                f"{container_id} - {traceback.print_exc()}"
            )
            if result_queue:
                result_queue.put_nowait(msg)
            self.logger.info(msg)
            raise e
        
        if complete and result_queue: # In case action fails somehow
            result_queue.put_nowait("__COMPLETE__")

    def shell_start(self,container_id:str,result_queue:bool=None, complete:bool=True) -> None:
        return self._handle_shell_action("start", container_id, result_queue, complete)
    def shell_stop(self,container_id:str,result_queue:bool=None, complete:bool=True) -> None:
        return self._handle_shell_action("stop", container_id, result_queue, complete)
    def shell_remove(self,container_id:str,result_queue:bool=None, complete:bool=True) -> None:
        return self._handle_shell_action("remove", container_id, result_queue, complete)
    def shell_logs(self,container_id:str,result_queue:bool=None, complete:bool=True) -> None:
        return self._handle_shell_action("logs", container_id, result_queue, complete)
    def shell_follow(self,container_id:str,result_queue:bool=None, complete:bool=True) -> None:
        return self._handle_shell_action("follow", container_id, result_queue, complete)