# StayPresent

A lightweight Python package that keeps your bot or script alive by running a small Flask web server alongside your application.

Perfect for platforms like **Render**, **Railway**, **Koyeb**, **Heroku**, or anywhere an HTTP server is required to keep your service active.

---

## Features

- 🚀 One-line setup
- 🌐 Built-in Flask web server
- 🤖 Runs your Python bot/script automatically
- 📄 Custom text response
- 📦 JSON response support
- ⚡ Lightweight and easy to use

---

## Installation

```bash
pip install staypresent
```

Or install locally:

```bash
pip install .
```

---

## Basic Usage

```python
import staypresent

staypresent.web.text("Made With ❤️")

staypresent.run("bot.py")
```

Open your browser:

```
http://localhost:8080
```

Response:

```
Made With ❤️
```

---

## JSON Response

```python
import staypresent

staypresent.web.json({
    "status": "online",
    "developer": "John",
    "message": "Made With Love ❤️"
})

staypresent.run("bot.py")
```

Response

```json
{
  "status": "online",
  "developer": "John",
  "message": "Made With Love ❤️"
}
```

---

## Custom Port

```python
import staypresent

staypresent.run(
    "bot.py",
    port=5000
)
```

---

## Custom Host

```python
staypresent.run(
    "bot.py",
    host="0.0.0.0"
)
```

---

## Complete Example

```python
import staypresent

staypresent.web.json({
    "status": "Running",
    "version": "1.0.0",
    "message": "Made With Love ❤️"
})

staypresent.run(
    "body.py",
    host="0.0.0.0",
    port=8080
)
```

---

## API

### Run your bot

```python
staypresent.run(
    bot_file,
    host="0.0.0.0",
    port=8080
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `bot_file` | str | Path to your Python script |
| `host` | str | Flask host |
| `port` | int | Flask port |

---

### Plain Text Response

```python
staypresent.web.text("Hello World")
```

---

### JSON Response

```python
staypresent.web.json({
    "hello": "world"
})
```

---

## Requirements

- Python 3.8+
- Flask

---

## Use Cases

- Telegram Bots
- Discord Bots
- Automation Scripts
- Background Workers
- Render Deployments
- Railway Deployments
- Koyeb Deployments
- Heroku Apps

---

## License

MIT License

---

Made with ❤️ using Python.