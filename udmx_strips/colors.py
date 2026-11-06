"""Color parsing: turn terminal-friendly text into (R, G, B) tuples."""

import difflib
import re
from typing import Sequence, Tuple, Union

RGB = Tuple[int, int, int]
ColorLike = Union[str, Sequence[int]]


class ColorError(ValueError):
    """Raised when a color cannot be understood."""


NAMED_COLORS = {
    "off":        (0, 0, 0),
    "black":      (0, 0, 0),
    "red":        (255, 0, 0),
    "orange":     (255, 120, 0),
    "yellow":     (255, 220, 0),
    "green":      (0, 255, 0),
    "lime":       (128, 255, 0),
    "cyan":       (0, 255, 255),
    "blue":       (0, 0, 255),
    "purple":     (160, 0, 255),
    "magenta":    (255, 0, 255),
    "pink":       (255, 20, 147),
    "white":      (255, 255, 255),
    "warm-white": (255, 170, 80),
}


def _key(name: str) -> str:
    return re.sub(r"[\s_\-]+", "", name.strip().lower())


_LOOKUP = {_key(name): value for name, value in NAMED_COLORS.items()}
_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _check_channels(values: Sequence[float], text: str) -> RGB:
    if len(values) != 3:
        raise ColorError(f"{text!r}: expected 3 values (R,G,B)")
    out = []
    for v in values:
        if isinstance(v, bool) or int(v) != v:
            raise ColorError(f"{text!r}: channel values must be integers")
        if not 0 <= int(v) <= 255:
            raise ColorError(f"{text!r}: channel values must be 0-255")
        out.append(int(v))
    return tuple(out)  # type: ignore[return-value]


def parse_color(value: ColorLike) -> RGB:
    """
    Accepts:
        "red", "warm-white", "OFF"          named colors
        "#ff8800", "ff8800", "#f80"         hex
        "255,136,0"                         decimal R,G,B
        (255, 136, 0)                       tuple or list
    Returns (R, G, B).
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
            [int(digits[i:i + 2], 16) for i in range(0, 6, 2)], text
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


def scale_color(color: RGB, brightness: float) -> RGB:
    """Scale all channels by brightness (0.0 - 1.0)."""
    if not 0.0 <= brightness <= 1.0:
        raise ValueError("brightness must be between 0.0 and 1.0")
    return tuple(int(round(c * brightness)) for c in color)  # type: ignore
