import os
from flask import Response
from queue import Queue
from .compose import DockerComposeHandler
from app.extensions.common.stream_handler import StreamHandler

class DockerComposeHandlerStreaming(DockerComposeHandler):
    def __init__(self, file:os.PathLike, modified_callback, context:bool=True):
        DockerComposeHandler.__init__(self, file, modified_callback)
        self.stream_compose_up : Response = StreamHandler.create_stream(self.compose_up, context=context)
        self.stream_compose_start : Response = StreamHandler.create_stream(self.compose_start, context=context)
        self.stream_compose_stop : Response = StreamHandler.create_stream(self.compose_stop, context=context)
        self.stream_compose_down : Response = StreamHandler.create_stream(self.compose_down, context=context)
        self.stream_compose_kill : Response = StreamHandler.create_stream(self.compose_kill, context=context)
        self.stream_compose_logs : Response = StreamHandler.create_stream(self.compose_logs, context=context)
        self.stream_compose_follow : Response = StreamHandler.create_stream(self.compose_follow, context=context)
        self.stream_compose_restart : Response = StreamHandler.create_stream(self.compose_restart, context=context)
        self.stream_compose_rm : Response = StreamHandler.create_stream(self.compose_rm, context=context)
        self.stream_compose_run : Response = StreamHandler.create_stream(self.compose_run, context=context)