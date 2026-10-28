"""Ubuntu Lab Manager Agent Daemon.
Runs locally on each Ubuntu PC as a systemd service.
Zero third-party dependencies: uses standard library urllib, ssl, json, subprocess.
"""
import os
import sys
import time
import ssl
import json
import logging
import argparse
import socket
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple

# Enable relative or absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.config import AgentConfig
from agent.system_info import collect_system_vitals, get_lan_ip
from agent.executor import execute_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ubuntu-lab-agent")


def make_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
    ca_cert_path: Optional[str] = None,
    timeout: int = 15
) -> Tuple[int, Any]:
    """Perform HTTP/HTTPS request using standard library urllib."""
    req_headers = {"User-Agent": "UbuntuLabAgent/1.0", "Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)

    # SSL context handling
    ctx = ssl.create_default_context()
    if ca_cert_path and os.path.exists(ca_cert_path):
        ctx.load_verify_locations(ca_cert_path)
    elif url.startswith("https://"):
        # For development / LAN self-signed certificates without explicit CA configured:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx if url.startswith("https://") else None, timeout=timeout) as resp:
            resp_code = resp.getcode()
            resp_body = resp.read().decode("utf-8")
            try:
                parsed = json.loads(resp_body) if resp_body else {}
            except Exception:
                parsed = resp_body
            return resp_code, parsed
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = err_body
        return e.code, parsed
    except Exception as e:
        logger.error(f"Network error connecting to {url}: {e}")
        return 0, str(e)


class LabAgent:
    def __init__(self, config: AgentConfig):
        self.config = config

    def register(self, enrollment_token: str, server_url: Optional[str] = None, hostname: Optional[str] = None) -> bool:
        """Enroll this PC with the central management server."""
        if server_url:
            self.config.server_url = server_url.rstrip("/")
        
        my_hostname = hostname or self.config.hostname or socket.gethostname()
        vitals = collect_system_vitals()
        
        payload = {
            "enrollment_token": enrollment_token.strip(),
            "hostname": my_hostname,
            "ip_address": get_lan_ip(),
            "mac_address": vitals.get("mac_address"),
            "os_version": vitals.get("os_version", "Ubuntu 22.04 LTS"),
            "kernel_version": vitals.get("kernel_version"),
            "agent_version": "1.0.0"
        }

        endpoint = f"{self.config.server_url}/api/v1/agent/enroll"
        logger.info(f"Enrolling device '{my_hostname}' with server at {endpoint}...")
        
        code, resp = make_request(endpoint, method="POST", data=payload, ca_cert_path=self.config.ca_cert_path)
        if code in (200, 201) and isinstance(resp, dict):
            self.config.device_id = resp["device_id"]
            self.config.device_token = resp["device_token"]
            self.config.hostname = resp["hostname"]
            self.config.save()
            logger.info(f"Enrollment successful! Device ID: {self.config.device_id}, Hostname: {self.config.hostname}")
            return True
        else:
            logger.error(f"Enrollment failed (HTTP {code}): {resp}")
            return False

    def send_heartbeat(self) -> Tuple[bool, int]:
        """Send periodic health ping to server. Returns (success, pending_tasks_count)."""
        if not self.config.device_token:
            logger.warning("Device not registered. Cannot send heartbeat.")
            return False, 0

        vitals = collect_system_vitals()
        payload = {
            "ip_address": get_lan_ip(),
            "mac_address": vitals.get("mac_address"),
            "os_version": vitals.get("os_version"),
            "kernel_version": vitals.get("kernel_version"),
            "agent_version": "1.0.0",
            "uptime_seconds": vitals.get("uptime_seconds"),
            "cpu_percent": vitals.get("cpu_percent"),
            "memory_percent": vitals.get("memory_percent"),
            "disk_percent": vitals.get("disk_percent")
        }

        endpoint = f"{self.config.server_url}/api/v1/agent/heartbeat"
        headers = {"X-Device-Token": self.config.device_token}
        
        code, resp = make_request(endpoint, method="POST", headers=headers, data=payload, ca_cert_path=self.config.ca_cert_path)
        if code == 200 and isinstance(resp, dict):
            pending_count = resp.get("pending_tasks_count", 0)
            return True, pending_count
        else:
            logger.warning(f"Heartbeat failed (HTTP {code}): {resp}")
            return False, 0

    def poll_and_execute_task(self) -> bool:
        """Poll server for next authorized account task and execute locally."""
        if not self.config.device_token:
            return False

        endpoint = f"{self.config.server_url}/api/v1/agent/tasks/poll"
        headers = {"X-Device-Token": self.config.device_token}

        code, resp = make_request(endpoint, method="GET", headers=headers, ca_cert_path=self.config.ca_cert_path)
        if code != 200 or not isinstance(resp, dict) or not resp.get("task"):
            return False

        task = resp["task"]
        task_id = task.get("task_id")
        op = task.get("operation")
        target_user = task.get("target_username")

        logger.info(f"Received authorized task [{task_id}]: {op} for user '{target_user}'")

        # Execute locally
        success, err_msg, details = execute_task(task)

        # Report results back to server
        report_endpoint = f"{self.config.server_url}/api/v1/agent/tasks/report"
        report_payload = {
            "task_id": task_id,
            "status": "SUCCEEDED" if success else "FAILED",
            "error_message": err_msg,
            "result_details": details
        }
        rep_code, rep_resp = make_request(
            report_endpoint, method="POST", headers=headers, data=report_payload,
            ca_cert_path=self.config.ca_cert_path
        )
        logger.info(f"Task [{task_id}] execution result reported: {'SUCCEEDED' if success else 'FAILED'} (HTTP {rep_code})")
        return True

    def run_daemon(self):
        """Main agent service loop: continuous heartbeat and task execution."""
        logger.info(f"Starting Ubuntu Lab Agent daemon for device '{self.config.hostname or socket.gethostname()}'...")
        last_heartbeat_time = 0.0

        while True:
            try:
                now = time.time()
                # Send heartbeat when due
                if now - last_heartbeat_time >= self.config.heartbeat_interval:
                    hb_success, pending_count = self.send_heartbeat()
                    if hb_success:
                        last_heartbeat_time = now
                        if pending_count > 0:
                            # Promptly process pending tasks
                            self.poll_and_execute_task()

                # Poll for tasks
                has_task = self.poll_and_execute_task()
                if has_task:
                    # If a task was executed, immediately check if another task is waiting
                    continue

            except KeyboardInterrupt:
                logger.info("Agent daemon stopped by signal.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in agent daemon loop: {e}", exc_info=True)

            time.sleep(self.config.poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Ubuntu Lab Manager PC Agent")
    subparsers = parser.add_subparsers(dest="command")

    # Register command
    reg_parser = subparsers.add_parser("register", help="Enroll device with central server")
    reg_parser.add_argument("--server", required=True, help="Central server base URL (e.g. https://192.168.1.50:8000)")
    reg_parser.add_argument("--enrollment-token", required=True, help="One-time enrollment token")
    reg_parser.add_argument("--hostname", help="Override computer hostname (e.g. LAB-PC-01)")
    reg_parser.add_argument("--config", help="Custom config path")

    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run agent background service loop")
    daemon_parser.add_argument("--config", help="Custom config path")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check local agent status")
    status_parser.add_argument("--config", help="Custom config path")

    # Run-once command
    run_once_parser = subparsers.add_parser("run-once", help="Execute single heartbeat and poll cycle")
    run_once_parser.add_argument("--config", help="Custom config path")

    args = parser.parse_args()
    config_path = getattr(args, "config", None)
    config = AgentConfig.load(config_path)
    agent = LabAgent(config)

    if args.command == "register":
        success = agent.register(
            enrollment_token=args.enrollment_token,
            server_url=args.server,
            hostname=args.hostname
        )
        sys.exit(0 if success else 1)
    elif args.command == "daemon":
        agent.run_daemon()
    elif args.command == "status":
        print(f"Server URL:     {config.server_url}")
        print(f"Device ID:      {config.device_id or 'Not enrolled'}")
        print(f"Hostname:       {config.hostname or socket.gethostname()}")
        print(f"Token Config:   {'Present' if config.device_token else 'Missing'}")
        print(f"LAN IP:         {get_lan_ip()}")
        if config.device_token:
            ok, pending = agent.send_heartbeat()
            print(f"Server Ping:    {'OK' if ok else 'UNREACHABLE'}")
            print(f"Pending Tasks:  {pending}")
    elif args.command == "run-once":
        agent.send_heartbeat()
        agent.poll_and_execute_task()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
