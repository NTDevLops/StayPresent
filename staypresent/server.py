from flask import Flask, jsonify
from . import web

app = Flask(__name__)


@app.route("/")
def home():
    data = web.get()

    if isinstance(data, (dict, list)):
        return jsonify(data)

    return str(data)