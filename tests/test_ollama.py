from knowledge_forward.config import OllamaConfig
from knowledge_forward.ollama import OllamaClient, OllamaError, strip_thinking


def test_strip_thinking_tags() -> None:
    content = "<think>private reasoning</think>\n\n最終回答です。"

    assert strip_thinking(content) == "最終回答です。"


def test_strip_thinking_prefix() -> None:
    content = "Thinking...\n最終回答だけです。"

    assert strip_thinking(content) == "最終回答だけです。"


def test_chat_wraps_socket_timeout_as_ollama_error(monkeypatch) -> None:
    def raise_timeout(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr("urllib.request.urlopen", raise_timeout)
    client = OllamaClient(OllamaConfig(timeout_seconds=3))

    try:
        client.chat("system", "user")
    except OllamaError as exc:
        assert "timed out after 3s" in str(exc)
    else:
        raise AssertionError("TimeoutError should be wrapped as OllamaError")
