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
- [Self-Ping / Keep-Warm](#-self-ping--keep-warm)
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
* **Optional Self-Ping / Keep-Warm:** Periodically ping your own public URL in the background to prevent free-tier hosts from spinning your service down due to inactivity — fully opt-in, off by default.

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

## 📡 Self-Ping / Keep-Warm

Some free hosting tiers (Render, Railway, Replit, etc.) spin your service down after a period of inactivity, and only wake it back up on the next incoming request. `staypresent.ping()` and `staypresent.cron()` are a completely optional way to work around this by having your app periodically hit its own **public** URL — nothing runs unless you call one of them yourself.

> ⚠️ **Ping your public URL, not `127.0.0.1`/`0.0.0.0`.** Traffic that never leaves the machine doesn't count as activity to the hosting platform. `staypresent.cron("https://your-app.onrender.com")` works for that; `staypresent.cron("0.0.0.0", port=8080)` is only useful for locally smoke-testing that your own server is responding.

### `staypresent.ping(...)` — one-off check

Synchronous — fires a single HTTP GET and returns immediately with the result.

```python
result = staypresent.ping("https://my-app.onrender.com")
# -> {"url": "...", "ok": True, "status_code": 200, "elapsed": 0.31, "error": None}

if not result["ok"]:
    print("Something's wrong:", result["error"])
```

### `staypresent.cron(...)` — repeat on a schedule

Non-blocking — starts a background thread that calls `ping()` on a schedule. Call it before `staypresent.run()`.

```python
import staypresent

# Ping our own public URL every 4 minutes to keep the free-tier instance awake
staypresent.cron("https://my-app.onrender.com", interval=240)

staypresent.run("bot.py")
```

With callbacks, e.g. to log failures somewhere more visible:

```python
staypresent.cron(
    "https://my-app.onrender.com",
    interval=240,
    on_success=lambda r: print(f"warm ping ok ({r['elapsed']}s)"),
    on_failure=lambda r: print(f"warm ping failed: {r['error']}"),
)
```

`host` accepts a bare domain (`"my-app.onrender.com"`), a full URL (`"https://my-app.onrender.com/health"`), or a local bind address (`"0.0.0.0"`, treated as `127.0.0.1`) — same rules for both `ping()` and `cron()`.

`cron()` returns a handle if you ever need to cancel it:

```python
handle = staypresent.cron("https://my-app.onrender.com", interval=240)
...
handle.stop()          # stop pinging
handle.is_running       # True/False
```

Starting and stopping are both logged (`Started cron: pinging ... every 240s`), so you can confirm it's actually active. Pings run one at a time — if a ping takes a while to time out, the actual gap before the next one grows accordingly rather than piling up requests in parallel.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `host` | `str` | **Required** | Bare domain, full URL, or bind address (see above). |
| `port` | `int` | `None` | Port to connect to. Ignored if `host` is already a full URL. |
| `path` | `str` | `"/"` | Path to request. Ignored if `host` is already a full URL. |
| `timeout` | `float` | `10.0` | Seconds to wait for a response before treating the ping as failed. |
| `https` | `bool` | `None` | Force `http`/`https`. Auto-detected by default (local addresses → `http`, everything else → `https`). |
| `interval` *(cron only)* | `float` | `300.0` | Seconds between pings. |
| `repeat` *(cron only)* | `bool` | `True` | Keep pinging forever, or just once in the background. |
| `on_success` *(cron only)* | `callable` | `None` | `fn(result)` called after each successful ping. |
| `on_failure` *(cron only)* | `callable` | `None` | `fn(result)` called after each failed ping. |

---

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
| `bot_args` | `list` | `None` | Extra command-line arguments to pass to `bot_file` (e.g., `["--verbose"]`). Must be a list — a bare string like `"--flag"` raises a clear error instead of silently exploding into individual characters. |
| `env` | `dict` | `None` | Extra environment variables for the bot process. Merges over the current environment. |

> **Note:** `port`, `threads`, `max_restarts`, `restart_delay`, and `restart_reset_after` are validated up front — passing an invalid value (e.g. `threads=0`, a negative `port`) raises a `ValueError` immediately instead of failing silently or deep inside `waitress`.

### Crash Recovery Details

StayPresent automatically monitors your bot process. If it exits with a non-zero exit code, StayPresent restarts it based on your configuration:

* **Clean Exits:** An exit code of `0` is considered intentional and will *not* trigger a restart.
* **Manual Shutdowns:** Stopping StayPresent via `Ctrl+C` (SIGINT) or `SIGTERM` shuts down both the server and the bot cleanly.
* **Smart Counters:** The `max_restarts` limit applies to *consecutive* crashes. If your bot runs successfully for the duration of `restart_reset_after` (default 60 seconds), the crash counter resets.
* **Non-Zero Exit on Giving Up:** If the bot ultimately fails to stay up — restarts disabled and it crashed, or `max_restarts` was exhausted — `staypresent.run()` exits the whole process with the bot's last exit code instead of returning normally. This lets a hosting platform's own restart-on-crash policy (Render, Railway, Docker, systemd, etc.) kick in as a last resort, instead of the process quietly exiting `0` as if nothing went wrong.

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
