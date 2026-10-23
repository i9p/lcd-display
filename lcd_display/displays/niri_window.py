"""Show the focused Niri window (app basename + CPU%)."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any, Optional

import psutil

from ..display import Display
from ..lcd import LCD


def _niri_socket_path() -> Optional[Path]:
    env = os.environ.get("NIRI_SOCKET")
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        candidate = Path(xdg) / "niri" / "niri.sock"
        if candidate.exists():
            return candidate
    # last-ditch
    uid = os.getuid()
    candidate = Path(f"/run/user/{uid}/niri/niri.sock")
    return candidate if candidate.exists() else None


def _niri_request(request: str | dict) -> Any:
    """Send a single JSON request to Niri and return the parsed reply.

    Simple requests are just a JSON string, e.g. '"FocusedWindow"'.
    Complex ones are objects.
    """
    path = _niri_socket_path()
    if path is None:
        raise RuntimeError("Niri socket not found (is NIRI_SOCKET set?)")

    # If the caller passed a plain string like "FocusedWindow", turn it into
    # the JSON string value that niri expects.
    if isinstance(request, str):
        payload = json.dumps(request) + "\n"          # → "FocusedWindow"\n
    else:
        payload = json.dumps(request) + "\n"

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        sock.connect(str(path))
        sock.sendall(payload.encode())
        # shutdown write side so niri knows the request is complete
        sock.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
    line = data.decode().split("\n", 1)[0]
    reply = json.loads(line)
    if "Ok" in reply:
        return reply["Ok"]
    raise RuntimeError(f"Niri error: {reply.get('Err', reply)}")


def _basename_from_cmdline(cmdline: list[str]) -> str:
    """Turn a full cmdline into a short friendly name."""
    if not cmdline:
        return "?"
    # Prefer the executable basename
    exe = Path(cmdline[0]).name
    # Common patterns: "zen-twilight", "firefox", "Alacritty"
    # Strip common prefixes / suffixes
    for prefix in ("flatpak-spawn", "python", "python3", "node", "electron"):
        if exe.startswith(prefix) and len(cmdline) > 1:
            exe = Path(cmdline[1]).name
            break
    # Remove .desktop-style suffixes or version numbers if present
    if exe.endswith(".desktop"):
        exe = exe[:-8]
    return exe[:16]


def _find_process_for_app(app_id: str, title: str) -> Optional[psutil.Process]:
    """Best-effort match of a running process to the focused window."""
    app_id_l = (app_id or "").lower()
    # Try exact / partial matches on name or cmdline
    candidates = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info["name"] or "").lower()
            cmd = " ".join(proc.info["cmdline"] or []).lower()
            if app_id_l and (app_id_l in name or app_id_l in cmd):
                candidates.append(proc)
            elif title and title[:20].lower() in cmd:
                candidates.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not candidates:
        return None
    # Prefer the one with highest CPU (most likely the main process)
    try:
        return max(candidates, key=lambda p: p.cpu_percent(interval=0.0))
    except Exception:
        return candidates[0]


class NiriWindowDisplay(Display):
    name = "niri"
    description = "Focused Niri window (name + CPU%)"
    update_interval = 0.5

    def __init__(self) -> None:
        self._last_app = ""
        self._last_cpu = 0.0
        self._proc: Optional[psutil.Process] = None

    def on_activate(self) -> None:
        # Warm up psutil cpu_percent
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def on_deactivate(self) -> None:
        self._proc = None

    def _get_focused(self) -> dict:
        try:
            resp = _niri_request("FocusedWindow")
            # Response shape: {"FocusedWindow": { ... }} or just the window dict
            if isinstance(resp, dict) and "FocusedWindow" in resp:
                win = resp["FocusedWindow"]
            else:
                win = resp
            return win or {}
        except Exception:
            return {}

    def update(self, lcd: LCD) -> None:
        win = self._get_focused()
        if not win:
            lcd.write_both("No focused win", "niri offline?")
            return

        app_id = win.get("app_id") or ""
        title = win.get("title") or ""

        # Resolve a nice short name
        short = app_id or "unknown"
        # Try to get a better basename from the real process
        if self._proc is None or not self._proc.is_running():
            self._proc = _find_process_for_app(app_id, title)

        cpu = 0.0
        if self._proc is not None:
            try:
                cmdline = self._proc.cmdline()
                short = _basename_from_cmdline(cmdline) or short
                # Non-blocking CPU% (needs a previous call to be meaningful)
                cpu = self._proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._proc = None

        self._last_app = short[:16]
        self._last_cpu = cpu

        line1 = self._last_app.ljust(16)[:16]
        # Second line: CPU + truncated title
        cpu_str = f"{self._last_cpu:4.0f}%"
        rest = 16 - len(cpu_str) - 1
        title_part = (title or "")[:rest]
        line2 = f"{cpu_str} {title_part}".ljust(16)[:16]

        lcd.write_both(line1, line2)