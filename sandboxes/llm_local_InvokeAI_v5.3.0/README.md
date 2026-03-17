# InvokeAI Sandbox 

This sandbox environment deploys a vulnerable instance of InvokeAI (v5.3.0). It is designed for security researchers to practice exploitation techniques against GenAI image generation platforms, specifically focusing on unauthenticated Remote Code Execution (RCE) via model deserialization.

---


## Prerequisites

- Podman (preferred) or Docker
- Make utility

> **Note:** Ensure port `9090` is not being used by another local service before starting the sandbox.

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

The InvokeAI UI should be accessible at:

```
http://localhost:9090
```

---

### 3. Running an Attack

To trigger the automated attack, navigate to the `exploitation/InvokeAI_v5.3.0` directory. First start a listener:

```bash
make listen
```

Then in a second terminal, serve the payload:

```bash
make serve
```

Then in a third terminal, trigger the exploit:

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
sandboxes/InvokeAI_v5.3.0/
├── Containerfile       # Podman definition for the vulnerable environment
├── Makefile            # Automation for build/run/stop/clean
└── README.md           # Documentation
```
