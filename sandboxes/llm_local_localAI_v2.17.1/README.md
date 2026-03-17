# LocalAI Sandbox
This sandbox environment deploys a vulnerable instance of LocalAI (v2.17.1). It is designed for security researchers to practice exploitation techniques against self-hosted AI engines, specifically focusing on arbitrary file write leading to Remote Code Execution (RCE) via a tarslip vulnerability.

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
