"""Color parsing: turn terminal-friendly text into (R, G, B, W) tuples."""

import difflib
import re
from typing import Sequence, Tuple, Union

RGBW = Tuple[int, int, int, int]
ColorLike = Union[str, Sequence[int]]


class ColorError(ValueError):
    """Raised when a color cannot be understood."""


# name -> (R, G, B, W)
NAMED_COLORS = {
    "off":        (0, 0, 0, 0),
    "black":      (0, 0, 0, 0),
    "red":        (255, 0, 0, 0),
    "orange":     (255, 120, 0, 0),
    "yellow":     (255, 220, 0, 0),
    "green":      (0, 255, 0, 0),
    "lime":       (128, 255, 0, 0),
    "cyan":       (0, 255, 255, 0),
    "blue":       (0, 0, 255, 0),
    "purple":     (160, 0, 255, 0),
    "magenta":    (255, 0, 255, 0),
    "pink":       (255, 20, 147, 0),
    "white":      (0, 0, 0, 255),          # white LED only
    "warm-white": (255, 120, 40, 200),
    "full-white": (255, 255, 255, 255),    # every LED at full power
}


def _key(name: str) -> str:
    return re.sub(r"[\s_\-]+", "", name.strip().lower())


_LOOKUP = {_key(name): value for name, value in NAMED_COLORS.items()}
_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _check_channels(values: Sequence[int], text: str) -> RGBW:
    if len(values) not in (3, 4):
        raise ColorError(f"{text!r}: expected 3 (R,G,B) or 4 (R,G,B,W) values")
    out = []
    for v in values:
        if isinstance(v, bool) or int(v) != v:
            raise ColorError(f"{text!r}: channel values must be integers")
        if not 0 <= int(v) <= 255:
            raise ColorError(f"{text!r}: channel values must be 0-255")
        out.append(int(v))
    if len(out) == 3:
        out.append(0)
    return tuple(out)  # type: ignore[return-value]


def parse_color(value: ColorLike) -> RGBW:
    """
    Accepts:
        "red", "warm-white", "OFF"          named colors
        "#ff8800", "ff8800", "#f80"         hex RGB
        "ff880080"                          hex RGBW (last byte = white)
        "255,136,0" or "255,136,0,64"       decimal R,G,B[,W]
        (255, 136, 0) / (255, 136, 0, 64)   tuples or lists
    Returns (R, G, B, W).
    """
    if not isinstance(value, str):
        return _check_channels(list(value), str(value))

    text = value.strip()
    if not text:
        raise ColorError("empty color")

    named = _LOOKUP.get(_key(text))
    if named is not None:
        return named

    match = _HEX.match(text)
    if match:
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        return _check_channels(
            [int(digits[i:i + 2], 16) for i in range(0, len(digits), 2)], text
        )

    if "," in text or " " in text:
        parts = [p for p in re.split(r"[,\s]+", text) if p]
        try:
            numbers = [float(p) for p in parts]
        except ValueError:
            numbers = None
        if numbers is not None:
            return _check_channels(numbers, text)

    hint = difflib.get_close_matches(_key(text), _LOOKUP.keys(), n=1)
    suggestion = f" Did you mean {hint[0]!r}?" if hint else ""
    raise ColorError(f"unknown color {text!r}.{suggestion}")


def scale_color(color: RGBW, brightness: float) -> RGBW:
    """Scale all four channels by brightness (0.0 - 1.0)."""
    if not 0.0 <= brightness <= 1.0:
        raise ValueError("brightness must be between 0.0 and 1.0")
    return tuple(int(round(c * brightness)) for c in color)  # type: ignore
