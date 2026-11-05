"""udmx-strips: control RGBW LED strips through a uDMX USB interface."""

from .colors import ColorError, NAMED_COLORS, parse_color, scale_color
from .controller import DMXStrips
from .device import (
    DeviceNotFoundError, DummyDevice, PermissionDeniedError,
    TransferError, UDMX, UDMXError,
)

__all__ = [
    "DMXStrips", "UDMX", "DummyDevice", "parse_color", "scale_color",
    "NAMED_COLORS", "ColorError", "UDMXError", "DeviceNotFoundError",
    "PermissionDeniedError", "TransferError",
]
__version__ = "1.0.0"
