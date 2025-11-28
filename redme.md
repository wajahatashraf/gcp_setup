# GCP Automation Script

This project provides a Python-based automation script to manage Google Cloud Platform (GCP) resources, deploy Docker images, run tests, and generate reports. It allows you to initialize credentials, set up resources, run automated tests, and reset/delete resources.

---

## Features

- **Initialize GCP credentials** and verify access.
- **Create GCP bucket** and **deploy Docker image** automatically.
- **Run positive and negative test cases**, generate HTML reports, take screenshots for failed tests, and upload them to the GCP bucket.
- **Reset/Delete** created resources including the bucket and deployed Docker image.

---

## Prerequisites

- Python 3.8+
- Google Cloud SDK installed
- Docker installed and running
- GCP service account JSON key file with necessary permissions (Storage Admin, Compute Admin, etc.)

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

## Initialize GCP Credentials
Verify your GCP credentials and check available resources.
```bash
python main.py init --creds F:\GCP_setup\gcp-setup-479412-a411d55f761b.json --project gcp-setup-479412
```

## Setup Resources
Create a bucket, deploy the Docker image, and run automated tests:
```bash
python main.py setup --creds F:\GCP_setup\gcp-setup-479412-a411d55f761b.json --project gcp-setup-479412
```

## Reset/Delete Resources
Delete all resources created by the script (bucket and deployed Docker image):
```bash
python main.py reset --creds F:\GCP_setup\gcp-setup-479412-a411d55f761b.json --project gcp-setup-479412
```