"""Gradio web interface for the LLM Mock API (persistent-memory variant).

This module provides an interactive chat interface using Gradio that connects
to the mock API server for testing LLM interactions. Unlike the plain
llm_local template, this version exposes a session_id textbox so you can
switch between simulated users/conversations and directly observe the
memory-poisoning vulnerability: plant a fact under one session_id, switch
to a different one, and see whether it leaks in.
"""

import os
import uuid
from pathlib import Path

import gradio as gr
import requests
import tomli

# Load model configuration
config_path = Path(__file__).parent.parent / "config" / "model.toml"
with open(config_path, "rb") as f:
    config = tomli.load(f)

# Configure the mock API endpoint
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-mock-key"
if "OPENAI_BASE_URL" not in os.environ:
    os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"


def new_session():
    """Generate a fresh, random session_id — simulates starting a brand-new conversation/user."""
    return str(uuid.uuid4())


def chat_with_llm(message, history, session_id):
    """Send one message to the mock API under the given session_id.

    session_id comes from the UI's textbox (an additional_input), not from
    Gradio's own `history` — this is what lets the same UI demonstrate
    cross-session memory leakage by simply changing that one field between
    messages.
    """
    try:
        response = requests.post(
            "http://127.0.0.1:8000/v1/chat/completions",
            headers={"Authorization": "Bearer sk-mock-key"},
            json={
                "model": config["default"]["model"],
                "messages": [{"role": "user", "content": message}],
                "session_id": session_id,
            },
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ Error: {str(e)}\n\nMake sure the mock API server is running on http://localhost:8000"


session_box = gr.Textbox(
    label="session_id",
    value=new_session(),
    info="Change this (or generate a new one) to simulate a different user/session.",
)


# Create the Gradio interface
demo = gr.ChatInterface(
    fn=chat_with_llm,
    additional_inputs=[session_box],
    title="🤖 LLM Mock API - Chat Interface",
    description="Chat with a local Ollama model through the mock OpenAI API.",
    examples=[
        ["Hello, are you working?", "demo-session-1"],
        ["What can you help me with?", "demo-session-1"],
        ["Tell me about large language models.", "demo-session-1"],
    ],
    theme=gr.themes.Soft(),
)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
