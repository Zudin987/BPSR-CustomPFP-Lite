from __future__ import annotations

import queue
from pathlib import Path

from tkinter import filedialog, messagebox

from crop_dialog import CropDialog
from game_helpers import auto_container, validate_container
from backup_ops import backup_session_status
from package_ops import remember_target
from unity_ops import Target
from settings import (
    APP_NAME,
    CARD_OUTPUT,
    CARD_RATIO,
    KNOWN_PACKAGE,
    PORTRAIT_OUTPUT,
    PORTRAIT_RATIO,
    package_number,
    save_cfg,
)

class UiStateMixin:
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
                    self.target_status.set(
                        f"{target.package.name} • file{target.segment.number} • {target.slot_name}"
                    )
                    remember_target(self.cfg, target)
                    self.refresh_packages()
                elif kind == "done":
                    self.worker = None
                    self.session_active = True
                    self.progress_var.set(100)
                    self.main_status.set("Applied successfully. Do Step 5 now. After the photo is saved, do Step 6.")
                    self.show_capture_instructions()
                    self.set_busy(False)
                    messagebox.showinfo(
                        APP_NAME,
                        "Applied successfully.\n\n"
                        "Do not close with the job half-finished:\n"
                        "1. Follow Step 5 and save the photo inside BPSR.\n"
                        "2. Then click Step 6 — Restore Original BPSR File.",
                    )
                elif kind == "search_done":
                    self.worker = None
                    self.progress_var.set(100)
                    self.set_busy(False)
                    messagebox.showinfo(APP_NAME, "Search finished. A supported picture location was found.")
                elif kind == "error":
                    self.worker = None
                    self.progress_var.set(0)
                    self.main_status.set(value)
                    self.set_busy(False)
                    messagebox.showerror(APP_NAME, value)
        except queue.Empty:
            pass
        self.after(100, self.drain_events)

    def initial_setup(self) -> None:
        saved = self.container_var.get().strip()
        found = auto_container(saved)
        if found:
            self.set_game_folder(found, "BPSR found ✓")
        else:
            self.game_status.set("BPSR not found yet — use one of the buttons below")
            self.main_status.set("Step 1: Find your BPSR game folder.")

        source = Path(self.source_image_var.get()) if self.source_image_var.get() else None
        crop = Path(self.image_var.get()) if self.image_var.get() else None
        if source and source.is_file() and crop and crop.is_file() and self.cfg.get("crop_mode") == self.mode_var.get():
            self.update_preview(crop)
            self.picture_status.set("Picture ready ✓")
        elif source and source.is_file():
            self.picture_status.set("Picture selected — adjust the crop for this shape.")
        self.show_cached_target()
        self.refresh_active_session_state()
        self.update_capture_buttons()
        self.update_card_prepare_visibility()
        self.apply_session_lock()
        self.update_ready_state()

    def refresh_active_session_state(self) -> None:
        self.session_active = False
        if not self.valid_game():
            return
        folder = Path(self.container_var.get())
        candidates = []
        for name in (self.cfg.get("detected_package"), self.package_var.get(), KNOWN_PACKAGE):
            if name and name not in candidates:
                candidates.append(name)
        for name in candidates:
            pkg = folder / name
            if not pkg.is_file():
                continue
            status = backup_session_status(pkg)
            if status == "modified":
                self.session_active = True
                self.main_status.set(
                    "A temporary custom-picture file is still active from an earlier session. "
                    "Finish Step 5 if needed, then do Step 6 to restore the original BPSR file."
                )
                self.show_capture_instructions()
                return

    def set_game_folder(self, path: Path, status: str = "BPSR found ✓") -> None:
        self.container_var.set(str(path))
        self.cfg["container"] = str(path)
        save_cfg(self.cfg)
        self.game_status.set(status)
        self.refresh_packages()
        self.refresh_active_session_state()
        self.apply_session_lock()
        self.update_ready_state()

    def auto_find_game(self) -> None:
        found = auto_container(self.container_var.get().strip() or None)
        if found:
            self.set_game_folder(found, "BPSR found automatically ✓")
            self.main_status.set("Step 2: Choose the picture you want." if not self.valid_image() else "Continue with Step 3.")
        else:
            self.game_status.set("Automatic search did not find BPSR")
            messagebox.showinfo(
                APP_NAME,
                "I could not find BPSR automatically.\n\n"
                "Click “I Will Choose the BPSR Folder”.\n"
                "Then choose the folder named:\n"
                "StreamingAssets\\container\n\n"
                "That folder should contain many files named m1.pkg, m2.pkg, and so on.",
            )
        self.update_ready_state()

    def choose_game_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose BPSR StreamingAssets\\container folder")
        if not selected:
            return
        path = Path(selected)
        if not validate_container(path):
            messagebox.showerror(
                APP_NAME,
                "That is not the right folder yet.\n\n"
                "Baby step:\n"
                "1. Keep opening folders until you reach StreamingAssets.\n"
                "2. Open the folder named container.\n"
                "3. It should contain many files such as m1.pkg, m2.pkg, m79.pkg.\n"
                "4. Select that container folder.",
            )
            return
        for key in (
            "detected_package",
            "detected_file",
            "detected_slot",
            "detected_offset",
            "detected_size",
            "detected_fingerprint",
            "package",
            "hint",
        ):
            self.cfg.pop(key, None)
        self.cfg["container"] = str(path)
        self.container_var.set(str(path))
        self.package_var.set("")
        self.hint_var.set("")
        self.target_status.set("Not searched yet")
        save_cfg(self.cfg)
        self.game_status.set("BPSR folder selected ✓")
        self.refresh_packages()
        self.update_ready_state()

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
            bool(self.source_image_var.get())
            and Path(self.source_image_var.get()).is_file()
            and bool(self.image_var.get())
            and Path(self.image_var.get()).is_file()
            and self.cfg.get("crop_mode") == self.mode_var.get()
        )

    def update_ready_state(self) -> None:
        if self.worker:
            self.apply_button.state(["disabled"])
            self.step_status.configure(text="Working now… please wait. Do not change folders or close BPSR.")
            return

        if self.session_active:
            self.apply_button.state(["disabled"])
            self.apply_session_lock()
            self.step_status.configure(
                text="✓ Step 1  ✓ Step 2  ✓ Step 3  ✓ Step 4  →  👉 Step 5 SAVE PHOTO  →  👉 Step 6 RESTORE ORIGINAL"
            )
            if not self.main_status.get().startswith("Applied"):
                self.main_status.set(
                    "Temporary picture is active. Save the photo in Step 5, then restore the original file in Step 6."
                )
            return

        self.apply_session_lock()

        if self.main_status.get().startswith("Finished"):
            self.apply_button.state(["disabled"])
            self.step_status.configure(text="Finished ✓  To make another picture, start again from Step 2.")
            return

        if not self.valid_game():
            self.apply_button.state(["disabled"])
            self.step_status.configure(text="👉 Step 1 — Find BPSR")
            self.main_status.set("Step 1: Find your BPSR game folder.")
            return
        if not self.valid_image():
            self.apply_button.state(["disabled"])
            self.step_status.configure(text="✓ Step 1  →  👉 Step 2 — Pick and crop your picture")
            self.main_status.set("Step 2: Choose a picture and finish the crop.")
            return
        if not self.booth_ready_var.get() or not self.windowed_ready_var.get():
            self.apply_button.state(["disabled"])
            self.step_status.configure(text="✓ Step 1  ✓ Step 2  →  👉 Step 3 — Get BPSR ready")
            self.main_status.set("Step 3: Open BPSR, go to the Guild Photo Booth, use Windowed mode, then tick both boxes.")
            return

        self.apply_button.state(["!disabled"])
        self.step_status.configure(text="✓ Step 1  ✓ Step 2  ✓ Step 3  →  👉 Step 4 — Apply")
        self.main_status.set("Ready. Click Step 4 — Apply Picture to BPSR.")

    def prep_changed(self) -> None:
        self.update_ready_state()

    def crop_settings(self):
        if self.mode_var.get() == "card":
            return CARD_RATIO, CARD_OUTPUT, "Card"
        return PORTRAIT_RATIO, PORTRAIT_OUTPUT, "Square"

    def choose_picture(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose your picture",
            filetypes=[("Pictures", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")],
        )
        if not selected:
            return
        source = Path(selected)
        self.source_image_var.set(str(source))
        self.cfg["source_image"] = str(source)
        save_cfg(self.cfg)
        self.open_crop(source)

    def adjust_crop(self) -> None:
        source = Path(self.source_image_var.get()) if self.source_image_var.get() else None
        if not source or not source.is_file():
            self.choose_picture()
            return
        self.open_crop(source)

    def open_crop(self, source: Path) -> None:
        try:
            ratio, output, label = self.crop_settings()
            dialog = CropDialog(self, source, ratio, output, label)
            self.wait_window(dialog)
            if dialog.result_path:
                self.image_var.set(str(dialog.result_path))
                self.cfg.update(
                    source_image=str(source),
                    image=str(dialog.result_path),
                    mode=self.mode_var.get(),
                    crop_mode=self.mode_var.get(),
                )
                save_cfg(self.cfg)
                self.update_preview(dialog.result_path)
                self.picture_status.set("Picture ready ✓")
                self.main_status.set("Continue with Step 3.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"I could not open that picture.\n\nDetails: {exc}")
        self.update_ready_state()

    def mode_changed(self) -> None:
        self.cfg["mode"] = self.mode_var.get()
        self.cfg.pop("crop_mode", None)
        save_cfg(self.cfg)
        self.reset_card_steps()
        self.capture_help_var.set(
            "This section will unlock after Apply succeeds. The app will then tell you exactly what to click."
        )
        source = Path(self.source_image_var.get()) if self.source_image_var.get() else None
        if source and source.is_file():
            self.picture_status.set("Picture shape changed — make a fresh crop from your original image.")
            self.after(50, lambda: self.open_crop(source))
        self.update_capture_buttons()
        self.update_card_prepare_visibility()
        self.update_ready_state()

    def update_preview(self, image_path: Path) -> None:
        from PIL import Image, ImageTk

        with Image.open(image_path) as source:
            image = source.copy()
        image.thumbnail((150, 150), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.preview_photo, text="")

    def worker_guard(self) -> bool:
        if self.worker:
            messagebox.showinfo(APP_NAME, "Please wait for the current step to finish.")
            return False
        self.progress_var.set(0)
        self.set_busy(True)
        return True
