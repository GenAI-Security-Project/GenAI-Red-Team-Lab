"""Tests for the LSB image steganography canary lab."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest
from PIL import Image

from stego_canary_lab import (
    DEFAULT_CANARY,
    decode_lsb_png,
    encode_lsb_png,
    inspect_lsb_png,
    run_demo,
    sanitize_lsb_png,
)


def test_rgba_and_rgb_roundtrip(tmp_path: Path) -> None:
    modes: tuple[Literal["RGBA", "RGB"], ...] = ("RGBA", "RGB")
    for mode in modes:
        out = tmp_path / f"canary_{mode.lower()}.png"
        encode_lsb_png(DEFAULT_CANARY, out, channels=mode)
        assert decode_lsb_png(out, channels=mode) == DEFAULT_CANARY


def test_rejects_non_canary_and_small_carrier(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="CANARY-"):
        encode_lsb_png("unlabelled-payload", tmp_path / "bad.png")

    tiny = tmp_path / "tiny.png"
    Image.new("RGB", (2, 2), color=(10, 20, 30)).save(tiny, format="PNG")
    with pytest.raises(ValueError, match="too small"):
        encode_lsb_png(
            DEFAULT_CANARY, tmp_path / "out.png", channels="RGB", carrier_path=tiny
        )


def test_inspect_and_sanitize(tmp_path: Path) -> None:
    stego = tmp_path / "stego.png"
    clean = tmp_path / "clean.png"
    encode_lsb_png(DEFAULT_CANARY, stego, channels="RGBA")

    info = inspect_lsb_png(stego, channels="RGBA")
    assert info["delimiter_detected"] is True
    assert info["recovered_canary"] == DEFAULT_CANARY

    report = sanitize_lsb_png(stego, clean, channels="RGBA")
    assert report["canary_before"] is True
    assert report["canary_after"] is False
    assert report["max_channel_delta"] <= 1


def test_run_demo(tmp_path: Path) -> None:
    res = run_demo(tmp_path / "demo")
    assert res["stego_carrier"]["recovered_canary"] == DEFAULT_CANARY
    assert res["sanitization"]["canary_after"] is False
