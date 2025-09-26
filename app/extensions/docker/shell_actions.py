from .action_base import DockerActionBase

_DOCKER_ACTIONS = {
    'start': DockerActionBase(["docker", "container", "start"]),
    'stop': DockerActionBase(["docker", "container", "stop"]),
    'remove': DockerActionBase(["docker", "container", "remove"]),
    'logs': DockerActionBase(["docker", "container", "logs"]),
    'follow': DockerActionBase(["docker", "container", "logs", "--follow", "--tail", "--150"]),
}

def docker_shell_start(services, result_queue, complete=True):
    return _DOCKER_ACTIONS['start'].execute(services, result_queue, complete)

def docker_shell_stop(services, result_queue, complete=True):
    return _DOCKER_ACTIONS['stop'].execute(services, result_queue, complete)

def docker_shell_remove(services, result_queue, complete=True):
    docker_shell_stop(services, result_queue, False)  # Stop before removing, don't complete
    return _DOCKER_ACTIONS['remove'].execute(services, result_queue, complete)

def docker_shell_logs(services, result_queue, complete=True):
    return _DOCKER_ACTIONS['logs'].execute(services, result_queue, complete)

def docker_shell_follow(services, result_queue, complete=True):
    return _DOCKER_ACTIONS['follow'].execute(services, result_queue, complete)

class DockerShellActions:
    start = docker_shell_start
    stop = docker_shell_stop
    remove = docker_shell_remove
    logs = docker_shell_logs
    follow = docker_shell_follow
    ACTIONS = {
        'start': docker_shell_start,
        'stop': docker_shell_stop,
        'remove': docker_shell_remove,
        'logs': docker_shell_logs,
        'follow': docker_shell_follow
    }