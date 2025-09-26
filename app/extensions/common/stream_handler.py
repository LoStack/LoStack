"""Creates streams used to pipe data through a websocket"""

import time
import logging
from flask import Response
from .stream_generator import stream_generator

class StreamHandler:
    """Handler for websocket stream generation"""
    
    @staticmethod
    def create_response(generator_func, mimetype='text/event-stream'):
        """Standard response wrapper for all streaming endpoints"""
        return Response(
            generator_func(),
            mimetype=mimetype,
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no' # Fixes issues with nginx proxies
            }
        )
    
    @staticmethod
    def generic_stream(action, target, *args, **kw):
        """Generic streaming handler"""

        stream = stream_generator(action, (target, *args), kw)
        
        def generator():
            for message in stream(): 
                yield message
            
            time.sleep(3) # wait for queue to flush
                
        return StreamHandler.create_response(generator)

    @staticmethod
    def generic_context_stream(action, app, target, *args, force_sync=True, **kw):
        """Generic streaming handler"""
        if force_sync:
            kw.update({"complete":False})
            
        stream = stream_generator(action, (target, *args), kw)
        
        def generator():
            for message in stream(): 
                yield message

            yield("data: POSTRUN\n\n")

            if force_sync:
                try:
                    with app.app_context():
                        yield("data: SYNCING\n\n")
                        app.docker_handler.force_sync()
                except Exception as e:
                    yield(f"data: Error Handling sync - {e}\n\n")
                    time.sleep(1)
            else:
                return
            
            time.sleep(3) # wait for queue to flush
                
        return StreamHandler.create_response(generator)

    @staticmethod
    def message_completion_stream(message):
        """
        Stream a message and complete the stream
        """
        def generator():
            yield "data: " + message + "\n\n"
            yield "data: __COMPLETE__ \n\n"
            
        return StreamHandler.create_response(generator)

    @staticmethod
    def create_stream(action, context=False):
        """Factory function to create docker streaming functions"""
        if context:
            def stream_func(app, *args, **kw):
                print(action, app, *args)
                return StreamHandler.generic_context_stream(action, app, *args, **kw)
        else:
            def stream_func(*args, **kw):
                return StreamHandler.generic_stream(action, *args, **kw)
        return stream_func