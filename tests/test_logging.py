from mxterm.utils.logging import clear_logs, log_event, log_path, tail_logs


def test_log_helpers_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("mxterm.utils.logging.logs_dir", lambda: tmp_path)
    clear_logs()
    log_event("test.event", {"value": 1})
    assert log_path().exists()
    entries = tail_logs(5)
    assert len(entries) == 1
    assert "test.event" in entries[0]
