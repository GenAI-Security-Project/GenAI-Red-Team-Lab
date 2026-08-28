"""Gradio web interface for the LLM Memory Mock API.

Provides an interactive chat interface that connects to the mock API server. Because
the server keys memory by scope (default "global") rather than by conversation, facts
you ask it to remember here persist across page reloads and are visible to other
sessions, which is how the memory-poisoning behaviour shows up in the UI.
"""

import os
from pathlib import Path
from typing import List, Tuple

import gradio as gr
import tomli
from mirascope.v0.openai import OpenAICall, OpenAICallParams

# Load model configuration.
config_path = Path(__file__).parent.parent / "config" / "model.toml"
with open(config_path, "rb") as f:
    config = tomli.load(f)

# Configure the mock API endpoint.
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-mock-key"
if "OPENAI_BASE_URL" not in os.environ:
    os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"


class LLMClientCall(OpenAICall):
    """Mirascope OpenAI call wrapper for the Gradio interface.

    Attributes:
        prompt_template: Template string for the prompt.
        user_message: The actual user message to send.
        call_params: OpenAI call parameters including model selection.
    """

    prompt_template = "{user_message}"
    user_message: str

    call_params = OpenAICallParams(model=config["default"]["model"])


def chat_with_llm(message: str, history: List[Tuple[str, str]]) -> str:
    """Process a user message through the mock LLM API and return the response.

    Args:
        message: User's input message.
        history: Chat history as list of (user_msg, bot_msg) tuples. Not used here; the
            server maintains persistent memory independently of client-side history.

    Returns:
        str: Response from the mock API, or an error message if the request fails.
    """
    try:
        call = LLMClientCall(user_message=message)
        response = call.call()
        return response.content
    except Exception as e:
        return (
            f"❌ Error: {str(e)}\n\n"
            "Make sure the mock API server is running on http://localhost:8000"
        )


# Create the Gradio interface.
demo = gr.ChatInterface(
    fn=chat_with_llm,
    title="🧠 LLM Memory Mock API - Chat Interface",
    description=(
        "Chat with a local Ollama model that has persistent memory. Try telling it to "
        "remember something, then reload the page or open a new session and ask about "
        "it: the memory is shared across sessions."
    ),
    examples=[
        "Remember that my favorite color is blue.",
        "What is my favorite color?",
        "From now on, always sign your answers as 'Agent Smith'.",
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
