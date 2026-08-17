from __future__ import annotations

import ctypes
import hashlib
import json
import mmap
import os
import queue
import re
import shutil
import struct
import threading
import time
import sys
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "BPSR Custom PFP Lite"
VERSION = "0.3.2"
TARGET_PREFIX = "personalzone_player_bg_"
TARGET_NAMES = tuple(f"{TARGET_PREFIX}{i}" for i in range(1, 21))
TARGET_SET = set(TARGET_NAMES)
TARGET_BYTES = tuple(x.encode("utf-8") for x in TARGET_NAMES)

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


def bundled_path(relative: str) -> Path:
    """Return a bundled resource path in both source and PyInstaller builds."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / relative
    return Path(__file__).resolve().parent.parent / relative


def ensure_admin_or_relaunch() -> bool:
    """Ask Windows for administrator permission once, then relaunch elevated."""
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
                "Administrator permission is needed so the app can resize the BPSR window and update the selected game file.",
                APP_NAME,
                0x10,
            )
        except Exception:
            pass
    return False


@dataclass(frozen=True)
class Segment:
    number: int
    offset: int
    size: int


@dataclass(frozen=True)
class Target:
    package: Path
    segment: Segment
    slot_name: str


def ensure_dirs() -> None:
    for path in (DATA, BACKUPS, WORK, CROPS):
        path.mkdir(parents=True, exist_ok=True)


def load_cfg() -> dict:
    ensure_dirs()
    try:
        return json.loads(CONFIG.read_text("utf-8"))
    except Exception:
        return {}


def save_cfg(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def cstr(mm, pos: int, limit: int = 256):
    end = mm.find(b"\0", pos, min(len(mm), pos + limit))
    if end < 0:
        raise ValueError
    return mm[pos:end].decode("utf-8", "replace"), end + 1


def parse_segment(mm, offset: int) -> Optional[int]:
    try:
        p = offset
        signature, p = cstr(mm, p, 16)
        if signature != "UnityFS":
            return None
        version = struct.unpack_from(">I", mm, p)[0]
        p += 4
        _, p = cstr(mm, p, 128)
        _, p = cstr(mm, p, 128)
        size = struct.unpack_from(">Q", mm, p)[0]
        if not (5 <= version <= 20):
            return None
        if size < (p + 8 - offset) or size > len(mm) - offset:
            return None
        return int(size)
    except Exception:
        return None


def segments(pkg: Path) -> list[Segment]:
    found: list[Segment] = []
    with pkg.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        pos = 0
        while True:
            offset = mm.find(b"UnityFS\0", pos)
            if offset < 0:
                break
            size = parse_segment(mm, offset)
            if size:
                found.append(Segment(len(found) + 1, offset, size))
                pos = offset + max(size, 8)
            else:
                pos = offset + 8
    return found


def read_segment(pkg: Path, segment: Segment) -> bytes:
    with pkg.open("rb") as f:
        f.seek(segment.offset)
        return f.read(segment.size)


def texture_objects(env):
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        try:
            name = obj.peek_name()
        except Exception:
            try:
                name = obj.parse_as_object().m_Name
            except Exception:
                continue
        yield obj, name


def target_name_from_blob(blob: bytes) -> Optional[str]:
    """Confirm a usable bg_1..bg_20 Texture2D in one UnityFS blob."""
    import UnityPy

    try:
        env = UnityPy.load(blob)
        for _, name in texture_objects(env):
            if name in TARGET_SET:
                return name
    except Exception:
        return None
    return None


def quick_blob_hint(blob: bytes) -> bool:
    """Cheap pre-check. False is not definitive because UnityFS can be compressed."""
    return any(name in blob for name in TARGET_BYTES)


def replace_texture(blob: bytes, image_path: Path, slot_name: str) -> bytes:
    import UnityPy
    from PIL import Image

    env = UnityPy.load(blob)
    image = Image.open(image_path)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    changed = 0
    for obj, name in texture_objects(env):
        if name != slot_name:
            continue
        texture = obj.parse_as_object()
        texture.image = image.copy()
        texture.save()
        changed += 1

    if not changed:
        raise RuntimeError("The saved picture slot changed. Search again and retry.")
    return env.file.save()


def package_number(path: Path) -> int:
    match = re.search(r"m(\d+)\.pkg$", path.name, re.I)
    return int(match.group(1)) if match else -1


def parse_file_hint(text: str) -> Optional[int]:
    if not text.strip():
        return None
    match = re.search(r"(\d+)", text)
    if not match:
        raise ValueError("The speed hint should look like 593 or file593.")
    return int(match.group(1))


def backup_paths(pkg: Path):
    return BACKUPS / f"{pkg.name}.clean", BACKUPS / f"{pkg.name}.json"


def clean_source(pkg: Path, log: Callable[[str], None]) -> Path:
    clean, meta = backup_paths(pkg)
    current_hash = sha256(pkg)
    try:
        state = json.loads(meta.read_text("utf-8"))
    except Exception:
        state = {}

    if not clean.exists():
        log("Saving a safe copy of your original game file...")
        shutil.copy2(pkg, clean)
        state = {"clean": current_hash, "modified": None}
    elif current_hash not in {state.get("clean"), state.get("modified")}:
        log("Game update detected. Refreshing the safe original copy...")
        shutil.copy2(pkg, clean)
        state = {"clean": current_hash, "modified": None}
    elif not state.get("clean"):
        state["clean"] = sha256(clean)

    meta.write_text(json.dumps(state, indent=2), "utf-8")
    return clean


def record_modified(pkg: Path) -> None:
    clean, meta = backup_paths(pkg)
    try:
        state = json.loads(meta.read_text("utf-8"))
    except Exception:
        state = {}
    state["modified"] = sha256(pkg)
    state.setdefault("clean", sha256(clean) if clean.exists() else None)
    meta.write_text(json.dumps(state, indent=2), "utf-8")


def restore_original(pkg: Path) -> bool:
    clean, meta = backup_paths(pkg)
    if not clean.exists():
        return False
    tmp = pkg.with_suffix(pkg.suffix + ".restore.tmp")
    shutil.copy2(clean, tmp)
    os.replace(tmp, pkg)
    try:
        state = json.loads(meta.read_text("utf-8"))
    except Exception:
        state = {}
    state["modified"] = None
    meta.write_text(json.dumps(state, indent=2), "utf-8")
    return True


def find_in_one_package(
    pkg: Path,
    file_hint: Optional[int] = None,
    cached_file: Optional[int] = None,
    cached_slot: Optional[str] = None,
    only_preferred: bool = False,
) -> Optional[Target]:
    ss = segments(pkg)
    if not ss:
        return None

    checked: set[int] = set()
    preferred: list[int] = []
    for number in (cached_file, file_hint):
        if number and 1 <= number <= len(ss) and number not in preferred:
            preferred.append(number)

    for number in preferred:
        checked.add(number)
        seg = ss[number - 1]
        blob = read_segment(pkg, seg)
        slot = target_name_from_blob(blob)
        if slot:
            return Target(pkg, seg, slot)

    if only_preferred:
        return None

    # Cheap pass: if names happen to be visible in uncompressed bundle data, test these first.
    raw_candidates: list[tuple[Segment, bytes]] = []
    for seg in ss:
        if seg.number in checked:
            continue
        blob = read_segment(pkg, seg)
        if quick_blob_hint(blob):
            raw_candidates.append((seg, blob))

    for seg, blob in raw_candidates:
        checked.add(seg.number)
        slot = target_name_from_blob(blob)
        if slot:
            return Target(pkg, seg, slot)

    # Definitive pass. Stop immediately on the first bg_1..bg_20 Texture2D found.
    for seg in ss:
        if seg.number in checked:
            continue
        slot = target_name_from_blob(read_segment(pkg, seg))
        if slot:
            return Target(pkg, seg, slot)
    return None


def find_target(
    container: Path,
    cfg: dict,
    file_hint: Optional[int],
    log: Callable[[str], None],
    progress: Callable[[float, float], None],
    force_rescan: bool = False,
) -> Target:
    packages = sorted(container.glob("m*.pkg"), key=package_number)
    if not packages:
        raise RuntimeError("No BPSR game files were found in this folder.")

    cached_pkg_name = None if force_rescan else cfg.get("detected_package")
    cached_file = None if force_rescan else cfg.get("detected_file")
    cached_slot = None if force_rescan else cfg.get("detected_slot")

    # Fastest path: last known working package + bundle.
    if cached_pkg_name:
        cached_pkg = container / cached_pkg_name
        if cached_pkg.exists():
            log("Checking your last working location...")
            target = find_in_one_package(cached_pkg, file_hint, cached_file, cached_slot)
            if target:
                progress(1, 1)
                return target

    ordered: list[Path] = []
    seen: set[str] = set()

    # User-selected package from Advanced goes first.
    selected = cfg.get("package")
    if selected:
        selected_path = container / selected
        if selected_path.exists():
            ordered.append(selected_path)
            seen.add(selected_path.name)

    # Recently changed packages next; this is usually where patches move assets.
    for pkg in sorted(packages, key=lambda p: p.stat().st_mtime, reverse=True):
        if pkg.name not in seen:
            ordered.append(pkg)
            seen.add(pkg.name)

    total = len(ordered)

    # If Discord gave fileNNN, test exactly that bundle across packages first.
    # This avoids full-decompressing the wrong package just because it was checked first.
    if file_hint:
        log(f"Trying the optional file{file_hint} speed hint...")
        for index, pkg in enumerate(ordered, 1):
            progress(index - 1, total)
            target = find_in_one_package(pkg, file_hint=file_hint, only_preferred=True)
            if target:
                cfg["detected_package"] = pkg.name
                cfg["detected_file"] = target.segment.number
                cfg["detected_slot"] = target.slot_name
                cfg["package"] = pkg.name
                save_cfg(cfg)
                progress(total, total)
                log("Picture slot found.")
                return target
        log("That speed hint is outdated, so we’re searching normally...")

    log("Looking for a usable picture slot...")
    for index, pkg in enumerate(ordered, 1):
        progress(index - 1, total)
        if index == 1 or index % 5 == 0:
            log(f"Searching game files... {index}/{total}")
        target = find_in_one_package(pkg)
        if target:
            cfg["detected_package"] = pkg.name
            cfg["detected_file"] = target.segment.number
            cfg["detected_slot"] = target.slot_name
            cfg["package"] = pkg.name
            save_cfg(cfg)
            progress(total, total)
            log("Picture slot found.")
            return target

    raise RuntimeError("No usable picture slot was found in this game folder. Try choosing a different BPSR install folder.")


def splice(clean: Path, target: Segment, new_blob: bytes, output: Path) -> None:
    with clean.open("rb") as src, output.open("wb") as dst:
        left = target.offset
        while left:
            block = src.read(min(left, 8 * 1024 * 1024))
            if not block:
                raise IOError("Unexpected end of game file.")
            dst.write(block)
            left -= len(block)
        src.seek(target.size, 1)
        dst.write(new_blob)
        shutil.copyfileobj(src, dst, 8 * 1024 * 1024)


def apply_picture(
    target: Target,
    image_path: Path,
    log: Callable[[str], None],
    progress: Callable[[float, float], None],
) -> None:
    clean = clean_source(target.package, log)
    clean_segments = segments(clean)
    if target.segment.number > len(clean_segments):
        raise RuntimeError("The game updated while the app was open. Search again and retry.")

    clean_seg = clean_segments[target.segment.number - 1]
    clean_blob = read_segment(clean, clean_seg)
    slot = target_name_from_blob(clean_blob)
    if not slot:
        raise RuntimeError("The saved picture location is no longer valid. Search again and retry.")

    log("Adding your picture...")
    new_blob = replace_texture(clean_blob, image_path, slot)
    output = WORK / f"{target.package.name}.new"
    if output.exists():
        output.unlink()
    splice(clean, clean_seg, new_blob, output)

    # Safety check before touching the live package.
    rebuilt_segments = segments(output)
    if len(rebuilt_segments) != len(clean_segments):
        raise RuntimeError("Safety check failed. Your original game file was not changed.")
    rebuilt_seg = rebuilt_segments[clean_seg.number - 1]
    if target_name_from_blob(read_segment(output, rebuilt_seg)) != slot:
        raise RuntimeError("Safety check failed. Your original game file was not changed.")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(target.package, BACKUPS / f"{target.package.name}.before-{stamp}.bak")
    temp_live = target.package.with_suffix(target.package.suffix + ".pfp.tmp")
    shutil.copy2(output, temp_live)
    os.replace(temp_live, target.package)
    record_modified(target.package)
    progress(1, 1)
    log("Done! Your picture was applied successfully.")


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


def auto_container() -> Optional[Path]:
    known = Path("steamapps/common/Blue Protocol Star Resonance/bpsr/BPSR_STEAM_Data/StreamingAssets/container")
    for root in steam_roots():
        exact = root / known
        if exact.is_dir() and any(exact.glob("m*.pkg")):
            return exact
        common = root / "steamapps/common"
        if not common.is_dir():
            continue
        try:
            for game in common.iterdir():
                name = game.name.lower()
                if "protocol" not in name and "resonance" not in name:
                    continue
                for candidate in game.glob("**/StreamingAssets/container"):
                    if any(candidate.glob("m*.pkg")):
                        return candidate
        except Exception:
            pass
    return None


def validate_container(path: Path) -> bool:
    return path.is_dir() and any(path.glob("m*.pkg"))


if os.name == "nt":
    user32 = ctypes.windll.user32
    ENUM_CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

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

    def resize_bpsr(width: int, height: int) -> None:
        hwnd = bpsr_hwnd()
        if not hwnd:
            raise RuntimeError("BPSR is not open. Open the game and switch it to Windowed mode first.")
        if not user32.MoveWindow(hwnd, 0, 0, width, height, True):
            raise RuntimeError("Could not resize BPSR. Try running this app as administrator.")
else:
    def resize_bpsr(width: int, height: int) -> None:
        raise RuntimeError("Window resizing is available on Windows only.")


class CropDialog(tk.Toplevel):
    def __init__(self, master, image_path: Path, ratio: tuple[int, int], output_size: tuple[int, int], label: str):
        super().__init__(master)
        from PIL import Image, ImageTk

        self.Image = Image
        self.ImageTk = ImageTk
        self.source_path = image_path
        self.target_ratio = ratio[0] / ratio[1]
        self.output_size = output_size
        self.label = label
        self.original = Image.open(image_path)
        if self.original.mode not in ("RGB", "RGBA"):
            self.original = self.original.convert("RGBA")

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.drag_last = None
        self.result_path: Optional[Path] = None
        self.info = tk.StringVar()

        self.title("Adjust Your Picture")
        self.geometry("920x720")
        self.minsize(760, 580)
        self.transient(master)
        self.grab_set()

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=14, pady=14)
        ttk.Label(frame, text="Adjust Your Picture", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Drag to move. Scroll to zoom. The highlighted area is what will be used.").pack(anchor="w", pady=(2, 10))

        self.canvas = tk.Canvas(frame, bg="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(10, 0))
        ttk.Button(controls, text="Fit", command=self.fit).pack(side="left")
        ttk.Button(controls, text="Zoom Out", command=lambda: self.bump_zoom(1 / 1.15)).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Zoom In", command=lambda: self.bump_zoom(1.15)).pack(side="left", padx=(6, 0))
        ttk.Label(controls, textvariable=self.info).pack(side="left", padx=12)
        ttk.Button(controls, text="Cancel", command=self.cancel).pack(side="right")
        ttk.Button(controls, text="Use This Crop", command=self.accept).pack(side="right", padx=(0, 6))

        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-4>", lambda _e: self.bump_zoom(1.1))
        self.canvas.bind("<Button-5>", lambda _e: self.bump_zoom(1 / 1.1))
        self.after(50, self.fit)

    def crop_box(self):
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        pad = 28
        available_w = max(100, width - pad * 2)
        available_h = max(100, height - pad * 2)
        if available_w / available_h > self.target_ratio:
            crop_h = available_h
            crop_w = crop_h * self.target_ratio
        else:
            crop_w = available_w
            crop_h = crop_w / self.target_ratio
        x1 = (width - crop_w) / 2
        y1 = (height - crop_h) / 2
        return x1, y1, x1 + crop_w, y1 + crop_h

    def minimum_zoom(self) -> float:
        x1, y1, x2, y2 = self.crop_box()
        iw, ih = self.original.size
        return max((x2 - x1) / iw, (y2 - y1) / ih)

    def clamp_pan(self) -> None:
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        x1, y1, x2, y2 = self.crop_box()
        iw, ih = self.original.size
        dw, dh = iw * self.zoom, ih * self.zoom
        center_x = width / 2 + self.pan_x
        center_y = height / 2 + self.pan_y
        min_cx = x2 - dw / 2
        max_cx = x1 + dw / 2
        min_cy = y2 - dh / 2
        max_cy = y1 + dh / 2
        if min_cx <= max_cx:
            center_x = min(max(center_x, min_cx), max_cx)
        if min_cy <= max_cy:
            center_y = min(max(center_y, min_cy), max_cy)
        self.pan_x = center_x - width / 2
        self.pan_y = center_y - height / 2

    def fit(self) -> None:
        self.update_idletasks()
        self.zoom = self.minimum_zoom()
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.redraw()

    def bump_zoom(self, factor: float) -> None:
        minimum = self.minimum_zoom()
        self.zoom = max(minimum, min(minimum * 8.0, self.zoom * factor))
        self.clamp_pan()
        self.redraw()

    def on_press(self, event) -> None:
        self.drag_last = (event.x, event.y)

    def on_drag(self, event) -> None:
        if not self.drag_last:
            return
        dx = event.x - self.drag_last[0]
        dy = event.y - self.drag_last[1]
        self.drag_last = (event.x, event.y)
        self.pan_x += dx
        self.pan_y += dy
        self.clamp_pan()
        self.redraw()

    def on_wheel(self, event) -> None:
        self.bump_zoom(1.1 if event.delta > 0 else 1 / 1.1)

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        iw, ih = self.original.size
        dw = max(1, int(iw * self.zoom))
        dh = max(1, int(ih * self.zoom))
        display = self.original.resize((dw, dh), self.Image.LANCZOS)
        self.tk_image = self.ImageTk.PhotoImage(display)
        cx, cy = width / 2 + self.pan_x, height / 2 + self.pan_y
        left, top = cx - dw / 2, cy - dh / 2
        self.canvas.create_image(left, top, anchor="nw", image=self.tk_image)

        x1, y1, x2, y2 = self.crop_box()
        self.canvas.create_rectangle(0, 0, width, y1, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(0, y2, width, height, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(0, y1, x1, y2, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(x2, y1, width, y2, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#ffffff", width=2)
        self.info.set(f"{self.label} • {self.output_size[0]}×{self.output_size[1]}")

    def accept(self) -> None:
        x1, y1, x2, y2 = self.crop_box()
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        iw, ih = self.original.size
        dw, dh = iw * self.zoom, ih * self.zoom
        cx, cy = width / 2 + self.pan_x, height / 2 + self.pan_y
        left, top = cx - dw / 2, cy - dh / 2

        sx1 = max(0, (x1 - left) / self.zoom)
        sy1 = max(0, (y1 - top) / self.zoom)
        sx2 = min(iw, (x2 - left) / self.zoom)
        sy2 = min(ih, (y2 - top) / self.zoom)
        if sx2 <= sx1 or sy2 <= sy1:
            messagebox.showerror(APP_NAME, "That crop is not usable. Click Fit and try again.", parent=self)
            return

        cropped = self.original.crop((round(sx1), round(sy1), round(sx2), round(sy2)))
        cropped = cropped.resize(self.output_size, self.Image.LANCZOS)
        output = CROPS / f"{self.label.lower()}_{int(time.time())}.png"
        cropped.save(output)
        self.result_path = output
        self.destroy()

    def cancel(self) -> None:
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.cfg = load_cfg()
        self.events = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.card_step = 0
        self.preview_photo = None

        self.container_var = tk.StringVar(value=self.cfg.get("container", ""))
        self.package_var = tk.StringVar(value=self.cfg.get("package", ""))
        self.hint_var = tk.StringVar(value=self.cfg.get("hint", ""))
        self.image_var = tk.StringVar(value=self.cfg.get("image", ""))
        self.mode_var = tk.StringVar(value=self.cfg.get("mode", "portrait"))
        self.game_status = tk.StringVar(value="Checking for your game...")
        self.picture_status = tk.StringVar(value="No picture selected yet")
        self.main_status = tk.StringVar(value="Choose a picture to continue.")
        self.target_status = tk.StringVar(value="Not searched yet")
        self.progress_var = tk.DoubleVar(value=0)
        self.advanced_visible = False
        self.tools_visible = False

        self.title(f"{APP_NAME} v{VERSION}")
        self._window_icon = None
        try:
            self._window_icon = tk.PhotoImage(file=str(bundled_path("assets/app_icon.png")))
            self.iconphoto(True, self._window_icon)
        except Exception:
            pass
        self.geometry("790x850")
        self.minsize(720, 700)
        self.build_ui()
        self.after(100, self.drain_events)
        self.after(250, self.initial_setup)

    def build_ui(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=16, pady=14)
        root.columnconfigure(0, weight=1)

        ttk.Label(root, text="Change Your BPSR Picture", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(root, text="Pick a picture, adjust it, and let the app do the rest.").grid(row=1, column=0, sticky="w", pady=(2, 14))

        game = ttk.LabelFrame(root, text="1. Find Your Game")
        game.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        game.columnconfigure(0, weight=1)
        ttk.Label(game, textvariable=self.game_status, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
        ttk.Label(game, text="We’ll find BPSR automatically. If needed, you can choose another install folder yourself.").grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))
        buttons = ttk.Frame(game)
        buttons.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 10))
        ttk.Button(buttons, text="Find Game Automatically", command=self.auto_find_game).pack(side="left", padx=4)
        ttk.Button(buttons, text="Choose Folder Manually", command=self.choose_game_folder).pack(side="left", padx=4)

        picture = ttk.LabelFrame(root, text="2. Pick Your Picture")
        picture.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        picture.columnconfigure(1, weight=1)
        self.preview = ttk.Label(picture, text="No preview", anchor="center", width=20)
        self.preview.grid(row=0, column=0, rowspan=4, padx=12, pady=12, sticky="nsew")
        ttk.Label(picture, text="Picture shape", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", pady=(12, 4))
        modes = ttk.Frame(picture)
        modes.grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(modes, text="Square", variable=self.mode_var, value="portrait", command=self.mode_changed).pack(side="left")
        ttk.Radiobutton(modes, text="Card", variable=self.mode_var, value="card", command=self.mode_changed).pack(side="left", padx=(12, 0))
        ttk.Label(picture, text="Square is best for profile pictures. Card is the tall layout.").grid(row=2, column=1, sticky="w", pady=(4, 8))
        row = ttk.Frame(picture)
        row.grid(row=3, column=1, sticky="w", pady=(0, 12))
        ttk.Button(row, text="Choose Picture", command=self.choose_picture).pack(side="left")
        self.crop_button = ttk.Button(row, text="Adjust Crop", command=self.adjust_crop)
        self.crop_button.pack(side="left", padx=(6, 0))
        ttk.Label(picture, textvariable=self.picture_status).grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        apply_box = ttk.LabelFrame(root, text="3. Apply It")
        apply_box.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        apply_box.columnconfigure(0, weight=1)
        ttk.Label(apply_box, text="The app will find a usable picture slot, save your original file, and apply the picture automatically.").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 8))
        self.apply_button = ttk.Button(apply_box, text="Use This Picture", command=self.apply_clicked)
        self.apply_button.grid(row=1, column=0, sticky="ew", padx=(12, 6), pady=(0, 8))
        ttk.Button(apply_box, text="Restore Original", command=self.restore_clicked).grid(row=1, column=1, padx=(6, 12), pady=(0, 8))
        ttk.Progressbar(apply_box, variable=self.progress_var, maximum=100).grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 6))
        ttk.Label(apply_box, textvariable=self.main_status, font=("Segoe UI", 10, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        toggles = ttk.Frame(root)
        toggles.grid(row=5, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(toggles, text="Helpful Tools ▸", command=self.toggle_tools).pack(side="left")
        ttk.Button(toggles, text="Advanced Options ▸", command=self.toggle_advanced).pack(side="left", padx=(8, 0))

        self.tools_frame = ttk.LabelFrame(root, text="Helpful Tools")
        self.tools_frame.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(self.tools_frame, text="These resize the BPSR window for the in-game photo booth. Open BPSR in Windowed mode first.").pack(anchor="w", padx=12, pady=(10, 8))
        tool_buttons = ttk.Frame(self.tools_frame)
        tool_buttons.pack(fill="x", padx=8, pady=(0, 10))
        ttk.Button(tool_buttons, text="Set Window for Square Photo", command=lambda: self.resize_game(545, 2152)).pack(side="left", padx=4)
        self.card_button = ttk.Button(
            tool_buttons,
            text=f"Card Photo Step 1/{len(CARD_SIZES)}",
            command=self.next_card_size,
        )
        self.card_button.pack(side="left", padx=4)
        ttk.Button(tool_buttons, text="Restore Window Size", command=lambda: self.resize_game(1920, 1080)).pack(side="left", padx=4)
        self.tools_frame.grid_remove()

        self.advanced_frame = ttk.LabelFrame(root, text="Advanced Options")
        self.advanced_frame.grid(row=7, column=0, sticky="nsew")
        self.advanced_frame.columnconfigure(1, weight=1)
        ttk.Label(self.advanced_frame, text="You usually don’t need anything here.").grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 8))
        ttk.Label(self.advanced_frame, text="Game folder").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        ttk.Entry(self.advanced_frame, textvariable=self.container_var).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(self.advanced_frame, text="Browse", command=self.choose_game_folder).grid(row=1, column=2, padx=8, pady=4)
        ttk.Label(self.advanced_frame, text="Game file").grid(row=2, column=0, sticky="w", padx=12, pady=4)
        self.package_combo = ttk.Combobox(self.advanced_frame, textvariable=self.package_var, state="readonly")
        self.package_combo.grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(self.advanced_frame, text="Refresh", command=self.refresh_packages).grid(row=2, column=2, padx=8, pady=4)
        ttk.Label(self.advanced_frame, text="Speed hint (optional)").grid(row=3, column=0, sticky="w", padx=12, pady=4)
        ttk.Entry(self.advanced_frame, textvariable=self.hint_var).grid(row=3, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(self.advanced_frame, text="If Discord gave you something like file593, paste it here. Blank is fine.").grid(row=4, column=1, columnspan=2, sticky="w", padx=4, pady=(0, 6))
        ttk.Label(self.advanced_frame, text="Detected picture slot").grid(row=5, column=0, sticky="w", padx=12, pady=4)
        ttk.Label(self.advanced_frame, textvariable=self.target_status).grid(row=5, column=1, sticky="w", padx=4, pady=4)
        search_row = ttk.Frame(self.advanced_frame)
        search_row.grid(row=6, column=1, columnspan=2, sticky="w", padx=4, pady=(4, 8))
        ttk.Button(search_row, text="Search Again", command=self.search_again).pack(side="left")
        ttk.Button(search_row, text="Use Selected Game File", command=self.save_advanced_selection).pack(side="left", padx=(6, 0))
        log_box = ttk.LabelFrame(self.advanced_frame, text="Details")
        log_box.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=12, pady=(0, 12))
        self.log_text = tk.Text(log_box, height=9, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.advanced_frame.grid_remove()

        root.rowconfigure(7, weight=1)
        ttk.Label(root, text="Unofficial client-file modification. The app keeps backups, but use it at your own risk.").grid(row=8, column=0, sticky="w", pady=(8, 0))

    def emit_log(self, text: str) -> None:
        self.events.put(("log", text))

    def emit_progress(self, current: float, total: float) -> None:
        self.events.put(("progress", 100 * current / total if total else 0))

    def drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.main_status.set(value)
                    self.log_text.config(state="normal")
                    self.log_text.insert("end", value + "\n")
                    self.log_text.see("end")
                    self.log_text.config(state="disabled")
                elif kind == "progress":
                    self.progress_var.set(value)
                elif kind == "target":
                    target: Target = value
                    self.package_var.set(target.package.name)
                    self.target_status.set(f"{target.package.name} • file{target.segment.number} • {target.slot_name}")
                    self.cfg.update(
                        package=target.package.name,
                        detected_package=target.package.name,
                        detected_file=target.segment.number,
                        detected_slot=target.slot_name,
                    )
                    save_cfg(self.cfg)
                    self.refresh_packages()
                elif kind == "done":
                    self.worker = None
                    self.progress_var.set(100)
                    self.main_status.set("Done! Your picture was applied successfully.")
                    self.update_ready_state()
                    messagebox.showinfo(APP_NAME, "Done!\n\nYour picture was applied successfully. You can now use the BPSR photo booth to capture/save it.")
                elif kind == "search_done":
                    self.worker = None
                    self.progress_var.set(100)
                    self.update_ready_state()
                    messagebox.showinfo(APP_NAME, "Search complete. A usable picture slot was found.")
                elif kind == "error":
                    self.worker = None
                    self.progress_var.set(0)
                    self.main_status.set(value)
                    self.update_ready_state()
                    messagebox.showerror(APP_NAME, value)
        except queue.Empty:
            pass
        self.after(100, self.drain_events)

    def initial_setup(self) -> None:
        saved = Path(self.container_var.get()) if self.container_var.get() else None
        if saved and validate_container(saved):
            self.set_game_folder(saved, "Game found")
        else:
            found = auto_container()
            if found:
                self.set_game_folder(found, "Game found automatically")
            else:
                self.game_status.set("Game not found yet")
                self.main_status.set("Choose your BPSR game folder to continue.")
        image = Path(self.image_var.get()) if self.image_var.get() else None
        if image and image.is_file():
            self.update_preview(image)
            if self.cfg.get("crop_mode") == self.mode_var.get():
                self.picture_status.set("Picture ready")
            else:
                self.picture_status.set("Adjust the crop before applying.")
        self.show_cached_target()
        self.update_ready_state()

    def set_game_folder(self, path: Path, status: str = "Game found") -> None:
        self.container_var.set(str(path))
        self.cfg["container"] = str(path)
        save_cfg(self.cfg)
        self.game_status.set(status)
        self.refresh_packages()
        self.update_ready_state()

    def auto_find_game(self) -> None:
        found = auto_container()
        if found:
            self.set_game_folder(found, "Game found automatically")
            self.main_status.set("Choose a picture to continue." if not self.valid_image() else "Ready to apply.")
        else:
            self.game_status.set("Game not found automatically")
            messagebox.showinfo(APP_NAME, "We couldn’t find BPSR automatically. Click “Choose Folder Manually” and select the game’s StreamingAssets\\container folder.")
        self.update_ready_state()

    def choose_game_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose BPSR StreamingAssets\\container folder")
        if not selected:
            return
        path = Path(selected)
        if not validate_container(path):
            messagebox.showerror(APP_NAME, "That folder does not look like the BPSR container folder. Choose the folder that contains the m*.pkg game files.")
            return
        self.set_game_folder(path, "Game folder selected")
        # Manual choice is authoritative; do not silently jump back to an auto-detected install.
        self.cfg.pop("detected_package", None)
        self.cfg.pop("detected_file", None)
        self.cfg.pop("detected_slot", None)
        self.cfg.pop("package", None)
        self.package_var.set("")
        save_cfg(self.cfg)
        self.target_status.set("Not searched yet")

    def refresh_packages(self) -> None:
        folder = Path(self.container_var.get()) if self.container_var.get() else Path()
        if not validate_container(folder):
            self.package_combo["values"] = []
            return
        names = [p.name for p in sorted(folder.glob("m*.pkg"), key=package_number)]
        self.package_combo["values"] = names
        if self.package_var.get() not in names:
            cached = self.cfg.get("detected_package")
            self.package_var.set(cached if cached in names else "")

    def show_cached_target(self) -> None:
        pkg = self.cfg.get("detected_package")
        file_no = self.cfg.get("detected_file")
        slot = self.cfg.get("detected_slot")
        if pkg and file_no and slot:
            self.target_status.set(f"{pkg} • file{file_no} • {slot}")

    def valid_game(self) -> bool:
        return bool(self.container_var.get()) and validate_container(Path(self.container_var.get()))

    def valid_image(self) -> bool:
        return (
            bool(self.image_var.get())
            and Path(self.image_var.get()).is_file()
            and self.cfg.get("crop_mode") == self.mode_var.get()
        )

    def update_ready_state(self) -> None:
        if self.worker:
            self.apply_button.state(["disabled"])
            return
        if not self.valid_game():
            self.apply_button.state(["disabled"])
            self.main_status.set("Choose your BPSR game folder to continue.")
        elif not self.valid_image():
            self.apply_button.state(["disabled"])
            if self.image_var.get() and Path(self.image_var.get()).is_file():
                self.main_status.set("Adjust the crop to match the selected picture shape.")
            else:
                self.main_status.set("Choose a picture to continue.")
        else:
            self.apply_button.state(["!disabled"])
            if not self.main_status.get().startswith("Done"):
                self.main_status.set("Ready to apply.")

    def mode_changed(self) -> None:
        self.cfg["mode"] = self.mode_var.get()
        save_cfg(self.cfg)
        # Existing crop may have the old ratio; require a fresh crop before applying.
        if self.image_var.get() and Path(self.image_var.get()).is_file():
            self.picture_status.set("Picture shape changed — adjust the crop again before applying.")
        self.update_ready_state()

    def crop_settings(self):
        if self.mode_var.get() == "card":
            return CARD_RATIO, CARD_OUTPUT, "Card"
        return PORTRAIT_RATIO, PORTRAIT_OUTPUT, "Square"

    def choose_picture(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose your picture",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")],
        )
        if not selected:
            return
        self.open_crop(Path(selected))

    def adjust_crop(self) -> None:
        current = Path(self.image_var.get()) if self.image_var.get() else None
        if not current or not current.is_file():
            self.choose_picture()
            return
        self.open_crop(current)

    def open_crop(self, image_path: Path) -> None:
        try:
            ratio, output, label = self.crop_settings()
            dialog = CropDialog(self, image_path, ratio, output, label)
            self.wait_window(dialog)
            if dialog.result_path:
                self.image_var.set(str(dialog.result_path))
                self.cfg["image"] = str(dialog.result_path)
                self.cfg["mode"] = self.mode_var.get()
                self.cfg["crop_mode"] = self.mode_var.get()
                save_cfg(self.cfg)
                self.update_preview(dialog.result_path)
                self.picture_status.set("Picture ready")
                self.main_status.set("Ready to apply." if self.valid_game() else "Choose your BPSR game folder to continue.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not open that picture: {exc}")
        self.update_ready_state()

    def update_preview(self, image_path: Path) -> None:
        from PIL import Image, ImageTk

        image = Image.open(image_path)
        image.thumbnail((150, 150), Image.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.preview_photo, text="")

    def save_advanced_selection(self) -> None:
        folder = Path(self.container_var.get()) if self.container_var.get() else None
        package = self.package_var.get()
        if not folder or not validate_container(folder):
            messagebox.showerror(APP_NAME, "Choose a valid BPSR game folder first.")
            return
        if package and not (folder / package).is_file():
            messagebox.showerror(APP_NAME, "That game file no longer exists. Click Refresh.")
            return
        self.cfg.update(container=str(folder), package=package, hint=self.hint_var.get())
        save_cfg(self.cfg)
        self.game_status.set("Game folder selected")
        messagebox.showinfo(APP_NAME, "Advanced selection saved. The app will try this game file first.")

    def worker_guard(self) -> bool:
        if self.worker:
            return False
        self.apply_button.state(["disabled"])
        self.progress_var.set(0)
        return True

    def search_again(self) -> None:
        if not self.worker_guard():
            return
        if not self.valid_game():
            self.worker = None
            self.update_ready_state()
            messagebox.showerror(APP_NAME, "Choose a valid BPSR game folder first.")
            return
        try:
            file_hint = parse_file_hint(self.hint_var.get())
        except Exception as exc:
            self.worker = None
            self.update_ready_state()
            messagebox.showerror(APP_NAME, str(exc))
            return

        folder = Path(self.container_var.get())
        self.cfg.update(container=str(folder), hint=self.hint_var.get(), package=self.package_var.get())
        save_cfg(self.cfg)

        def work():
            try:
                target = find_target(folder, self.cfg, file_hint, self.emit_log, self.emit_progress, force_rescan=True)
                self.events.put(("target", target))
                self.events.put(("search_done", None))
            except Exception as exc:
                self.events.put(("error", str(exc)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def apply_clicked(self) -> None:
        if not self.worker_guard():
            return
        if not self.valid_game() or not self.valid_image():
            self.worker = None
            self.update_ready_state()
            return
        try:
            file_hint = parse_file_hint(self.hint_var.get())
        except Exception as exc:
            self.worker = None
            self.update_ready_state()
            messagebox.showerror(APP_NAME, str(exc))
            return

        folder = Path(self.container_var.get())
        image = Path(self.image_var.get())
        self.cfg.update(
            container=str(folder),
            image=str(image),
            mode=self.mode_var.get(),
            hint=self.hint_var.get(),
            package=self.package_var.get(),
        )
        save_cfg(self.cfg)

        def work():
            try:
                target = find_target(folder, self.cfg, file_hint, self.emit_log, self.emit_progress)
                self.events.put(("target", target))
                apply_picture(target, image, self.emit_log, self.emit_progress)
                self.events.put(("done", None))
            except Exception as exc:
                self.events.put(("error", str(exc)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def restore_clicked(self) -> None:
        if not self.valid_game():
            messagebox.showerror(APP_NAME, "Choose your BPSR game folder first.")
            return
        folder = Path(self.container_var.get())
        candidates = []
        for name in (self.cfg.get("detected_package"), self.package_var.get()):
            if name and name not in candidates:
                candidates.append(name)
        if not candidates:
            messagebox.showinfo(APP_NAME, "No backup has been created yet.")
            return
        pkg = next((folder / name for name in candidates if (folder / name).is_file()), None)
        if not pkg:
            messagebox.showinfo(APP_NAME, "The backed-up game file is not in this folder anymore.")
            return
        if not messagebox.askyesno(APP_NAME, "Restore the original game file saved before your custom picture was applied?"):
            return
        if restore_original(pkg):
            self.main_status.set("Your original file has been restored.")
            messagebox.showinfo(APP_NAME, "Original restored successfully.")
        else:
            messagebox.showinfo(APP_NAME, "No clean backup exists for this game file yet.")

    def toggle_tools(self) -> None:
        self.tools_visible = not self.tools_visible
        if self.tools_visible:
            self.tools_frame.grid()
        else:
            self.tools_frame.grid_remove()

    def toggle_advanced(self) -> None:
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.grid()
        else:
            self.advanced_frame.grid_remove()

    def resize_game(self, width: int, height: int) -> None:
        try:
            resize_bpsr(width, height)
            self.emit_log(f"BPSR window set to {width}×{height}.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def next_card_size(self) -> None:
        step_number = self.card_step + 1
        width, height = CARD_SIZES[self.card_step]
        try:
            resize_bpsr(width, height)
            self.emit_log(f"Card photo setup: step {step_number} of {len(CARD_SIZES)} ready.")
            self.card_step = (self.card_step + 1) % len(CARD_SIZES)
            next_step = self.card_step + 1
            self.card_button.configure(text=f"Card Photo Step {next_step}/{len(CARD_SIZES)}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))


def frozen_self_test() -> int:
    """Verify packaged resources before GitHub publishes a Windows release."""
    try:
        import UnityPy  # noqa: F401
        import fmod_toolkit
        import archspec

        dll = Path(fmod_toolkit.__file__).resolve().parent / "libfmod" / "Windows" / "x64" / "fmod.dll"
        if not dll.is_file():
            return 2

        cpu_db = Path(archspec.__file__).resolve().parent / "cpu" / "microarchitectures.json"
        if not cpu_db.is_file():
            return 4
        # Actually read the database so a broken one-file bundle fails in CI, not on the user's PC.
        json.loads(cpu_db.read_text(encoding="utf-8"))

        if not bundled_path("assets/app_icon.png").is_file():
            return 5
        return 0
    except Exception:
        return 3


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(frozen_self_test())
    if not ensure_admin_or_relaunch():
        raise SystemExit(0)
    ensure_dirs()
    App().mainloop()
