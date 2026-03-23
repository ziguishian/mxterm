from mxterm.routing.classifier import classify_input


def test_direct_command_is_detected(monkeypatch):
    monkeypatch.setattr("mxterm.routing.classifier.command_exists", lambda token, shell: token == "git")
    assert classify_input("git status", "bash") == "direct"


def test_natural_language_in_chinese_is_detected(monkeypatch):
    monkeypatch.setattr("mxterm.routing.classifier.command_exists", lambda token, shell: False)
    assert classify_input("帮我看看当前目录", "bash") == "natural_language"


def test_ambiguous_typo_is_detected(monkeypatch):
    monkeypatch.setattr("mxterm.routing.classifier.command_exists", lambda token, shell: False)
    assert classify_input("gti status", "bash") == "ambiguous"
