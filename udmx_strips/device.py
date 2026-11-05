"""Low-level uDMX (Anyma) USB access."""

import errno
import sys
from typing import Optional, Sequence

import usb.core
import usb.util

try:
    import libusb_package
except ImportError:           # Linux/macOS normally use the system libusb
    libusb_package = None

VID = 0x16C0
PID = 0x05DC

_CMD_SET_CHANNEL_RANGE = 0x02
_REQUEST_TYPE_OUT = 0x40      # vendor | host-to-device


class UDMXError(RuntimeError):
    """Base class for device errors."""


class DeviceNotFoundError(UDMXError):
    pass


class PermissionDeniedError(UDMXError):
    pass


class TransferError(UDMXError):
    pass


LINUX_PERMISSION_HINT = (
    "Permission denied talking to the uDMX.\n"
    "  Quick test:  run with sudo.\n"
    "  Permanent:   sudo cp 99-udmx.rules /etc/udev/rules.d/ && "
    "sudo udevadm control --reload && sudo udevadm trigger\n"
    "               then unplug and replug the uDMX."
)


def _is_permission_error(error: usb.core.USBError) -> bool:
    return (
        getattr(error, "errno", None) in (errno.EACCES, errno.EPERM)
        or "denied" in str(error).lower()
        or "permission" in str(error).lower()
    )


class UDMX:
    """
    Thin wrapper around the uDMX USB device.

    The uDMX keeps its DMX buffer while powered, so values written here stay
    on the lights after your program exits.
    """

    def __init__(self, auto_open: bool = True):
        self.device = None
        if auto_open:
            self.open()

    # ---------------- lifecycle ----------------

    @property
    def is_open(self) -> bool:
        return self.device is not None

    def open(self) -> None:
        backend = libusb_package.get_libusb1_backend() if libusb_package else None

        try:
            devices = list(
                usb.core.find(find_all=True, backend=backend,
                              idVendor=VID, idProduct=PID)
            )
        except usb.core.NoBackendError:
            raise UDMXError(
                "libusb was not found.\n"
                "  Linux:   sudo apt install libusb-1.0-0\n"
                "  Windows: python -m pip install libusb-package"
            )

        if not devices:
            raise DeviceNotFoundError(
                "uDMX not found (VID 16C0, PID 05DC). Check the USB cable"
                + (" and the udev rule (see README)."
                   if sys.platform.startswith("linux")
                   else " and the WinUSB driver (Zadig).")
            )

        device = self._prefer_udmx(devices)

        if sys.platform.startswith("linux"):
            try:
                if device.is_kernel_driver_active(0):
                    device.detach_kernel_driver(0)
            except (NotImplementedError, usb.core.USBError, ValueError):
                pass

        try:
            device.set_configuration()
        except usb.core.USBError as error:
            if _is_permission_error(error):
                raise PermissionDeniedError(LINUX_PERMISSION_HINT)
            # "already configured" and similar are harmless

        self.device = device

    @staticmethod
    def _prefer_udmx(devices):
        """16C0:05DC is a shared V-USB id; prefer a device named like a uDMX."""
        for dev in devices:
            try:
                product = usb.util.get_string(dev, dev.iProduct) or ""
            except Exception:
                continue
            if "dmx" in product.lower():
                return dev
        return devices[0]

    def close(self) -> None:
        if self.device is not None:
            try:
                usb.util.dispose_resources(self.device)
            except Exception:
                pass
        self.device = None

    def __enter__(self):
        if not self.is_open:
            self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    # ---------------- DMX output ----------------

    def send_channels(self, start_channel: int, values: Sequence[int]) -> None:
        """Write consecutive DMX channels beginning at start_channel (1-512)."""
        if self.device is None:
            raise UDMXError("device is not open")
        if not values:
            return
        if start_channel < 1 or start_channel + len(values) - 1 > 512:
            raise ValueError("DMX data must fit inside channels 1-512")
        if any(not 0 <= int(v) <= 255 for v in values):
            raise ValueError("DMX values must be between 0 and 255")

        try:
            self.device.ctrl_transfer(
                _REQUEST_TYPE_OUT,
                _CMD_SET_CHANNEL_RANGE,
                len(values),             # wValue: channel count
                start_channel - 1,       # wIndex: zero-based first channel
                bytes(int(v) for v in values),
                timeout=2000,
            )
        except usb.core.USBError as error:
            if _is_permission_error(error):
                raise PermissionDeniedError(LINUX_PERMISSION_HINT)
            self.close()
            raise TransferError(f"USB write failed: {error}")


class DummyDevice:
    """Stand-in device for testing and --dry-run. Records what would be sent."""

    def __init__(self, echo: bool = False):
        self.echo = echo
        self.writes = []
        self.is_open = True

    def send_channels(self, start_channel: int, values: Sequence[int]) -> None:
        self.writes.append((start_channel, list(values)))
        if self.echo:
            print(f"[dry-run] CH{start_channel}+{len(values)}: "
                  + " ".join(f"{v:3d}" for v in values))

    def close(self) -> None:
        self.is_open = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
