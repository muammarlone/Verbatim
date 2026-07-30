from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "quality"


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_server(url: str, timeout_seconds: float = 20) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Local quality-UAT server did not become ready.")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    port = available_port()
    base_url = f"http://127.0.0.1:{port}"
    cases = [
        ("mobile-light", 375, 812, "light"),
        ("tablet-light", 768, 1024, "light"),
        ("desktop-light", 1440, 900, "light"),
        ("desktop-dark", 1440, 900, "dark"),
    ]
    errors: list[str] = []
    results: list[dict] = []
    server: subprocess.Popen | None = None

    with tempfile.TemporaryDirectory(prefix="verbatim-quality-uat-") as temporary:
        temporary_root = Path(temporary)
        model = temporary_root / "fixture-model.pt"
        model.write_bytes(b"quality-uat-readiness-fixture")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        environment["STS_DATA_DIR"] = str(temporary_root / "data")
        environment["STS_MODEL_PATH"] = str(model)
        server = subprocess.Popen(
            [sys.executable, "-m", "secure_transcribe", "--port", str(port), "--no-browser"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            wait_for_server(f"{base_url}/api/health")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                browser_version = browser.version
                for name, width, height, color_scheme in cases:
                    console_errors: list[str] = []
                    external_requests: list[str] = []
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        color_scheme=color_scheme,
                    )
                    page = context.new_page()
                    page.on(
                        "console",
                        lambda message: console_errors.append(message.text)
                        if message.type == "error"
                        else None,
                    )
                    page.on("pageerror", lambda error: console_errors.append(str(error)))
                    page.on(
                        "request",
                        lambda request: external_requests.append(request.url)
                        if not request.url.startswith(base_url)
                        else None,
                    )
                    started = time.monotonic()
                    response = page.goto(base_url, wait_until="networkidle")
                    load_ms = round((time.monotonic() - started) * 1000, 1)
                    if response is None or response.status != 200:
                        errors.append(f"{name}: root response was not 200")
                        context.close()
                        continue

                    page.locator("#single-mode-tab").focus()
                    page.keyboard.press("ArrowRight")
                    batch_selected = page.locator("#batch-mode-tab").get_attribute(
                        "aria-selected"
                    ) == "true"
                    batch_focused = page.locator("#batch-mode-tab").evaluate(
                        "element => element === document.activeElement"
                    )
                    page.keyboard.press("ArrowLeft")
                    single_selected = page.locator("#single-mode-tab").get_attribute(
                        "aria-selected"
                    ) == "true"

                    page.locator(".skip-link").focus()
                    page.keyboard.press("Enter")
                    skip_target_focused = page.locator("#main-content").evaluate(
                        "element => element === document.activeElement"
                    )
                    page.locator("#health-button").click()
                    dialog_visible = page.get_by_role(
                        "dialog", name="Local processing check"
                    ).is_visible()
                    page.locator("#health-dialog .dialog-close").click()

                    horizontal_overflow = page.evaluate(
                        "document.documentElement.scrollWidth > window.innerWidth"
                    )
                    computed_scheme = page.evaluate(
                        "matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'"
                    )
                    headers = {key.lower(): value for key, value in response.all_headers().items()}
                    security_headers = all(
                        headers.get(key) == value
                        for key, value in {
                            "cross-origin-opener-policy": "same-origin",
                            "cross-origin-resource-policy": "same-origin",
                            "x-content-type-options": "nosniff",
                            "x-frame-options": "DENY",
                            "x-permitted-cross-domain-policies": "none",
                            "referrer-policy": "no-referrer",
                        }.items()
                    ) and "default-src 'self'" in headers.get("content-security-policy", "")

                    checks = {
                        "batch_tab_arrow_navigation": batch_selected and batch_focused,
                        "single_tab_reverse_navigation": single_selected,
                        "skip_link_focuses_main": skip_target_focused,
                        "named_health_dialog": dialog_visible,
                        "no_horizontal_overflow": not horizontal_overflow,
                        "requested_color_scheme": computed_scheme == color_scheme,
                        "security_headers": security_headers,
                        "no_console_errors": not console_errors,
                        "no_external_requests": not external_requests,
                    }
                    failed_checks = sorted(key for key, passed in checks.items() if not passed)
                    errors.extend(f"{name}: {check}" for check in failed_checks)
                    if name in {"mobile-light", "desktop-dark"}:
                        page.screenshot(
                            path=EVIDENCE / f"{name}.png",
                            full_page=True,
                        )
                    results.append(
                        {
                            "case": name,
                            "viewport": {"width": width, "height": height},
                            "color_scheme": color_scheme,
                            "load_ms": load_ms,
                            "checks": checks,
                            "console_errors": console_errors,
                            "external_requests": external_requests,
                        }
                    )
                    context.close()
                browser.close()
        finally:
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    server.kill()

    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python": sys.version.split()[0],
            "browser": "Chromium",
            "browser_version": browser_version,
        },
        "data_classification": "synthetic readiness fixture; no media or credentials",
        "cases": results,
        "summary": {
            "total_cases": len(results),
            "passed_cases": sum(
                all(case["checks"].values()) for case in results
            ),
            "failed_cases": sum(
                not all(case["checks"].values()) for case in results
            ),
            "errors": errors,
            "validated": not errors and len(results) == len(cases),
        },
        "claim_boundary": (
            "Automated Chromium checks only; supported screen-reader and independent "
            "penetration testing remain open promotion gates."
        ),
    }
    (EVIDENCE / "browser-uat.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if not report["summary"]["validated"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
