<h1 align="center">StayPresent</h1>
<p align="center">
  <a href="https://github.com/NTDevLops/StayPresent/">
    <img src="https://i.ibb.co/WNzhLjQn/Stay-Present-1.png" alt="StayPresent Logo" height="150">
  </a>
</p>
<p align="center">
  <a href="https://pypi.org/project/staypresent/"><img src="https://img.shields.io/pypi/v/staypresent.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/staypresent/"><img src="https://img.shields.io/pypi/pyversions/staypresent.svg" alt="Python versions"></a>
  <a href="https://github.com/NTDevLops/StayPresent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT"></a>
</p>

### 🛖 About

A lightweight Python package designed to keep your bots and background scripts alive by running a dedicated Flask web server alongside your main application.

Perfect for deploying on platforms like **Render**, **Railway**, **Koyeb**, **Heroku**, or any host that requires an active HTTP port to keep your service running.

---

## Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage Guide](#-usage-guide)
- [API Reference](#️-api-reference)
- [Logging](#-logging)
- [Requirements](#-requirements)
- [Use Cases](#-use-cases)

---

## 🚀 Features

* **Zero-Friction Setup:** Get running with just one line of code.
* **Production-Ready by Default:** Automatically detects and uses `waitress` to avoid Flask's "development server" warnings.
* **Auto-Restarts & Crash Recovery:** Automatically respawns your bot process if it crashes, complete with customizable delays and max-restart limits.
* **Flexible Responses:** Serve custom plain text, JSON (default), or full HTML templates.
* **Static Asset Serving:** Automatically serves CSS, JS, and images located next to your HTML templates.
* **Advanced Control:** Easily pass custom command-line arguments and environment variables directly to your bot process.
* **Fail-Safe Logging:** Logs a clear error if the underlying web server dies unexpectedly.

---

## 📦 Installation

Install via pip:

```bash
pip install staypresent

```

**Recommended for Production:**
To automatically use a production WSGI server and suppress Flask development warnings, install the `prod` extra. This pulls in [`waitress`](https://pypi.org/project/waitress/).

```bash
pip install staypresent[prod]

```

*(Note: If `waitress` isn't installed, StayPresent gracefully falls back to Flask's built-in development server and logs a one-time warning.)*

---

## 💻 Usage Guide

### Basic Usage (Text Response)

```python
import staypresent

staypresent.web.text("Made With ❤️")
staypresent.run("bot.py")

```

*Navigating to `http://localhost:8080` will return plain text: `Made With ❤️*`

> **Note:** If you don't configure a response, StayPresent defaults to a JSON response of `{"message": "I'm Present"}` at the root `/` route.

### JSON Response

A safe copy of your dictionary is stored. If you need to update live data, just call `staypresent.web.json()` again.

```python
import staypresent

staypresent.web.json({
    "status": "online",
    "developer": "John",
    "message": "Made With Love ❤️"
})

staypresent.run("bot.py")

```

### HTML Response (with Static Files)

Serve a full HTML page. The file is read fresh on every request, allowing you to edit your HTML on disk without restarting your bot.

```python
import staypresent

# The path is validated immediately and will raise a FileNotFoundError if missing
staypresent.web.html("template/index.html")
staypresent.run("bot.py")

```

**Serving Static Assets:**
Any files (CSS, JS, images) in the same directory as your HTML file are automatically served. Path traversal is strictly blocked for security.

```html
<!-- template/index.html -->
<!DOCTYPE html>
<html>
  <head>
    <title>My Bot</title>
    <link rel="stylesheet" href="style.css">
  </head>
  <body>
    <h1>I'm alive!</h1>
    <img src="images/logo.png">
  </body>
</html>

```

### Custom Host, Port, and Threads (Complete Example)

```python
import staypresent

staypresent.web.json({
    "status": "Running",
    "version": "1.0.0"
})

staypresent.run(
    "bot.py",
    host="0.0.0.0",
    port=8080,
    threads=8  # Increase if receiving real web traffic
)

```

---

## ⚙️ API Reference

### `staypresent.run(...)`

Launch your bot script alongside the web server.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `bot_file` | `str` | **Required** | Path to the Python script to run alongside the server. |
| `host` | `str` | `"0.0.0.0"` | Host to bind the web server to. |
| `port` | `int` | `8080` | Port to bind the web server to. |
| `production` | `bool` | `True` | Uses `waitress` if installed. Set to `False` to force the Flask dev server. |
| `threads` | `int` | `4` | Number of worker threads for `waitress`. Increase this if serving real web traffic rather than just keep-alive pings. *(Requires `production=True` and `waitress`)*. |
| `restart_on_crash` | `bool` | `True` | Relaunch the bot process if it exits with a non-zero exit code. |
| `max_restarts` | `int` | `5` | Maximum restart attempts after a crash before giving up. |
| `restart_delay` | `float` | `2.0` | Seconds to wait before relaunching the bot process after a crash. |
| `restart_reset_after` | `float` | `60.0` | Seconds the bot must stay alive to reset the consecutive crash counter back to 0. |
| `bot_args` | `list` | `None` | Extra command-line arguments to pass to `bot_file` (e.g., `["--verbose"]`). |
| `env` | `dict` | `None` | Extra environment variables for the bot process. Merges over the current environment. |

> **Note:** `port`, `threads`, `max_restarts`, `restart_delay`, and `restart_reset_after` are validated up front — passing an invalid value (e.g. `threads=0`, a negative `port`) raises a `ValueError` immediately instead of failing silently or deep inside `waitress`.

### Crash Recovery Details

StayPresent automatically monitors your bot process. If it exits with a non-zero exit code, StayPresent restarts it based on your configuration:

* **Clean Exits:** An exit code of `0` is considered intentional and will *not* trigger a restart.
* **Manual Shutdowns:** Stopping StayPresent via `Ctrl+C` (SIGINT) or `SIGTERM` shuts down both the server and the bot cleanly.
* **Smart Counters:** The `max_restarts` limit applies to *consecutive* crashes. If your bot runs successfully for the duration of `restart_reset_after` (default 60 seconds), the crash counter resets.

### Built-in Health Check

A dedicated `/health` endpoint is automatically exposed, returning `{"status": "ok"}`. This is incredibly useful for platform pingers and uptime monitors that require a dedicated health-check path separate from your root `/` response.

### Inspecting the Current Response

```python
staypresent.web.get()
# -> {"type": "json", "value": {"message": "I'm Present"}}
```

Returns whatever `text()` / `json()` / `html()` last configured, as `{"type": ..., "value": ...}`. Mainly useful for debugging or unit-testing your own code around StayPresent.

---

## 📝 Logging

StayPresent logs to its own `"staypresent"` logger, not the root logger — it never calls `logging.basicConfig()` globally. This means it won't clobber, duplicate, or reformat logging you've already set up elsewhere in your script for unrelated loggers.

To change the log level or format, configure it like any other logger:

```python
import logging
logging.getLogger("staypresent").setLevel(logging.WARNING)
```

---

## 🛠 Requirements

* Python 3.8+
* Flask
* `waitress` *(optional, but highly recommended for production)*

## 💡 Use Cases

* Discord & Telegram Bots
* Background Workers & Automation Scripts
* Keeping deployments alive on Render, Railway, Koyeb, and Heroku

---

**License:** MIT License

*Made with ❤️ using Python.*
