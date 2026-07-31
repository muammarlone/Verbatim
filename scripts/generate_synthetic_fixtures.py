"""Generate synthetic media fixture files for all 8 supported source formats.

Each file contains valid format magic bytes so it passes
`validate_media_signature()` in src/secure_transcribe/security.py. The files
hold no actual audio; they are minimal stubs that satisfy the format guard and
can be uploaded through the API in tests without triggering FFprobe or Whisper.

Formats and their validation paths (from security.py):
  MP4/M4A  — bytes 4-8 == b"ftyp"  (ftyp box, ISO BMFF)
  WAV      — bytes 0-3 == b"RIFF", bytes 8-11 == b"WAVE"
  MP3      — bytes 0-2 == b"ID3"   (ID3v2 tag header)
  FLAC     — bytes 0-3 == b"fLaC"  (FLAC stream marker)
  OGG      — bytes 0-3 == b"OggS"  (OGG page capture pattern)
  AAC      — deferred to FFprobe; stub uses ADTS sync word (0xFF 0xF1)
  WMA      — deferred to FFprobe; stub uses ASF header GUID
  (WMA deferred GUID: 30 26 B2 75 8E 66 CF 11 A6 D9 00 AA 00 62 CE 6C)

Run once to create/refresh the fixture directory:
  python scripts/generate_synthetic_fixtures.py

Files are written to tests/fixtures/. Safe to re-run; existing files are
overwritten with identical bytes (deterministic output).

CLAIM BOUNDARY: These are synthetic stubs for format-validation testing. They
do not represent real audio content and must never be used as transcription
accuracy evidence. See tests/eval/synthetic_fixtures.py for the transcript
accuracy eval dataset.
"""
from __future__ import annotations

import struct
import wave
from io import BytesIO
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def _mp4_bytes(brand: bytes = b"isom") -> bytes:
    """Minimal valid ftyp box: size(4) + 'ftyp'(4) + major_brand(4) + version(4)."""
    size = 16
    return struct.pack(">I", size) + b"ftyp" + brand + b"\x00\x00\x00\x00"


def _wav_bytes() -> bytes:
    """Minimal valid RIFF/WAVE with empty fmt + data chunks."""
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 3200)  # 100 ms of silence
    return buf.getvalue()


def _mp3_bytes() -> bytes:
    """Minimal ID3v2 header (10 bytes) so MP3 detection uses the ID3 path."""
    # ID3v2 header: "ID3" + version(2) + flags(1) + size(4, syncsafe)
    return b"ID3" + b"\x03\x00\x00" + b"\x00\x00\x00\x00" + b"\x00" * 64


def _flac_bytes() -> bytes:
    """fLaC marker + minimal STREAMINFO metadata block (stub, not playable)."""
    # STREAMINFO: block type 0, last-metadata flag 1 → header byte = 0x80
    # Length is 34 bytes; we pad with zeros for the streaminfo fields.
    header = b"fLaC"
    block_header = b"\x80" + b"\x00\x00\x22"  # last-meta flag | type=0, size=34
    block_data = b"\x00" * 34
    return header + block_header + block_data


def _ogg_bytes() -> bytes:
    """Minimal OGG capture pattern: 4-byte magic + stub page header."""
    # OGG page structure: magic(4) + version(1) + type(1) + granule(8) + serial(4)
    #                     + seq(4) + checksum(4) + segments(1) + ...
    magic = b"OggS"
    stub = b"\x00" * 60  # rest of minimal page stub (not CRC-valid, but magic passes)
    return magic + stub


def _aac_bytes() -> bytes:
    """Stub AAC file using ADTS sync word (0xFF 0xF1) — validation deferred to FFprobe."""
    # ADTS frame sync: 0xFFF (12 bits), ID=0 (MPEG-4), layer=0, protection=1
    # This file will fail FFprobe; security.py defers AAC to FFprobe so the
    # magic-byte check passes but a real upload would fail FFprobe validation.
    # Useful for testing the format-routing path, not the full upload pipeline.
    return b"\xff\xf1" + b"\x00" * 62


def _wma_bytes() -> bytes:
    """Stub WMA file using ASF header GUID — validation deferred to FFprobe."""
    # ASF Header Object GUID: {75B22630-668E-11CF-A6D9-00AA0062CE6C}
    # Little-endian on disk:
    guid = bytes([
        0x30, 0x26, 0xB2, 0x75,  # Data1
        0x8E, 0x66,              # Data2
        0xCF, 0x11,              # Data3
        0xA6, 0xD9,              # Data4[0:2]
        0x00, 0xAA, 0x00, 0x62, 0xCE, 0x6C,  # Data4[2:8]
    ])
    # Object size (8 bytes, LE): at least 30 bytes for a valid header stub
    size = struct.pack("<Q", 30)
    return guid + size + b"\x00" * 12


FIXTURES: dict[str, bytes] = {
    "synthetic_meeting.mp4": _mp4_bytes(b"isom"),
    "synthetic_voicememo.m4a": _mp4_bytes(b"M4A "),
    "synthetic_interview.mp3": _mp3_bytes(),
    "synthetic_conference.wav": _wav_bytes(),
    "synthetic_podcast.flac": _flac_bytes(),
    "synthetic_recording.ogg": _ogg_bytes(),
    "synthetic_audio.aac": _aac_bytes(),
    "synthetic_audio.wma": _wma_bytes(),
}


def generate(out_dir: Path = FIXTURE_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in FIXTURES.items():
        path = out_dir / name
        path.write_bytes(data)
        print(f"  wrote {path.name:35s}  {len(data):6d} bytes")


if __name__ == "__main__":
    print(f"Generating synthetic media fixtures in {FIXTURE_DIR.resolve()}")
    generate()
    print("Done.")
