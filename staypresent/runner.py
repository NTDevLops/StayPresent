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


def _run_server(host: str, port: int, started_event: threading.Event, error_holder: list):
    try:
        app.run(host=host, port=port)
    except OSError as exc:
        # e.g. "Address already in use" - surface it instead of dying silently
        error_holder.append(exc)
    finally:
        started_event.set()


def run(bot_file: str, host: str = "0.0.0.0", port: int = 8080):
    """
    Starts Flask + Bot

    Example:
        staypresent.run("bot.py")
        staypresent.run("bot.py", host="0.0.0.0", port=5000)
    """

    if not os.path.isfile(bot_file):
        raise FileNotFoundError(
            f"staypresent.run(): bot file '{bot_file}' does not exist or is not a file."
        )

    started_event = threading.Event()
    error_holder = []

    flask_thread = threading.Thread(
        target=_run_server,
        args=(host, port, started_event, error_holder),
        daemon=True,
    )
    flask_thread.start()

    # Give the server a brief moment to fail fast (e.g. port already in use)
    # before we launch the bot process alongside it.
    started_event.wait(timeout=1.5)
    if error_holder:
        logger.error("Web server failed to start on %s:%s -> %s", host, port, error_holder[0])
        raise error_holder[0]

    logger.info("Web server running on %s:%s", host, port)

    process = subprocess.Popen([sys.executable, bot_file])

    def shutdown(*args):
        logger.info("Stopping...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Bot process did not exit in time, killing it.")
            process.kill()
            process.wait()
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
    except ValueError:
        # signal handlers can only be registered on the main thread;
        # if run() is called elsewhere, skip graceful signal handling
        # rather than crashing.
        logger.warning(
            "Could not register signal handlers (not running on main thread). "
            "Ctrl+C / SIGTERM will not gracefully stop the bot process."
        )

    process.wait()
