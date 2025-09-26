import docker
import logging
import os
import traceback
from .compose_file_manager import ComposeFileManager
from .compose_actions import DockerComposeActions


class DockerComposeHandler(ComposeFileManager):
    def __init__(self, file:os.PathLike, modified_callback=None):
        ComposeFileManager.__init__(self, file, modified_callback)
        self.logger = logging.getLogger(__name__ + ".DockerComposeHandler")

    def _handle_compose_action(
        self,
        action,
        container_id:str|list[str],
        result_queue=None,
        complete=True
    ) -> None:
        
        actions = list(DockerComposeActions.ACTIONS.keys())
        if not action in actions:
            raise ValueError("Invalid API action")
        
        msg = f"Running {action} on {container_id}"
        if result_queue:
            result_queue.put_nowait(msg)
        self.logger.info(msg)

        try:
            act = DockerComposeActions.ACTIONS[action]
            act(
                container_id,
                result_queue, 
                compose_file = self.file, # From compose file manager mixin
                complete = complete
            )
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

    def compose_up(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("up", container_id, result_queue, complete=complete)
    def compose_start(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("start", container_id, result_queue, complete=complete)
    def compose_stop(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("stop", container_id, result_queue, complete=complete)
    def compose_down(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("down", container_id, result_queue, complete=complete)
    def compose_kill(self, container_id:str|list[str], result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("kill", container_id, result_queue, complete=complete)
    def compose_logs(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("logs", container_id, result_queue, complete=complete)
    def compose_follow(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("follow", container_id, result_queue, complete=complete)
    def compose_restart(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("restart", container_id, result_queue, complete=complete)
    def compose_rm(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("rm", container_id, result_queue, complete=complete)
    def compose_run(self,container_id:str|list[str],result_queue:bool=None,complete:bool=True) -> None:
        return self._handle_compose_action("run", container_id, result_queue, complete=complete)