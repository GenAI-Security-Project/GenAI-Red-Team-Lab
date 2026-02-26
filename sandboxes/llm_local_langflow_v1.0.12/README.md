# Langflow Sandbox (CVE-2024-37014)

This sandbox environment deploys a vulnerable instance of Langflow (v1.0.12). It is designed for security researchers to practice exploitation techniques against GenAI orchestration frameworks, specifically focusing on unauthenticated Remote Code Execution (RCE).

---

## Vulnerability Overview: CVE-2024-37014

- **Vulnerability Type:** Path Traversal / Remote Code Execution (RCE)
- **Affected Component:** `/api/v1/files/upload` endpoint

### Description

Langflow versions prior to 1.0.13 fail to properly sanitize file uploads. An attacker can leverage this to upload malicious scripts or overwrite sensitive files, leading to RCE on the host system or container.

---

## Prerequisites

- Podman (preferred) or Docker
- Make utility

> **Note:** Ensure port `7860` is not being used by a local installation of Langflow before starting the sandbox.

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

The Langflow UI should be accessible at:

```
http://localhost:7860
```

---

### 3. Running an Attack

To trigger the automated attack (in the `exploitation` directory ) First you have to start a listener :

 ```bash
make listen
```
after that you can run the automated attack 

```bash
make attack
```

---

### 4. Stop and Cleanup

To stop the container and remove the image:

```bash
make clean
```

---

## Directory Structure

```
sandboxes/Langflow-CVE-2024-37014/
├── Containerfile       # Podman definition for the vulnerable environment
├── Makefile            # Automation for build/run/stop/attack
└── README.md           # Documentation
```
