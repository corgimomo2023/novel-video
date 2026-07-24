#!/usr/bin/env python3
"""Populate a RunPod network volume with checksummed ComfyUI models."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

CHUNK_SIZE = 8 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def download(model: dict, root: Path, *, dry_run: bool = False) -> str:
    destination = root / "models" / model["folder"] / model["filename"]
    expected_size = int(model["bytes"])
    expected_hash = model["sha256"].lower()

    if destination.exists() and destination.stat().st_size == expected_size:
        if sha256_file(destination) == expected_hash:
            return f"OK   {destination}"
        destination.unlink()

    if dry_run:
        return f"NEED {destination} ({expected_size / 1024**3:.2f} GiB)"

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > expected_size:
        partial.unlink()
        offset = 0

    headers = {"User-Agent": "novel-video-volume-populator/1.0"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(model["url"], headers=headers)

    try:
        response = urllib.request.urlopen(request, timeout=120)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"download failed for {model['filename']}: HTTP {error.code}") from None

    if offset and getattr(response, "status", 200) != 206:
        response.close()
        partial.unlink(missing_ok=True)
        return download(model, root, dry_run=False)

    mode = "ab" if offset else "wb"
    completed = offset
    with response, partial.open(mode) as output:
        while chunk := response.read(CHUNK_SIZE):
            output.write(chunk)
            completed += len(chunk)
            print(
                f"\r{model['filename']}: {completed / 1024**3:.2f}/{expected_size / 1024**3:.2f} GiB",
                end="",
                flush=True,
            )
    print()

    if partial.stat().st_size != expected_size:
        raise RuntimeError(
            f"size mismatch for {model['filename']}: got {partial.stat().st_size}, expected {expected_size}"
        )
    actual_hash = sha256_file(partial)
    if actual_hash != expected_hash:
        raise RuntimeError(f"sha256 mismatch for {model['filename']}")
    os.replace(partial, destination)
    return f"DONE {destination}"


def check_space(root: Path, required_bytes: int, *, dry_run: bool) -> None:
    target = root if root.exists() else root.parent
    free = shutil.disk_usage(target).free
    reserve = 5 * 1024**3
    if not dry_run and free < required_bytes + reserve:
        raise RuntimeError(
            f"insufficient free space: {free / 1024**3:.2f} GiB available; "
            f"need {(required_bytes + reserve) / 1024**3:.2f} GiB including reserve"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("models.json"))
    parser.add_argument("--root", type=Path, default=Path("/runpod-volume"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    models = manifest["models"]
    required = sum(int(model["bytes"]) for model in models)
    check_space(args.root, required, dry_run=args.dry_run)

    failures = 0
    for model in models:
        try:
            print(download(model, args.root, dry_run=args.dry_run))
        except Exception as error:
            failures += 1
            print(f"FAIL {model['filename']}: {error}", file=sys.stderr)

    if failures or args.dry_run:
        return 1 if failures else 0

    marker = args.root / ".novel-video-models-ready.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker_tmp = marker.with_suffix(".tmp")
    marker_tmp.write_text(
        json.dumps(
            {
                "models": [
                    {
                        key: model[key]
                        for key in ("folder", "filename", "bytes", "sha256")
                    }
                    for model in models
                ],
                "total_bytes": required,
            },
            indent=2,
        )
        + "\n"
    )
    os.replace(marker_tmp, marker)
    print(f"READY {marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
