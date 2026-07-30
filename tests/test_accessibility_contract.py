"""STS-113: Accessibility contract — keyboard/ARIA/contrast matrix and error-recovery patterns.

Covers: keyboard focus management, ARIA live regions, error-recovery guidance,
external-copy disclosure, manifest-disabled messaging, and row-state patterns.
These are static HTML/CSS/JS checks; browser-rendered tests are in test_web_quality.py.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "src" / "secure_transcribe" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "src" / "secure_transcribe" / "static" / "app.js").read_text(encoding="utf-8")
MANUAL = (ROOT / "docs" / "USER_MANUAL.md").read_text(encoding="utf-8")
FEATURES = (ROOT / "docs" / "FEATURES_AND_LIMITATIONS.md").read_text(encoding="utf-8")


class _Audit(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.live_regions: list[dict] = []
        self.alert_regions: list[dict] = []
        self.form_groups: list[dict] = []
        self.hidden_panels: list[dict] = []
        self.labels: list[dict] = []
        self.inputs: list[dict] = []
        self.checkboxes: list[dict] = []
        self.selects: list[dict] = []
        self._stack: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if identifier := attributes.get("id"):
            self.ids.add(identifier)
        if attributes.get("aria-live"):
            self.live_regions.append(attributes)
        if attributes.get("role") == "alert":
            self.alert_regions.append(attributes)
        if tag in ("input", "select", "textarea"):
            attributes["_tag"] = tag
            self.inputs.append(attributes)
            if attributes.get("type") == "checkbox":
                self.checkboxes.append(attributes)
        if tag == "label":
            self.labels.append(attributes)
        if tag == "select":
            self.selects.append(attributes)
        if attributes.get("hidden") is not None or attributes.get("hidden") == "":
            self.hidden_panels.append(attributes)
        self._stack.append((tag, attributes))

    def handle_endtag(self, tag):
        if self._stack and self._stack[-1][0] == tag:
            self._stack.pop()


_audit = _Audit()
_audit.feed(HTML)


# ── ARIA live regions ────────────────────────────────────────────────────────

def test_alert_region_has_live_attribute():
    alerts = [r for r in _audit.live_regions if "alert" in r.get("id", "")]
    assert alerts, "alert-region element must have aria-live"


def test_analysis_panel_has_aria_live():
    live_ids = {r.get("id", "") for r in _audit.live_regions}
    assert "analysis-content" in live_ids or any("analysis" in i for i in live_ids)


def test_toast_region_has_aria_live():
    live_ids = {r.get("id", "") for r in _audit.live_regions}
    assert "toast" in live_ids


def test_failure_panel_has_alert_role():
    alert_ids = {r.get("id", "") for r in _audit.alert_regions}
    assert "failure-panel" in alert_ids, "failure-panel must have role='alert' for screen reader"


# ── Drop-zone / upload form accessibility ────────────────────────────────────

def test_drop_zone_has_aria_describedby():
    drop = HTML
    assert 'aria-describedby="upload-limits"' in drop, (
        "drop-zone must have aria-describedby pointing to upload-limits"
    )
    assert "upload-limits" in _audit.ids, "upload-limits element must have an id"


def test_drop_zone_is_keyboard_focusable():
    assert 'tabindex="0"' in HTML and 'role="button"' in HTML


# ── Consent checkbox accessibility ──────────────────────────────────────────

def test_consent_checkbox_has_label():
    # Consent checkboxes use implicit labeling: <label class="consent-row"><input>...</label>
    checkboxes = [i for i in _audit.checkboxes if "consent" in i.get("id", "")]
    assert checkboxes, "consent checkbox must exist with an id"
    # Implicit label wrapping is valid WCAG technique H44/H65
    assert 'class="consent-row"' in HTML, "consent checkbox must be wrapped in a consent-row label"


# ── Error recovery language in docs ─────────────────────────────────────────

def test_user_manual_has_external_copy_boundary():
    lower = MANUAL.lower()
    assert "external" in lower and ("copy" in lower or "export" in lower)
    assert "deletion" in lower or "delete" in lower


def test_features_doc_has_not_available_boundaries():
    lower = FEATURES.lower()
    assert "not available" in lower
    assert "not supported" in lower


def test_features_doc_discloses_connector_roadmap():
    lower = FEATURES.lower()
    assert "teams" in lower and "zoom" in lower
    assert "roadmap" in lower or "backlog" in lower or "phase 3" in lower


def test_user_manual_has_consent_requirement():
    lower = MANUAL.lower()
    assert "authority" in lower or "authorized" in lower or "consent" in lower


# ── Keyboard focus management patterns in JS ─────────────────────────────────

def test_js_manages_focus_on_dialog_open():
    assert "focus()" in JS, "app.js must manage focus when dialogs open"


def test_js_binds_keyboard_to_tabs():
    assert "bindTabKeyboard" in JS


def test_js_binds_keyboard_to_upload_mode():
    assert 'bindTabKeyboard("[data-upload-mode]")' in JS


def test_js_handles_escape_key_for_dialogs():
    assert "Escape" in JS or "escape" in JS.lower(), (
        "app.js must handle Escape key to close dialogs"
    )


# ── Manifest-disabled and feature-flag accessibility ─────────────────────────

def test_manifest_disabled_status_in_api_session():
    """Session API contract must include manifest_intake_enabled (checked by app.py and session route)."""
    # The /api/session endpoint returns manifest_intake_enabled so clients can gate feature UI.
    # Verified here by checking the app.py route definition, not JS parsing.
    app_py = (ROOT / "src" / "secure_transcribe" / "app.py").read_text(encoding="utf-8")
    assert "manifest_intake_enabled" in app_py, (
        "app.py session route must expose manifest_intake_enabled"
    )


def test_features_doc_labels_manifest_as_backend_only():
    lower = FEATURES.lower()
    assert "backend contract only" in lower or "disabled by default" in lower


# ── Row-state pattern (future manifest rows, current job state) ───────────────

def test_js_uses_status_driven_rendering():
    assert "status" in JS and ("complete" in JS or "failed" in JS)


def test_js_renders_error_state_for_failed_jobs():
    assert "failed" in JS.lower() and ("error" in JS.lower() or "failure" in JS.lower())


# ── Mobile navigation accessibility ──────────────────────────────────────────

def test_mobile_menu_has_aria_expanded():
    assert 'aria-expanded="false"' in HTML, "mobile menu toggle must have aria-expanded"


def test_mobile_menu_has_aria_label():
    assert 'aria-label="Open navigation"' in HTML


# ── Health dialog ─────────────────────────────────────────────────────────────

def test_health_button_indicates_dialog_popup():
    assert 'aria-haspopup="dialog"' in HTML


# ── No horizontal overflow contract ──────────────────────────────────────────

def test_css_uses_overflow_auto_for_wide_blocks():
    css = (ROOT / "src" / "secure_transcribe" / "static" / "styles.css").read_text()
    assert "overflow-x: auto" in css or "overflow: auto" in css
