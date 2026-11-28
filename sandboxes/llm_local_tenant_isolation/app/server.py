"""Synthetic inference API for testing model-level tenant authorization."""

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKENS = {"lab-token-alpha": "alpha", "lab-token-beta": "beta"}
MODELS = {"alpha-private": "alpha", "beta-private": "beta"}
MODES = ("hardened", "intentionally-vulnerable")


def create_handler(mode):
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Suppress request logs, including authorization headers.
            pass

        def _send(self, status, payload):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _tenant(self):
            scheme, _, token = self.headers.get("Authorization", "").partition(" ")
            if scheme.lower() != "bearer":
                return None
            return TOKENS.get(token)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"status": "ok", "mode": mode})
            if self.path != "/v1/models":
                return self._send(404, {"error": "unknown endpoint"})

            tenant = self._tenant()
            if mode == "hardened" and tenant is None:
                return self._send(401, {"error": "authentication required"})

            visible = [
                {"id": name, "object": "model"}
                for name, owner in MODELS.items()
                if mode == "intentionally-vulnerable" or owner == tenant
            ]
            return self._send(200, {"object": "list", "data": visible})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                return self._send(404, {"error": "unknown endpoint"})

            tenant = self._tenant()
            if tenant is None:
                return self._send(401, {"error": "authentication required"})

            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    return self._send(413, {"error": "invalid request size"})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    return self._send(400, {"error": "expected JSON object"})
                model = body.get("model")
            except (ValueError, json.JSONDecodeError):
                return self._send(400, {"error": "invalid request body"})

            if not isinstance(model, str) or model not in MODELS:
                return self._send(404, {"error": "model not found"})
            if mode == "hardened" and MODELS[model] != tenant:
                return self._send(403, {"error": "model not authorized for tenant"})

            # The response is synthetic; this lab tests only the gateway decision.
            return self._send(
                200,
                {
                    "object": "chat.completion",
                    "model": model,
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Synthetic response",
                            }
                        }
                    ],
                },
            )

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Local tenant-isolation lab")
    parser.add_argument(
        "--mode", choices=MODES, default=os.getenv("LAB_MODE", "hardened")
    )
    parser.add_argument("--host", default=os.getenv("LAB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("LAB_PORT", "8765")))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), create_handler(args.mode))
    print(f"Listening on {args.host}:{args.port} ({args.mode})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
