from __future__ import annotations

import ctypes, hashlib, json, mmap, os, queue, re, shutil, struct, threading, time
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME="BPSR Custom PFP Lite"
VERSION="0.2.1"
TEXTURE="personalzone_player_bg_3"
DATA=Path(os.environ.get("LOCALAPPDATA", Path.home()))/"BPSR-CustomPFP-Lite"
BACKUPS=DATA/"backups"; WORK=DATA/"work"; CROPS=DATA/"crops"; CONFIG=DATA/"config.json"
PORTRAIT_RATIO=(1,1); CARD_RATIO=(468,774)

@dataclass(frozen=True)
class Segment:
    number:int; offset:int; size:int

def dirs():
    for p in (DATA,BACKUPS,WORK,CROPS): p.mkdir(parents=True, exist_ok=True)

def load_cfg():
    dirs()
    try: return json.loads(CONFIG.read_text("utf-8"))
    except Exception: return {}

def save_cfg(cfg): CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def sha256(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024), b""): h.update(b)
    return h.hexdigest()

def cstr(mm,pos,limit=256):
    end=mm.find(b"\0", pos, min(len(mm), pos+limit))
    if end<0: raise ValueError
    return mm[pos:end].decode("utf-8","replace"), end+1

def parse_segment(mm, off):
    try:
        p=off; sig,p=cstr(mm,p,16)
        if sig!="UnityFS": return None
        version=struct.unpack_from(">I", mm, p)[0]; p+=4
        _,p=cstr(mm,p,128); _,p=cstr(mm,p,128)
        size=struct.unpack_from(">Q", mm, p)[0]
        if not(5<=version<=20) or size<(p+8-off) or size>len(mm)-off: return None
        return int(size)
    except Exception: return None

def segments(pkg:Path):
    out=[]
    with pkg.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        pos=0
        while True:
            off=mm.find(b"UnityFS\0", pos)
            if off<0: break
            size=parse_segment(mm, off)
            if size: out.append(Segment(len(out)+1, off, size)); pos=off+max(size,8)
            else: pos=off+8
    return out

def read_seg(pkg:Path, seg:Segment):
    with pkg.open("rb") as f:
        f.seek(seg.offset); return f.read(seg.size)

def textures(env):
    for obj in env.objects:
        if obj.type.name!="Texture2D": continue
        try: name=obj.peek_name()
        except Exception:
            try: name=obj.parse_as_object().m_Name
            except Exception: continue
        yield obj,name

def has_texture(blob):
    import UnityPy
    try:
        env=UnityPy.load(blob)
        return any(name==TEXTURE for _,name in textures(env))
    except Exception: return False

def replace_texture(blob, image_path:Path):
    import UnityPy
    from PIL import Image
    env=UnityPy.load(blob)
    img=Image.open(image_path)
    if img.mode not in ("RGB","RGBA"): img=img.convert("RGBA")
    changed=0
    for obj,name in textures(env):
        if name!=TEXTURE: continue
        tex=obj.parse_as_object(); tex.image=img.copy(); tex.save(); changed+=1
    if not changed: raise RuntimeError(f"{TEXTURE} was not found in the target bundle")
    return env.file.save()

def hint_num(text):
    if not text.strip(): return None
    m=re.search(r"(\d+)", text)
    if not m: raise ValueError("file hint must look like 593 or file593.unity3d")
    return int(m.group(1))

def backup_files(pkg:Path): return BACKUPS/(pkg.name+".clean"), BACKUPS/(pkg.name+".json")

def clean_source(pkg:Path, log):
    clean,meta=backup_files(pkg); cur=sha256(pkg)
    try: m=json.loads(meta.read_text("utf-8"))
    except Exception: m={}
    if not clean.exists():
        log("Creating clean baseline backup..."); shutil.copy2(pkg, clean); m={"clean":cur,"modified":None}
    elif cur not in {m.get("clean"), m.get("modified")}:
        log("Detected patched/verified package; refreshing clean baseline..."); shutil.copy2(pkg, clean); m={"clean":cur,"modified":None}
    elif not m.get("clean"): m["clean"]=sha256(clean)
    meta.write_text(json.dumps(m, indent=2), "utf-8")
    return clean

def record_modified(pkg:Path):
    clean,meta=backup_files(pkg)
    try: m=json.loads(meta.read_text("utf-8"))
    except Exception: m={}
    m["modified"]=sha256(pkg); m.setdefault("clean", sha256(clean) if clean.exists() else None)
    meta.write_text(json.dumps(m, indent=2), "utf-8")

def restore_clean(pkg:Path):
    clean,meta=backup_files(pkg)
    if not clean.exists(): return False
    tmp=pkg.with_suffix(pkg.suffix+".restore.tmp")
    shutil.copy2(clean,tmp); os.replace(tmp,pkg)
    try: m=json.loads(meta.read_text("utf-8"))
    except Exception: m={}
    m["modified"]=None; meta.write_text(json.dumps(m, indent=2), "utf-8")
    return True

def fast_raw_candidate(pkg:Path):
    needle=TEXTURE.encode("utf-8")
    try:
        ss=segments(pkg)
        if not ss: return None,len(ss)
        with pkg.open("rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            pos=mm.find(needle)
            if pos<0: return None,len(ss)
            for seg in ss:
                if seg.offset<=pos<seg.offset+seg.size:
                    if has_texture(read_seg(pkg,seg)): return seg,len(ss)
    except Exception: pass
    return None,0

def find_in_package(pkg:Path, hint:int|None, progress=None):
    ss=segments(pkg)
    if not ss: return None,None
    if hint:
        if 1<=hint<=len(ss):
            seg=ss[hint-1]
            if has_texture(read_seg(pkg,seg)): return seg,len(ss)
        return None,len(ss)
    raw,_=fast_raw_candidate(pkg)
    if raw: return raw,len(ss)
    for i,seg in enumerate(ss,1):
        if progress: progress(i,len(ss))
        if has_texture(read_seg(pkg,seg)): return seg,len(ss)
    return None,len(ss)

def locate_target_in_selected(pkg:Path, hint:int|None, log, progress):
    ss=segments(pkg)
    if not ss: raise RuntimeError("No UnityFS bundles found; wrong mXX.pkg?")
    log(f"Found {len(ss)} UnityFS bundles in {pkg.name}")
    if hint:
        if hint<1 or hint>len(ss): raise RuntimeError(f"file{hint} is outside this package (1-{len(ss)})")
        s=ss[hint-1]; log(f"Checking Discord hint file{hint}.unity3d...")
        if has_texture(read_seg(pkg,s)): return s,ss
        raise RuntimeError(f"file{hint}.unity3d does not contain {TEXTURE}. Clear the hint and use Auto Detect.")
    log(f"Auto Scan: checking {len(ss)} UnityFS bundles...")
    for i,s in enumerate(ss,1):
        progress(i,len(ss))
        if i==1 or i%25==0: log(f"Scanning file{s.number}.unity3d ({i}/{len(ss)})...")
        if has_texture(read_seg(pkg,s)): log(f"Found {TEXTURE} in file{s.number}.unity3d"); return s,ss
    raise RuntimeError(f"Could not find {TEXTURE} in this mXX.pkg")

def splice(clean:Path, target:Segment, new_blob:bytes, out:Path):
    with clean.open("rb") as src, out.open("wb") as dst:
        left=target.offset
        while left:
            block=src.read(min(left,8*1024*1024))
            if not block: raise IOError("Unexpected EOF")
            dst.write(block); left-=len(block)
        src.seek(target.size,1); dst.write(new_blob); shutil.copyfileobj(src,dst,8*1024*1024)

def apply_image(pkg:Path, image:Path, hint:int|None, log, progress):
    clean=clean_source(pkg, log)
    target,ss=locate_target_in_selected(clean,hint,log,progress)
    new_blob=replace_texture(read_seg(clean,target), image)
    out=WORK/(pkg.name+".new")
    if out.exists(): out.unlink()
    log(f"Rebuilding package with edited file{target.number}.unity3d...")
    splice(clean,target,new_blob,out)
    check=segments(out)
    if len(check)!=len(ss) or not has_texture(read_seg(out, check[target.number-1])): raise RuntimeError("Rebuilt-package safety check failed")
    stamp=time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(pkg, BACKUPS/f"{pkg.name}.before-{stamp}.bak")
    tmp=pkg.with_suffix(pkg.suffix+".pfp.tmp")
    shutil.copy2(out,tmp); os.replace(tmp,pkg); record_modified(pkg)
    progress(1,1); log(f"DONE — installed {pkg.name}; target was file{target.number}.unity3d")
    return target.number

def pkg_num(path:Path):
    m=re.search(r"m(\d+)\.pkg$", path.name, re.I)
    return int(m.group(1)) if m else -1

def detect_package(container:Path, hint:int|None, cfg:dict, log, progress):
    pkgs=sorted(container.glob("m*.pkg"), key=pkg_num)
    if not pkgs: raise RuntimeError("No m*.pkg files were found in this container folder")
    ordered=[]; seen=set()
    for key in ("detected_package","package"):
        name=cfg.get(key)
        if name:
            p=container/name
            if p.exists() and p.name not in seen: ordered.append(p); seen.add(p.name)
    for p in sorted(pkgs, key=lambda x:x.stat().st_mtime, reverse=True):
        if p.name not in seen: ordered.append(p); seen.add(p.name)

    # Fastest path: validate the last known package+bundle first.
    cached_pkg=container/cfg.get("detected_package","")
    cached_file=cfg.get("detected_file")
    if cached_pkg.is_file() and cached_file and not hint:
        log(f"Checking cached target {cached_pkg.name} -> file{cached_file}.unity3d...")
        seg,_=find_in_package(cached_pkg, int(cached_file))
        if seg:
            progress(1,1); return cached_pkg,seg.number

    def scan(pass_hint):
        total=len(ordered); log(f"Auto Detect: checking {total} mXX.pkg files" + (f" with file{pass_hint} hint..." if pass_hint else "..."))
        for idx,pkg in enumerate(ordered,1):
            progress(idx-1,total)
            log(f"Checking {pkg.name} ({idx}/{total})..." + (f" using file{pass_hint}" if pass_hint else ""))
            seg,_=find_in_package(pkg,pass_hint)
            if seg:
                cfg["detected_package"]=pkg.name; cfg["detected_file"]=seg.number; save_cfg(cfg)
                progress(total,total); log(f"Found target in {pkg.name} -> file{seg.number}.unity3d")
                return pkg,seg.number
        return None

    found=scan(hint)
    if found: return found
    if hint:
        log(f"file{hint} hint did not match any package. Falling back to full scan automatically...")
        found=scan(None)
        if found: return found
    raise RuntimeError(f"Could not find {TEXTURE} in any mXX.pkg inside this container")

def steam_roots():
    roots=[]
    for p in [Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))/"Steam", Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))/"Steam"]:
        if p.exists() and p not in roots: roots.append(p)
        vdf=p/"steamapps/libraryfolders.vdf"
        if vdf.exists():
            try:
                for x in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text("utf-8", errors="ignore")):
                    q=Path(x.replace("\\\\","\\"))
                    if q.exists() and q not in roots: roots.append(q)
            except Exception: pass
    return roots

def auto_container():
    rel=Path("steamapps/common/Blue Protocol Star Resonance/bpsr/BPSR_STEAM_Data/StreamingAssets/container")
    for root in steam_roots():
        p=root/rel
        if p.is_dir(): return p
        common=root/"steamapps/common"
        if common.is_dir():
            try:
                for g in common.iterdir():
                    if "protocol" not in g.name.lower() and "resonance" not in g.name.lower(): continue
                    for q in g.glob("**/StreamingAssets/container"):
                        if any(q.glob("m*.pkg")): return q
            except Exception: pass
    return None

if os.name=="nt":
    user32=ctypes.windll.user32; CB=ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def hwnd():
        found=[]
        @CB
        def cb(h,_):
            if not user32.IsWindowVisible(h): return True
            n=user32.GetWindowTextLengthW(h); buf=ctypes.create_unicode_buffer(n+1); user32.GetWindowTextW(h, buf, n+1)
            t=buf.value.lower()
            if "blue protocol" in t and "resonance" in t: found.append(h); return False
            return True
        user32.EnumWindows(cb,0); return found[0] if found else None
    def resize(w,h):
        x=hwnd()
        if not x: raise RuntimeError("BPSR window not found. Put BPSR in Windowed mode.")
        if not user32.MoveWindow(x,0,0,w,h,True): raise RuntimeError("Resize failed; try Run as administrator")
else:
    def resize(w,h): raise RuntimeError("Windows only")

class CropDialog(tk.Toplevel):
    def __init__(self, master, image_path:Path, ratio:tuple[int,int], label:str):
        super().__init__(master)
        from PIL import Image, ImageTk
        self.Image=Image; self.ImageTk=ImageTk; self.src=Path(image_path); self.label=label
        self.target_ratio=ratio[0]/ratio[1]; self.title(f"Crop {label} image")
        self.geometry("960x740"); self.minsize(820,620); self.transient(master); self.grab_set()
        self.original=Image.open(self.src)
        if self.original.mode not in ("RGB","RGBA"): self.original=self.original.convert("RGBA")
        self.zoom=1.0; self.min_zoom=0.05; self.max_zoom=8.0; self.pan_x=0.0; self.pan_y=0.0; self.drag=None; self.result_path=None
        self.info=tk.StringVar()
        top=ttk.Frame(self); top.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(top, text=f"Adjust your {label} crop", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(top, text="Drag image to reposition. Mouse wheel = zoom. Highlighted area is what will be used.").pack(anchor="w", pady=(0,8))
        self.canvas=tk.Canvas(top, bg="#1e1e1e", highlightthickness=0); self.canvas.pack(fill="both", expand=True)
        ctr=ttk.Frame(top); ctr.pack(fill="x", pady=(8,0))
        ttk.Button(ctr, text="Fit", command=self.fit).pack(side="left")
        ttk.Button(ctr, text="Zoom -", command=lambda:self.bump(1/1.15)).pack(side="left", padx=4)
        ttk.Button(ctr, text="Zoom +", command=lambda:self.bump(1.15)).pack(side="left")
        ttk.Label(ctr, textvariable=self.info).pack(side="left", padx=12)
        ttk.Button(ctr, text="Cancel", command=self.cancel).pack(side="right")
        ttk.Button(ctr, text="Use Crop", command=self.accept).pack(side="right", padx=(0,6))
        self.canvas.bind("<Configure>", lambda e:self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-4>", lambda e:self.bump(1.1))
        self.canvas.bind("<Button-5>", lambda e:self.bump(1/1.1))
        self.fit()
    def crop_box(self):
        cw=max(1,self.canvas.winfo_width()); ch=max(1,self.canvas.winfo_height()); pad=30
        aw,ah=cw-pad*2, ch-pad*2
        if aw<=50 or ah<=50: return (20,20,cw-20,ch-20)
        if aw/ah>self.target_ratio: h=ah; w=h*self.target_ratio
        else: w=aw; h=w/self.target_ratio
        x1=(cw-w)/2; y1=(ch-h)/2; return (x1,y1,x1+w,y1+h)
    def cover_zoom(self):
        x1,y1,x2,y2=self.crop_box(); iw,ih=self.original.size
        return max((x2-x1)/iw, (y2-y1)/ih)
    def clamp_pan(self):
        cw=max(1,self.canvas.winfo_width()); ch=max(1,self.canvas.winfo_height()); x1,y1,x2,y2=self.crop_box(); iw,ih=self.original.size
        dw,dh=iw*self.zoom, ih*self.zoom; cx,cy=cw/2+self.pan_x, ch/2+self.pan_y
        left=cx-dw/2; right=cx+dw/2; top=cy-dh/2; bottom=cy+dh/2
        if left>x1: self.pan_x-=left-x1
        if right<x2: self.pan_x+=x2-right
        if top>y1: self.pan_y-=top-y1
        if bottom<y2: self.pan_y+=y2-bottom
    def fit(self):
        self.update_idletasks(); self.min_zoom=max(0.01,self.cover_zoom()); self.zoom=self.min_zoom; self.pan_x=0.0; self.pan_y=0.0; self.redraw()
    def bump(self,factor):
        self.min_zoom=max(0.01,self.cover_zoom()); self.zoom=max(self.min_zoom, min(self.max_zoom, self.zoom*factor)); self.clamp_pan(); self.redraw()
    def on_press(self,e): self.drag=(e.x,e.y)
    def on_drag(self,e):
        if not self.drag: return
        dx,dy=e.x-self.drag[0], e.y-self.drag[1]; self.drag=(e.x,e.y); self.pan_x+=dx; self.pan_y+=dy; self.clamp_pan(); self.redraw()
    def on_wheel(self,e): self.bump(1.1 if e.delta>0 else 1/1.1)
    def redraw(self):
        self.canvas.delete("all")
        cw=max(1,self.canvas.winfo_width()); ch=max(1,self.canvas.winfo_height()); iw,ih=self.original.size
        self.min_zoom=max(0.01,self.cover_zoom())
        if self.zoom<self.min_zoom: self.zoom=self.min_zoom
        self.clamp_pan()
        dw=max(1,int(iw*self.zoom)); dh=max(1,int(ih*self.zoom)); disp=self.original.resize((dw,dh), self.Image.LANCZOS)
        self.tk_img=self.ImageTk.PhotoImage(disp)
        cx,cy=cw/2+self.pan_x, ch/2+self.pan_y; left=cx-dw/2; top=cy-dh/2
        self.canvas.create_image(left, top, anchor="nw", image=self.tk_img)
        x1,y1,x2,y2=self.crop_box()
        self.canvas.create_rectangle(0,0,cw,y1, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(0,y2,cw,ch, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(0,y1,x1,y2, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(x2,y1,cw,y2, fill="#000", stipple="gray50", outline="")
        self.canvas.create_rectangle(x1,y1,x2,y2, outline="#66d9ef", width=2)
        self.info.set(f"Source: {iw}×{ih}   Zoom: {self.zoom:.2f}x")
    def accept(self):
        x1,y1,x2,y2=self.crop_box(); cw=max(1,self.canvas.winfo_width()); ch=max(1,self.canvas.winfo_height()); iw,ih=self.original.size
        dw=max(1,int(iw*self.zoom)); dh=max(1,int(ih*self.zoom)); cx,cy=cw/2+self.pan_x, ch/2+self.pan_y; left=cx-dw/2; top=cy-dh/2
        sx1=max(0,int(round((x1-left)/self.zoom))); sy1=max(0,int(round((y1-top)/self.zoom)))
        sx2=min(iw,int(round((x2-left)/self.zoom))); sy2=min(ih,int(round((y2-top)/self.zoom)))
        if sx2<=sx1 or sy2<=sy1: messagebox.showerror(APP_NAME, "Crop area is invalid. Try Fit first.", parent=self); return
        cropped=self.original.crop((sx1,sy1,sx2,sy2))
        target_size=(1024,1024) if self.label.lower()=="portrait" else (468,774)
        cropped=cropped.resize(target_size, self.Image.LANCZOS)
        out=CROPS/f"cropped_{self.label.lower()}_{int(time.time())}.png"; cropped.save(out); self.result_path=out; self.destroy()
    def cancel(self): self.result_path=None; self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__(); dirs(); self.cfg=load_cfg(); self.q=queue.Queue(); self.worker=None; self.card_i=0
        self.title(f"{APP_NAME} v{VERSION}"); self.geometry("820x760"); self.minsize(760,620)
        self.cv=tk.StringVar(value=self.cfg.get("container","")); self.pv=tk.StringVar(value=self.cfg.get("package","")); self.iv=tk.StringVar(value=self.cfg.get("image",""))
        self.hv=tk.StringVar(value=self.cfg.get("hint","")); self.sv=tk.StringVar(value="Ready"); self.prog=tk.DoubleVar()
        self.modev=tk.StringVar(value=self.cfg.get("mode","portrait")); self.detected=tk.StringVar(value="Not detected yet")
        self.build(); self.after(100,self.drain); self.after(250,self.initial)
    def build(self):
        f=ttk.Frame(self); f.pack(fill="both", expand=True, padx=12, pady=12); pad=dict(padx=8,pady=5)
        ttk.Label(f, text=APP_NAME, font=("Segoe UI",18,"bold")).grid(row=0,column=0,columnspan=5,sticky="w",**pad)
        ttk.Label(f, text="Standalone Windows build — no Python installation needed.").grid(row=1,column=0,columnspan=5,sticky="w",**pad)
        ttk.Label(f, text="BPSR StreamingAssets\\container — auto-find, type a path, or Browse anytime").grid(row=2,column=0,columnspan=5,sticky="w",**pad)
        ttk.Entry(f,textvariable=self.cv).grid(row=3,column=0,columnspan=3,sticky="ew",**pad)
        ttk.Button(f,text="Auto Find",command=self.autofind).grid(row=3,column=3,**pad)
        ttk.Button(f,text="Browse",command=self.browse).grid(row=3,column=4,**pad)
        ttk.Label(f,text="Current mXX.pkg").grid(row=4,column=0,sticky="w",**pad)
        self.combo=ttk.Combobox(f,textvariable=self.pv,state="readonly"); self.combo.grid(row=5,column=0,columnspan=3,sticky="ew",**pad)
        ttk.Button(f,text="Refresh",command=self.refresh).grid(row=5,column=3,**pad)
        ttk.Button(f,text="Auto Detect mXX + fileNNN",command=self.auto_detect).grid(row=5,column=4,**pad)
        ttk.Label(f,text="Detected target").grid(row=6,column=0,sticky="w",**pad)
        ttk.Label(f,textvariable=self.detected).grid(row=7,column=0,columnspan=5,sticky="w",**pad)
        ttk.Label(f,text="Discord fileNNN — optional").grid(row=8,column=0,sticky="w",**pad)
        ttk.Entry(f,textvariable=self.hv).grid(row=9,column=0,sticky="ew",**pad)
        ttk.Label(f,text="Use 593 / file593 to speed up detection, or leave blank for full Auto Scan.").grid(row=9,column=1,columnspan=4,sticky="w",**pad)
        ttk.Label(f,text="Image type").grid(row=10,column=0,sticky="w",**pad)
        m=ttk.Frame(f); m.grid(row=11,column=0,columnspan=5,sticky="w",**pad)
        ttk.Radiobutton(m,text="Portrait (1:1)",variable=self.modev,value="portrait",command=self.on_mode_change).pack(side="left")
        ttk.Radiobutton(m,text="Card (468:774)",variable=self.modev,value="card",command=self.on_mode_change).pack(side="left",padx=(12,0))
        ttk.Label(f,text="Custom image").grid(row=12,column=0,sticky="w",**pad)
        ttk.Entry(f,textvariable=self.iv).grid(row=13,column=0,columnspan=3,sticky="ew",**pad)
        ttk.Button(f,text="Select Image",command=self.pick_image).grid(row=13,column=3,**pad)
        ttk.Button(f,text="Crop / Reposition",command=self.crop_current).grid(row=13,column=4,**pad)
        b=ttk.Frame(f); b.grid(row=14,column=0,columnspan=5,sticky="ew",**pad)
        self.apply_b=ttk.Button(b,text="APPLY CUSTOM IMAGE",command=self.apply); self.apply_b.pack(side="left",fill="x",expand=True,padx=(0,5))
        ttk.Button(b,text="Restore Original",command=self.restore).pack(side="left")
        h=ttk.LabelFrame(f,text="Photo booth helper"); h.grid(row=15,column=0,columnspan=5,sticky="ew",**pad)
        ttk.Button(h,text="Portrait 545×2152",command=lambda:self.rz(545,2152)).pack(side="left",padx=5,pady=7)
        ttk.Button(h,text="Next Card Size",command=self.card).pack(side="left",padx=5)
        ttk.Button(h,text="Restore 1920×1080",command=lambda:self.rz(1920,1080)).pack(side="left",padx=5)
        ttk.Progressbar(f,variable=self.prog,maximum=100).grid(row=16,column=0,columnspan=5,sticky="ew",**pad)
        ttk.Label(f,textvariable=self.sv).grid(row=17,column=0,columnspan=5,sticky="w",**pad)
        box=ttk.LabelFrame(f,text="Log"); box.grid(row=18,column=0,columnspan=5,sticky="nsew",**pad)
        self.logbox=tk.Text(box,height=12,state="disabled",wrap="word"); self.logbox.pack(fill="both",expand=True,padx=5,pady=5)
        ttk.Label(f,text="Unofficial client-file modification. Keep backups; avoid NSFW/offensive images.").grid(row=19,column=0,columnspan=5,sticky="w",**pad)
        for i in range(4): f.columnconfigure(i,weight=1)
        f.rowconfigure(18,weight=1)
    def log(self,msg): self.q.put(("log",msg))
    def progress(self,a,b): self.q.put(("progress",100*a/b if b else 0))
    def drain(self):
        try:
            while True:
                kind,val=self.q.get_nowait()
                if kind=="log":
                    self.logbox.config(state="normal"); self.logbox.insert("end", val+"\n"); self.logbox.see("end"); self.logbox.config(state="disabled"); self.sv.set(val)
                elif kind=="progress": self.prog.set(val)
                elif kind=="done": self.apply_b.config(state="normal"); self.worker=None; messagebox.showinfo(APP_NAME,val)
                elif kind=="detected":
                    pkg,file_no=val; self.pv.set(pkg); self.hv.set(str(file_no)); self.detected.set(f"{pkg} -> file{file_no}.unity3d"); self.apply_b.config(state="normal"); self.worker=None
                    messagebox.showinfo(APP_NAME, f"Auto Detect complete.\n\nPackage: {pkg}\nBundle: file{file_no}.unity3d")
                elif kind=="error": self.apply_b.config(state="normal"); self.worker=None; messagebox.showerror(APP_NAME,val)
        except queue.Empty: pass
        self.after(100,self.drain)
    def initial(self):
        if self.cv.get() and Path(self.cv.get()).is_dir(): self.refresh()
        else: self.autofind(True)
        if self.cfg.get("detected_package") and self.cfg.get("detected_file"): self.detected.set(f"{self.cfg['detected_package']} -> file{self.cfg['detected_file']}.unity3d")
    def autofind(self,silent=False):
        p=auto_container()
        if p: self.cv.set(str(p)); self.cfg["container"]=str(p); save_cfg(self.cfg); self.refresh(); self.log(f"Found BPSR: {p}")
        elif not silent: messagebox.showinfo(APP_NAME,"Could not auto-find BPSR; Browse to StreamingAssets\\container")
    def browse(self):
        p=filedialog.askdirectory(title="Select BPSR StreamingAssets\\container")
        if p: self.cv.set(p); self.cfg["container"]=p; save_cfg(self.cfg); self.refresh()
    def refresh(self):
        p=Path(self.cv.get())
        if not p.is_dir():
            messagebox.showerror(APP_NAME,"That folder does not exist. Use Browse to locate StreamingAssets\\container.")
            return
        self.cfg["container"]=str(p); save_cfg(self.cfg)
        vals=[x.name for x in sorted(p.glob("m*.pkg"), key=pkg_num)]; self.combo["values"]=vals
        if vals and self.pv.get() not in vals: self.pv.set(self.cfg.get("detected_package") if self.cfg.get("detected_package") in vals else vals[-1])
        if vals: self.log(f"Found {len(vals)} m*.pkg files.")
    def current_ratio(self): return PORTRAIT_RATIO if self.modev.get()=="portrait" else CARD_RATIO
    def ask_crop(self,path:Path):
        dlg=CropDialog(self,path,self.current_ratio(),self.modev.get().capitalize()); self.wait_window(dlg)
        if dlg.result_path: self.iv.set(str(dlg.result_path)); self.cfg["image"]=str(dlg.result_path); save_cfg(self.cfg); self.log(f"Saved cropped image: {dlg.result_path.name}")
    def pick_image(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp"),("All files","*.*")])
        if p: self.iv.set(p); self.cfg["image"]=p; save_cfg(self.cfg); self.ask_crop(Path(p))
    def crop_current(self):
        p=Path(self.iv.get())
        if not p.is_file(): messagebox.showerror(APP_NAME,"Select an image first"); return
        try: self.ask_crop(p)
        except Exception as e: messagebox.showerror(APP_NAME,f"Crop tool failed: {e}")
    def on_mode_change(self): self.cfg["mode"]=self.modev.get(); save_cfg(self.cfg)
    def selected(self):
        c=Path(self.cv.get()); p=c/self.pv.get()
        if not c.is_dir(): raise ValueError("Select the BPSR container folder")
        if not p.is_file(): raise ValueError("Select the current mXX.pkg")
        return p
    def auto_detect(self):
        if self.worker: return
        container=Path(self.cv.get())
        if not container.is_dir(): messagebox.showerror(APP_NAME,"Select the BPSR container folder first"); return
        try: hint=hint_num(self.hv.get())
        except Exception as e: messagebox.showerror(APP_NAME,str(e)); return
        self.apply_b.config(state="disabled"); self.prog.set(0); self.log("Starting auto detect...")
        def work():
            try:
                pkg,file_no=detect_package(container,hint,self.cfg,self.log,self.progress)
                self.cfg.update(container=str(container), package=pkg.name, hint=str(file_no)); save_cfg(self.cfg); self.q.put(("detected", (pkg.name,file_no)))
            except Exception as e: self.q.put(("error", f"{type(e).__name__}: {e}"))
        self.worker=threading.Thread(target=work,daemon=True); self.worker.start()
    def apply(self):
        if self.worker: return
        try:
            pkg=self.selected(); img=Path(self.iv.get()); hint=hint_num(self.hv.get())
            if not img.is_file(): raise ValueError("Select your image first")
        except Exception as e: messagebox.showerror(APP_NAME,str(e)); return
        self.cfg.update(container=str(pkg.parent), package=pkg.name, hint=self.hv.get(), mode=self.modev.get(), image=str(img)); save_cfg(self.cfg); self.apply_b.config(state="disabled"); self.prog.set(0)
        def work():
            try:
                file_no=apply_image(pkg,img,hint,self.log,self.progress)
                self.cfg["detected_package"]=pkg.name; self.cfg["detected_file"]=file_no; save_cfg(self.cfg)
                self.q.put(("done", f"Installed successfully. Target: file{file_no}.unity3d.\n\nNow capture/save it at the BPSR guild photo booth."))
            except Exception as e: self.q.put(("error", f"{type(e).__name__}: {e}\n\nThe tool only installs a rebuilt package after its safety checks pass."))
        self.worker=threading.Thread(target=work,daemon=True); self.worker.start()
    def restore(self):
        try:
            pkg=self.selected()
            if messagebox.askyesno(APP_NAME, f"Restore clean backup for {pkg.name}?"): messagebox.showinfo(APP_NAME, "Original restored" if restore_clean(pkg) else "No clean backup exists yet")
        except Exception as e: messagebox.showerror(APP_NAME,str(e))
    def rz(self,w,h):
        try: resize(w,h); self.log(f"BPSR resized to {w}×{h}")
        except Exception as e: messagebox.showerror(APP_NAME,str(e))
    def card(self):
        sizes=[(545,2152),(545,3130),(545,4000),(545,5000),(545,6191)]; w,h=sizes[self.card_i]; self.rz(w,h); self.card_i=(self.card_i+1)%len(sizes)

if __name__=="__main__": dirs(); App().mainloop()
