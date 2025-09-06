from typing import List, Dict, Iterable, Optional
import os


class LLMClient:
    """Client for local LLM server (Ollama/OpenAI-Compat)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.model = model or os.getenv("LLM_MODEL", os.getenv("OLLAMA_MODEL", "gemma3:12b"))
        self.api = os.getenv("LLM_API", "ollama")  # ollama | openai
        self.timeout = float(os.getenv("LLM_TIMEOUT", "60"))

    def chat(self, messages: List[Dict[str, str]]) -> str:
        try:
            import httpx
        except Exception:
            return "Not implemented (LLM call stub)."

        if self.api == "openai":
            url = self.base_url.rstrip("/") + "/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
                "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "512")),
                "stream": False,
            }
            try:
                r = httpx.post(url, json=payload, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
            except Exception:
                return ""

        # Default: Ollama API
        url = self.base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
                "num_ctx": int(os.getenv("LLM_CONTEXT", "8192")),
                "num_predict": int(os.getenv("LLM_MAX_TOKENS", "512")),
            },
            "stream": False,
        }
        try:
            r = httpx.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            # Ollama chat (non-stream) returns {message:{content:...}}
            if isinstance(data, dict) and "message" in data:
                return data["message"].get("content", "")
            return ""
        except Exception:
            return ""

    def chat_stream(self, messages: List[Dict[str, str]]) -> Iterable[str]:
        """Yield text deltas as they arrive (SSE-ready)."""
        try:
            import httpx
        except Exception:
            yield ""
            return

        if self.api == "openai":
            url = self.base_url.rstrip("/") + "/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
                "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "512")),
                "stream": True,
            }
            with httpx.stream("POST", url, json=payload, timeout=self.timeout) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    # Expect lines like: data: {json}
                    try:
                        if line.startswith("data: "):
                            import json as _json

                            obj = _json.loads(line[len("data: ") :])
                            delta = obj["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                    except Exception:
                        continue
            return

        # Ollama streaming via /api/chat with stream=true returns JSON lines
        url = self.base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
                "num_ctx": int(os.getenv("LLM_CONTEXT", "8192")),
                "num_predict": int(os.getenv("LLM_MAX_TOKENS", "512")),
            },
            "stream": True,
        }
        with httpx.stream("POST", url, json=payload, timeout=None) as r:
            r.raise_for_status()
            import json as _json

            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    obj = _json.loads(line)
                    msg = obj.get("message") or {}
                    content = msg.get("content", "")
                    if content:
                        yield content
                except Exception:
                    continue
