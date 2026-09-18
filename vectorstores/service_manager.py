import os
import sys
import subprocess
import time
import socket
import shutil
import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class QdrantServiceManager:
    """Cross-platform Qdrant vector database daemon lifecycle manager."""

    def __init__(self, qdrant_bin: Optional[str] = None, host: str = settings.qdrant_host, port: int = settings.qdrant_port):
        self.qdrant_bin = qdrant_bin or getattr(settings, "qdrant_bin", None) or os.getenv("QDRANT_BIN") or shutil.which("qdrant")
        self.host = host
        self.port = port
        self._process: Optional[subprocess.Popen] = None

    def is_port_in_use(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, self.port)) == 0

    def ensure_running(self) -> None:
        if self.is_port_in_use():
            logger.info(f"Qdrant is already running at {self.host}:{self.port}.")
            return

        if not self.qdrant_bin or not os.path.exists(self.qdrant_bin):
            raise FileNotFoundError(
                f"Qdrant executable not found at '{self.qdrant_bin}'. "
                "Please set QDRANT_BIN environment variable or install Qdrant."
            )

        logger.info(f"Starting Qdrant daemon from '{self.qdrant_bin}'...")
        os.makedirs("data", exist_ok=True)
        env = os.environ.copy()
        env["QDRANT__STORAGE__STORAGE_PATH"] = os.path.abspath("data/storage")

        kwargs = {"env": env}
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            self._process = subprocess.Popen(
                [self.qdrant_bin],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **kwargs
            )
        except Exception as e:
            raise RuntimeError(f"Failed to launch Qdrant subprocess: {e}")

        # Wait for port to become active
        for _ in range(30):
            if self.is_port_in_use():
                logger.info("Qdrant daemon successfully started and responding.")
                return
            time.sleep(0.5)

        raise TimeoutError("Timed out waiting for Qdrant service to start.")

    def stop(self) -> None:
        if self._process:
            logger.info("Stopping Qdrant daemon process...")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
