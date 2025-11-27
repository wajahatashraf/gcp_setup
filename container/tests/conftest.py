# conftest.py
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import json
from google.cloud import storage

# Load bucket name from gcp_created_resources.json
RESOURCE_LOG_FILE = "/app/gcp_created_resources.json"
def get_bucket_name():
    if os.path.exists(RESOURCE_LOG_FILE):
        with open(RESOURCE_LOG_FILE) as f:
            data = json.load(f)
        return data.get("buckets", [None])[0]
    return None

@pytest.fixture(scope="function")
def driver(request):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()

# Hook to take screenshot and embed in HTML report on failure
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.when == "call" and rep.failed:
        driver = item.funcargs.get("driver")
        if driver:
            screenshots_dir = "/app/screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            screenshot_file = os.path.join(screenshots_dir, f"{item.name}.png")
            driver.save_screenshot(screenshot_file)

            # Attach screenshot to pytest-html report
            if "pytest_html" in item.config.pluginmanager.list_name_plugin():
                from pytest_html import extras
                extra = getattr(rep, "extra", [])
                extra.append(extras.image(screenshot_file))
                rep.extra = extra

# Hook to upload report after the entire test session
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    report_file = "/app/report.html"

    # Wait for pytest-html to finish writing final report
    import time
    time.sleep(1)

    if not os.path.exists(report_file):
        print("Report not found, skipping upload.")
        return

    bucket_name = get_bucket_name()
    if not bucket_name:
        print("No GCP bucket found. Skipping upload.")
        return

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Upload FINAL HTML report
        blob = bucket.blob("report.html")
        blob.upload_from_filename(report_file)
        print(f"Uploaded pytest HTML report to gs://{bucket_name}/report.html")

        # Upload screenshots
        screenshots_dir = "/app/screenshots"
        if os.path.exists(screenshots_dir):
            for file in os.listdir(screenshots_dir):
                if file.endswith(".png"):
                    screenshot_path = os.path.join(screenshots_dir, file)
                    bucket.blob(f"screenshots/{file}").upload_from_filename(screenshot_path)
                    print(f"Uploaded screenshot {file} to gs://{bucket_name}/screenshots/{file}")

    except Exception as e:
        print("Failed to upload report:", e)

