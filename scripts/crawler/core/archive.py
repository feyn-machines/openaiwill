"""Run archive: immutable, credential-free run files and raw responses.

Every run writes a new JSON file under the project's ignored data/ directory
(0600) and never overwrites one; raw provider responses sit beside it in
<run>.pages/ with their SHA-256. The run file is the provenance that ingestion
reads, so it is kept even when its rows are already in the database.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]


def write_json(path, data, indent=2):
    payload = json.dumps(data, ensure_ascii=False, indent=indent).encode()
    Path(path).write_bytes(payload)
    os.chmod(path, 0o600)


def write_raw(directory, name, data):
    """Persist one raw response compactly. Returns (file name, sha256)."""
    path = Path(directory) / name
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    path.write_bytes(payload)
    os.chmod(path, 0o600)
    return path.name, hashlib.sha256(payload).hexdigest()


def reserve(output, root=ROOT):
    """Validate a new run path under data/ and lock it. Returns the resolved path."""
    output = Path(output).resolve()
    if not output.is_relative_to((Path(root) / "data").resolve()) or output.suffix != ".json":
        raise ValueError("Output must be a new JSON file under this project's private data directory")
    if output.exists() or output.with_suffix(".lock").exists():
        raise ValueError("Existing collection runs are immutable; choose a new output filename")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with output.with_suffix(".lock").open("x") as lock:
        lock.write("Reserved crawler run; do not overwrite.\n")
    return output


def pages_dir(output):
    path = Path(output).parent / (Path(output).stem + ".pages")
    path.mkdir(mode=0o700, exist_ok=True)
    return path


def implementation_hashes():
    """SHA-256 of every crawler source file, keyed by its path in the package."""
    return {str(p.relative_to(PACKAGE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(PACKAGE.rglob("*.py"))}
