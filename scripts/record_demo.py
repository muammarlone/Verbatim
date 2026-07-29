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
DEMO_ROOT = PROJECT_ROOT / "evidence" / "demo"
FIXTURE = DEMO_ROOT / "fixture" / "synthetic-quarterly-review.mp4"
MODEL_PATH = Path(os.getenv("STS_MODEL_PATH", Path.home() / ".cache" / "whisper" / "base.pt"))
PORT = 8770


def wait_for_server(url: str, timeout_seconds: float = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError("Local demo server did not become ready.")


def move_to(page: Page, locator: Locator, *, steps: int = 18) -> None:
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=steps)
        page.wait_for_timeout(350)


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
          badge.textContent = 'SYNTHETIC DEMO · LOCAL ONLY';
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
    download_dir = run_dir / "downloads"
    data_dir = run_dir / "runtime-data"
    for directory in (video_dir, download_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=False)

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["STS_DATA_DIR"] = str(data_dir)
    environment["STS_MODEL_PATH"] = str(MODEL_PATH)
    environment["STS_TRANSCRIPTION_TIMEOUT_SECONDS"] = "180"
    environment["STS_RETENTION_DAYS"] = "1"

    server = subprocess.Popen(
        [sys.executable, "-m", "secure_transcribe", "--port", str(PORT), "--no-browser"],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    milestones: dict[str, float] = {}
    console_errors: list[str] = []
    started = time.monotonic()

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
                accept_downloads=True,
            )
            page = context.new_page()
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
            page.wait_for_timeout(7000)

            drop_zone = page.locator("#drop-zone")
            move_to(page, drop_zone)
            page.locator("#file-input").set_input_files(str(FIXTURE))
            mark("file_selected")
            page.wait_for_timeout(4500)

            click(page, page.locator("#consent-checkbox"))
            page.wait_for_timeout(800)
            click(page, page.locator("#start-button"))
            page.locator("#processing-panel").wait_for(state="visible", timeout=15_000)
            mark("processing_started")

            page.locator("#review-workspace").wait_for(state="visible", timeout=180_000)
            mark("job_complete")
            page.wait_for_timeout(5500)

            transcript_panel = page.locator("#transcript-panel, .transcript-panel").first
            transcript_panel.scroll_into_view_if_needed()
            page.wait_for_timeout(900)
            search = page.locator("#transcript-search")
            click(page, search)
            search.fill("evidence")
            mark("search_shown")
            page.wait_for_timeout(4200)
            search.fill("")
            page.wait_for_timeout(1200)

            analysis = page.locator("#analysis-heading")
            analysis.scroll_into_view_if_needed()
            page.wait_for_timeout(700)
            for tab_name in ("actions", "questions", "terms", "moments"):
                click(page, page.locator(f'[data-tab="{tab_name}"]'))
                mark(f"analysis_{tab_name}")
                page.wait_for_timeout(2200)

            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            page.wait_for_timeout(900)
            click(page, page.locator("#export-button"))
            page.wait_for_timeout(700)
            with page.expect_download() as download_info:
                click(page, page.locator('[data-format="json"]'))
            download = download_info.value
            download_path = download_dir / "synthetic-review-evidence.json"
            download.save_as(download_path)
            mark("export_saved")
            page.wait_for_timeout(3500)

            click(page, page.locator("#health-button"))
            page.locator("#health-dialog").wait_for(state="visible")
            mark("health_opened")
            page.wait_for_timeout(4500)
            click(page, page.locator("#health-dialog .dialog-close"))
            page.wait_for_timeout(800)

            click(page, page.locator("#delete-button"))
            page.locator("#delete-dialog").wait_for(state="visible")
            mark("delete_opened")
            page.wait_for_timeout(4500)
            click(page, page.locator("#confirm-delete"))
            page.locator("#workspace-view").wait_for(state="visible")
            page.locator("#empty-jobs").wait_for(state="visible")
            mark("deleted")
            page.wait_for_timeout(5500)

            context.close()
            raw_video = Path(video.path())
            browser.close()

        visual_output = run_dir / "verbatim-demo-visual.webm"
        shutil.copy2(raw_video, visual_output)
        report = {
            "schema_version": "1.0",
            "run_id": run_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "fixture": str(FIXTURE.relative_to(PROJECT_ROOT)),
            "model": MODEL_PATH.name,
            "milestones": milestones,
            "console_errors": console_errors,
            "download": str(download_path.relative_to(PROJECT_ROOT)),
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


if __name__ == "__main__":
    main()
