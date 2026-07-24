#!/usr/bin/env python3
"""Run the model downloader and expose safe progress over HTTP."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
MODEL_ROOT = Path(os.environ.get("MODEL_ROOT", "/runpod-volume"))
MANIFEST = json.loads((APP_ROOT / "models.json").read_text(encoding="utf-8"))
PROCESS: subprocess.Popen[str] | None = None


def status() -> dict[str, object]:
    files = []
    downloaded = 0
    expected = 0
    for model in MANIFEST["models"]:
        target = MODEL_ROOT / "models" / model["folder"] / model["filename"]
        partial = target.with_suffix(target.suffix + ".part")
        current = target.stat().st_size if target.exists() else partial.stat().st_size if partial.exists() else 0
        total = int(model["bytes"])
        downloaded += min(current, total)
        expected += total
        files.append({
            "filename": model["filename"],
            "downloaded_bytes": current,
            "expected_bytes": total,
            "verified": target.exists() and current == total,
        })
    marker = MODEL_ROOT / ".novel-video-models-ready.json"
    return {
        "ready": marker.exists(),
        "downloader_running": PROCESS is not None and PROCESS.poll() is None,
        "exit_code": None if PROCESS is None else PROCESS.poll(),
        "downloaded_bytes": downloaded,
        "expected_bytes": expected,
        "files": files,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/", "/health", "/status"}:
            self.send_error(404)
            return
        body = json.dumps(status(), separators=(",", ":")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_downloader() -> None:
    global PROCESS
    command = ["python", str(APP_ROOT / "populate_volume.py"), "--root", str(MODEL_ROOT)]
    if os.environ.get("POPULATOR_DRY_RUN") == "1":
        command.append("--dry-run")
    PROCESS = subprocess.Popen(command, text=True)
    PROCESS.wait()


def main() -> None:
    threading.Thread(target=run_downloader, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
