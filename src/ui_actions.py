from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from tkinter import messagebox

from game_helpers import get_bpsr_rect, resize_bpsr, restore_bpsr_rect, validate_container
from backup_ops import restore_original
from package_ops import apply_picture, find_target
from settings import backup_paths
from settings import APP_NAME, CARD_SIZES, KNOWN_PACKAGE, parse_file_hint, save_cfg

class UiActionsMixin:
    def search_again(self) -> None:
        if not self.worker_guard():
            return
        if not self.valid_game():
            self.set_busy(False)
            messagebox.showerror(APP_NAME, "Do Step 1 first and choose a valid BPSR game folder.")
            return
        try:
            file_hint = parse_file_hint(self.hint_var.get())
        except Exception as exc:
            self.set_busy(False)
            messagebox.showerror(APP_NAME, str(exc))
            return

        folder = Path(self.container_var.get())
        self.cfg.update(container=str(folder), hint=self.hint_var.get(), package=self.package_var.get())
        for key in (
            "detected_package",
            "detected_file",
            "detected_slot",
            "detected_offset",
            "detected_size",
            "detected_fingerprint",
        ):
            self.cfg.pop(key, None)
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
            self.set_busy(False)
            self.update_ready_state()
            return
        if not self.booth_ready_var.get() or not self.windowed_ready_var.get():
            self.set_busy(False)
            self.update_ready_state()
            messagebox.showwarning(APP_NAME, "Finish Step 3 and tick both boxes before Apply.")
            return
        try:
            file_hint = parse_file_hint(self.hint_var.get())
        except Exception as exc:
            self.set_busy(False)
            messagebox.showerror(APP_NAME, str(exc))
            return

        folder = Path(self.container_var.get())
        image = Path(self.image_var.get())
        self.cfg.update(
            container=str(folder),
            source_image=self.source_image_var.get(),
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
        if self.worker:
            messagebox.showinfo(APP_NAME, "Please wait for the current Apply/Search step to finish first.")
            return
        if not self.valid_game():
            messagebox.showerror(APP_NAME, "Choose your BPSR game folder first.")
            return

        folder = Path(self.container_var.get())
        candidates = []
        for name in (self.cfg.get("detected_package"), self.package_var.get(), KNOWN_PACKAGE):
            if name and name not in candidates:
                candidates.append(name)
        pkg = next((folder / name for name in candidates if (folder / name).is_file() and backup_paths(folder / name)[0].exists()), None)
        if not pkg:
            messagebox.showinfo(APP_NAME, "No clean backup from this BPSR installation was found yet.")
            return

        if not messagebox.askyesno(
            APP_NAME,
            "Have you already SAVED the portrait/card inside BPSR?\n\n"
            "Click Yes only when the in-game photo is safely saved. "
            "The app will then put the original BPSR file back.",
        ):
            return

        self.set_busy(True)
        try:
            result = restore_original(pkg)
            if result == "restored":
                text = "Finished ✓  The original BPSR file is back in place."
            elif result == "already":
                text = "Finished ✓  BPSR was already using the original clean file."
            else:
                text = "No clean backup was found."
            self.session_active = False
            self.main_status.set(text)
            self.capture_help_var.set(
                "Finished. The temporary custom-picture game-file change has been removed. "
                "To make another picture, start again from Step 2."
            )
            self.booth_ready_var.set(False)
            self.windowed_ready_var.set(False)
            self.cfg.pop("crop_mode", None)
            save_cfg(self.cfg)
            self.picture_status.set("Finished. For another picture, choose a new image or adjust the crop again.")
            self.reset_card_steps()
            self.clear_saved_window_rect()
            messagebox.showinfo(APP_NAME, text)
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
        finally:
            self.set_busy(False)

    def save_advanced_selection(self) -> None:
        folder = Path(self.container_var.get()) if self.container_var.get() else None
        package = self.package_var.get()
        if not folder or not validate_container(folder):
            messagebox.showerror(APP_NAME, "Choose a valid BPSR container folder first.")
            return
        if package and not (folder / package).is_file():
            messagebox.showerror(APP_NAME, "That game file no longer exists. Click Refresh List.")
            return
        self.cfg.update(container=str(folder), package=package, hint=self.hint_var.get())
        save_cfg(self.cfg)
        self.game_status.set("BPSR folder selected ✓")
        messagebox.showinfo(APP_NAME, "Advanced choice saved. Normal Apply will try it first.")

    def show_capture_instructions(self) -> None:
        if self.mode_var.get() == "card":
            self.capture_help_var.set(
                "CARD — follow these baby steps in order:\n"
                "1. If you have not already: in Step 3 click “Remember My Normal BPSR Window”, then set BPSR to Windowed 1600×900 in BPSR Settings.\n"
                "2. Click “Card Resize — Step 1/5” below.\n"
                "3. In Guild Photo Booth choose Take Card Photo → Settings → select your custom background.\n"
                "4. Use a lying-down/hidden-character emote, freeze it, then press F to hide the UI.\n"
                "5. Drag the BPSR picture/capture window to the TOP of your screen.\n"
                "6. Click the Card Resize button again. After every resize, drag the picture window back to the TOP.\n"
                "7. Repeat until the log/status says step 5 of 5 is ready.\n"
                "8. Press V and SAVE the card photo in BPSR.\n"
                "9. Click “Restore My Previous BPSR Window”.\n"
                "10. Upload/use the captured card in BPSR, then do Step 6 below."
            )
        else:
            self.capture_help_var.set(
                "SQUARE PROFILE — follow these baby steps in order:\n"
                "1. Click “Resize BPSR for Square Photo” below.\n"
                "2. In Guild Photo Booth choose Take Portrait → Settings → select your custom background.\n"
                "3. Use a lying-down/hidden-character emote, freeze it, then press F to hide the UI.\n"
                "4. Drag the BPSR picture/capture window to the TOP of your screen.\n"
                "5. Press V and SAVE the portrait in BPSR.\n"
                "6. Click “Restore My Previous BPSR Window”.\n"
                "7. Upload/use the captured portrait in BPSR, then do Step 6 below."
            )
        self.update_capture_buttons()

    def update_card_prepare_visibility(self) -> None:
        if not hasattr(self, "card_prepare_row"):
            return
        if self.mode_var.get() == "card":
            if not self.card_prepare_row.winfo_ismapped():
                self.card_prepare_row.pack(fill="x", padx=8, pady=(0, 8), before=self.booth_check)
        else:
            self.card_prepare_row.pack_forget()

    def remember_normal_window_clicked(self) -> None:
        try:
            rect = get_bpsr_rect()
            self.cfg["window_rect"] = list(rect)
            save_cfg(self.cfg)
            self.card_window_status.set(
                f"Saved ✓  Normal window: {rect[2]}×{rect[3]}. Now set BPSR to Windowed 1600×900."
            )
            messagebox.showinfo(
                APP_NAME,
                "Saved your normal BPSR window size and position.\n\n"
                "Next baby step: inside BPSR Settings, switch to Windowed 1600×900. "
                "Then continue Step 3.",
            )
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def get_saved_window_rect(self) -> Optional[tuple[int, int, int, int]]:
        value = self.cfg.get("window_rect")
        if isinstance(value, list) and len(value) == 4:
            try:
                return tuple(int(x) for x in value)
            except Exception:
                return None
        return None

    def remember_window_rect_once(self) -> None:
        if self.get_saved_window_rect():
            return
        rect = get_bpsr_rect()
        self.cfg["window_rect"] = list(rect)
        save_cfg(self.cfg)

    def clear_saved_window_rect(self) -> None:
        self.cfg.pop("window_rect", None)
        save_cfg(self.cfg)
        self.card_window_status.set("Card only: save your normal window size before switching BPSR to 1600×900.")

    def square_resize(self) -> None:
        try:
            self.remember_window_rect_once()
            resize_bpsr(545, 2152)
            self.emit_log("Square photo helper ready at 545×2152. Move the picture window to the top, then press V.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def reset_card_steps(self) -> None:
        self.card_step = 0
        if hasattr(self, "card_button"):
            self.card_button.configure(text=f"Card Resize — Step 1/{len(CARD_SIZES)}")

    def next_card_size(self) -> None:
        try:
            self.remember_window_rect_once()
            width, height = CARD_SIZES[self.card_step]
            step_number = self.card_step + 1
            resize_bpsr(width, height)
            self.emit_log(
                f"Card photo helper: step {step_number}/{len(CARD_SIZES)} ready at {width}×{height}. "
                "Drag the picture window back to the TOP before continuing."
            )
            if self.card_step < len(CARD_SIZES) - 1:
                self.card_step += 1
                self.card_button.configure(text=f"Card Resize — Step {self.card_step + 1}/{len(CARD_SIZES)}")
            else:
                self.card_button.configure(text="Card Resize — Step 5/5 Ready ✓")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def restore_window_size(self) -> None:
        rect = self.get_saved_window_rect()
        if not rect:
            messagebox.showinfo(
                APP_NAME,
                "The app did not save a previous BPSR window size in this session.\n\n"
                "If you changed BPSR resolution inside its own Settings, put your normal resolution back there.",
            )
            return
        try:
            restore_bpsr_rect(rect)
            self.emit_log(f"BPSR window restored to its previous {rect[2]}×{rect[3]} size and position.")
            self.clear_saved_window_rect()
            self.reset_card_steps()
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def update_capture_buttons(self) -> None:
        if not hasattr(self, "square_resize_button"):
            return
        if self.mode_var.get() == "card":
            self.square_resize_button.pack_forget()
            if not self.card_button.winfo_ismapped():
                self.card_button.pack(side="left", padx=4)
        else:
            self.card_button.pack_forget()
            if not self.square_resize_button.winfo_ismapped():
                self.square_resize_button.pack(side="left", padx=4)

    def toggle_advanced(self) -> None:
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.grid()
        else:
            self.advanced_frame.grid_remove()

    def toggle_details(self) -> None:
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.details_frame.grid()
        else:
            self.details_frame.grid_remove()
