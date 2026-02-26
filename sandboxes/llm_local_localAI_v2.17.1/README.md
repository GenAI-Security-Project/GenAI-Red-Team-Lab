# LocalAI Sandbox
This sandbox environment deploys a vulnerable instance of LocalAI (v2.17.1). It is designed for security researchers to practice exploitation techniques against self-hosted AI engines, specifically focusing on arbitrary file write leading to Remote Code Execution (RCE) via a tarslip vulnerability.

---

## Vulnerability Overview: CVE-2024-6868
- **Vulnerability Type:** Path Traversal (Tarslip) / Remote Code Execution (RCE)
- **Affected Component:** Model file download and archive extraction logic
### Description
LocalAI versions up to and including v2.17.1 allow users to specify remote files that the model will download. When the downloaded file is an archive (e.g., `.tar`), it is automatically extracted without proper path sanitization. An attacker can craft a malicious tar archive containing a symlink that points to an arbitrary directory on the host, enabling writes outside the intended models directory. By overwriting an executable backend asset (e.g., a Whisper backend binary under `/tmp/localai/backend_data/backend-assets/`), an attacker can achieve RCE the next time a model using that backend is loaded.

---

## Prerequisites
- Podman (preferred) or Docker
- Make utility

> **Note:** Ensure port `8080` is not being used by another local service before starting the sandbox.

---

## Setup and Lifecycle
This lab uses a `Makefile` to simplify container management using Podman.

### 1. Build and Start the Sandbox
This will build the image and start the container in detached mode.
```bash
make all
```

### 2. Verify the Environment
Check if the service is running:
```bash
podman ps
```
The LocalAI UI should be accessible at:
```
http://localhost:8080
```

---

### 3. Stop and Cleanup
To stop the container and remove the image:
```bash
make clean
```

---

## Directory Structure
```
sandboxes/LocalAI-CVE-2024-6868/
├── Containerfile       # Podman definition for the vulnerable environment
├── Makefile            # Automation for build/run/stop/attack
└── README.md           # Documentation
```
