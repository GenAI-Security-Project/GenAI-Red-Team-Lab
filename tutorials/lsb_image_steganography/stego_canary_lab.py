"""Lossless PNG LSB steganography canary encoder, decoder, inspector, and sanitizer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal, Sequence

from PIL import Image

ChannelMode = Literal["RGB", "RGBA"]
DEFAULT_DELIMITER = "====EOF===="
DEFAULT_CANARY = "CANARY-OWASP-LSB-7F3A: harmless multimodal verification seed"


def _check_params(channels: ChannelMode, delimiter: str) -> int:
    if channels not in ("RGB", "RGBA"):
        raise ValueError("channels must be 'RGB' or 'RGBA'")
    if not delimiter:
        raise ValueError("delimiter must be non-empty")
    return 4 if channels == "RGBA" else 3


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_lsb_png(
    canary_text: str,
    output_path: Path,
    *,
    channels: ChannelMode = "RGBA",
    delimiter: str = DEFAULT_DELIMITER,
    carrier_path: Path | None = None,
) -> Path:
    """Embed a harmless CANARY- string into the LSB plane of a lossless PNG."""
    cpp = _check_params(channels, delimiter)
    if not canary_text.strip().startswith("CANARY-"):
        raise ValueError("canary_text must start with 'CANARY-'")

    payload = canary_text.encode("utf-8")
    delim = delimiter.encode("utf-8")
    framed = payload + delim
    if framed.find(delim) != len(payload):
        raise ValueError("canary_text collides with delimiter")
    needed_bits = len(framed) * 8

    if carrier_path is not None:
        with Image.open(carrier_path) as existing:
            cover = existing.convert(channels).copy()
        if needed_bits > cover.width * cover.height * cpp:
            raise ValueError("carrier image too small for payload")
    else:
        side = max(64, math.ceil(math.sqrt(math.ceil(needed_bits / cpp))))
        bg = (240, 244, 248, 255) if channels == "RGBA" else (240, 244, 248)
        cover = Image.new(channels, (side, side), color=bg)

    raw = bytearray(cover.tobytes())
    bit_idx = 0
    for byte_val in framed:
        for shift in range(7, -1, -1):
            raw[bit_idx] = (raw[bit_idx] & 0xFE) | ((byte_val >> shift) & 1)
            bit_idx += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.frombytes(channels, cover.size, bytes(raw)).save(output_path, format="PNG")
    return output_path


def decode_lsb_png(
    image_path: Path,
    *,
    channels: ChannelMode = "RGBA",
    delimiter: str = DEFAULT_DELIMITER,
) -> str:
    """Extract a delimiter-terminated UTF-8 string from PNG channel LSBs."""
    _check_params(channels, delimiter)
    with Image.open(image_path) as img:
        raw = img.convert(channels).tobytes()

    delim = delimiter.encode("utf-8")
    buf = bytearray()
    cur = 0
    bits = 0
    for val in raw:
        cur = (cur << 1) | (val & 1)
        bits += 1
        if bits == 8:
            buf.append(cur)
            if buf.endswith(delim):
                return bytes(buf[: -len(delim)]).decode("utf-8")
            cur = 0
            bits = 0
    raise ValueError(f"delimiter {delimiter!r} not found")


def inspect_lsb_png(
    image_path: Path,
    *,
    channels: ChannelMode = "RGBA",
    delimiter: str = DEFAULT_DELIMITER,
) -> dict[str, Any]:
    """Return bit-plane transition stats and any decoded canary string."""
    _check_params(channels, delimiter)
    with Image.open(image_path) as img:
        conv = img.convert(channels)
        width, height = conv.size
        raw = conv.tobytes()

    sample = [b & 1 for b in raw[: min(len(raw), 4096)]]
    transitions = sum(1 for i in range(1, len(sample)) if sample[i] != sample[i - 1])
    try:
        recovered: str | None = decode_lsb_png(
            image_path, channels=channels, delimiter=delimiter
        )
    except ValueError:
        recovered = None

    return {
        "sha256": sha256_file(image_path),
        "size": [width, height],
        "channels": channels,
        "lsb_ones_ratio": round(sum(sample) / len(sample), 4),
        "lsb_transition_rate": round(transitions / max(1, len(sample) - 1), 4),
        "delimiter_detected": recovered is not None,
        "recovered_canary": recovered,
    }


def sanitize_lsb_png(
    image_path: Path,
    output_path: Path,
    *,
    channels: ChannelMode = "RGBA",
    delimiter: str = DEFAULT_DELIMITER,
) -> dict[str, Any]:
    """Strip ancillary metadata and zero the LSB of every pixel channel."""
    before = inspect_lsb_png(image_path, channels=channels, delimiter=delimiter)
    with Image.open(image_path) as img:
        conv = img.convert(channels)
        orig_bytes = conv.tobytes()
        scrubbed = bytes(b & 0xFE for b in orig_bytes)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.frombytes(channels, conv.size, scrubbed).save(output_path, format="PNG")

    after = inspect_lsb_png(output_path, channels=channels, delimiter=delimiter)
    max_delta = max((abs(a - b) for a, b in zip(orig_bytes, scrubbed)), default=0)
    return {
        "input_sha256": before["sha256"],
        "output_sha256": after["sha256"],
        "max_channel_delta": max_delta,
        "canary_before": before["delimiter_detected"],
        "canary_after": after["delimiter_detected"],
    }


def run_demo(work_dir: Path) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    cover = work_dir / "clean_cover.png"
    stego = work_dir / "stego_canary.png"
    clean = work_dir / "sanitized.png"

    Image.new("RGBA", (64, 64), color=(240, 244, 248, 255)).save(cover, format="PNG")
    encode_lsb_png(DEFAULT_CANARY, stego, channels="RGBA", carrier_path=cover)
    return {
        "clean_cover": inspect_lsb_png(cover, channels="RGBA"),
        "stego_carrier": inspect_lsb_png(stego, channels="RGBA"),
        "sanitization": sanitize_lsb_png(stego, clean, channels="RGBA"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LSB steganography canary lab.")
    parser.add_argument("--work-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args(argv)
    print(json.dumps(run_demo(args.work_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
