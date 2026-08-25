from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

APP_NAME = "BPSR Custom PFP Lite"
VERSION = "1.1.0"

TARGET_PREFIX = "personalzone_player_bg_"
TARGET_NAMES = tuple(f"{TARGET_PREFIX}{i}" for i in range(1, 21))
TARGET_SET = set(TARGET_NAMES)
TARGET_BYTES = tuple(x.encode("utf-8") for x in TARGET_NAMES)
PREFERRED_SLOT = "personalzone_player_bg_3"
KNOWN_PACKAGE = "m79.pkg"
KNOWN_FILE = 593

DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "BPSR-CustomPFP-Lite"
BACKUPS = DATA / "backups"
WORK = DATA / "work"
CROPS = DATA / "crops"
CONFIG = DATA / "config.json"

PORTRAIT_RATIO = (1, 1)
CARD_RATIO = (468, 774)
PORTRAIT_OUTPUT = (1024, 1024)
CARD_OUTPUT = (468, 774)
CARD_SIZES = [(545, 2152), (545, 3130), (545, 4000), (545, 5000), (545, 6191)]


def set_dpi_awareness() -> None:
    """Use physical pixels so exact capture-helper window sizes stay exact on scaled displays."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


set_dpi_awareness()


def bundled_path(relative: str) -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / relative
    return Path(__file__).resolve().parent.parent / relative


def ensure_admin_or_relaunch() -> bool:
    """Ask once at launch. This keeps the beginner workflow predictable for file + window operations."""
    if os.name != "nt":
        return True
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return True
    except Exception:
        return True

    if getattr(sys, "frozen", False):
        executable = sys.executable
        args = sys.argv[1:]
    else:
        executable = sys.executable
        args = [str(Path(__file__).resolve()), *sys.argv[1:]]

    params = subprocess.list2cmdline(args)
    try:
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
    except Exception:
        result = 0

    if result <= 32:
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "Windows permission is needed so this app can safely update the selected BPSR file "
                "and resize the BPSR window for the photo steps.",
                APP_NAME,
                0x10,
            )
        except Exception:
            pass
    return False


def ensure_dirs() -> None:
    for path in (DATA, BACKUPS, WORK, CROPS):
        path.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text("utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def load_cfg() -> dict:
    ensure_dirs()
    return load_json(CONFIG)


def save_cfg(cfg: dict) -> None:
    atomic_write_json(CONFIG, cfg)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def install_id_for(pkg: Path) -> str:
    try:
        container = pkg.parent.resolve()
    except Exception:
        container = pkg.parent.absolute()
    identity = os.path.normcase(str(container)).encode("utf-8", "surrogatepass")
    return hashlib.sha256(identity).hexdigest()[:16]


def backup_paths(pkg: Path) -> tuple[Path, Path, Path]:
    folder = BACKUPS / install_id_for(pkg) / pkg.name
    return folder / "clean.pkg", folder / "state.json", folder


def package_fingerprint(pkg: Path) -> str:
    st = pkg.stat()
    return f"{st.st_size}:{st.st_mtime_ns}"


def cleanup_temp_files() -> None:
    now = time.time()
    for folder, max_age in ((WORK, 3 * 86400), (CROPS, 30 * 86400)):
        try:
            for item in folder.iterdir():
                if item.is_file() and now - item.stat().st_mtime > max_age:
                    item.unlink(missing_ok=True)
        except Exception:
            pass


def prune_before_backups(folder: Path, keep: int = 2) -> None:
    try:
        items = sorted(folder.glob("before-*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
        for item in items[keep:]:
            item.unlink(missing_ok=True)
    except Exception:
        pass


def package_number(path: Path) -> int:
    match = re.search(r"m(\d+)\.pkg$", path.name, re.I)
    return int(match.group(1)) if match else 999999


def parse_file_hint(text: str) -> Optional[int]:
    text = text.strip()
    if not text:
        return None
    match = re.fullmatch(r"(?:file\s*)?(\d+)", text, re.I)
    if not match:
        raise ValueError("The optional speed hint should look like 593 or file593.")
    return int(match.group(1))
