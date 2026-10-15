# Tenant isolation in an inference API

A small, offline lab for testing authorization at a shared inference gateway. Two synthetic tenants own separate private models. The lab has two modes: one with deliberately missing authorization checks and another that enforces the stated tenant policy.

This is a mock API, not a vLLM integration. It never calls a model, sends traffic to an external service, or handles real tenant data.

## Policy and expected behavior

For this lab, model identifiers are private to the tenant that owns them. The same rule applies to model invocation. Real deployments may deliberately expose a public model catalog; unauthenticated model listing is only a problem where the intended policy is private listing.

| Request | Deliberately vulnerable | Hardened |
| --- | --- | --- |
| `GET /v1/models` without a token | 200, both models | 401 |
| `GET /v1/models` with tenant Alpha token | 200, both models | 200, Alpha only |
| `POST /v1/chat/completions` for Beta model with Alpha token | 200 | 403 |
| `POST /v1/chat/completions` for Alpha model with Alpha token | 200 | 200 |

The model calls return synthetic text. A 200 response represents an authorization decision, not real inference or disclosure of private model data.

## Run locally

Requires Python 3.9 or newer; no third-party packages.

```sh
cd sandboxes/llm_local_tenant_isolation
make test
make run-local                         # hardened mode on 127.0.0.1:8765
```

In another terminal, from the same directory:

```sh
make attack
```

To switch to the deliberately vulnerable mode, stop the local server and run:

```sh
make MODE=intentionally-vulnerable run-local
# In the other terminal:
make MODE=intentionally-vulnerable attack
```

The probe produces JSON with HTTP statuses, visible model identifiers and explicit policy-violation indicators. Its exit code is nonzero if observed behavior does not match the expected mode.

## Container run

Requires Podman or Docker. By default the container starts in hardened mode and publishes its API to localhost only.

```sh
make all
make attack
make stop

make MODE=intentionally-vulnerable all
make MODE=intentionally-vulnerable attack
make stop
```

Use `make CONTAINER=docker all` and `make CONTAINER=docker stop` with Docker. Stop the previous container before starting another mode.

## Files

- `app/server.py`: synthetic inference API and policy switch.
- `tests/test_boundaries.py`: authorization regression tests in both modes.
- `../../exploitation/tenant_isolation/probe.py`: repeatable localhost-only probe.

## Scope

This lab illustrates broken object-level authorization at an inference gateway and a tenant-scoped enforcement pattern. It does not evaluate real inference servers, denial of service, token issuance, model prompt behavior, or cross-tenant leakage from an inference backend. No CVE is claimed.

Run the probe only against the included localhost lab. The example tokens in `app/server.py` are test fixtures, not secure production credentials.

Discussion: [issue #93](https://github.com/GenAI-Security-Project/GenAI-Red-Team-Lab/issues/93).
