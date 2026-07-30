from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "explainer"
BUILD = OUT / "build"
NARRATION = BUILD / "narration"
CARDS = BUILD / "cards"
SCENES = BUILD / "scenes"
FINAL = OUT / "verbatim-grounded-product-explainer.mp4"
WIDTH, HEIGHT = 1440, 900

FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
FONT_SERIF = Path("C:/Windows/Fonts/georgiab.ttf")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, cwd=ROOT)


def duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def wrapped(draw: ImageDraw.ImageDraw, text: str, face, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def base_card() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#F4F2EC")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((54, 48, 1386, 852), radius=30, fill="#FFFEF9")
    draw.rectangle((54, 48, 78, 852), fill="#176B54")
    draw.text((112, 82), "VERBATIM  /  GROUNDED PRODUCT EXPLAINER", font=font(FONT_BOLD, 20), fill="#176B54")
    draw.text((112, 808), "SYNTHETIC EVIDENCE  •  LOCAL-ONLY DEMONSTRATION", font=font(FONT_BOLD, 16), fill="#68756F")
    return image


def draw_card(number: int, title: str, subtitle: str, bullets: list[str], *, hero: Path | None = None) -> Path:
    image = base_card()
    draw = ImageDraw.Draw(image)
    text_right = 1320 if hero is None else 705
    draw.text((112, 145), f"{number:02d}", font=font(FONT_SERIF, 38), fill="#B66B1A")
    y = 205
    title_face = font(FONT_SERIF, 54 if len(title) < 32 else 46)
    for line in wrapped(draw, title, title_face, text_right - 112):
        draw.text((112, y), line, font=title_face, fill="#17201D")
        y += title_face.size + 7
    subtitle_face = font(FONT_REGULAR, 24)
    y += 18
    for line in wrapped(draw, subtitle, subtitle_face, text_right - 112):
        draw.text((112, y), line, font=subtitle_face, fill="#35433E")
        y += 34
    y += 20
    bullet_face = font(FONT_REGULAR, 23)
    for item in bullets:
        draw.ellipse((116, y + 8, 128, y + 20), fill="#176B54")
        lines = wrapped(draw, item, bullet_face, text_right - 158)
        for line_index, line in enumerate(lines):
            draw.text((148, y + line_index * 32), line, font=bullet_face, fill="#17201D")
        y += max(48, len(lines) * 32 + 14)
    if hero is not None:
        source = Image.open(hero).convert("RGB")
        source.thumbnail((600, 570), Image.Resampling.LANCZOS)
        backdrop = source.filter(ImageFilter.GaussianBlur(18))
        backdrop = ImageEnhance.Brightness(backdrop).enhance(0.78)
        frame = Image.new("RGB", (610, 580), "#17201D")
        frame.paste(backdrop.resize((590, 560)), (10, 10))
        frame.paste(source, ((610 - source.width) // 2, (580 - source.height) // 2))
        image.paste(frame, (742, 165))
    path = CARDS / f"scene-{number:02d}.png"
    image.save(path, optimize=True)
    return path


def make_scene(number: int, visual: Path, audio: Path, *, start: float | None = None, label: str | None = None) -> Path:
    target = SCENES / f"scene-{number:02d}.mp4"
    audio_length = duration(audio) + 1.0
    if start is None:
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(visual), "-i", str(audio)]
    else:
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-i", str(visual), "-i", str(audio)]
    video_filter = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x17201D,setsar=1,"
        "fade=t=in:st=0:d=0.35,"
        f"fade=t=out:st={max(0.1, audio_length - 0.45):.3f}:d=0.4"
    )
    if label:
        safe_label = label.replace(":", "\\:").replace("'", "")
        video_filter += (
            ",drawbox=x=36:y=h-72:w=640:h=42:color=0x17201D@0.9:t=fill,"
            f"drawtext=fontfile='C\\:/Windows/Fonts/segoeuib.ttf':text='{safe_label}':"
            "fontcolor=white:fontsize=18:x=54:y=h-61"
        )
    command += [
        "-t",
        f"{audio_length:.3f}",
        "-vf",
        video_filter,
        "-af",
        "apad=pad_dur=1,loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.15",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "25",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-ac",
        "1",
        "-shortest",
        str(target),
    ]
    run(command)
    return target


def main() -> None:
    for directory in (OUT, BUILD, NARRATION, CARDS, SCENES):
        directory.mkdir(parents=True, exist_ok=True)
    required = [FONT_REGULAR, FONT_BOLD, FONT_SERIF]
    if any(not item.is_file() for item in required):
        raise SystemExit("Required Windows fonts are unavailable.")

    single = ROOT / "evidence" / "demo" / "verbatim-end-to-end-demo.mp4"
    batch = ROOT / "evidence" / "batch-demo" / "verbatim-batch-end-to-end-demo.mp4"
    hero = ROOT / "evidence" / "screenshots" / "review-desktop.png"
    if any(not item.is_file() for item in (single, batch, hero)):
        raise SystemExit("Verified source footage is missing.")

    card_specs = {
        1: ("Local transcription with an explicit boundary", "What the product does today", ["Single-user Windows utility", "On-device Whisper and local media tools", "Synthetic evidence, not a production claim"], hero),
        5: ("Cleanup is explicit, not magical", "Know which copies Verbatim controls", ["Single jobs remove the managed source and derived files", "Batch cleanup preserves original inputs and requested outputs", "Downloads, backups, and indexes remain external"], None),
        6: ("Planned is not available", "Protected and remote intake remain gated", ["Manifest preview: backend-only and disabled by default", "Password-protected archive extraction: not implemented", "Zoom retrieval and signed deployment: not implemented"], None),
        7: ("Where Verbatim is strong", "Controls that are implemented and tested", ["Local processing and no silent model download", "Time-linked human review", "Bounded paths, sizes, durations, and workers", "Portable outputs with provenance"], None),
        8: ("The trade-offs are real", "Local-first shifts responsibility; it does not remove it", ["Endpoint CPU, disk, ACL, encryption, and patching matter", "Accuracy changes with audio and domain", "Rule-based cues can miss context", "Exports leave the managed deletion boundary"], None),
        9: ("Use it as a review tool", "A safe operating sequence", ["Verify authority and readiness", "Use approved local storage", "Check consequential text against the source", "Export only to governed destinations", "Apply retention and deletion to every copy"], None),
        10: ("Evidence supports a controlled demo", "Measured results and open gates", ["92 tests; 84% Python branch coverage", "23 deterministic architecture gates", "4 responsive browser quality cases", "Pilot blocked: 6 open principal-architect gates"], None),
    }
    cards = {number: draw_card(number, *spec[:3], hero=spec[3]) for number, spec in card_specs.items()}

    inputs = {
        1: (cards[1], None, None),
        2: (single, 7.0, "VERIFIED SYNTHETIC SINGLE-FILE WORKFLOW"),
        3: (single, 72.0, "TIME-LINKED REVIEW AND EXPORT"),
        4: (batch, 7.0, "VERIFIED SYNTHETIC TWO-FILE BATCH"),
        5: (cards[5], None, None),
        6: (cards[6], None, None),
        7: (cards[7], None, None),
        8: (cards[8], None, None),
        9: (cards[9], None, None),
        10: (cards[10], None, None),
    }
    scene_paths: list[Path] = []
    for number, (visual, start, label) in inputs.items():
        audio = NARRATION / f"scene-{number:02d}.wav"
        if not audio.is_file():
            raise SystemExit(f"Missing narration: {audio}")
        scene_paths.append(make_scene(number, visual, audio, start=start, label=label))

    concat_file = BUILD / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in scene_paths), encoding="utf-8"
    )
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(FINAL),
        ]
    )
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            "5",
            "-i",
            str(FINAL),
            "-frames:v",
            "1",
            str(OUT / "explainer-poster.png"),
        ]
    )
    run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(FINAL),
            "-vf",
            "fps=1/25,scale=480:300,tile=3x4:padding=6:margin=6",
            "-frames:v",
            "1",
            str(OUT / "explainer-contact-sheet.png"),
        ]
    )

    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video": str(FINAL.relative_to(ROOT)),
        "duration_seconds": round(duration(FINAL), 3),
        "sha256": sha256(FINAL),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": 25,
        "scenes": len(scene_paths),
        "source_videos": [
            {"path": str(single.relative_to(ROOT)), "sha256": sha256(single)},
            {"path": str(batch.relative_to(ROOT)), "sha256": sha256(batch)},
        ],
        "claim_boundary": (
            "Synthetic controlled evidence only; no general accuracy, production security, "
            "accessibility, compliance, deployment approval, or ROI claim."
        ),
    }
    (OUT / "explainer-evidence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
