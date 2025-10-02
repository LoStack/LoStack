"""Stream a threaded action to a queue"""

import queue
import threading
import logging


def stream_generator(target, args=(), kwargs={}, app=None):
    """Runs an action as a thread, yields output queue contents to a generator"""
    def context_target(*a, **k):
        if app:
            with app.app_context():
                return target(*a, **k)
        else:
            return target(*a, **k)

    def generator():
        result_queue = queue.Queue()
        kw = kwargs.copy()
        kw.update({"result_queue": result_queue})
        thread = threading.Thread(
            target=context_target,
            args=args,
            kwargs=kw,
            daemon=False
        )
        thread.start()
        while thread.is_alive():
            try:
                line = result_queue.get(timeout=0.5)
                if line == "__COMPLETE__":
                    result_queue.task_done()
                    break
                yield "data: "+line+"\n\n"
                # logging.info(line)
                result_queue.task_done()
            except queue.Empty:
                continue
            except GeneratorExit:
                break
    return generator