from flask import Response
from queue import Queue
from .api_client import DockerApiHandler
from app.extensions.common.stream_handler import StreamHandler

class DockerApiHandlerStreaming(DockerApiHandler):
    def __init__(self):
        DockerApiHandler.__init__(self)
        self.stream_api_start : Response = StreamHandler.create_stream(self.api_start)
        self.stream_api_stop : Response = StreamHandler.create_stream(self.api_stop)
        self.stream_api_kill : Response = StreamHandler.create_stream(self.api_kill)
        self.stream_api_restart : Response = StreamHandler.create_stream(self.api_restart)
        self.stream_api_logs : Response = StreamHandler.create_stream(self.api_logs)