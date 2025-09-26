from app.extensions.common.runner import RunBase

class DockerActionBase:
    def __init__(self, base_cmd):
        self.base_cmd = base_cmd

    def execute(self, services:str|list[str], result_queue, complete=True):
        if isinstance(services, str):
            services = [services]
        result_queue.put_nowait(f"Running {' '.join(self.base_cmd)} on services: {services}")

        return RunBase(
            [*self.base_cmd, *services],
            result_queue,
            complete=complete
        ).run()