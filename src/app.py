from __future__ import annotations

import ctypes, hashlib, json, mmap, os, queue, re, shutil, struct, threading, time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "BPSR Custom PFP Lite"
VERSION = "0.1.0"
TEXTURE = "personalzone_player_bg_3"
DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "BPSR-CustomPFP-Lite"
BACKUPS = DATA / "backups"
WORK = DATA / "work"
CONFIG = DATA / "config.json"

@dataclass(frozen=True)
class Segment:
    number: int
    offset: int
    size: int


def dirs():
    DATA.mkdir(parents=True, exist_ok=True); BACKUPS.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)


def load_cfg():
    dirs()
    try: return json.loads(CONFIG.read_text("utf-8"))
    except Exception: return {}


def save_cfg(c):
    CONFIG.write_text(json.dumps(c, indent=2), encoding="utf-8")


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""): h.update(b)
    return h.hexdigest()


def cstr(mm, pos, limit=256):
    e = mm.find(b"\0", pos, min(len(mm), pos + limit))
    if e < 0: raise ValueError
    return mm[pos:e].decode("utf-8", "replace"), e + 1


def parse_segment(mm, off):
    try:
        p = off
        sig, p = cstr(mm, p, 16)
        if sig != "UnityFS": return None
        version = struct.unpack_from(">I", mm, p)[0]; p += 4
        _, p = cstr(mm, p, 128); _, p = cstr(mm, p, 128)
        size = struct.unpack_from(">Q", mm, p)[0]
        if not (5 <= version <= 20) or size < (p + 8 - off) or size > len(mm) - off: return None
        return int(size)
    except Exception: return None


def segments(pkg: Path):
    out = []
    with pkg.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        pos = 0
        while True:
            off = mm.find(b"UnityFS\0", pos)
            if off < 0: break
            size = parse_segment(mm, off)
            if size:
                out.append(Segment(len(out) + 1, off, size)); pos = off + max(size, 8)
            else: pos = off + 8
    return out


def read_seg(pkg, s):
    with pkg.open("rb") as f: f.seek(s.offset); return f.read(s.size)


def textures(env):
    for obj in env.objects:
        if obj.type.name != "Texture2D": continue
        try: name = obj.peek_name()
        except Exception:
            try: name = obj.parse_as_object().m_Name
            except Exception: continue
        yield obj, name


def has_texture(blob):
    import UnityPy
    try:
        env = UnityPy.load(blob)
        return any(n == TEXTURE for _, n in textures(env))
    except Exception: return False


def replace_texture(blob, image):
    import UnityPy
    from PIL import Image
    env = UnityPy.load(blob); img = Image.open(image)
    if img.mode not in ("RGB", "RGBA"): img = img.convert("RGBA")
    changed = 0
    for obj, name in textures(env):
        if name != TEXTURE: continue
        t = obj.parse_as_object(); t.image = img.copy(); t.save(); changed += 1
    if not changed: raise RuntimeError(f"{TEXTURE} was not found in the target bundle")
    return env.file.save()


def hint_num(text):
    if not text.strip(): return None
    m = re.search(r"(\d+)", text)
    if not m: raise ValueError("file hint must look like 593 or file593.unity3d")
    return int(m.group(1))


def backup_files(pkg):
    return BACKUPS / (pkg.name + ".clean"), BACKUPS / (pkg.name + ".json")


def clean_source(pkg, log):
    clean, meta = backup_files(pkg); cur = sha256(pkg)
    try: m = json.loads(meta.read_text("utf-8"))
    except Exception: m = {}
    if not clean.exists():
        log("Creating clean baseline backup..."); shutil.copy2(pkg, clean); m = {"clean": cur, "modified": None}
    elif cur not in {m.get("clean"), m.get("modified")}:
        log("Detected patched/verified package; refreshing clean baseline...")
        shutil.copy2(pkg, clean); m = {"clean": cur, "modified": None}
    elif not m.get("clean"): m["clean"] = sha256(clean)
    meta.write_text(json.dumps(m, indent=2), "utf-8"); return clean


def record_modified(pkg):
    clean, meta = backup_files(pkg)
    try: m = json.loads(meta.read_text("utf-8"))
    except Exception: m = {}
    m["modified"] = sha256(pkg); m.setdefault("clean", sha256(clean) if clean.exists() else None)
    meta.write_text(json.dumps(m, indent=2), "utf-8")


def restore(pkg):
    clean, meta = backup_files(pkg)
    if not clean.exists(): return False
    tmp = pkg.with_suffix(pkg.suffix + ".restore.tmp"); shutil.copy2(clean, tmp); os.replace(tmp, pkg)
    try: m = json.loads(meta.read_text("utf-8"))
    except Exception: m = {}
    m["modified"] = None; meta.write_text(json.dumps(m, indent=2), "utf-8"); return True


def find_target(pkg, ss, hint, log, progress):
    if hint:
        if hint < 1 or hint > len(ss): raise RuntimeError(f"file{hint} is outside this package (1-{len(ss)})")
        s = ss[hint - 1]; log(f"Checking Discord hint file{hint}.unity3d...")
        if has_texture(read_seg(pkg, s)): return s
        raise RuntimeError(f"file{hint}.unity3d does not contain {TEXTURE}. Clear the hint to Auto Scan.")
    log(f"Auto Scan: checking {len(ss)} UnityFS bundles...")
    for i, s in enumerate(ss, 1):
        progress(i, len(ss))
        if i == 1 or i % 25 == 0: log(f"Scanning file{s.number}.unity3d ({i}/{len(ss)})...")
        if has_texture(read_seg(pkg, s)):
            log(f"Found {TEXTURE} in file{s.number}.unity3d"); return s
    raise RuntimeError(f"Could not find {TEXTURE} in this mXX.pkg")


def splice(clean, s, new_blob, out):
    with clean.open("rb") as src, out.open("wb") as dst:
        left = s.offset
        while left:
            b = src.read(min(left, 8 * 1024 * 1024))
            if not b: raise IOError("Unexpected EOF")
            dst.write(b); left -= len(b)
        src.seek(s.size, 1); dst.write(new_blob)
        shutil.copyfileobj(src, dst, 8 * 1024 * 1024)


def apply(pkg, image, hint, log, progress):
    dirs(); clean = clean_source(pkg, log); ss = segments(clean)
    if not ss: raise RuntimeError("No UnityFS bundles found; wrong mXX.pkg?")
    log(f"Found {len(ss)} UnityFS bundles in {pkg.name}")
    target = find_target(clean, ss, hint, log, progress)
    new_blob = replace_texture(read_seg(clean, target), image)
    out = WORK / (pkg.name + ".new")
    if out.exists(): out.unlink()
    log(f"Rebuilding package with edited file{target.number}.unity3d..."); splice(clean, target, new_blob, out)
    check = segments(out)
    if len(check) != len(ss) or not has_texture(read_seg(out, check[target.number - 1])):
        raise RuntimeError("Rebuilt-package safety check failed")
    stamp = time.strftime("%Y%m%d-%H%M%S"); shutil.copy2(pkg, BACKUPS / f"{pkg.name}.before-{stamp}.bak")
    tmp = pkg.with_suffix(pkg.suffix + ".pfp.tmp"); shutil.copy2(out, tmp); os.replace(tmp, pkg); record_modified(pkg)
    progress(1, 1); log(f"DONE — installed {pkg.name}; target was file{target.number}.unity3d"); return target.number


def steam_roots():
    roots = []
    for p in [Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Steam", Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Steam"]:
        if p.exists() and p not in roots: roots.append(p)
        vdf = p / "steamapps/libraryfolders.vdf"
        if vdf.exists():
            try:
                for x in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text("utf-8", errors="ignore")):
                    q = Path(x.replace("\\\\", "\\"))
                    if q.exists() and q not in roots: roots.append(q)
            except Exception: pass
    return roots


def auto_container():
    rel = Path("steamapps/common/Blue Protocol Star Resonance/bpsr/BPSR_STEAM_Data/StreamingAssets/container")
    for r in steam_roots():
        p = r / rel
        if p.is_dir(): return p
        common = r / "steamapps/common"
        if common.is_dir():
            try:
                for g in common.iterdir():
                    if "protocol" not in g.name.lower() and "resonance" not in g.name.lower(): continue
                    for q in g.glob("**/StreamingAssets/container"):
                        if any(q.glob("m*.pkg")): return q
            except Exception: pass
    return None


def pkg_num(p):
    m = re.search(r"m(\d+)\.pkg$", p.name, re.I); return int(m.group(1)) if m else -1

if os.name == "nt":
    user32 = ctypes.windll.user32; CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def hwnd():
        found = []
        @CB
        def cb(h, _):
            if not user32.IsWindowVisible(h): return True
            n = user32.GetWindowTextLengthW(h); b = ctypes.create_unicode_buffer(n + 1); user32.GetWindowTextW(h, b, n + 1)
            t = b.value.lower()
            if "blue protocol" in t and "resonance" in t: found.append(h); return False
            return True
        user32.EnumWindows(cb, 0); return found[0] if found else None
    def resize(w, h):
        x = hwnd()
        if not x: raise RuntimeError("BPSR window not found. Put BPSR in Windowed mode.")
        if not user32.MoveWindow(x, 0, 0, w, h, True): raise RuntimeError("Resize failed; try Run as administrator")
else:
    def resize(w, h): raise RuntimeError("Windows only")


class App(tk.Tk):
    def __init__(self):
        super().__init__(); dirs(); self.cfg = load_cfg(); self.q = queue.Queue(); self.worker = None; self.card_i = 0
        self.title(f"{APP_NAME} v{VERSION}"); self.geometry("760x650"); self.minsize(700, 570)
        self.cv = tk.StringVar(value=self.cfg.get("container", "")); self.pv = tk.StringVar(value=self.cfg.get("package", "")); self.iv = tk.StringVar(); self.hv = tk.StringVar(value=self.cfg.get("hint", "")); self.sv = tk.StringVar(value="Ready"); self.prog = tk.DoubleVar()
        self.build(); self.after(100, self.drain); self.after(250, self.initial)

    def build(self):
        f = ttk.Frame(self); f.pack(fill="both", expand=True, padx=12, pady=12); pad = dict(padx=8, pady=5)
        ttk.Label(f, text=APP_NAME, font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", **pad)
        ttk.Label(f, text="Standalone Windows build — no Python installation needed.").grid(row=1, column=0, columnspan=4, sticky="w", **pad)
        ttk.Label(f, text="BPSR StreamingAssets\\container").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(f, textvariable=self.cv).grid(row=3, column=0, columnspan=2, sticky="ew", **pad); ttk.Button(f, text="Auto Find", command=self.autofind).grid(row=3, column=2, **pad); ttk.Button(f, text="Browse", command=self.browse).grid(row=3, column=3, **pad)
        ttk.Label(f, text="Current mXX.pkg (match Discord)").grid(row=4, column=0, sticky="w", **pad)
        self.combo = ttk.Combobox(f, textvariable=self.pv, state="readonly"); self.combo.grid(row=5, column=0, columnspan=3, sticky="ew", **pad); ttk.Button(f, text="Refresh", command=self.refresh).grid(row=5, column=3, **pad)
        ttk.Label(f, text="Discord fileNNN — optional").grid(row=6, column=0, sticky="w", **pad); ttk.Entry(f, textvariable=self.hv).grid(row=7, column=0, sticky="ew", **pad); ttk.Label(f, text="Use 593 / file593, or leave blank for Auto Scan").grid(row=7, column=1, columnspan=3, sticky="w", **pad)
        ttk.Label(f, text="Custom image").grid(row=8, column=0, sticky="w", **pad); ttk.Entry(f, textvariable=self.iv).grid(row=9, column=0, columnspan=3, sticky="ew", **pad); ttk.Button(f, text="Select Image", command=self.image).grid(row=9, column=3, **pad)
        b = ttk.Frame(f); b.grid(row=10, column=0, columnspan=4, sticky="ew", **pad); self.apply_b = ttk.Button(b, text="APPLY CUSTOM IMAGE", command=self.apply); self.apply_b.pack(side="left", fill="x", expand=True, padx=(0, 5)); ttk.Button(b, text="Restore Original", command=self.restore).pack(side="left")
        h = ttk.LabelFrame(f, text="Photo booth helper"); h.grid(row=11, column=0, columnspan=4, sticky="ew", **pad); ttk.Button(h, text="Portrait 545×2152", command=lambda:self.rz(545,2152)).pack(side="left", padx=5, pady=7); ttk.Button(h, text="Next Card Size", command=self.card).pack(side="left", padx=5); ttk.Button(h, text="Restore 1920×1080", command=lambda:self.rz(1920,1080)).pack(side="left", padx=5)
        ttk.Progressbar(f, variable=self.prog, maximum=100).grid(row=12, column=0, columnspan=4, sticky="ew", **pad); ttk.Label(f, textvariable=self.sv).grid(row=13, column=0, columnspan=4, sticky="w", **pad)
        box = ttk.LabelFrame(f, text="Log"); box.grid(row=14, column=0, columnspan=4, sticky="nsew", **pad); self.logbox = tk.Text(box, height=12, state="disabled", wrap="word"); self.logbox.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Label(f, text="Unofficial client-file modification. Keep backups; avoid NSFW/offensive images.").grid(row=15, column=0, columnspan=4, sticky="w", **pad)
        for i in range(3): f.columnconfigure(i, weight=1)
        f.rowconfigure(14, weight=1)

    def log(self, x): self.q.put(("log", x))
    def progress(self, a, b): self.q.put(("progress", 100*a/b if b else 0))
    def drain(self):
        try:
            while True:
                k, v = self.q.get_nowait()
                if k == "log": self.logbox.config(state="normal"); self.logbox.insert("end", v+"\n"); self.logbox.see("end"); self.logbox.config(state="disabled"); self.sv.set(v)
                elif k == "progress": self.prog.set(v)
                elif k == "done": self.apply_b.config(state="normal"); self.worker=None; messagebox.showinfo(APP_NAME,v)
                elif k == "error": self.apply_b.config(state="normal"); self.worker=None; messagebox.showerror(APP_NAME,v)
        except queue.Empty: pass
        self.after(100, self.drain)

    def initial(self):
        if self.cv.get() and Path(self.cv.get()).is_dir(): self.refresh()
        else: self.autofind(True)
    def autofind(self, silent=False):
        p = auto_container()
        if p: self.cv.set(str(p)); self.cfg["container"]=str(p); save_cfg(self.cfg); self.refresh(); self.log(f"Found BPSR: {p}")
        elif not silent: messagebox.showinfo(APP_NAME,"Could not auto-find BPSR; Browse to StreamingAssets\\container")
    def browse(self):
        p=filedialog.askdirectory(title="Select BPSR StreamingAssets\\container")
        if p: self.cv.set(p); self.refresh()
    def refresh(self):
        p=Path(self.cv.get())
        if not p.is_dir(): return
        xs=sorted(p.glob("m*.pkg"), key=pkg_num); names=[x.name for x in xs]; self.combo["values"]=names
        if self.pv.get() not in names and names: self.pv.set(names[-1])
        if names: self.log(f"Found {len(names)} m*.pkg files. Confirm the current one from Discord.")
    def image(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp"),("All files","*.*")])
        if p:self.iv.set(p)
    def selected(self):
        c=Path(self.cv.get()); p=c/self.pv.get()
        if not c.is_dir(): raise ValueError("Select the BPSR container folder")
        if not p.is_file(): raise ValueError("Select the current mXX.pkg")
        return p
    def apply(self):
        if self.worker:return
        try:
            p=self.selected(); img=Path(self.iv.get()); h=hint_num(self.hv.get())
            if not img.is_file(): raise ValueError("Select your image first")
        except Exception as e: messagebox.showerror(APP_NAME,str(e)); return
        self.cfg.update(container=str(p.parent),package=p.name,hint=self.hv.get()); save_cfg(self.cfg); self.apply_b.config(state="disabled"); self.prog.set(0)
        def work():
            try:n=apply(p,img,h,self.log,self.progress);self.q.put(("done",f"Installed successfully. Target: file{n}.unity3d.\n\nNow capture/save it at the BPSR guild photo booth."))
            except Exception as e:self.q.put(("error",f"{type(e).__name__}: {e}\n\nThe tool only installs a rebuilt package after its safety checks pass."))
        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()
    def restore(self):
        try:
            p=self.selected()
            if messagebox.askyesno(APP_NAME,f"Restore clean backup for {p.name}?"):
                messagebox.showinfo(APP_NAME,"Original restored" if restore(p) else "No clean backup exists yet")
        except Exception as e: messagebox.showerror(APP_NAME,str(e))
    def rz(self,w,h):
        try:resize(w,h);self.log(f"BPSR resized to {w}×{h}")
        except Exception as e:messagebox.showerror(APP_NAME,str(e))
    def card(self):
        sizes=[(545,2152),(545,3130),(545,4000),(545,5000),(545,6191)];w,h=sizes[self.card_i];self.rz(w,h);self.card_i=(self.card_i+1)%len(sizes)

if __name__ == "__main__": dirs(); App().mainloop()
