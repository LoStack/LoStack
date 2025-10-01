"""
session_manager.py - Andrew Spangler
Manages service session tracking and container tasks using JSON backend
"""

import datetime
import json
import logging
import os
import queue
import threading
import time
import uuid
from collections import defaultdict

def parse_duration(dur_str: str) -> float:
    """Convert '1m', '2h', '30s' into seconds"""
    if isinstance(dur_str, int):
        return dur_str
    items = dur_str.strip().split(" ")
    total = 0
    units = {'s': 1, 'm': 60, 'h': 3600}
    for item in items:
        if item[-1] in units:
            total += int(item[:-1]) * units[item[-1]]
    if items:
        return total
    return int(dur_str)

class TaskInfo:
    def __init__(self, task_id, containers, action, queue, package_entry=None, task_redirect: str = None, refresh_frequency: int = 1):
        self.task_id = task_id
        self.containers = containers
        self.action = action
        self.queue = queue
        self.thread = None
        self.status = "pending"
        self.created_at = datetime.datetime.utcnow()
        self.completed_at = None
        self.error = None
        self.package_entry = package_entry
        self.task_redirect = task_redirect
        self.refresh_frequency = refresh_frequency

class SessionManager:
    """
    Handles LoStack autostart/stop sessions
    """
    def __init__(self, app, json_file='/config/lostack/sessions.json', update_interval=10):
        self.app = app

        parent = os.path.exists(os.path.dirname(json_file))
        if not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        self.json_file = json_file
        self.update_interval = update_interval
        self.logger = app.logger
        self.lock = threading.Lock()

        self.tasks = {}
        self.container_queues = defaultdict(set)
        self.active_containers = set()

        self.sessions = {}  # key: container_name, value: session dict
        self._load_sessions()

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()       

        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()

    # Clean up old tasks every hour
    def _cleanup_worker(self):
        while True:
            try:
                self.cleanup_old_tasks()
                self._flush_sessions()
            except Exception as e:
                self.logger.error(f"Error in cleanup worker: {e}")
            threading.Event().wait(60)  # cleanup every 10 seconds
    
    def cleanup_old_tasks(self, max_age_hours=24):
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=max_age_hours)
        with self.lock:
            to_remove = [tid for tid, t in self.tasks.items()
                         if t.status in ["completed", "failed"] and t.completed_at and t.completed_at < cutoff]
            for tid in to_remove:
                del self.tasks[tid]

    # ------------------ JSON Backend ------------------ #
    def _load_sessions(self):
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r') as f:
                    data = json.load(f)
                # Convert timestamps back to datetime
                for k, v in data.items():
                    v['last_access'] = datetime.datetime.fromisoformat(v['last_access'])
                    v['start_time'] = datetime.datetime.fromisoformat(v['start_time'])
                self.sessions = data
                self.logger.info(f"Loaded {len(self.sessions)} sessions from JSON")
            except Exception as e:
                self.logger.error(f"Failed to load sessions from {self.json_file}: {e}")

    def _flush_sessions(self):
        with self.lock:
            data = {}
            for container_name, session in self.sessions.items():
                s = session.copy()
                # Serialize datetime objects
                s['last_access'] = s['last_access'].isoformat()
                s['start_time'] = s['start_time'].isoformat()
                data[container_name] = s
            try:
                with open(self.json_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                self.logger.error(f"Error writing sessions to JSON: {e}")

    # ------------------ Session Management ------------------ #
    def start_session(self, container_name: str, user: "User", session_duration: int = 3600):
        duration = parse_duration(session_duration)
        now = datetime.datetime.utcnow()
        with self.lock:
            self.sessions[container_name] = {
                "user_id": user.id,
                "duration": duration,
                "last_access": now,
                "start_time": now
            }
        self.needs_flush = True
        # self._flush_sessions()

    def update_access(self, container_name: str, user: "User"):
        now = datetime.datetime.utcnow()
        with self.lock:
            if container_name in self.sessions:
                self.sessions[container_name]['last_access'] = now
            else:
                self.sessions[container_name] = {
                    "user_id": user.id,
                    "duration": 3600,
                    "last_access": now,
                    "start_time": now
                }
        self.needs_flush = True
        # self._flush_sessions()

    def end_session(self, container_name: str):
        with self.lock:
            if container_name not in self.sessions:
                return
            session = self.sessions.pop(container_name)
        self._flush_sessions()

        with self.app.app_context():
            try:
                self.app.docker_manager.shell_stop([container_name], result_queue=queue.Queue())
            except Exception as e:
                self.logger.error(f"Failed to stop container {container_name}: {e}")

    def _update_loop(self):
        while self.running:
            try:
                now = datetime.datetime.utcnow()
                expired = []
                with self.lock:
                    for container, session in self.sessions.items():
                        idle_seconds = (now - session['last_access']).total_seconds()
                        if idle_seconds > session['duration']:
                            expired.append(container)
                for container in expired:
                    self.logger.info(f"Session expired for {container}, stopping container")
                    self.end_session(container)
            except Exception as e:
                self.logger.error(f"Error in session update loop: {e}")
            time.sleep(self.update_interval)

    # ------------------ Task Management ------------------ #
    def has_task_access(self, task_id, user_groups, admin_group):
        """Check if user has access to a specific task"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            if admin_group in user_groups:
                return True
            task_info = self.tasks[task_id]
            if task_info.package_entry:
                return any(g in task_info.package_entry.allowed_groups for g in user_groups)
            return False

    def _has_conflicting_task(self, containers, action):
        for task_info in self.tasks.values():
            if task_info.status in ["pending", "running"]:
                if set(containers) & set(task_info.containers):
                    if action == task_info.action:
                        self.logger.info(f"Duplicate {action} task detected for containers: {set(containers) & set(task_info.containers)}")
                        return True
                    else:
                        self.logger.info(f"Conflicting task detected: trying to {action} while {task_info.action} is active")
                        return True
        return False

    def _complete_task(self, task_id, success=True, error=None):
        with self.lock:
            if task_id not in self.tasks:
                return
            task_info = self.tasks[task_id]
            task_info.status = "completed" if success else "failed"
            task_info.completed_at = datetime.datetime.utcnow()
            task_info.error = error
            for container in task_info.containers:
                self.active_containers.discard(container)
                self.container_queues[container].discard(task_id)
                if not self.container_queues[container]:
                    del self.container_queues[container]

    def _make_docker_task(self, task_id, containers, action):
        def handle():
            try:
                task_info = self.tasks[task_id]
                task_info.status = "running"
                task_info.queue.put({"type": "status", "message": f"Starting {action} for {containers}", "timestamp": datetime.datetime.utcnow().isoformat()})
                
                if action == "start":
                    self.app.docker_manager.shell_start(containers, task_info.queue)
                elif action == "stop":
                    self.app.docker_manager.shell_stop(containers, task_info.queue)
                else:
                    raise ValueError(f"Unknown action: {action}")
                
                for container in containers:
                    task_info.queue.put({"type": "progress", "container": container, "action": action, "status": "success", "timestamp": datetime.datetime.utcnow().isoformat()})
                
                task_info.queue.put({"type": "complete", "message": f"{action.capitalize()} completed", "timestamp": datetime.datetime.utcnow().isoformat()})
                self._complete_task(task_id, success=True)
            except Exception as e:
                self.logger.error(f"Error in {action} task {task_id}: {e}", exc_info=True)
                if task_info:
                    task_info.queue.put({"type": "error", "message": str(e), "timestamp": datetime.datetime.utcnow().isoformat()})
                self._complete_task(task_id, success=False, error=str(e))

        thread = threading.Thread(target=handle, name=f"docker-{action}-{task_id[:8]}")
        thread.daemon = True
        return thread

    def get_task_stream(self, task_id):
        """Generator for streaming task updates"""
        self.logger.debug(f"Starting task stream for {task_id}")
        
        if task_id not in self.tasks:
            self.logger.error(f"Task {task_id} not found")
            yield json.dumps({"type": "error", "message": "Task not found"}) + "\n"
            return
            
        task_info = self.tasks[task_id]
        self.logger.debug(f"Task {task_id} status: {task_info.status}")
        
        start_time = datetime.datetime.utcnow()

        max_wait_time = 500
        while task_info.status in ["pending", "running"]:
            try:
                # Check if we've been waiting too long
                if (datetime.datetime.utcnow() - start_time).total_seconds() > max_wait_time:
                    self.logger.error(f"Task {task_id} timed out after {max_wait_time} seconds")
                    yield json.dumps({
                        "type": "error", 
                        "message": f"Task timed out after {max_wait_time} seconds"
                    }) + "\n"
                    break
                
                message = task_info.queue.get(timeout=0.5)

                if isinstance(message, str):
                    message = {
                        "type" : "status",
                        "message" : message
                    }

                self.logger.debug(f"Task {task_id} queue message: {message}")
                yield json.dumps(message) + "\n"
                
                if message.get("type") in ["complete", "error"]:
                    self.logger.debug(f"Task {task_id} finished with type: {message.get('type')}")
                    break
                    
            except queue.Empty:
                current_time = datetime.datetime.utcnow()
                yield json.dumps({
                    "type": "heartbeat",
                    "timestamp": current_time.isoformat(),
                    "status": task_info.status
                }) + "\n"
                
                if task_info.status not in ["pending", "running"]:
                    self.logger.debug(f"Task {task_id} status changed to {task_info.status}")
                    break
            
            except Exception as e:
                self.logger.error(f"Error in task stream for {task_id}: {e}")
                yield json.dumps({
                    "type": "error", 
                    "message": f"Stream error: {traceback.print_exc()}"
                }) + "\n"
                break
        
        if task_info.status == "completed":
            yield json.dumps({
                "type": "complete",
                "message": "Task completed successfully",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }) + "\n"
        elif task_info.status == "failed":
            yield json.dumps({
                "type": "error",
                "message": f"Task failed: {task_info.error or 'Unknown error'}",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }) + "\n"
        
        self.logger.debug(f"Task stream for {task_id} ended")

    def get_task_status(self, task_id):
        with self.lock:
            if task_id not in self.tasks:
                return None
            t = self.tasks[task_id]
            return {
                "task_id": task_id,
                "containers": t.containers,
                "action": t.action,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "error": t.error
            }

    def start_task(self, containers, package_entry, redirect="/"):
        valid_containers = [str(c).strip() for c in containers if c and str(c).strip()]
        if not valid_containers or self._has_conflicting_task(valid_containers, "start"):
            return None
        task_id = str(uuid.uuid4())
        q = queue.Queue()
        with self.lock:
            task_info = TaskInfo(task_id, valid_containers, "start", q, package_entry=package_entry, task_redirect=redirect)
            self.tasks[task_id] = task_info
            for c in valid_containers:
                self.active_containers.add(c)
                self.container_queues[c].add(task_id)
        task_info.thread = self._make_docker_task(task_id, valid_containers, "start")
        task_info.thread.start()
        return task_id

    def stop_task(self, containers, package_entry=None):
        if not containers or self._has_conflicting_task(containers, "stop"):
            return None
        task_id = str(uuid.uuid4())
        q = queue.Queue()
        with self.lock:
            task_info = TaskInfo(task_id, containers, "stop", q, package_entry=package_entry)
            self.tasks[task_id] = task_info
            for c in containers:
                self.active_containers.add(c)
                self.container_queues[c].add(task_id)
        task_info.thread = self._make_docker_task(task_id, containers, "stop")
        task_info.thread.start()
        return task_id

    def start_containers(self, containers, package_entry, task_redirect="/"):
        """Start containers, return task_id or None if conflicts exist"""
        # Validate containers list
        if not containers:
            self.logger.error("No containers provided to start_containers")
            return None
            
        # Filter out invalid container names
        valid_containers = [str(c).strip() for c in containers if c and str(c).strip()]
        if not valid_containers:
            self.logger.error("No valid container names after filtering")
            return None
            
        if len(valid_containers) != len(containers):
            self.logger.warning(f"Filtered containers: {containers} -> {valid_containers}")
        
        self.logger.debug(f"Starting containers: {valid_containers}")
        
        task_id = str(uuid.uuid4())
        q = queue.Queue()
        
        with self.lock:
            if self._has_conflicting_task(valid_containers, "start"):
                return None
                
            task_info = TaskInfo(
                task_id,
                valid_containers,
                "start",
                q,
                package_entry=package_entry,
                task_redirect=task_redirect,
                refresh_frequency=package_entry.refresh_frequency
                )
            self.tasks[task_id] = task_info
            
            # Add containers to active set
            for container in valid_containers:
                self.active_containers.add(container)
                self.container_queues[container].add(task_id)
        
        # Start thread outside of lock
        task_info.thread = self._make_docker_task(task_id, valid_containers, "start")
        task_info.thread.start()
        
        return task_id

    def stop_containers(self, containers, package_entry=None):
        """Stop containers, return task_id or None if conflicts exist"""
        task_id = str(uuid.uuid4())
        q = queue.Queue()
        
        with self.lock:
            if self._has_conflicting_task(containers, "stop"):
                return None
                
            task_info = TaskInfo(
                task_id,
                containers,
                "stop",
                q,
                package_entry=package_entry,
                task_redirect=None
            )
            self.tasks[task_id] = task_info
            
            # Add containers to active set
            for container in containers:
                self.active_containers.add(container)
                self.container_queues[container].add(task_id)
        
        # Start thread outside of lock
        task_info.thread = self._make_docker_task(task_id, containers, "stop")
        task_info.thread.start()
        
        return task_id
    
    def handle_autostart(self, package_entry, user: "User", redirect="/"):
        container_names = package_entry.docker_services
        if isinstance(container_names, str):
            container_names = [name.strip() for name in container_names.split(',') if name.strip()]
        elif isinstance(container_names, list):
            container_names = [name.strip() for name in container_names if name and str(name).strip()]
        else:
            return None

        if not container_names or not package_entry.lostack_autostart_enabled:
            return None

        try:
            with self.app.app_context():
                info = self.app.docker_manager.get_services_info(container_names)
        except Exception as e:
            self.logger.error(f"Failed to get container info: {e}")
            return None
        
        if not info:
            self.logger.error("Failed to get container info!")
            return None

        print(info)
        to_start = []
        for name, data in info.items():
            if not data:
                self.logger.warning(f"Failed to get container data for {name}")
                continue
            if not data.get("State") == "running":
                to_start.append(name)

        try:
            for container in container_names:
                self.start_session(
                    container_name=container,
                    user=user,
                    session_duration=package_entry.session_duration,
                )
        except Exception as e:
            self.logger.error(f"Failed to create/update session for autostart: {e}")

        task_id = None
        if to_start:
            valid_containers = [name for name in to_start if name and str(name).strip()]
            if valid_containers:
                task_id = self.start_containers(valid_containers, package_entry, redirect)

        return task_id