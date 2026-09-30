"""Run only P01's isolated CPU browser gallery on unique loopback ports."""
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "artifacts" / "refit-capture"
RAW.mkdir(parents=True, exist_ok=True)

def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", port)) == 0

def wait_port(port, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(f"Owned process for {port} exited: {process.returncode}")
        if port_open(port):
            return
        time.sleep(0.1)
    raise RuntimeError(f"Owned process for {port} did not start")

def main():
    if port_open(19101) or port_open(19102):
        raise RuntimeError("Dedicated P01 capture port is already occupied")
    processes = []
    try:
        with (RAW / "server.log").open("wb") as server_log, (RAW / "chrome.log").open("wb") as chrome_log:
            server = subprocess.Popen(
                [sys.executable, "-m", "workbench.server", "--port", "19101", "--db", str(RAW / "gallery-final.sqlite3")],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(server)
            wait_port(19101, server)
            chrome = subprocess.Popen(
                ["/opt/google/chrome/chrome", "--headless=new", "--disable-gpu",
                 "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=19102",
                 "--user-data-dir=" + str(RAW / "chrome-profile"), "--no-first-run",
                 "--no-default-browser-check", "about:blank"],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=chrome_log, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(chrome)
            wait_port(19102, chrome)
            from scripts.refit_gallery_capture import main as capture
            capture()
            from scripts import keyboard_queue_browser as keyboard
            from scripts import operator_review_browser as workflow
            workflow.APP = "http://127.0.0.1:19101"
            original_args = sys.argv
            try:
                sys.argv = ["keyboard_queue_browser", "--phase", "after", "--cdp", "http://127.0.0.1:19102"]
                keyboard.main()
            finally:
                sys.argv = original_args
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

if __name__ == "__main__":
    main()
