import os
import json
import uuid
import argparse
from google.cloud import storage
from google.oauth2 import service_account

# File to track resources created by the script
RESOURCE_LOG_FILE = "gcp_created_resources.json"

# ------------------------- LOAD CREDENTIALS -------------------------
def load_credentials(json_path):
    """Load GCP credentials from a JSON file (required)."""
    if not json_path or not os.path.exists(json_path):
        raise FileNotFoundError(f"Service account JSON not found: {json_path}")
    creds = service_account.Credentials.from_service_account_file(json_path)
    return creds

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
def gcp_setup(creds, project_id):
    """Create resources in GCP and log them."""
    client = storage.Client(credentials=creds, project=project_id)

    # Create a unique storage bucket
    bucket_name = f"automation-bucket-{uuid.uuid4().hex[:8]}"
    bucket = client.bucket(bucket_name)
    bucket.location = "US"
    bucket = client.create_bucket(bucket)
    print(f"Created bucket: {bucket.name}")

    # Track created resources
    created_resources = {"buckets": [bucket.name]}
    with open(RESOURCE_LOG_FILE, "w") as f:
        json.dump(created_resources, f)

    print("GCP Setup Complete.")

# ------------------------- RESET -------------------------
def gcp_reset(creds, project_id):
    """Delete resources created by this script."""
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

    os.remove(RESOURCE_LOG_FILE)
    print("GCP Reset Complete.")

# ------------------------- CLI -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GCP Automation Script")
    parser.add_argument("command", choices=["init", "setup", "reset"], help="Command to run")
    parser.add_argument("--creds", required=True, help="Path to service account JSON")
    parser.add_argument("--project", help="GCP Project ID (required for setup/reset)")
    args = parser.parse_args()

    # Load credentials from file ONLY
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
        gcp_setup(creds, args.project)
    elif args.command == "reset":
        if not args.project:
            print("Project ID is required for reset.")
            exit(1)
        gcp_reset(creds, args.project)
