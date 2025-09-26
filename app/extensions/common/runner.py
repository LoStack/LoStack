"""Run a subprocess, and pipe output to queue"""

import os
import subprocess
import threading
from queue import Queue


class RunBase:
    """Object to stream shell output to a queue."""
    def __init__(
        self,
        call : list[str],
        result_queue : Queue,
        complete : bool = False, # Stream complete message on finish
        work_dir : os.PathLike = "/docker"
    ):
        self.call = call
        self.queue = result_queue
        self.complete_at_end = complete
        self.work_dir = work_dir

    def run(self) -> Queue:
        oldcwd = os.getcwd()
        self.status = None
        try:
            def pipe_output(pipe, tag) -> None:
                for line in iter(pipe.readline, ''):
                    msg = tag + line.strip()
                    self.queue.put_nowait(msg)
                pipe.close()

            os.chdir(self.work_dir)
            process = subprocess.Popen(
                self.call,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            stdout_thread = threading.Thread(
                target=pipe_output,
                args=(process.stdout, "stdout: ")
                )
            stderr_thread = threading.Thread(
                target=pipe_output,
                args=(process.stderr, "stderr: ")
                )
            stdout_thread.start()
            stderr_thread.start()
            process.wait()
            stdout_thread.join()
            stderr_thread.join()
        except Exception as e:
            self.status = e
        os.chdir(oldcwd)
        if self.complete_at_end:
            self.queue.put_nowait("__COMPLETE__")
        if self.status:
            raise self.status
        return self.queue