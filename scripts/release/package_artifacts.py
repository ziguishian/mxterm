from __future__ import annotations

import hashlib
import json
import platform
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    dist_dir = Path("dist")
    build_dir = dist_dir / "release"
    build_dir.mkdir(parents=True, exist_ok=True)
    system = platform.system().lower()
    artifact_name = {
        "windows": "mxterm-windows-x64",
        "darwin": "mxterm-macos-universal",
    }.get(system, "mxterm-linux-x86_64")
    source = dist_dir / ("mxterm.exe" if system == "windows" else "mxterm")
    target = build_dir / artifact_name
    if system == "windows":
        archive_path = Path(shutil.make_archive(str(target), "zip", root_dir=source.parent, base_dir=source.name))
    else:
        archive_path = Path(shutil.make_archive(str(target), "gztar", root_dir=source.parent, base_dir=source.name))
    manifest = {
        "artifact": archive_path.name,
        "platform": system,
        "size_bytes": archive_path.stat().st_size,
        "sha256": sha256(archive_path),
    }
    manifest_path = build_dir / f"{artifact_name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
