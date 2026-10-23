"""CLI entry point: python -m lcd_display ..."""

from __future__ import annotations

import argparse
import sys

from .displays import DISPLAYS
from .manager import DisplayManager


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lcd-display",
        description="Modular 16x2 LCD display manager (VU meter, Niri window, …)",
    )
    parser.add_argument(
        "--port",
        default="/dev/ttyUSB0",
        help="Serial port of the D1 Mini (default: /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Baud rate (default: 115200)",
    )
    parser.add_argument(
        "--display", "-d",
        default="vu",
        choices=list(DISPLAYS.keys()),
        help="Initial display to show",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available displays and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("Available displays:")
        for name, cls in DISPLAYS.items():
            print(f"  {name:12}  {cls.description}")
        return 0

    mgr = DisplayManager(port=args.port, baud=args.baud, initial=args.display)
    print(f"Starting with display '{args.display}'. Send SIGUSR1 to cycle.")
    print(f"Available: {', '.join(DISPLAYS)}")
    mgr.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())