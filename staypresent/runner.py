import subprocess
import threading
import logging
import signal
import time
import sys
import os

from .server import app

logger = logging.getLogger("staypresent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Attach our own handler to the "staypresent" logger only, instead of
    # calling logging.basicConfig() (which configures the *root* logger).
    # A library touching the root logger can silently clobber, duplicate,
    # or reformat log output the host script/bot has already set up for
    # its own unrelated loggers.
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False


def _serve_with_waitress(host: str, port: int, threads: int) -> bool:
    """
    Try to serve the app with waitress, a production-grade WSGI server.
    Returns True if waitress was available and used, False if it isn't installed.
    """
    try:
        from waitress import serve as waitress_serve
    except ImportError:
        return False

    logger.info(
        "Using waitress (production WSGI server) on %s:%s with %s thread(s)",
        host, port, threads,
    )
    waitress_serve(app, host=host, port=port, threads=threads)
    return True


def _run_server(
    host: str,
    port: int,
    started_event: threading.Event,
    error_holder: list,
    production: bool = True,
    threads: int = 4,
):
    try:
        if production:
            used_waitress = _serve_with_waitress(host, port, threads)
            if used_waitress:
                return

            logger.warning(
                "waitress is not installed, falling back to Flask's built-in "
                "development server (not recommended for production). "
                "Install it with `pip install waitress` or `pip install staypresent[prod]` "
                "to silence this warning, or pass staypresent.run(..., production=False) "
                "to use the dev server intentionally."
            )

        app.run(host=host, port=port, threaded=True)
    except OSError as exc:
        # e.g. "Address already in use" - surface it instead of dying silently
        logger.error("Web server thread failed: %s", exc)
        error_holder.append(exc)
    except Exception as exc:  # noqa: BLE001 - surface any other startup failure too
        # e.g. bad host, waitress raising something other than OSError, etc.
        # Without this, a failure here would just make the thread die silently
        # and the bot would run with no working web server and no explanation.
        logger.error("Web server thread failed: %s", exc)
        error_holder.append(exc)
    finally:
        started_event.set()


def run(
    bot_file: str,
    host: str = "0.0.0.0",
    port: int = 8080,
    production: bool = True,
    threads: int = 4,
    restart_on_crash: bool = True,
    max_restarts: int = 5,
    restart_delay: float = 2.0,
    restart_reset_after: float = 60.0,
    bot_args: list = None,
    env: dict = None,
):
    """
    Starts the web server + your bot process.

    Example:
        staypresent.run("bot.py")
        staypresent.run("bot.py", host="0.0.0.0", port=5000)

    By default, if the optional `waitress` package is installed, it is used
    to serve the app so you don't see Flask's "development server" warning.
    If `waitress` isn't installed, StayPresent automatically falls back to
    Flask's built-in dev server and logs a one-time warning explaining how
    to fix it.

    If the bot process crashes (exits with a non-zero code), StayPresent
    will automatically restart it, up to `max_restarts` times, waiting
    `restart_delay` seconds between attempts. A clean exit (exit code 0)
    is treated as intentional and is not restarted. Restarts do not apply
    when you stop StayPresent yourself (Ctrl+C / SIGTERM).

    Args:
        bot_file: Path to the Python script to run alongside the server.
        host: Host to bind the web server to.
        port: Port to bind the web server to.
        production: If True (default), use waitress when available for a
            production-ready server. Set to False to force Flask's dev
            server even if waitress is installed.
        threads: Number of worker threads for waitress to use (default 4,
            same as waitress's own default). Only applies when waitress is
            actually used (i.e. `production=True` and waitress installed).
            Increase this if you're pointing real traffic at the server,
            not just occasional keep-alive pings.
        restart_on_crash: If True (default), automatically relaunch the bot
            process if it exits with a non-zero exit code. Set to False to
            keep the old behavior of exiting once the bot process ends.
        max_restarts: Maximum number of times to restart the bot process
            after a crash before giving up. Ignored if restart_on_crash is
            False.
        restart_delay: Seconds to wait before relaunching the bot process
            after a crash. Ignored if restart_on_crash is False.
        restart_reset_after: If the bot stays up for at least this many
            seconds after a restart, the restart counter is reset to 0.
            This makes `max_restarts` a "consecutive crashes" budget
            instead of a lifetime one, so a bot that runs fine for a long
            time and then crashes once isn't penalized for earlier,
            unrelated crashes. Ignored if restart_on_crash is False.
        bot_args: Optional list of extra command-line arguments to pass to
            `bot_file` (e.g. `["--verbose"]`).
        env: Optional dict of extra environment variables for the bot
            process. Merged on top of the current process's environment
            (i.e. you only need to specify what you want to add/override).
    """

    if not os.path.isfile(bot_file):
        raise FileNotFoundError(
            f"staypresent.run(): bot file '{bot_file}' does not exist or is not a file."
        )

    started_event = threading.Event()
    error_holder = []

    flask_thread = threading.Thread(
        target=_run_server,
        args=(host, port, started_event, error_holder, production, threads),
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

    bot_cmd = [sys.executable, bot_file] + list(bot_args or [])
    bot_env = {**os.environ, **{k: str(v) for k, v in env.items()}} if env else None

    # Holds the current bot Popen object (or None before the first launch /
    # briefly during a restart). A plain mutable container so `shutdown()`
    # can be registered up front and still always see the live process,
    # even one launched after it was registered.
    proc_holder = {"process": None}
    stopping = threading.Event()

    def _launch_bot():
        p = subprocess.Popen(bot_cmd, env=bot_env)
        proc_holder["process"] = p
        return p

    def shutdown(signum, frame):
        stopping.set()
        try:
            sig_name = signal.Signals(signum).name
        except ValueError:
            sig_name = str(signum)
        logger.info("Received %s, stopping...", sig_name)
        proc = proc_holder["process"]
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Bot process did not exit in time, killing it.")
                proc.kill()
                proc.wait()
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

    # Watch for the web server thread dying unexpectedly after a successful
    # startup (e.g. waitress hitting an unhandled error mid-run). A crash at
    # startup is already caught above; this catches crashes later on, since
    # otherwise the thread would just silently disappear (it's a daemon
    # thread) and the bot would keep running with no working web server.
    def _watch_server_thread():
        flask_thread.join()
        if not stopping.is_set():
            if error_holder:
                logger.error("Web server stopped unexpectedly: %s", error_holder[-1])
            else:
                logger.error("Web server thread exited unexpectedly.")

    threading.Thread(target=_watch_server_thread, daemon=True).start()

    process = _launch_bot()
    process_started_at = time.monotonic()

    restarts = 0
    while True:
        process.wait()

        if stopping.is_set():
            # We're shutting down deliberately (signal handler already
            # handles process cleanup + exit), nothing more to do here.
            break

        exit_code = process.returncode
        uptime = time.monotonic() - process_started_at

        if exit_code == 0:
            logger.info("Bot process exited cleanly (code 0). Not restarting.")
            break

        if not restart_on_crash:
            logger.warning("Bot process exited with code %s. Restarts are disabled.", exit_code)
            break

        if uptime >= restart_reset_after and restarts > 0:
            logger.info(
                "Bot process had been running for %.0fs, treating this as a fresh crash streak.",
                uptime,
            )
            restarts = 0

        if restarts >= max_restarts:
            logger.error(
                "Bot process crashed with code %s. Reached max_restarts (%s), giving up.",
                exit_code,
                max_restarts,
            )
            break

        restarts += 1
        logger.warning(
            "Bot process crashed with code %s. Restarting in %.1fs... (attempt %s/%s)",
            exit_code,
            restart_delay,
            restarts,
            max_restarts,
        )
        time.sleep(restart_delay)
        process = _launch_bot()
        process_started_at = time.monotonic()