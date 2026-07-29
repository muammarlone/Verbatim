from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = PROJECT_ROOT / "evidence" / "batch-demo"
FIXTURE = PROJECT_ROOT / "evidence" / "demo" / "fixture" / "synthetic-quarterly-review.mp4"
MODEL_PATH = Path(os.getenv("STS_MODEL_PATH", Path.home() / ".cache" / "whisper" / "base.pt"))
PORT = 8772


def wait_for_server(url: str, timeout_seconds: float = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError("Local batch demo server did not become ready.")


def move_to(page: Page, locator: Locator, *, steps: int = 18) -> None:
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=steps)
        page.wait_for_timeout(300)


def click(page: Page, locator: Locator) -> None:
    move_to(page, locator)
    locator.click()


def install_demo_overlay(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const cursor = document.createElement('div');
          cursor.id = 'recording-cursor';
          cursor.style.cssText = 'position:fixed;left:0;top:0;width:18px;height:18px;border:2px solid white;border-radius:50%;background:#176b54;box-shadow:0 2px 8px rgba(0,0,0,.35);pointer-events:none;z-index:99999;transform:translate(-50%,-50%);transition:width .12s,height .12s;';
          const badge = document.createElement('div');
          badge.textContent = 'SYNTHETIC BATCH DEMO · LOCAL ONLY';
          badge.style.cssText = 'position:fixed;right:18px;bottom:16px;padding:7px 11px;border-radius:20px;background:rgba(23,32,29,.9);color:#fff;font:700 10px Segoe UI,sans-serif;letter-spacing:.12em;pointer-events:none;z-index:99998;box-shadow:0 5px 18px rgba(0,0,0,.18);';
          document.body.append(cursor, badge);
          document.addEventListener('mousemove', (event) => {
            cursor.style.left = `${event.clientX}px`;
            cursor.style.top = `${event.clientY}px`;
          });
          document.addEventListener('mousedown', () => { cursor.style.width = '12px'; cursor.style.height = '12px'; });
          document.addEventListener('mouseup', () => { cursor.style.width = '18px'; cursor.style.height = '18px'; });
        }
        """
    )


def main() -> None:
    if not FIXTURE.is_file():
        raise SystemExit(f"Synthetic fixture is missing: {FIXTURE}")
    if not MODEL_PATH.is_file():
        raise SystemExit(f"Local Whisper model is missing: {MODEL_PATH}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = DEMO_ROOT / "runs" / run_id
    video_dir = run_dir / "browser-video"
    data_dir = run_dir / "runtime-data"
    input_dir = data_dir / "batch-workspace" / "incoming"
    server_log_path = run_dir / "server-output.log"
    for directory in (video_dir, input_dir):
        directory.mkdir(parents=True, exist_ok=False)
    shutil.copy2(FIXTURE, input_dir / "quarterly-security-review.mp4")
    shutil.copy2(FIXTURE, input_dir / "planning-approval-review.mp4")

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["STS_DATA_DIR"] = str(data_dir)
    environment["STS_MODEL_PATH"] = str(MODEL_PATH)
    environment["STS_TRANSCRIPTION_TIMEOUT_SECONDS"] = "300"
    environment["STS_RETENTION_DAYS"] = "1"

    server_log = server_log_path.open("w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "-m", "secure_transcribe", "--port", str(PORT), "--no-browser"],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=server_log,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    milestones: dict[str, float] = {}
    console_errors: list[str] = []
    started = 0.0

    def mark(name: str) -> None:
        milestones[name] = round(time.monotonic() - started, 3)

    try:
        wait_for_server(f"http://127.0.0.1:{PORT}/api/health")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                record_video_dir=str(video_dir),
                record_video_size={"width": 1440, "height": 900},
            )
            page = context.new_page()
            started = time.monotonic()
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: console_errors.append(str(error)))
            video = page.video
            page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle")
            install_demo_overlay(page)
            mark("page_ready")
            page.wait_for_timeout(5000)

            click(page, page.locator('[data-upload-mode="batch"]'))
            mark("batch_mode_opened")
            page.wait_for_timeout(2800)
            page.locator("#batch-input-folder").fill("incoming")
            page.locator("#batch-output-folder").fill("transcripts")
            click(page, page.locator('input[name="batch-format"][value="srt"]'))
            click(page, page.locator('input[name="batch-format"][value="vtt"]'))
            mark("folders_configured")
            page.wait_for_timeout(2500)
            click(page, page.locator("#batch-consent-checkbox"))
            mark("consent_confirmed")
            page.wait_for_timeout(1200)
            click(page, page.locator("#batch-start-button"))
            page.locator(".batch-card").wait_for(state="visible", timeout=15_000)
            mark("batch_started")

            page.locator(".batch-card-header .status-badge").filter(has_text="Complete").wait_for(
                state="visible", timeout=360_000
            )
            mark("batch_complete")
            page.wait_for_timeout(5500)

            page.locator(".batch-card").scroll_into_view_if_needed()
            page.wait_for_timeout(2800)
            first_job = page.locator(".job-row").first
            click(page, first_job)
            page.locator("#review-workspace").wait_for(state="visible", timeout=20_000)
            mark("job_reviewed")
            page.wait_for_timeout(5000)

            click(page, page.locator("#back-button"))
            page.locator(".batch-card").scroll_into_view_if_needed()
            page.wait_for_timeout(2200)
            click(page, page.locator(".batch-card-footer button"))
            page.locator("#batch-delete-dialog").wait_for(state="visible")
            mark("cleanup_opened")
            page.wait_for_timeout(4500)
            click(page, page.locator("#confirm-batch-delete"))
            page.locator("#empty-batches").wait_for(state="visible", timeout=15_000)
            page.locator("#empty-jobs").wait_for(state="visible", timeout=15_000)
            mark("cleanup_complete")
            page.wait_for_timeout(5500)

            context.close()
            raw_video = Path(video.path())
            browser.close()

        visual_output = run_dir / "verbatim-batch-demo-visual.webm"
        shutil.copy2(raw_video, visual_output)
        output_dir = data_dir / "batch-workspace" / "transcripts"
        output_files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
        audit_path = data_dir / "audit" / "events.jsonl"
        audit_events = [
            json.loads(line)["event"]
            for line in audit_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        report = {
            "schema_version": "1.0",
            "run_id": run_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "fixture": str(FIXTURE.relative_to(PROJECT_ROOT)),
            "input_file_count": 2,
            "formats": ["txt", "md", "srt", "vtt", "json"],
            "model": MODEL_PATH.name,
            "milestones": milestones,
            "processing_wall_seconds": round(
                milestones["batch_complete"] - milestones["batch_started"], 3
            ),
            "console_errors": console_errors,
            "output_files": output_files,
            "audit_events": audit_events,
            "managed_job_entries_after_cleanup": len(list((data_dir / "jobs").iterdir())),
            "managed_batch_entries_after_cleanup": len(list((data_dir / "batches").iterdir())),
            "visual_video": str(visual_output.relative_to(PROJECT_ROOT)),
        }
        (run_dir / "recording-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (DEMO_ROOT / "latest-run.txt").write_text(run_id + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
        server_log.close()


if __name__ == "__main__":
    main()
