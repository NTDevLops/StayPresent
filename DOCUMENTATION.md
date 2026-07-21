# StayPresent Documentation

**StayPresent** is a lightweight Python package designed to manage the lifecycle of background scripts and bot applications. It runs a Flask-powered HTTP server alongside your application, with optional production serving through Waitress, making it easy to deploy services on platforms that require an active HTTP port (e.g., Render, Railway, Koyeb, Heroku).

---

## 1. Requirements

* **Python** 3.8+
* **Flask**
* **waitress** (optional, but highly recommended for production)

---

## 2. Getting Started

### Installation

Install the package via standard package managers.

**Standard Installation:**

```bash
pip install staypresent

```

**Production Installation (Recommended):**

To suppress development server warnings and utilize a production-grade WSGI server, install the `prod` extra. This automatically provisions `waitress`.

```bash
pip install staypresent[prod]

```

---

## 3. Web Server Configuration (`staypresent.web`)

The `staypresent.web` module dictates the HTTP response served by the background web server at the root (`/`) endpoint. If unconfigured, it defaults to a JSON response: `{"message": "I'm Present"}`.

**Basic Usage Example:**

```python
import staypresent

staypresent.web.json({
    "status": "running"
})

staypresent.run("bot.py")

```

### Text Responses

Returns a `text/plain` response.

```python
import staypresent

staypresent.web.text("Service Operational")

```

### JSON Responses

Returns an `application/json` response. The dictionary is safely copied. Subsequent calls will update the live response data.

```python
import staypresent

staypresent.web.json({
    "status": "online",
    "version": "1.2.0"
})

```

### HTML & Static Assets

Reads and serves an HTML file on every request. This allows for dynamic, on-disk updates without restarting the Python process.

```python
import staypresent

staypresent.web.html("templates/index.html")

```

> **Note:** Any static assets (CSS, JS, images) located in the same directory as the target HTML file are automatically served. Path traversal is strictly prohibited by internal security checks.

### State Inspection

To retrieve the currently configured response payload for debugging or testing:

```python
current_state = staypresent.web.get()
# Returns: {"type": "json", "value": {"status": "online", ...}}

```

---

## 4. Process Execution (`staypresent.run`)

The `run` function is the primary entry point. It spawns the web server and concurrently executes your target Python script.

```python
import staypresent

staypresent.run(
    "bot.py",
    host="0.0.0.0",
    port=8080,
    threads=8
)

```

### Execution Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `bot_file` | `str` | **Required** | Target Python script to execute concurrently. |
| `host` | `str` | `"0.0.0.0"` | Network interface to bind the web server. |
| `port` | `int` | `8080` | Port allocation for the web server. |
| `production` | `bool` | `True` | Utilizes `waitress` if available. Set to `False` to force Flask's dev server. |
| `threads` | `int` | `4` | Worker threads for `waitress` (requires `production=True`). |
| `restart_on_crash` | `bool` | `True` | Relaunches the bot upon a non-zero exit code. |
| `max_restarts` | `int` | `5` | Maximum consecutive restart attempts. |
| `restart_delay` | `float` | `2.0` | Seconds to wait before process respawn. |
| `restart_reset_after` | `float` | `60.0` | Seconds of continuous uptime required to reset the crash counter to zero. |
| `bot_args` | `list` | `None` | CLI arguments to pass to the target script (e.g., `["--verbose"]`). |
| `env` | `dict` | `None` | Environment variables injected into the target process. |

### Crash Recovery Protocol

StayPresent strictly monitors the subprocess lifecycle:

* **Clean Exits:** An exit code of `0` is treated as an intentional shutdown and bypasses restart logic.
* **Signals:** Interruptions (`SIGINT`/`Ctrl+C`, `SIGTERM`) initiate a clean teardown of both the server and the bot.
* **Terminal Failures:** If `max_restarts` is exhausted, or if restarts are disabled and a crash occurs, `staypresent.run()` exits the main process with the bot's final non-zero exit code. This ensures platform-level orchestrators (Docker, systemd) correctly interpret the failure state.

---

## 5. Keep-Warm Module (`staypresent.ping` and `staypresent.cron`)

Many platform-as-a-service (PaaS) providers hibernate instances after periods of inactivity. The Keep-Warm module provides an internal mechanism to generate synthetic traffic against your application's public URL.

> **Crucial Setup:** You must target your application's **publicly routable URL**. Pinging `0.0.0.0` or `127.0.0.1` will not prevent platform hibernation.

> **Note:** Keep-Warm only generates HTTP activity. It does not prevent platform policies that explicitly suspend or terminate applications (such as hard usage limits or strict free-tier quotas).

### Synchronous Pings (`staypresent.ping`)

Executes an immediate, blocking HTTP GET request.

```python
result = staypresent.ping("https://api.yourdomain.com")

```

### Scheduled Pings (`staypresent.cron`)

Spawns an isolated background thread to execute periodic requests. This must be invoked prior to `staypresent.run()`.

```python
import staypresent

# Ping the public endpoint every 4 minutes
staypresent.cron("https://api.yourdomain.com", interval=240.0)

staypresent.run("bot.py")

```

### Cron Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `host` | `str` | **Required** | Target domain, full URL, or bind address. |
| `port` | `int` | `None` | Target port. Ignored if a full URL is provided. |
| `path` | `str` | `"/"` | Target endpoint path. Ignored if a full URL is provided. |
| `timeout` | `float` | `10.0` | HTTP timeout threshold in seconds. |
| `https` | `bool` | `None` | Forces protocol. Auto-detected if unassigned. |
| `interval` | `float` | `300.0` | Frequency of requests in seconds. |
| `repeat` | `bool` | `True` | Dictates continuous execution vs. a single background execution. |
| `on_success` | `callable` | `None` | Callback function invoked post-successful ping. |
| `on_failure` | `callable` | `None` | Callback function invoked upon request timeout or failure. |

---

## 6. Observability and Health

### Built-In Health Check

StayPresent automatically provisions a dedicated `/health` endpoint. This returns a fixed `{"status": "ok"}` payload, providing a clean separation between your configured root response and internal platform uptime monitoring.

### Logging Configuration

StayPresent isolates its telemetry within a dedicated `"staypresent"` logger. It will not mutate the root logger or interfere with existing logging configurations within your application.

To adjust verbosity:

```python
import logging
logging.getLogger("staypresent").setLevel(logging.INFO)

```

---

## 7. API Reference

### `staypresent.web`

* **`web.text(content: str)`** – Configures the root route to return plain text.
* **`web.json(data: dict)`** – Configures the root route to return a JSON payload.
* **`web.html(filepath: str)`** – Configures the root route to serve an HTML template (alongside neighboring static files).
* **`web.get()`** – Returns the currently configured response state as a dictionary.

### `staypresent`

* **`run(bot_file: str, ...)`** – Starts the HTTP server and manages the application process lifecycle.
* **`ping(host: str, ...)`** – Sends a synchronous HTTP request.
* **`cron(host: str, ...)`** – Runs scheduled background keep-warm requests.

---

## 8. Deployment Examples

StayPresent is built specifically to seamlessly handle port-binding requirements on modern PaaS environments. Ensure your `main.py` (or equivalent entry point) utilizes `staypresent.run()`.

### Render

Render assigns the listening port through the `PORT` environment variable. Configure your application to use that value when available.

```python
import os
import staypresent

staypresent.run(
    "bot.py",
    port=int(os.getenv("PORT", 8080))
)

```

**Start Command:**

```bash
python main.py

```

### Railway

Railway automatically detects Python applications and assigns a `$PORT`. The execution logic is identical to Render.

```python
import os
import staypresent

staypresent.run(
    "bot.py",
    port=int(os.getenv("PORT", 8080))
)

```

**Start Command:**

```bash
python main.py

```

---

## 9. Frequently Asked Questions (FAQ)

### Does StayPresent replace Flask?

No. StayPresent does not replace Flask. It provides a simplified wrapper around Flask-based hosting requirements for background scripts and bots, handling HTTP server setup, process management, and production WSGI configuration out of the box.

---

### Does StayPresent host my application?

No. StayPresent does not provide hosting infrastructure. It manages the local web server and application lifecycle **inside** your existing hosting environment. You still need to deploy your project on platforms like Render, Railway, Koyeb, Heroku, a VPS, or Docker.

---

### Why do I need StayPresent if my bot already works locally?

Many cloud hosting platforms require applications to listen on an HTTP port to verify health. Background bots and workers usually do not expose a web server, causing platforms to declare them unhealthy and shut them down. StayPresent solves this by running a lightweight HTTP server alongside your bot.

---

### Can StayPresent run Discord bots, Telegram bots, or automation scripts?

Yes. StayPresent is designed for long-running Python processes such as:

* Discord bots
* Telegram bots
* Web scrapers
* Automation workers
* Background jobs
* Scheduled scripts
* API polling services

---

### Does StayPresent keep my application online forever?

No. StayPresent can generate optional keep-warm HTTP requests via `cron()`, but it cannot bypass hosting provider limitations, account restrictions, resource quotas, or forced shutdown policies. Final availability always depends on your hosting provider.

---

### Does `staypresent.cron()` work with `localhost`?

No. Keep-warm requests must target your application's **public URL**.

```python
# ✅ Correct:
staypresent.cron(
    "https://my-app.onrender.com",
    interval=240
)

# ❌ Incorrect:
staypresent.cron(
    "http://127.0.0.1:8080",
    interval=240
)

```

Requests sent to `127.0.0.1` or `localhost` do not generate external inbound traffic and will not reset platform inactivity sleep timers.

---

### Is Waitress required?

No. Waitress is optional. If installed, StayPresent automatically uses Waitress as a production-grade WSGI server. Otherwise, it safely falls back to Flask's built-in development server.

For production environments, installing the `prod` extra is recommended:

```bash
pip install staypresent[prod]

```

---

### What happens if my bot crashes?

By default, StayPresent monitors your bot subprocess and attempts automatic recovery.

Features include:

* Automatic restarts upon non-zero exit codes
* Configurable restart limits (`max_restarts`)
* Custom restart delays (`restart_delay`)
* Automatic crash counter resets after sustained uptime (`restart_reset_after`)

```python
staypresent.run(
    "bot.py",
    restart_on_crash=True,
    max_restarts=5
)

```

---

### Can I disable automatic restarts?

Yes. Set `restart_on_crash=False`. When disabled, any subprocess crash will cause StayPresent to exit immediately with the bot's original exit code.

```python
staypresent.run(
    "bot.py",
    restart_on_crash=False
)

```

---

### Does StayPresent affect my existing logging system?

No. StayPresent isolates all of its logging under a dedicated logger namespace:

```python
import logging
logging.getLogger("staypresent")

```

It does not modify root logger handlers or invoke `logging.basicConfig()`.

---

### Can I serve my own website or dashboard with StayPresent?

Yes. StayPresent supports serving plain text, JSON payloads, static HTML templates, and associated static assets (CSS, JS, images).

```python
staypresent.web.html("templates/dashboard.html")

```

---

### Is StayPresent production ready?

Yes. StayPresent is designed specifically for production deployment scenarios where background processes require HTTP health endpoints, process supervision, crash recovery, and WSGI serving. However, overall reliability still depends on application code quality and hosting provider limits.

---

### Does StayPresent support Docker?

Yes. StayPresent works inside Docker containers like any standard Python package.

```dockerfile
CMD ["python", "main.py"]

```

Your `main.py` entry point can use `staypresent.run()` to expose the required HTTP port while managing the background worker process.

---

### What Python versions are supported?

StayPresent supports Python 3.8 and newer:

* Python 3.8
* Python 3.9
* Python 3.10
* Python 3.11
* Python 3.12+

---

### Is StayPresent free to use?

Yes. StayPresent is open-source software released under the **MIT License**. It can be freely used, modified, and distributed in both personal and commercial projects.

---

## 10. License

StayPresent is released under the **MIT License**.