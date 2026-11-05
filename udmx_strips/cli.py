"""Command line interface:  dmx red   /   dmx -s 1,3 '#00ff88'   /   dmx off"""

import argparse
import os
import sys
from typing import List, Optional

from .colors import ColorError, NAMED_COLORS, parse_color
from .controller import CHANNELS_PER_STRIP, DMXStrips
from .device import DummyDevice, UDMX, UDMXError

EXAMPLES = """\
examples:
  dmx red                      all strips red
  dmx '#ff8800'                all strips orange (quote the # in a shell)
  dmx 255,100,0                R,G,B decimal
  dmx 255,100,0,80             R,G,B,W decimal
  dmx warm-white -b 40         warm white at 40%% brightness
  dmx -s 2 blue                strip 2 only (others keep their color)
  dmx -s 1,3,5-6 green         strips 1, 3, 5 and 6
  dmx red green blue           strips 1, 2, 3 get their own colors
  dmx off                      turn everything off
  dmx --list-colors            show named colors
"""


def parse_strip_spec(spec: str, max_strip: int) -> List[int]:
    """'1,3,5-6' -> [1, 3, 5, 6]; 'all' -> every strip."""
    spec = spec.strip().lower()
    if spec == "all":
        return list(range(1, max_strip + 1))
    strips = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                lo, hi = int(a), int(b)
                if lo > hi:
                    raise ValueError
                strips.update(range(lo, hi + 1))
            else:
                strips.add(int(part))
        except ValueError:
            raise argparse.ArgumentTypeError(f"bad strip selection {part!r}")
    for s in strips:
        if not 1 <= s <= max_strip:
            raise argparse.ArgumentTypeError(
                f"strip {s} is out of range (1-{max_strip})")
    return sorted(strips)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dmx",
        description="Set the color of RGBW strips on a uDMX interface. "
                    "The color stays on after the command exits.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("colors", nargs="*", metavar="COLOR",
                   help="name, #hex, or R,G,B[,W]. One color applies to the "
                        "selected strips; several colors go to strips 1, 2, 3...")
    p.add_argument("-s", "--strip", metavar="N",
                   help="strips to change, e.g. 2 or 1,3 or 4-6 (default: all)")
    p.add_argument("-b", "--brightness", type=float, default=100.0,
                   metavar="PCT", help="brightness 0-100 (default 100)")
    p.add_argument("-w", "--white", type=int, metavar="0-255",
                   help="override the white channel value")
    p.add_argument("--strips", type=int, default=6, metavar="N",
                   help="number of strips on the decoder (default 6)")
    p.add_argument("--start-channel", type=int, metavar="CH",
                   default=int(os.environ.get("UDMX_START_CHANNEL", "1")),
                   help="decoder DMX address (default 1, or $UDMX_START_CHANNEL)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the DMX data instead of using the hardware")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="no output on success")
    p.add_argument("--list-colors", action="store_true",
                   help="list named colors and exit")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_colors:
        for name, (r, g, b, w) in NAMED_COLORS.items():
            print(f"{name:<11} R{r:<3} G{g:<3} B{b:<3} W{w:<3}")
        return 0

    if not args.colors:
        parser.error("a color is required, e.g.  dmx red")
    if not 0.0 <= args.brightness <= 100.0:
        parser.error("brightness must be between 0 and 100")
    if args.white is not None and not 0 <= args.white <= 255:
        parser.error("--white must be between 0 and 255")

    try:
        selected = (parse_strip_spec(args.strip, args.strips)
                    if args.strip else list(range(1, args.strips + 1)))
        parsed = [parse_color(c) for c in args.colors]
    except (argparse.ArgumentTypeError, ColorError) as error:
        parser.error(str(error))

    if len(args.colors) > 1:
        if args.strip and len(selected) != len(args.colors):
            parser.error(f"{len(args.colors)} colors given but "
                         f"{len(selected)} strips selected")
        if not args.strip and len(args.colors) > args.strips:
            parser.error(f"{len(args.colors)} colors given but only "
                         f"{args.strips} strips")
        if args.white is not None:
            parser.error("--white only works with a single color")

    try:
        device = DummyDevice(echo=True) if args.dry_run else UDMX()
        with DMXStrips(device=device, num_strips=args.strips,
                       start_channel=args.start_channel,
                       brightness=args.brightness / 100.0) as strips:
            if len(args.colors) == 1:
                if len(selected) == args.strips:
                    sent = strips.set_all(args.colors[0], white=args.white)
                else:
                    sent = strips.set_strips(selected, args.colors[0],
                                             white=args.white)
                where = ("all strips" if len(selected) == args.strips
                         else "strip " + ",".join(map(str, selected)))
                message = "%s: R%d G%d B%d W%d" % ((where,) + tuple(sent))
            else:
                if args.strip:
                    for strip, color in zip(selected, args.colors):
                        strips.set_strip(strip, color)
                else:
                    strips.set_colors(args.colors)
                message = f"set {len(args.colors)} strips individually"
    except (ValueError, UDMXError) as error:
        print(f"dmx: error: {error}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
