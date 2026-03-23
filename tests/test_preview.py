from pathlib import Path

from mxterm.safety.preview import preview_destructive_targets


def test_preview_destructive_targets_for_powershell_remove(tmp_path):
    target_dir = tmp_path / "bcd"
    target_dir.mkdir()
    first = target_dir / "8123.txt"
    second = target_dir / "8456.log"
    third = target_dir / "9123.txt"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    third.write_text("c", encoding="utf-8")

    shell_code = f"Remove-Item -Path '{target_dir / '8*'}' -Force -Recurse -File"
    summary, items = preview_destructive_targets("powershell", shell_code, cwd=str(tmp_path))

    assert "2 target(s)" in summary
    assert str(first) in items
    assert str(second) in items
    assert str(third) not in items
