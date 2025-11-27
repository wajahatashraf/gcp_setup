from flask import Flask, send_file
import subprocess
import os

app = Flask(__name__)

REPORT_PATH = "/app/report.html"

@app.route("/")
def index():
    return "Container is running. Visit /run-tests to run pytest."

@app.route("/run-tests")
def run_tests():
    # Run pytest with HTML report
    result = subprocess.run(
        ["pytest", "--html=report.html", "--self-contained-html", "tests/"],
        cwd="/app",
        capture_output=True,
        text=True
    )
    # Return pytest stdout for visibility
    return f"<pre>{result.stdout}\n\n{result.stderr}</pre>"

@app.route("/report")
def report():
    # Serve generated report if exists
    if os.path.exists(REPORT_PATH):
        return send_file(REPORT_PATH)
    return "Report not found. Run /run-tests first."
