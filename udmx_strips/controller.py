"""High-level API: set colors on RGBW strips."""

from typing import Iterable, Optional, Sequence

from .colors import ColorLike, RGBW, parse_color, scale_color
from .device import UDMX

CHANNELS_PER_STRIP = 4


class DMXStrips:
    """
    Control N RGBW strips laid out as consecutive DMX channels (R,G,B,W each).

        with DMXStrips() as strips:
            strips.set_all("red")
            strips.set_strip(3, "#00ff88")
            strips.set_colors(["red", "green", "blue"])   # strips 1-3
            strips.blackout()

    start_channel is the DMX address configured on your decoder.
    brightness (0.0-1.0) scales everything this object sends.
    """

    def __init__(self, device=None, num_strips: int = 6,
                 start_channel: int = 1, brightness: float = 1.0):
        if num_strips < 1:
            raise ValueError("num_strips must be at least 1")
        if start_channel < 1 or (
            start_channel + num_strips * CHANNELS_PER_STRIP - 1 > 512
        ):
            raise ValueError(
                f"{num_strips} strips starting at channel {start_channel} "
                "do not fit inside DMX channels 1-512"
            )
        self.num_strips = num_strips
        self.start_channel = start_channel
        self.brightness = brightness
        self._owns_device = device is None
        self.device = device if device is not None else UDMX()

    # ---------------- helpers ----------------

    def _prepare(self, color: ColorLike, white: Optional[int]) -> RGBW:
        r, g, b, w = parse_color(color)
        if white is not None:
            if not 0 <= white <= 255:
                raise ValueError("white must be between 0 and 255")
            w = white
        return scale_color((r, g, b, w), self.brightness)

    def _check_strip(self, strip: int) -> None:
        if not 1 <= strip <= self.num_strips:
            raise ValueError(
                f"strip must be between 1 and {self.num_strips}, got {strip}"
            )

    def channel_of(self, strip: int) -> int:
        """First DMX channel of a strip (1-based)."""
        self._check_strip(strip)
        return self.start_channel + (strip - 1) * CHANNELS_PER_STRIP

    # ---------------- API ----------------

    def set_strip(self, strip: int, color: ColorLike,
                  white: Optional[int] = None) -> RGBW:
        """Set one strip. Returns the (R,G,B,W) that was sent."""
        rgbw = self._prepare(color, white)
        self.device.send_channels(self.channel_of(strip), rgbw)
        return rgbw

    def set_strips(self, strips: Iterable[int], color: ColorLike,
                   white: Optional[int] = None) -> RGBW:
        """Set several strips to the same color; other strips are untouched."""
        strips = sorted(set(strips))
        for s in strips:
            self._check_strip(s)
        rgbw = self._prepare(color, white)
        for s in strips:
            self.device.send_channels(self.channel_of(s), rgbw)
        return rgbw

    def set_all(self, color: ColorLike, white: Optional[int] = None) -> RGBW:
        """Set every strip to one color in a single USB transfer."""
        rgbw = self._prepare(color, white)
        self.device.send_channels(
            self.start_channel, list(rgbw) * self.num_strips
        )
        return rgbw

    def set_colors(self, colors: Sequence[ColorLike],
                   first_strip: int = 1) -> None:
        """Give consecutive strips their own colors, starting at first_strip."""
        self._check_strip(first_strip)
        if first_strip + len(colors) - 1 > self.num_strips:
            raise ValueError("more colors than strips")
        data = []
        for color in colors:
            data.extend(self._prepare(color, None))
        self.device.send_channels(self.channel_of(first_strip), data)

    def blackout(self) -> None:
        """All strips off."""
        self.device.send_channels(
            self.start_channel, [0] * (self.num_strips * CHANNELS_PER_STRIP)
        )

    # ---------------- lifecycle ----------------

    def close(self) -> None:
        if self._owns_device:
            self.device.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
