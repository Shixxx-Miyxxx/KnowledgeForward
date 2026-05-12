from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import OllamaConfig


class OllamaError(RuntimeError):
    """Raised when the local Ollama API cannot produce an answer."""


@dataclass(frozen=True)
class OllamaClient:
    config: OllamaConfig

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": self.config.temperature},
        }
        if self.config.hide_thinking:
            payload["think"] = False
        request = urllib.request.Request(
            f"{self.config.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:  # nosec B310
                data = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise OllamaError(f"Ollama timed out after {self.config.timeout_seconds}s at {self.config.base_url}.") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(f"Could not connect to Ollama at {self.config.base_url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON.") from exc

        content = data.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama response did not contain message.content.")
        return strip_thinking(content).strip() if self.config.hide_thinking else content.strip()


def strip_thinking(content: str) -> str:
    text = re.sub(r"(?is)<think>.*?</think>", "", content)
    text = re.sub(r"(?is)^\s*thinking\s*\.\.\.\s*", "", text)
    text = re.sub(r"(?is)^\s*思考中\s*[。:：.]*\s*", "", text)
    return text.strip()
