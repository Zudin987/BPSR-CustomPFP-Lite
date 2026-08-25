from __future__ import annotations

import queue
import threading
from typing import Optional

import tkinter as tk

from settings import APP_NAME, VERSION, bundled_path, cleanup_temp_files, ensure_dirs, load_cfg
from ui_actions import UiActionsMixin
from ui_build import UiBuildMixin
from ui_state import UiStateMixin

class App(UiBuildMixin, UiStateMixin, UiActionsMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        cleanup_temp_files()
        self.cfg = load_cfg()
        self.events = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.card_step = 0
        self.preview_photo = None
        self.busy_widgets: list[tk.Widget] = []

        self.container_var = tk.StringVar(value=self.cfg.get("container", ""))
        self.package_var = tk.StringVar(value=self.cfg.get("package", ""))
        self.hint_var = tk.StringVar(value=self.cfg.get("hint", ""))
        self.source_image_var = tk.StringVar(value=self.cfg.get("source_image", ""))
        self.image_var = tk.StringVar(value=self.cfg.get("image", ""))
        self.mode_var = tk.StringVar(value=self.cfg.get("mode", "portrait"))
        self.booth_ready_var = tk.BooleanVar(value=False)
        self.windowed_ready_var = tk.BooleanVar(value=False)

        self.game_status = tk.StringVar(value="Checking for BPSR...")
        self.picture_status = tk.StringVar(value="No picture selected yet")
        self.main_status = tk.StringVar(value="Start with Step 1.")
        self.target_status = tk.StringVar(value="Not searched yet")
        self.capture_help_var = tk.StringVar(
            value="This section will unlock after Apply succeeds. The app will then tell you exactly what to click."
        )
        self.card_window_status = tk.StringVar(value="Card only: save your normal window size before switching BPSR to 1600×900.")
        self.progress_var = tk.DoubleVar(value=0)
        self.advanced_visible = False
        self.details_visible = False
        self.session_active = False

        self.title(f"{APP_NAME} v{VERSION}")
        self._window_icon = None
        try:
            self._window_icon = tk.PhotoImage(file=str(bundled_path("assets/app_icon.png")))
            self.iconphoto(True, self._window_icon)
        except Exception:
            pass

        self.geometry("860x980")
        self.minsize(780, 720)
        self.build_ui()
        self.after(100, self.drain_events)
        self.after(250, self.initial_setup)
