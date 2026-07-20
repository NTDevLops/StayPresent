import subprocess
import threading
import logging
import signal
import sys
import os

from .server import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)

logger = logging.getLogger("staypresent")


def _run_server():
    app.run(host="0.0.0.0", port=8080)


def run(bot_file: str):
    """
    Starts Flask + Bot

    Example:
        staypresent.run("bot.py")
    """

    flask_thread = threading.Thread(target=_run_server, daemon=True)
    flask_thread.start()

    process = subprocess.Popen([sys.executable, bot_file])

    def shutdown(*args):
        logger.info("Stopping...")
        process.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    process.wait()