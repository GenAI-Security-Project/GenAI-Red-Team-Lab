"""Mock API Services package.

Contains the mock OpenAI chat service extended with a persistent conversation-memory
layer, exposed as a FastAPI router that mounts into the main application.

Available Mocks:
    openai: Mock OpenAI API using Ollama as the backend, with scope-keyed memory
        recall and a "remember that ..." write path (Conversation Memory Poisoning).
"""

from app.mocks.openai import router as openai_router

__all__ = ["openai_router"]
