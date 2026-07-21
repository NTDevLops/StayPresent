import os

from flask import Flask, jsonify, Response, send_from_directory, abort
from werkzeug.exceptions import NotFound

from . import web


# static_folder=None disables Flask's own built-in "/static/<path:filename>"
# route. StayPresent doesn't ship any static assets of its own - but if left
# enabled, that built-in route silently shadows our own static_files() route
# below for any request path starting with "static/", which is the single
# most common naming convention for an assets folder (e.g. an HTML file that
# links to "static/style.css" or "static/logo.png" right next to it). With
# the built-in route active, those requests 404 against Flask's nonexistent
# default static folder instead of ever reaching static_files(), which knows
# how to correctly serve them from next to the user's HTML file.
app = Flask(__name__, static_folder=None)


@app.route("/")
def home():
    state = web.get()
    response_type = state.get("type")
    value = state.get("value")

    if response_type == "html":
        try:
            with open(value, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            return jsonify({"error": f"Could not read HTML file: {exc}"}), 500
        return Response(content, mimetype="text/html")

    if response_type == "json":
        try:
            return jsonify(value)
        except TypeError as exc:
            return jsonify({"error": f"Could not serialize JSON response: {exc}"}), 500

    if response_type == "text":
        return Response(str(value), mimetype="text/plain")

    # Fallback for any unexpected/legacy state shape.
    if isinstance(value, (dict, list)):
        return jsonify(value)
    return str(value)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/<path:filename>")
def static_files(filename):
    """
    Serve any file that lives alongside the HTML file passed to
    `staypresent.web.html()` (e.g. style.css, script.js, images/logo.png).

    Only active when the current response is an HTML response - if no HTML
    file has been set (or a JSON/text response is active instead), this
    route 404s just like any other unknown path would.
    """
    state = web.get()
    if state.get("type") != "html":
        abort(404)

    directory = os.path.dirname(state.get("value"))

    try:
        # send_from_directory safely resolves `filename` against `directory`
        # and refuses to serve anything that escapes it (no path traversal).
        return send_from_directory(directory, filename)
    except NotFound:
        abort(404)
