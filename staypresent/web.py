import copy
import os
import threading
from typing import Any

_lock = threading.Lock()

# Internal response state.
# type: "json" | "text" | "html"
# value:
#   - for "json": a JSON-serializable dict/list
#   - for "text": a str
#   - for "html": the filesystem path to an HTML file (read fresh on every request)
_state = {
    "type": "json",
    "value": {"message": "I'm Present"},
}


def text(message: str) -> None:
    """Set a plain-text response for the web server to return."""
    global _state
    with _lock:
        _state = {"type": "text", "value": str(message)}


def json(data: Any) -> None:
    """
    Set a JSON-serializable response (dict/list) for the web server to return.

    A deep copy of `data` is stored, so mutating the object you passed in
    afterwards (e.g. `my_dict["x"] = 1`) will NOT change the live response.
    Call `staypresent.web.json(...)` again if you want to update it.
    """
    global _state
    with _lock:
        _state = {"type": "json", "value": copy.deepcopy(data)}


def html(file_path: str) -> None:
    """
    Serve the content of an HTML file as the web response.

    The file is read fresh on every incoming request, so you can edit the
    file on disk (e.g. a template) without restarting the bot.

    Example:
        staypresent.web.html("template/index.html")

    Raises:
        FileNotFoundError: if `file_path` does not exist at call time.
    """
    global _state
    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"staypresent.web.html(): file '{file_path}' does not exist or is not a file."
        )

    with _lock:
        _state = {"type": "html", "value": os.path.abspath(file_path)}


def get() -> dict:
    """Return the currently configured response state as {'type': ..., 'value': ...}."""
    with _lock:
        return dict(_state)
