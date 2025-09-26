import os

from .api_client import DockerApiHandler
from .client import DockerHandler
from .compose import DockerComposeHandler
from .shell import DockerShellHandler

class DockerManager(
    DockerHandler,
    DockerApiHandler,
    DockerShellHandler
):
    def __init__(
        self,
        compose_files:list[os.PathLike],
        modified_callback=None
    ) -> None:
        DockerHandler.__init__(self)
        DockerApiHandler.__init__(self)
        DockerShellHandler.__init__(self)
        
        self.compose_file_handlers = {
            file_path : DockerComposeHandler(file_path, modified_callback)
            for file_path in compose_files
        }

from .api_client_streaming import DockerApiHandlerStreaming
from .client_streaming import DockerHandlerStreaming
from .compose_streaming import DockerComposeHandlerStreaming
from .shell_streaming import DockerShellHandlerStreaming

class DockerManagerStreaming(
    DockerApiHandlerStreaming,
    DockerHandlerStreaming,
    DockerShellHandlerStreaming
):
    def __init__(
        self,
        compose_files:list[os.PathLike],
        modified_callback=None
    ) -> None:
        DockerApiHandlerStreaming.__init__(self)
        DockerHandlerStreaming.__init__(self)
        DockerShellHandlerStreaming.__init__(self)
        
        self.compose_file_handlers = {
            file_path : DockerComposeHandlerStreaming(file_path, modified_callback)
            for file_path in compose_files
        }
