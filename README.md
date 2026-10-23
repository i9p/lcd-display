# lcd-display

Modular multi-screen driver for a 16×2 character LCD connected to a D1 Mini
(via serial). Ships with:

- **vu** – real-time microphone VU meter (dBFS + bar graph)
- **niri** – focused Niri window name + CPU usage

New screens are trivial to add (see [`docs/CREATING_DISPLAYS.md`](docs/CREATING_DISPLAYS.md)).

## Quick start (dev)

```bash
nix develop          # or: pip install -e .[ ]
python -m lcd_display --list
python -m lcd_display --display vu
```

Send `SIGUSR1` to cycle displays:

```bash
kill -USR1 $(pgrep -f 'lcd.display')
```

## Systemd user service (Nix)

```bash
nix build
# or just use the flake:
systemctl --user enable --now lcd-display.service
```

The service is defined in the flake and lands in the user systemd units when
you install the package.

## Configuration

| Flag / env          | Default          | Meaning                          |
|---------------------|------------------|----------------------------------|
| `--port`            | `/dev/ttyUSB0`   | Serial device                    |
| `--baud`            | `115200`         | Baud rate                        |
| `--display` / `-d`  | `vu`             | Initial screen                   |
| `NIRI_SOCKET`       | auto-detected    | Path to Niri IPC socket          |

## Hardware

D1 Mini running the companion firmware (see earlier conversation) + any
I²C HD44780 16×2 LCD. Power the LCD backpack from 5 V and put a ≥100 µF
capacitor across its supply for stable backlight.
