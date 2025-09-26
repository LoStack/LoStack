import os
from flask import Response
from queue import Queue
from .shell import DockerShellHandler
from app.extensions.common.stream_handler import StreamHandler

class DockerShellHandlerStreaming(DockerShellHandler):
    def __init__(self):
        DockerShellHandler.__init__(self)
        self.stream_shell_start : Response = StreamHandler.create_stream(self.shell_start)
        self.stream_shell_stop : Response = StreamHandler.create_stream(self.shell_stop)
        self.stream_shell_remove : Response = StreamHandler.create_stream(self.shell_remove)
        self.stream_shell_logs : Response = StreamHandler.create_stream(self.shell_logs)
        self.stream_shell_follow : Response = StreamHandler.create_stream(self.shell_follow)