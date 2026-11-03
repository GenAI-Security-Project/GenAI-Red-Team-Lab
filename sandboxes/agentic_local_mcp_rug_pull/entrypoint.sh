#!/bin/sh
exec uv run --no-sync python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
