from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = PROJECT_ROOT / "src" / "secure_transcribe" / "static" / "index.html"
CSS_PATH = PROJECT_ROOT / "src" / "secure_transcribe" / "static" / "styles.css"


class SemanticAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.html_lang = ""
        self.main_count = 0
        self.skip_target = ""
        self.tabs: list[dict[str, str]] = []
        self.dialogs: list[dict[str, str]] = []
        self.videos: list[dict[str, str]] = []
        self.progressbars: list[dict[str, str]] = []
        self.buttons: list[dict[str, object]] = []
        self._button_stack: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if identifier := attributes.get("id"):
            self.ids.add(identifier)
        if tag == "html":
            self.html_lang = attributes.get("lang", "")
        if tag == "main":
            self.main_count += 1
        if tag == "a" and "skip-link" in attributes.get("class", "").split():
            self.skip_target = attributes.get("href", "")
        if attributes.get("role") == "tab":
            self.tabs.append(attributes)
        if tag == "dialog":
            self.dialogs.append(attributes)
        if tag == "video":
            self.videos.append(attributes)
        if attributes.get("role") == "progressbar":
            self.progressbars.append(attributes)
        if tag == "button":
            button: dict[str, object] = {"attrs": attributes, "text": []}
            self.buttons.append(button)
            self._button_stack.append(button)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._button_stack:
            self._button_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._button_stack and data.strip():
            self._button_stack[-1]["text"].append(data.strip())


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_static_ui_has_accessible_semantics_and_keyboard_tab_contracts() -> None:
    audit = SemanticAudit()
    audit.feed(HTML_PATH.read_text(encoding="utf-8"))

    assert audit.html_lang == "en"
    assert audit.main_count == 1
    assert audit.skip_target == "#main-content"
    assert "main-content" in audit.ids
    assert audit.tabs
    assert all(tab.get("aria-controls") in audit.ids for tab in audit.tabs)
    assert all(tab.get("tabindex") in {"0", "-1"} for tab in audit.tabs)
    assert sum(tab.get("aria-selected") == "true" for tab in audit.tabs) == 2
    assert audit.dialogs
    assert all(dialog.get("aria-labelledby") in audit.ids for dialog in audit.dialogs)
    assert audit.videos and all(video.get("aria-label") for video in audit.videos)
    assert audit.progressbars and all(
        progress.get("aria-valuemin") == "0"
        and progress.get("aria-valuemax") == "100"
        and progress.get("aria-valuenow") == "0"
        for progress in audit.progressbars
    )
    assert all(
        button["attrs"].get("aria-label") or " ".join(button["text"]).strip()
        for button in audit.buttons
    )

    javascript = (HTML_PATH.parent / "app.js").read_text(encoding="utf-8")
    assert 'bindTabKeyboard("[data-upload-mode]")' in javascript
    assert 'bindTabKeyboard(".tab-list [role=\'tab\']")' in javascript
    assert 'setAttribute("aria-valuenow", String(job.progress))' in javascript


def test_canonical_text_colors_meet_normal_text_contrast_floor() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    roots = re.findall(r":root\s*{([^}]+)}", css)
    assert len(roots) == 2
    light = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", roots[0]))
    dark_overrides = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", roots[1]))
    dark = light | dark_overrides

    for variables in (light, dark):
        pairs = [
            (variables["accent-strong"], variables["surface"]),
            (variables["ink-soft"], variables["surface"]),
            (variables["danger"], variables["surface"]),
            (variables["sidebar-muted"], variables["sidebar"]),
            (variables["on-accent"], variables["accent"]),
            (variables["on-danger"], variables["danger"]),
            (variables["warning-text"], variables["warning-soft"]),
        ]
        assert all(
            _contrast(foreground, background) >= 4.5 for foreground, background in pairs
        )
