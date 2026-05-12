from knowledge_forward import security_audit


def test_redact_removes_ansi_escape_sequences() -> None:
    text = "\x1b[90m10:02PM\x1b[0m \x1b[32mINF\x1b[0m \x1b[1mno leaks found\x1b[0m"

    redacted = security_audit._redact(text, ())

    assert redacted == "10:02PM INF no leaks found"
    assert "\x1b" not in redacted


def test_redact_removes_sensitive_tokens_and_local_paths_after_stripping_ansi() -> None:
    user_path = "/" + "Users" + "/example/project"
    private_path = "/" + "private" + "/tmp/file"
    text = f"\x1b[32m{user_path}\x1b[0m token-value {private_path}"

    redacted = security_audit._redact(text, ("token-value",))

    assert redacted == "[local path] [redacted] [local path]"
