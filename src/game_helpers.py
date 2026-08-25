from __future__ import annotations

import ctypes
import os
import re
import time
from pathlib import Path
from typing import Optional


def steam_roots() -> list[Path]:
    roots: list[Path] = []
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Steam",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Steam",
    ]
    for root in candidates:
        if root.exists() and root not in roots:
            roots.append(root)
        vdf = root / "steamapps/libraryfolders.vdf"
        if vdf.exists():
            try:
                for raw in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text("utf-8", errors="ignore")):
                    path = Path(raw.replace("\\\\", "\\"))
                    if path.exists() and path not in roots:
                        roots.append(path)
            except Exception:
                pass
    return roots


def candidate_game_roots() -> list[Path]:
    roots: list[Path] = []
    env_roots = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("PROGRAMDATA"),
    ]
    for raw in env_roots:
        if raw:
            p = Path(raw)
            if p.exists() and p not in roots:
                roots.append(p)

    if os.name == "nt":
        for drive in "CDEFG":
            root = Path(f"{drive}:\\")
            if root.exists():
                for name in ("Games", "HAOPLAY", "Haoplay", "Program Files", "Program Files (x86)"):
                    p = root / name
                    if p.exists() and p not in roots:
                        roots.append(p)
    return roots


def container_from_game_folder(game: Path) -> Optional[Path]:
    exact_relatives = (
        Path("bpsr/BPSR_STEAM_Data/StreamingAssets/container"),
        Path("bpsr/BPSR_Data/StreamingAssets/container"),
        Path("BPSR_STEAM_Data/StreamingAssets/container"),
        Path("BPSR_Data/StreamingAssets/container"),
    )
    for rel in exact_relatives:
        candidate = game / rel
        if validate_container(candidate):
            return candidate

    # Launcher/region builds may rename the Unity *_Data directory. Search only one
    # shallow level so Auto Find stays fast and never crawls a whole drive.
    bases = [game]
    try:
        bases.extend(child for child in game.iterdir() if child.is_dir())
    except Exception:
        pass
    for base in bases:
        try:
            for data_dir in base.glob("*_Data"):
                candidate = data_dir / "StreamingAssets" / "container"
                if validate_container(candidate):
                    return candidate
        except Exception:
            pass
    return None


def auto_container(saved: Optional[str] = None) -> Optional[Path]:
    if saved:
        p = Path(saved)
        if validate_container(p):
            return p

    known = Path("steamapps/common/Blue Protocol Star Resonance")
    for root in steam_roots():
        exact_game = root / known
        found = container_from_game_folder(exact_game)
        if found:
            return found
        common = root / "steamapps/common"
        if common.is_dir():
            try:
                for game in common.iterdir():
                    name = game.name.lower()
                    if "protocol" in name or "resonance" in name:
                        found = container_from_game_folder(game)
                        if found:
                            return found
            except Exception:
                pass

    # Haoplay / non-Steam launchers: targeted shallow checks only; never recursively scan an entire drive.
    likely_names = (
        "Blue Protocol Star Resonance",
        "BLUE PROTOCOL STAR RESONANCE",
        "BPSR",
        "blue-protocol-star-resonance",
    )
    for root in candidate_game_roots():
        for name in likely_names:
            found = container_from_game_folder(root / name)
            if found:
                return found
        # Some launchers add one vendor directory.
        try:
            for vendor in root.iterdir():
                if not vendor.is_dir():
                    continue
                vname = vendor.name.lower()
                if "hao" not in vname and "protocol" not in vname and "resonance" not in vname:
                    continue
                for name in likely_names:
                    found = container_from_game_folder(vendor / name)
                    if found:
                        return found
                found = container_from_game_folder(vendor)
                if found:
                    return found
        except Exception:
            pass
    return None


def validate_container(path: Path) -> bool:
    try:
        return path.is_dir() and any(path.glob("m*.pkg"))
    except Exception:
        return False


if os.name == "nt":
    user32 = ctypes.windll.user32
    ENUM_CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    def bpsr_hwnd():
        found = []

        @ENUM_CB
        def callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
            if "blue protocol" in title and "resonance" in title:
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(callback, 0)
        return found[0] if found else None

    def get_bpsr_rect() -> tuple[int, int, int, int]:
        hwnd = bpsr_hwnd()
        if not hwnd:
            raise RuntimeError("BPSR is not open. Open BPSR first, then try again.")
        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("Windows could not read the BPSR window size.")
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top

    def resize_bpsr(width: int, height: int, preserve_position: bool = True) -> tuple[int, int, int, int]:
        hwnd = bpsr_hwnd()
        if not hwnd:
            raise RuntimeError("BPSR is not open. Open it and switch BPSR to Windowed mode first.")
        x, y, old_w, old_h = get_bpsr_rect()
        if not preserve_position:
            x, y = 0, 0
        if not user32.MoveWindow(hwnd, x, y, width, height, True):
            raise RuntimeError("Windows could not resize BPSR. Try reopening this app as Administrator.")
        time.sleep(0.08)
        _x2, _y2, actual_w, actual_h = get_bpsr_rect()
        if abs(actual_w - width) > 3 or abs(actual_h - height) > 3:
            raise RuntimeError(
                f"BPSR did not stay at the requested {width}×{height} size. "
                "Make sure BPSR is in Windowed mode, not Borderless/Fullscreen."
            )
        return x, y, old_w, old_h

    def restore_bpsr_rect(rect: tuple[int, int, int, int]) -> None:
        hwnd = bpsr_hwnd()
        if not hwnd:
            raise RuntimeError("BPSR is not open.")
        x, y, width, height = rect
        if not user32.MoveWindow(hwnd, x, y, width, height, True):
            raise RuntimeError("Windows could not restore the previous BPSR window.")
else:
    def get_bpsr_rect() -> tuple[int, int, int, int]:
        raise RuntimeError("Window helpers are available on Windows only.")

    def resize_bpsr(width: int, height: int, preserve_position: bool = True) -> tuple[int, int, int, int]:
        raise RuntimeError("Window helpers are available on Windows only.")

    def restore_bpsr_rect(rect: tuple[int, int, int, int]) -> None:
        raise RuntimeError("Window helpers are available on Windows only.")
