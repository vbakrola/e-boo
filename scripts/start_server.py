"""Ubuntu Lab Manager - Full Stack Server Launcher.
Starts FastAPI backend (port 8000) and Next.js frontend (port 3000) concurrently.
"""
import sys
import os
import subprocess
import time
import signal

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(ROOT_DIR, "venv", "bin", "python")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")


def main():
    print("=" * 65)
    print("      Ubuntu Lab Manager — Starting LAN Server Stack")
    print("=" * 65)
    print("Backend API:  http://0.0.0.0:8000 (LAN endpoint)")
    print("Frontend UI:  http://0.0.0.0:3000 (Admin Dashboard)")
    print("Press Ctrl+C to stop both servers.")
    print("=" * 65)

    backend_cmd = [
        VENV_PYTHON, "-m", "uvicorn", "backend.app.main:app",
        "--host", "0.0.0.0", "--port", "8000"
    ]

    npm_bin = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_cmd = [npm_bin, "run", "start", "--", "-p", "3000", "-H", "0.0.0.0"]

    procs = []
    try:
        # Start backend
        print("Starting FastAPI backend...")
        b_proc = subprocess.Popen(backend_cmd, cwd=ROOT_DIR)
        procs.append(b_proc)

        time.sleep(1.5)

        # Start frontend
        print("Starting Next.js frontend...")
        f_proc = subprocess.Popen(frontend_cmd, cwd=FRONTEND_DIR)
        procs.append(f_proc)

        while True:
            time.sleep(1)
            for p in procs:
                if p.poll() is not None:
                    print(f"Process {p.args} exited with code {p.returncode}")
                    return

    except KeyboardInterrupt:
        print("\nStopping Ubuntu Lab Manager services...")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        print("All services stopped.")


if __name__ == "__main__":
    main()
