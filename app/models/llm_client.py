from typing import List, Dict


class LLMClient:
    """OpenAI-compatible client stub for local LLM server (e.g., Ollama)."""

    def __init__(self, base_url: str = "http://ollama:11434", model: str = "gemma3:12b"):
        self.base_url = base_url
        self.model = model

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Return a placeholder response. Replace with real HTTP call."""
        return "Not implemented (LLM call stub)."

