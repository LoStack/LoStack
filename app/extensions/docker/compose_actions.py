from .action_base import DockerActionBase

_COMMANDS = {
    "up": ["up", "-d"],
    "start": ["start"],
    "stop": ["stop"],
    "down": ["down"],
    "kill": ["kill", "-s"],
    "logs": ["logs", "--tail", "150"],
    "follow": ["logs", "--follow", "--tail", "150"],
    "restart": ["restart"],
    "run": ["run"],
    "rm" : ["rm"]
}

def _create_docker_action(command_args):
    def action(services, result_queue, compose_file="/docker/docker-compose.yml", complete=True):
        return DockerActionBase(
            ["docker", "compose", "-f", str(compose_file)] + command_args
        ).execute(services, result_queue, complete)
    return action

docker_compose_up = _create_docker_action(_COMMANDS["up"])
docker_compose_start = _create_docker_action(_COMMANDS["start"])
docker_compose_stop = _create_docker_action(_COMMANDS["stop"])
docker_compose_down = _create_docker_action(_COMMANDS["down"])
docker_compose_kill = _create_docker_action(_COMMANDS["kill"])
docker_compose_logs = _create_docker_action(_COMMANDS["logs"])
docker_compose_follow = _create_docker_action(_COMMANDS["follow"])
docker_compose_restart = _create_docker_action(_COMMANDS["restart"])
docker_compose_rm = _create_docker_action(_COMMANDS["rm"])
docker_compose_run = _create_docker_action(_COMMANDS["run"])

class DockerComposeActions:
    up = docker_compose_up
    start = docker_compose_start
    stop = docker_compose_stop
    down = docker_compose_down
    kill = docker_compose_kill
    logs = docker_compose_logs
    follow = docker_compose_follow
    restart = docker_compose_restart
    rm = docker_compose_rm
    run = docker_compose_run
    ACTIONS = {
        "up": docker_compose_up,
        "start": docker_compose_start,
        "stop": docker_compose_stop,
        "down": docker_compose_down,
        "kill": docker_compose_kill,
        "logs": docker_compose_logs,
        "follow": docker_compose_follow,
        "restart": docker_compose_restart,
        "rm": docker_compose_rm,
        "run": docker_compose_run
    }