from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from settings import CARD_SIZES

class UiBuildMixin:
    def register_busy(self, widget):
        self.busy_widgets.append(widget)
        return widget

    def build_ui(self) -> None:
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True)

        canvas = tk.Canvas(shell, highlightthickness=0, borderwidth=0, background=self.cget("background"))
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        root = ttk.Frame(canvas, padding=(16, 14, 16, 18))
        window_id = canvas.create_window((0, 0), window=root, anchor="nw")
        root.columnconfigure(0, weight=1)

        root.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))

        def mousewheel(event):
            try:
                if event.widget.winfo_toplevel() == self and event.delta:
                    canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            except Exception:
                pass

        self.bind_all("<MouseWheel>", mousewheel, add="+")

        ttk.Label(root, text="Change Your BPSR Profile Picture", font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            root,
            text="Made for beginners: do one numbered box at a time. You do not need to know what Unity, "
            "QuickBMS, packages, or file593 mean.",
            wraplength=800,
        ).grid(row=1, column=0, sticky="w", pady=(3, 10))

        status = ttk.LabelFrame(root, text="Where am I?")
        status.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.step_status = ttk.Label(status, text="1 Find game  →  2 Pick picture  →  3 Get BPSR ready  →  4 Apply  →  5 Take photo  →  6 Restore")
        self.step_status.pack(anchor="w", padx=12, pady=10)

        game = ttk.LabelFrame(root, text="Step 1 — Find your BPSR game")
        game.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        game.columnconfigure(0, weight=1)
        ttk.Label(game, textvariable=self.game_status, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 3)
        )
        ttk.Label(
            game,
            text="The app tries Steam and common Haoplay/non-Steam locations automatically. "
            "If it cannot find your game, use the second button.",
            wraplength=800,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
        row = ttk.Frame(game)
        row.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 8))
        self.auto_button = self.register_busy(ttk.Button(row, text="Find BPSR Automatically", command=self.auto_find_game))
        self.auto_button.pack(side="left", padx=4)
        self.folder_button = self.register_busy(ttk.Button(row, text="I Will Choose the BPSR Folder", command=self.choose_game_folder))
        self.folder_button.pack(side="left", padx=4)
        ttk.Label(game, text="Found folder:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", padx=12)
        ttk.Label(game, textvariable=self.container_var, wraplength=800).grid(
            row=4, column=0, sticky="w", padx=12, pady=(0, 10)
        )

        picture = ttk.LabelFrame(root, text="Step 2 — Pick the picture you want")
        picture.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        picture.columnconfigure(1, weight=1)
        self.preview = ttk.Label(picture, text="No preview", anchor="center", width=20)
        self.preview.grid(row=0, column=0, rowspan=6, padx=12, pady=12, sticky="nsew")
        ttk.Label(picture, text="What are you changing?", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w", pady=(12, 4)
        )
        modes = ttk.Frame(picture)
        modes.grid(row=1, column=1, sticky="w")
        self.square_radio = self.register_busy(
            ttk.Radiobutton(modes, text="Square profile picture", variable=self.mode_var, value="portrait", command=self.mode_changed)
        )
        self.square_radio.pack(side="left")
        self.card_radio = self.register_busy(
            ttk.Radiobutton(modes, text="Tall card picture", variable=self.mode_var, value="card", command=self.mode_changed)
        )
        self.card_radio.pack(side="left", padx=(14, 0))
        ttk.Label(
            picture,
            text="Choose your normal image. The app will open a simple crop screen next.",
            wraplength=580,
        ).grid(row=2, column=1, sticky="w", pady=(5, 8))
        prow = ttk.Frame(picture)
        prow.grid(row=3, column=1, sticky="w")
        self.choose_picture_button = self.register_busy(ttk.Button(prow, text="Choose My Picture", command=self.choose_picture))
        self.choose_picture_button.pack(side="left")
        self.crop_button = self.register_busy(ttk.Button(prow, text="Adjust the Crop Again", command=self.adjust_crop))
        self.crop_button.pack(side="left", padx=(6, 0))
        ttk.Label(picture, textvariable=self.picture_status, font=("Segoe UI", 9, "bold")).grid(
            row=4, column=1, sticky="w", pady=(6, 12)
        )

        ready = ttk.LabelFrame(root, text="Step 3 — Get BPSR ready")
        ready.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(
            ready,
            text="Do these inside BPSR first. Nothing will be changed until both boxes are ticked.",
            font=("Segoe UI", 10, "bold"),
            wraplength=800,
        ).pack(anchor="w", padx=12, pady=(10, 6))
        ttk.Label(
            ready,
            text="1. Open BPSR.\n"
            "2. Go to Guild Center → Guild Photo Booth and stay there.\n"
            "3. Change BPSR to Windowed mode (not Fullscreen / Borderless).\n"
            "4. If you are making a Card: inside BPSR Settings, use 1600×900 before the card-resize helper.",
            justify="left",
            wraplength=800,
        ).pack(anchor="w", padx=12, pady=(0, 8))
        self.card_prepare_row = ttk.Frame(ready)
        self.card_prepare_row.pack(fill="x", padx=8, pady=(0, 8))
        self.card_prepare_button = self.register_busy(
            ttk.Button(
                self.card_prepare_row,
                text="Card only — Remember My Normal BPSR Window",
                command=self.remember_normal_window_clicked,
            )
        )
        self.card_prepare_button.pack(side="left", padx=4)
        ttk.Label(self.card_prepare_row, textvariable=self.card_window_status, wraplength=470).pack(
            side="left", padx=(8, 4)
        )

        self.booth_check = self.register_busy(
            ttk.Checkbutton(ready, text="I am inside the Guild Photo Booth now", variable=self.booth_ready_var, command=self.prep_changed)
        )
        self.booth_check.pack(anchor="w", padx=12)
        self.windowed_check = self.register_busy(
            ttk.Checkbutton(ready, text="BPSR is in Windowed mode", variable=self.windowed_ready_var, command=self.prep_changed)
        )
        self.windowed_check.pack(anchor="w", padx=12, pady=(0, 10))

        apply_box = ttk.LabelFrame(root, text="Step 4 — Apply your picture temporarily")
        apply_box.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        apply_box.columnconfigure(0, weight=1)
        ttk.Label(
            apply_box,
            text="The app first makes a clean backup, builds the change away from the live game file, checks it, "
            "then installs it. Do not update/verify BPSR while this temporary picture is applied.",
            wraplength=800,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 8))
        self.apply_button = ttk.Button(apply_box, text="Apply Picture to BPSR", command=self.apply_clicked)
        self.apply_button.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        ttk.Progressbar(apply_box, variable=self.progress_var, maximum=100).grid(
            row=2, column=0, sticky="ew", padx=12, pady=(0, 6)
        )
        ttk.Label(apply_box, textvariable=self.main_status, font=("Segoe UI", 10, "bold"), wraplength=800).grid(
            row=3, column=0, sticky="w", padx=12, pady=(0, 10)
        )

        capture = ttk.LabelFrame(root, text="Step 5 — Take and save the photo inside BPSR")
        capture.grid(row=7, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(capture, textvariable=self.capture_help_var, justify="left", wraplength=800).pack(
            anchor="w", padx=12, pady=(10, 8)
        )
        self.capture_tools = ttk.Frame(capture)
        self.capture_tools.pack(fill="x", padx=8, pady=(0, 8))
        self.square_resize_button = self.register_busy(
            ttk.Button(self.capture_tools, text="Resize BPSR for Square Photo", command=self.square_resize)
        )
        self.card_button = self.register_busy(
            ttk.Button(self.capture_tools, text=f"Card Resize — Step 1/{len(CARD_SIZES)}", command=self.next_card_size)
        )
        self.restore_window_button = self.register_busy(
            ttk.Button(self.capture_tools, text="Restore My Previous BPSR Window", command=self.restore_window_size)
        )
        self.square_resize_button.pack(side="left", padx=4)
        self.card_button.pack(side="left", padx=4)
        self.restore_window_button.pack(side="left", padx=4)
        ttk.Label(
            capture,
            text="If your custom background is missing: leave the booth → go Homestead → go back to Guild → reopen the Photo Booth.",
            wraplength=800,
        ).pack(anchor="w", padx=12, pady=(0, 10))

        finish = ttk.LabelFrame(root, text="Step 6 — Put the original BPSR file back")
        finish.grid(row=8, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(
            finish,
            text="Only do this after the portrait/card is saved in-game. This removes the temporary game-file change.",
            wraplength=800,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 8))
        self.finish_restore_button = self.register_busy(
            ttk.Button(finish, text="I'm Done — Restore Original BPSR File", command=self.restore_clicked)
        )
        self.finish_restore_button.pack(fill="x", padx=12, pady=(0, 10))

        toggles = ttk.Frame(root)
        toggles.grid(row=9, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(toggles, text="Advanced Options ▸", command=self.toggle_advanced).pack(side="left")
        ttk.Button(toggles, text="Technical Details / Log ▸", command=self.toggle_details).pack(side="left", padx=(8, 0))

        self.advanced_frame = ttk.LabelFrame(root, text="Advanced Options — most people should leave this closed")
        self.advanced_frame.grid(row=10, column=0, sticky="ew", pady=(0, 8))
        self.advanced_frame.columnconfigure(1, weight=1)
        ttk.Label(
            self.advanced_frame,
            text="Use this only if normal Auto Find / Apply cannot locate the picture background.",
            wraplength=800,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 8))
        ttk.Label(self.advanced_frame, text="BPSR container folder").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        self.advanced_folder_entry = self.register_busy(ttk.Entry(self.advanced_frame, textvariable=self.container_var))
        self.advanced_folder_entry.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        self.adv_browse = self.register_busy(ttk.Button(self.advanced_frame, text="Browse", command=self.choose_game_folder))
        self.adv_browse.grid(row=1, column=2, padx=8, pady=4)
        ttk.Label(self.advanced_frame, text="Optional known game file").grid(row=2, column=0, sticky="w", padx=12, pady=4)
        self.package_combo = self.register_busy(
            ttk.Combobox(self.advanced_frame, textvariable=self.package_var, state="readonly")
        )
        self.package_combo.grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        self.adv_refresh = self.register_busy(ttk.Button(self.advanced_frame, text="Refresh List", command=self.refresh_packages))
        self.adv_refresh.grid(row=2, column=2, padx=8, pady=4)
        ttk.Label(self.advanced_frame, text="Optional fileNNN speed hint").grid(row=3, column=0, sticky="w", padx=12, pady=4)
        self.hint_entry = self.register_busy(ttk.Entry(self.advanced_frame, textvariable=self.hint_var))
        self.hint_entry.grid(row=3, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(self.advanced_frame, text="Example: 593 or file593. Leave blank unless a current guide gives you one.").grid(
            row=4, column=1, columnspan=2, sticky="w", padx=4, pady=(0, 6)
        )
        ttk.Label(self.advanced_frame, text="Detected picture location").grid(row=5, column=0, sticky="w", padx=12, pady=4)
        ttk.Label(self.advanced_frame, textvariable=self.target_status).grid(row=5, column=1, columnspan=2, sticky="w", padx=4, pady=4)
        srow = ttk.Frame(self.advanced_frame)
        srow.grid(row=6, column=1, columnspan=2, sticky="w", padx=4, pady=(4, 10))
        self.search_button = self.register_busy(ttk.Button(srow, text="Search Again", command=self.search_again))
        self.search_button.pack(side="left")
        self.save_advanced_button = self.register_busy(ttk.Button(srow, text="Save Advanced Choice", command=self.save_advanced_selection))
        self.save_advanced_button.pack(side="left", padx=(6, 0))
        self.advanced_frame.grid_remove()

        self.details_frame = ttk.LabelFrame(root, text="Technical Details / Log")
        self.details_frame.grid(row=11, column=0, sticky="nsew")
        self.log_text = tk.Text(self.details_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.details_frame.grid_remove()

        self.session_lock_widgets = [
            self.auto_button,
            self.folder_button,
            self.square_radio,
            self.card_radio,
            self.choose_picture_button,
            self.crop_button,
            self.booth_check,
            self.windowed_check,
            self.adv_browse,
            self.adv_refresh,
            self.advanced_folder_entry,
            self.package_combo,
            self.hint_entry,
            self.search_button,
            self.save_advanced_button,
            self.card_prepare_button,
        ]

        ttk.Label(
            root,
            text="Unofficial client-file modification. Backups reduce risk, but this method is not officially supported "
            "and cannot be guaranteed ban-safe.",
            wraplength=800,
        ).grid(row=12, column=0, sticky="w", pady=(8, 0))

    def set_busy(self, busy: bool) -> None:
        if busy:
            for widget in self.busy_widgets:
                try:
                    widget.configure(state="disabled")
                except Exception:
                    pass
            self.apply_button.state(["disabled"])
            self.finish_restore_button.state(["disabled"])
        else:
            for widget in self.busy_widgets:
                try:
                    if hasattr(self, "package_combo") and widget is self.package_combo:
                        widget.configure(state="readonly")
                    else:
                        widget.configure(state="normal")
                except Exception:
                    pass
            self.apply_session_lock()
            self.update_ready_state()

    def apply_session_lock(self) -> None:
        """When a temporary custom file is active, lock Steps 1-4 so beginners cannot derail the session."""
        if not hasattr(self, "session_lock_widgets"):
            return
        for widget in self.session_lock_widgets:
            try:
                if self.session_active:
                    widget.configure(state="disabled")
                elif widget is self.package_combo:
                    widget.configure(state="readonly")
                else:
                    widget.configure(state="normal")
            except Exception:
                pass

    def emit_log(self, text: str) -> None:
        self.events.put(("log", text))

    def emit_progress(self, current: float, total: float) -> None:
        self.events.put(("progress", 100 * current / total if total else 0))
