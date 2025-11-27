import os
import json
import uuid
import argparse
import subprocess
import shutil
import sys
import time
import platform
from google.cloud import storage
from google.oauth2 import service_account

# ------------------------------------------------------------
# FIX FOR WINDOWS: Ensure Python can find gcloud.exe / gcloud.cmd
# ------------------------------------------------------------
# Try automatic detection
gcloud_cmd = shutil.which("gcloud") or shutil.which("gcloud.cmd")
if gcloud_cmd:
    gcloud_bin = os.path.dirname(gcloud_cmd)
    if gcloud_bin not in os.environ["PATH"]:
        os.environ["PATH"] += ";" + gcloud_bin
else:
    # Fallback manual path
    fallback_path = r"C:\Users\user\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
    if fallback_path not in os.environ["PATH"]:
        os.environ["PATH"] += ";" + fallback_path
# ------------------------------------------------------------

CONTAINER_DIR = os.path.join(os.path.abspath("."), "container")

# Ensure container/ exists
if not os.path.isdir(CONTAINER_DIR):
    raise RuntimeError(f"container/ folder not found at: {CONTAINER_DIR}")

# Write resource file INSIDE container folder
RESOURCE_LOG_FILE = os.path.join(CONTAINER_DIR, "gcp_created_resources.json")

# ------------------------- LOAD CREDENTIALS -------------------------
def load_credentials(json_path):
    """Load GCP credentials from a JSON file (required)."""
    if not json_path or not os.path.exists(json_path):
        raise FileNotFoundError(f"Service account JSON not found: {json_path}")
    creds = service_account.Credentials.from_service_account_file(json_path)
    return creds

# ------------------------- GCloud helpers -------------------------
def run_cmd(cmd, env=None, check=True, capture_output=False):
    """Run a shell command and return (returncode, stdout). Raises on check=True and rc!=0."""
    # On Windows, replace 'gcloud' with full path to gcloud.cmd
    if platform.system() == "Windows" and cmd[0] == "gcloud":
        gcloud_cmd_path = shutil.which("gcloud.cmd")
        if gcloud_cmd_path:
            cmd[0] = gcloud_cmd_path

    print("->", " ".join(cmd))
    proc = subprocess.run(cmd, env=env, capture_output=capture_output, text=True)
    if check and proc.returncode != 0:
        print("Command failed:", proc.returncode)
        print("stdout:", proc.stdout)
        print("stderr:", proc.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return proc

def gcloud_auth_activate(sa_json_path, project_id):
    """Activate gcloud using the provided service account JSON and set project."""
    run_cmd(["gcloud", "auth", "activate-service-account", "--key-file", sa_json_path])
    run_cmd(["gcloud", "config", "set", "project", project_id])

def enable_apis(project_id, apis):
    """Enable required APIs using gcloud."""
    for api in apis:
        run_cmd(["gcloud", "services", "enable", api, "--project", project_id])

# ------------------------- BUILD & DEPLOY -------------------------
def build_and_deploy_cloud_run(sa_json_path, project_id,
                               service_name="example-fetcher",
                               image_name=None,
                               region="us-central1"):
    """
    Build container with Cloud Build and deploy to Cloud Run.
    Returns the service URL.
    """
    if image_name is None:
        image_name = f"{service_name}-{uuid.uuid4().hex[:8]}"

    image_tag = f"gcr.io/{project_id}/{image_name}"

    # Make sure container/ exists with Dockerfile + main.py
    container_dir = os.path.join(os.path.abspath("."), "container")
    if not os.path.exists(container_dir):
        raise FileNotFoundError(f"Directory {container_dir} not found. Make sure container/ exists with Dockerfile and main.py")

    # Authenticate gcloud and enable APIs
    gcloud_auth_activate(sa_json_path, project_id)
    enable_apis(project_id, ["cloudbuild.googleapis.com", "run.googleapis.com", "containerregistry.googleapis.com"])

    # Build & push image
    run_cmd(["gcloud", "builds", "submit", container_dir, "--tag", image_tag, "--project", project_id])

    # Deploy to Cloud Run
    run_cmd([
        "gcloud", "run", "deploy", service_name,
        "--image", image_tag,
        "--platform", "managed",
        "--region", region,
        "--allow-unauthenticated",
        "--project", project_id
    ])

    # Get service URL
    proc = run_cmd([
        "gcloud", "run", "services", "describe", service_name,
        "--platform", "managed", "--region", region,
        "--format", "value(status.url)",
        "--project", project_id
    ], capture_output=True)
    service_url = proc.stdout.strip()
    print(f"Deployed Cloud Run service URL: {service_url}")
    return service_url

def verify_service_and_fetch(service_url, timeout=20):
    """Call the service URL and print returned JSON excerpt."""
    import requests
    try:
        r = requests.get(service_url, timeout=timeout)
        print("Service returned status", r.status_code)
        try:
            j = r.json()
            print("Response JSON keys:", list(j.keys()))
            if "example_excerpt" in j:
                excerpt = j["example_excerpt"]
                print("Example.com excerpt:", excerpt[:500])
        except Exception:
            print("Response body (first 1000 chars):", r.text[:1000])
    except Exception as e:
        print("Failed to call service URL:", e)

# ------------------------- INIT -------------------------
def gcp_init(creds):
    """Check GCP credentials by listing buckets."""
    try:
        client = storage.Client(credentials=creds)
        buckets = list(client.list_buckets())
        print(f"GCP Access Verified. Found {len(buckets)} buckets.")
    except Exception as e:
        print("GCP Init failed:", e)

# ------------------------- SETUP -------------------------
def gcp_setup(sa_json_path, project_id, service_name="example-fetcher"):
    """Create resources in GCP, deploy container, verify example.com fetch."""
    creds = load_credentials(sa_json_path)
    client = storage.Client(credentials=creds, project=project_id)

    # Create bucket
    bucket_name = f"automation-bucket-{uuid.uuid4().hex[:8]}"
    bucket = client.bucket(bucket_name)
    bucket = client.create_bucket(bucket, location="US")  # fixed deprecation warning
    print(f"Created bucket: {bucket.name}")

    # Track resources
    created_resources = {"buckets": [bucket.name], "cloud_run_service": service_name}
    with open(RESOURCE_LOG_FILE, "w") as f:
        json.dump(created_resources, f)

    # Build/deploy container
    print("Building and deploying container to Cloud Run. This uses gcloud & Cloud Build.")
    try:
        service_url = build_and_deploy_cloud_run(sa_json_path, project_id, service_name=service_name)
        time.sleep(5)
        print("Verifying deployed service by calling it and fetching example.com...")
        verify_service_and_fetch(service_url)

        # Save URL to log
        created_resources["cloud_run_url"] = service_url
        with open(RESOURCE_LOG_FILE, "w") as f:
            json.dump(created_resources, f)
    except Exception as e:
        print("Build/deploy/verify failed:", e)
        print("You can try to run the build/deploy commands manually and inspect Cloud Run in console.")

    print("GCP Setup Complete.")

# ------------------------- RESET -------------------------
def gcp_reset(sa_json_path, project_id):
    """Delete resources created by this script."""
    creds = load_credentials(sa_json_path)
    client = storage.Client(credentials=creds, project=project_id)

    if not os.path.exists(RESOURCE_LOG_FILE):
        print("No resource log found. Nothing to delete.")
        return

    with open(RESOURCE_LOG_FILE) as f:
        created_resources = json.load(f)

    # Delete buckets
    for bucket_name in created_resources.get("buckets", []):
        bucket = client.bucket(bucket_name)
        try:
            bucket.delete(force=True)
            print(f"Deleted bucket: {bucket_name}")
        except Exception as e:
            print(f"Failed to delete bucket {bucket_name}: {e}")

    # Delete Cloud Run service
    service_name = created_resources.get("cloud_run_service")
    if service_name:
        try:
            run_cmd([
                "gcloud", "run", "services", "delete", service_name,
                "--platform", "managed", "--region", "us-central1", "--quiet", "--project", project_id
            ])
            print(f"Deleted Cloud Run service: {service_name}")
        except Exception as e:
            print(f"Failed to delete Cloud Run service {service_name}: {e}")

    os.remove(RESOURCE_LOG_FILE)
    print("GCP Reset Complete.")

# ------------------------- CLI -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GCP Automation Script")
    parser.add_argument("command", choices=["init", "setup", "reset"], help="Command to run")
    parser.add_argument("--creds", required=True, help="Path to service account JSON")
    parser.add_argument("--project", help="GCP Project ID (required for setup/reset)")
    parser.add_argument("--service-name", default="example-fetcher", help="Cloud Run service name")
    args = parser.parse_args()

    try:
        creds = load_credentials(args.creds)
    except FileNotFoundError as e:
        print(e)
        exit(1)

    if args.command == "init":
        gcp_init(creds)
    elif args.command == "setup":
        if not args.project:
            print("Project ID is required for setup.")
            exit(1)
        gcp_setup(args.creds, args.project, service_name=args.service_name)
    elif args.command == "reset":
        if not args.project:
            print("Project ID is required for reset.")
            exit(1)
        gcp_reset(args.creds, args.project)
