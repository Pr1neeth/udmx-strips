# udmx-strips

Control RGB LED strips (3 DMX channels each) on a DMX decoder through a **uDMX** USB
interface. Works on **Linux** and Windows. Use it as a Python library or straight from
the terminal - the only input you need is a color.

The uDMX keeps its output while powered, so the color stays on after the command exits.

## Install

```bash
# Linux
sudo apt install libusb-1.0-0
pip install .                       # from this folder  (adds the `dmx` command)

# Windows
pip install .                       # also installs libusb-package; use Zadig to give the uDMX the WinUSB driver
```

### Linux: run without sudo

```bash
sudo cp 99-udmx.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
# unplug and replug the uDMX
```

Headless machine (e.g. Raspberry Pi over SSH)? Also run `sudo usermod -aG plugdev $USER` and log in again.

## Command line

```bash
dmx red                      # all strips red
dmx '#ff8800'                # hex (quote the # in a shell)
dmx 255,100,0                # R,G,B
dmx warm-white -b 40         # 40% brightness
dmx -s 2 blue                # strip 2 only, the others keep their color
dmx -s 1,3,5-6 green         # strips 1, 3, 5, 6
dmx red green blue           # strips 1, 2, 3 get their own colors
dmx off                      # everything off
dmx --list-colors
dmx --dry-run red            # print the DMX data, no hardware needed
```

Options: `-s/--strip`, `-b/--brightness 0-100`, `--strips N` (number of strips on your decoder, default 6),
`--start-channel CH` (your decoder's address, default 1, or set `UDMX_START_CHANNEL`), `-q`.

Colors: a name (`red orange yellow green lime cyan blue purple magenta pink white warm-white off`),
hex (`#f80`, `#ff8800`) or decimal `R,G,B`.

Exit codes: `0` ok, `1` device/hardware error, `2` bad arguments.

## Wrong colors? Set the color order

Decoders differ in which color each channel carries. If `dmx red` shows blue, `dmx blue` shows green and `dmx green` shows red, the decoder is **BRG**:

```bash
dmx --order brg red                     # one command
export UDMX_COLOR_ORDER=brg             # Linux/macOS: add to ~/.bashrc to keep it
setx UDMX_COLOR_ORDER brg               # Windows: then open a new terminal
```

In Python: `DMXStrips(color_order="BRG")`. Letters are the color on channel 1, 2, 3 in that order (default `RGB`).

## Python library

```python
from udmx_strips import DMXStrips

with DMXStrips(start_channel=1, brightness=1.0) as strips:
    strips.set_all("red")
    strips.set_strip(3, "#00ff88")
    strips.set_strips([1, 2], "warm-white")
    strips.set_colors(["red", "green", "blue"])   # strips 1-3
    strips.blackout()
```

Other pieces: `parse_color("#ff8800") -> (255, 136, 0, 0)`, `UDMX` (raw channel access via
`send_channels(start, values)`), and `DummyDevice` for tests:

```python
from udmx_strips import DMXStrips, DummyDevice
dev = DummyDevice()
DMXStrips(device=dev).set_strip(3, "blue")
print(dev.writes)        # [(7, [0, 0, 255])]
```

## Tests

```bash
pip install '.[test]' && pytest
```
