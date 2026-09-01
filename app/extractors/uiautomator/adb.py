"""Thin wrapper around the ADB binary.

Deliberately conservative: navigation is limited to taps, back and vertical
swipes needed by the explicit bulk-import workflow.
"""
from __future__ import annotations

import re
import subprocess


class AdbClient:
    def __init__(self, adb_path: str | None = None):
        self.adb = adb_path or "adb"

    def _run(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.adb, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def _run_bytes(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run([self.adb, *args], capture_output=True, timeout=timeout)

    def devices(self) -> list[str]:
        proc = self._run("devices")
        out: list[str] = []
        for line in proc.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                out.append(parts[0])
        return out

    def available(self) -> bool:
        try:
            return bool(self.devices())
        except Exception:
            return False

    def current_window_xml(self) -> str | None:
        proc = self._run("shell", "uiautomator", "dump", "/sdcard/window.xml")
        if "dumped" not in (proc.stdout or "") + (proc.stderr or ""):
            return None
        cat = self._run("shell", "cat", "/sdcard/window.xml")
        return cat.stdout if cat.returncode == 0 else None

    def screenshot_bytes(self) -> bytes | None:
        proc = self._run_bytes("exec-out", "screencap", "-p")
        if proc.returncode != 0 or not proc.stdout:
            return None
        return proc.stdout

    def screen_size(self) -> tuple[int, int]:
        proc = self._run("shell", "wm", "size")
        match = re.search(r"(\d+)x(\d+)", proc.stdout or "")
        if match:
            return int(match.group(1)), int(match.group(2))
        return 1080, 2400

    def swipe_up(self) -> None:
        # Advance about one and a half rows. A larger jump could move an image
        # directly from clipped-at-bottom to clipped-at-top without ever
        # exposing the complete ImageView.
        self._swipe(0.54, 0.31, duration=200)

    def swipe_down(self) -> None:
        self._swipe(0.31, 0.54, duration=200)

    def swipe_order_list_up(self) -> None:
        self._swipe(0.78, 0.43, duration=300)

    def tap(self, x: int, y: int) -> None:
        self._run("shell", "input", "tap", str(x), str(y))

    def back(self) -> None:
        self._run("shell", "input", "keyevent", "KEYCODE_BACK")

    def _swipe(self, y_from_frac: float, y_to_frac: float, duration: int = 400) -> None:
        """Swipe vertically in the center column, avoiding clickable buttons.

        The order screen has clickable rows (``查看评价``, address, tracking) in
        the lower half, so we drag within the middle band where the card text
        lives rather than the very bottom.
        """
        width, height = self.screen_size()
        x = width // 2
        y_from = int(height * y_from_frac)
        y_to = int(height * y_to_frac)
        self._run(
            "shell", "input", "swipe", str(x), str(y_from), str(x), str(y_to), str(duration)
        )
