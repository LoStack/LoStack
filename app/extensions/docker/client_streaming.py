from flask import Response
from queue import Queue
from .client import DockerHandler
from app.extensions.common.stream_handler import StreamHandler

class DockerHandlerStreaming(DockerHandler):
    def __init__(self):
        DockerHandler.__init__(self)
        self.stream_env_start : Response = StreamHandler.create_stream(self.env_start)
        self.stream_env_stop : Response = StreamHandler.create_stream(self.env_stop)
        self.stream_env_kill : Response = StreamHandler.create_stream(self.env_kill)
        self.stream_env_restart : Response = StreamHandler.create_stream(self.env_restart)
        self.stream_env_logs : Response = StreamHandler.create_stream(self.env_logs)