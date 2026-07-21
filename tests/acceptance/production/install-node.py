#!/usr/bin/env python3
"""Install one checksum-pinned official Node.js archive without running installers."""

from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path


VERSION = "22.23.1"
ARCHIVE = f"node-v{VERSION}-linux-x64.tar.xz"
URL = f"https://nodejs.org/dist/v{VERSION}/{ARCHIVE}"
SHA256 = "9749e988f437343b7fa832c69ded82a312e41a03116d766797ac14f6f9eee578"
DESTINATION = Path.home() / ".local" / f"node-v{VERSION}"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    node = DESTINATION / "bin" / "node"
    if node.is_file() and os.access(node, os.X_OK):
        print(f"node runtime already present: v{VERSION}")
        return

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="crabbox-node-") as temporary:
        root = Path(temporary)
        archive = root / ARCHIVE
        urllib.request.urlretrieve(URL, archive)
        observed = digest(archive)
        if observed != SHA256:
            raise SystemExit(f"checksum mismatch: expected {SHA256}, observed {observed}")
        with tarfile.open(archive, "r:xz") as bundle:
            bundle.extractall(root, filter="data")
        extracted = root / f"node-v{VERSION}-linux-x64"
        if not (extracted / "bin" / "node").is_file():
            raise SystemExit("verified archive did not contain the expected Node binary")
        if DESTINATION.exists():
            shutil.rmtree(DESTINATION)
        extracted.rename(DESTINATION)
    print(f"installed checksum-pinned Node.js v{VERSION}")


if __name__ == "__main__":
    main()
