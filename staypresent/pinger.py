"""
Optional self-ping / keep-warm feature.

Some free hosting tiers (Render, Railway, Replit, etc.) spin a web service
down after a period of inactivity, and only wake it back up once a new
request comes in. `staypresent.cron()` works around this by periodically
making a real HTTP request to your service's *public* URL from a background
thread, so the platform keeps seeing traffic.

Nothing in this module runs unless you explicitly call `staypresent.ping()`
or `staypresent.cron()` yourself - it's entirely opt-in.

Note: pinging your own 127.0.0.1/0.0.0.0 does NOT prevent platform-level
inactivity spin-down, since that traffic never leaves the machine. Point
`cron()` at your public URL (e.g. "https://your-app.onrender.com") for that
use case. Pinging a local host is still useful for other things (e.g.
smoke-testing that your server is actually responding).
"""

import logging
import threading
import time
import urllib.error
import urllib.request

logger = logging.getLogger("staypresent")

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_ANY_HOSTS = {"0.0.0.0", "::", ""}


def _build_url(host: str, port: int = None, path: str = "/", https: bool = None) -> str:
    if not isinstance(host, str):
        raise TypeError(f"staypresent.ping()/cron(): 'host' must be a str, got {type(host).__name__}.")
    if port is not None and not isinstance(port, int):
        raise TypeError(f"staypresent.ping()/cron(): 'port' must be an int, got {type(port).__name__}.")
    if not isinstance(path, str):
        raise TypeError(f"staypresent.ping()/cron(): 'path' must be a str, got {type(path).__name__}.")
    if not host or not host.strip():
        raise ValueError("staypresent.ping()/cron(): 'host' is required.")
    host = host.strip()

    # Already a full URL (e.g. "https://google.com" or "http://1.2.3.4:9000/x")
    if "://" in host:
        if port is not None or (path and path != "/") or https is not None:
            logger.warning(
                "staypresent.ping()/cron(): 'host' is already a full URL (%s) - "
                "the 'port'/'path'/'https' arguments are ignored.",
                host,
            )
        return host

    # "0.0.0.0" / "::" is a *bind* address, not something you can send an
    # outgoing request to on every platform - treat it as "this machine".
    target_host = "127.0.0.1" if host in _ANY_HOSTS else host

    if port is not None and not (1 <= port <= 65535):
        raise ValueError(f"staypresent.ping()/cron(): port must be between 1 and 65535, got {port}.")

    if https is None:
        # Bare local addresses default to http (that's what staypresent.run()
        # itself serves); anything else is assumed to be a public https site.
        https = target_host not in _LOCAL_HOSTS

    scheme = "https" if https else "http"
    netloc = f"{target_host}:{port}" if port else target_host

    if not path.startswith("/"):
        path = "/" + path

    return f"{scheme}://{netloc}{path}"


def ping(host: str, port: int = None, path: str = "/", timeout: float = 10.0, https: bool = None) -> dict:
    """
    Make a single HTTP GET request right now and return the result. This
    call blocks until the request finishes (or times out) - for a repeating
    background version, use `staypresent.cron()` instead.

    Args:
        host: A bare host ("google.com"), a bind address ("0.0.0.0", treated
            as this machine), or a full URL ("https://google.com/status").
        port: Optional port to connect to. Ignored if `host` is already a
            full URL.
        path: Path to request. Ignored if `host` is already a full URL.
            Defaults to "/".
        timeout: Seconds to wait for a response before giving up.
        https: Force http (False) or https (True). If not set, bare local
            addresses (127.0.0.1/localhost/0.0.0.0) default to http and
            everything else defaults to https.

    Returns:
        A dict: {"url", "ok", "status_code", "elapsed", "error"}.
        `ok` is True only for 2xx/3xx responses.

    Example:
        result = staypresent.ping("https://my-app.onrender.com")
        if not result["ok"]:
            print("Ping failed:", result["error"])
    """
    if timeout <= 0:
        raise ValueError(f"staypresent.ping(): timeout must be > 0, got {timeout}.")

    url = _build_url(host, port, path, https)
    result = {"url": url, "ok": False, "status_code": None, "elapsed": None, "error": None}

    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "staypresent-ping"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result["status_code"] = response.status
            result["ok"] = 200 <= response.status < 400
    except urllib.error.HTTPError as exc:
        # Server responded, but with an error status (4xx/5xx) - still
        # "reachable", just not a healthy response.
        result["status_code"] = exc.code
        result["error"] = f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - DNS failures, timeouts, connection refused, etc.
        result["error"] = str(exc)
    finally:
        result["elapsed"] = round(time.monotonic() - started, 3)

    if result["ok"]:
        logger.debug("Ping to %s succeeded (status %s, %.3fs)", url, result["status_code"], result["elapsed"])
    else:
        logger.warning("Ping to %s failed: %s", url, result["error"])

    return result


class CronHandle:
    """
    Returned by `staypresent.cron()`. Lets you stop the background pinger
    if you need to; otherwise it just keeps running for the life of the
    process (it's a daemon thread, so it won't block your program from
    exiting on its own).
    """

    def __init__(self, thread: threading.Thread, stop_event: threading.Event, url: str):
        self._thread = thread
        self._stop_event = stop_event
        self._url = url

    def stop(self, wait: bool = False, timeout: float = None) -> None:
        """Stop the background pinger. Safe to call more than once."""
        if not self._stop_event.is_set():
            logger.info("Stopping cron pinger for %s", self._url)
        self._stop_event.set()
        if wait:
            self._thread.join(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._thread.is_alive() and not self._stop_event.is_set()


def cron(
    host: str,
    port: int = None,
    path: str = "/",
    interval: float = 300.0,
    repeat: bool = True,
    timeout: float = 10.0,
    https: bool = None,
    on_success=None,
    on_failure=None,
) -> CronHandle:
    """
    Start a background thread that pings `host` on a schedule, to keep your
    service "warm" and prevent free-tier hosting platforms from spinning it
    down due to inactivity. Non-blocking - call this before `staypresent.run()`.

    An initial ping fires immediately, then again every `interval` seconds.

    Args:
        host / port / path / timeout / https: Same as `staypresent.ping()`.
        interval: Seconds between pings. Default 300 (5 minutes) - frequent
            enough to keep most platforms' idle timers from tripping,
            without hammering the target with traffic.
        repeat: If True (default), keep pinging forever on `interval`. If
            False, ping once in the background and stop (for a one-off
            ping you don't need to wait on, use `staypresent.ping()`
            directly instead, which is simpler and synchronous).
        on_success: Optional callback `fn(result)` called after every
            successful ping. Exceptions inside it are logged, not raised.
        on_failure: Optional callback `fn(result)` called after every
            failed ping. Exceptions inside it are logged, not raised.

    Returns:
        A CronHandle - call `.stop()` on it to cancel future pings.

    Example:
        # Keep a Render/Railway free-tier deployment from sleeping.
        staypresent.cron("https://my-app.onrender.com", interval=240)
        staypresent.run("bot.py")
    """
    if interval <= 0:
        raise ValueError(f"staypresent.cron(): interval must be > 0, got {interval}.")
    if timeout <= 0:
        raise ValueError(f"staypresent.cron(): timeout must be > 0, got {timeout}.")

    # Validate the URL/host up front so bad input fails immediately, not
    # silently inside the background thread on the first tick.
    url = _build_url(host, port, path, https)

    stop_event = threading.Event()

    def _loop():
        while True:
            result = ping(host, port=port, path=path, timeout=timeout, https=https)

            callback = on_success if result["ok"] else on_failure
            if callback is not None:
                try:
                    callback(result)
                except Exception:  # noqa: BLE001 - a bad callback must not kill the cron thread
                    logger.exception("staypresent.cron(): callback raised an exception.")

            if not repeat or stop_event.wait(timeout=interval):
                break

    if repeat:
        interval_str = f"{interval:g}"
        logger.info("Started cron: pinging %s every %ss", url, interval_str)
    else:
        logger.info("Started cron: pinging %s once", url)

    thread = threading.Thread(target=_loop, daemon=True, name=f"staypresent-cron-{host}")
    thread.start()

    return CronHandle(thread, stop_event, url)