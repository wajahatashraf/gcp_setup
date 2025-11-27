from flask import Flask, jsonify
import requests
import socket
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    """
    Fetch https://example.com and return an excerpt of the HTML plus some container metadata
    to prove the code executed in the deployed container.
    """
    try:
        resp = requests.get("https://example.com", timeout=10)
        body = resp.text
        status_code = resp.status_code
    except Exception as e:
        body = f"ERROR_FETCHING: {e}"
        status_code = 500

    info = {
        "service_env": {
            "K_SERVICE": os.environ.get("K_SERVICE"),
            "K_REVISION": os.environ.get("K_REVISION"),
            "GCP_PROJECT": os.environ.get("GCP_PROJECT"),
            "HOSTNAME": socket.gethostname()
        },
        "example_status": status_code,
        # return only the first 2000 chars so response stays small
        "example_excerpt": body[:2000]
    }
    return jsonify(info), status_code

if __name__ == "__main__":
    # local debug
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
