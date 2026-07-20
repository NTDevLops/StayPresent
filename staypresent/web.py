import threading
from typing import Any, Union

_lock = threading.Lock()
_response: Union[str, dict, list] = "StayPresent"


def text(message: str) -> None:
    """Set a plain-text response for the web server to return."""
    global _response
    with _lock:
        _response = str(message)


def json(data: Any) -> None:
    """Set a JSON-serializable response (dict/list) for the web server to return."""
    global _response
    with _lock:
        _response = data


def get() -> Union[str, dict, list]:
    """Return whatever response is currently configured."""
    with _lock:
        return _response
