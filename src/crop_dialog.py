from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import messagebox, ttk

from settings import APP_NAME, CROPS, ensure_dirs

class CropDialog(tk.Toplevel):
    def __init__(self, master, image_path: Path, ratio: tuple[int, int], output_size: tuple[int, int], label: str):
        super().__init__(master)
        from PIL import Image, ImageOps, ImageTk

        self.Image = Image
        self.ImageTk = ImageTk
        self.source_path = image_path
        self.target_ratio = ratio[0] / ratio[1]
        self.output_size = output_size
        self.label = label

        with Image.open(image_path) as source:
            self.original = ImageOps.exif_transpose(source).copy()
        if self.original.mode not in ("RGB", "RGBA"):
            self.original = self.original.convert("RGBA")

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.drag_last = None
        self.result_path: Optional[Path] = None
        self.info = tk.StringVar()

        self.title(f"Step 2 — Adjust {label} Picture")
        self.geometry("920x720")
        self.minsize(760, 580)
        self.transient(master)
        self.grab_set()

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"Make your {label.lower()} picture look right", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Baby step: drag the picture to move it. Use the mouse wheel to zoom. "
            "Everything inside the white box will be used.",
            wraplength=850,
        ).pack(anchor="w", pady=(3, 10))

        self.canvas = tk.Canvas(frame, bg="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(10, 0))
        ttk.Button(controls, text="Reset / Fit Picture", command=self.fit).pack(side="left")
        ttk.Button(controls, text="Zoom Out", command=lambda: self.bump_zoom(1 / 1.15)).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Zoom In", command=lambda: self.bump_zoom(1.15)).pack(side="left", padx=(6, 0))
        ttk.Label(controls, textvariable=self.info).pack(side="left", padx=12)
        ttk.Button(controls, text="Cancel", command=self.cancel).pack(side="right")
        ttk.Button(controls, text="Looks Good — Use This", command=self.accept).pack(side="right", padx=(0, 6))

        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
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
        display = self.original.resize((dw, dh), self.Image.Resampling.LANCZOS)
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
        self.info.set(f"Final size: {self.output_size[0]}×{self.output_size[1]}")

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
            messagebox.showerror(APP_NAME, "That crop is not usable. Click Reset / Fit Picture and try again.", parent=self)
            return

        cropped = self.original.crop((round(sx1), round(sy1), round(sx2), round(sy2)))
        cropped = cropped.resize(self.output_size, self.Image.Resampling.LANCZOS)
        ensure_dirs()
        output = CROPS / f"{self.label.lower()}_{int(time.time() * 1000)}.png"
        cropped.save(output)
        self.result_path = output
        self.destroy()

    def cancel(self) -> None:
        self.destroy()
