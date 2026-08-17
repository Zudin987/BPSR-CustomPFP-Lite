from pathlib import Path

app_path = Path('src/app.py')
s = app_path.read_text(encoding='utf-8')

s = s.replace('VERSION = "0.3.4"', 'VERSION = "0.3.5"', 1)

old_game = '''        buttons = ttk.Frame(game)\n        buttons.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 10))\n        ttk.Button(buttons, text="Find Game Automatically", command=self.auto_find_game).pack(side="left", padx=4)\n        ttk.Button(buttons, text="Choose Folder Manually", command=self.choose_game_folder).pack(side="left", padx=4)\n'''
new_game = '''        buttons = ttk.Frame(game)\n        buttons.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 6))\n        ttk.Button(buttons, text="Find Game Automatically", command=self.auto_find_game).pack(side="left", padx=4)\n        ttk.Button(buttons, text="Choose Folder Manually", command=self.choose_game_folder).pack(side="left", padx=4)\n        ttk.Label(game, text="Current game folder", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", padx=12, pady=(0, 2))\n        ttk.Label(game, textvariable=self.container_var, wraplength=730).grid(row=4, column=0, sticky="w", padx=12, pady=(0, 4))\n        ttk.Label(game, text="Auto Find checks common installs. If you use a launcher or another drive, choose the folder manually.", wraplength=730).grid(row=5, column=0, sticky="w", padx=12, pady=(0, 10))\n'''
if old_game not in s:
    raise SystemExit('game section anchor not found')
s = s.replace(old_game, new_game, 1)

old_warning = '''        ttk.Label(prepare, text="Do this before Apply. It avoids changing the picture file while the game is moving between other areas or screens.", font=("Segoe UI", 9, "bold"), wraplength=730).pack(anchor="w", padx=12, pady=(0, 6))\n'''
new_warning = '''        ttk.Label(prepare, text="Do this before Apply to reduce the chance of random crashes while the app temporarily changes the game files.", font=("Segoe UI", 9, "bold"), wraplength=730).pack(anchor="w", padx=12, pady=(0, 6))\n'''
if old_warning not in s:
    raise SystemExit('prepare warning anchor not found')
s = s.replace(old_warning, new_warning, 1)

start = s.index('    def show_capture_instructions(self, mode: Optional[str] = None) -> None:\n')
end = s.index('\n    def mode_changed', start)
new_capture = '''    def show_capture_instructions(self, mode: Optional[str] = None) -> None:\n        mode = mode or self.mode_var.get()\n        if mode == "card":\n            self.capture_help_var.set(\n                "Card photo:\\n"\n                "1) Open Helpful Tools below and click Card Photo Step 1/5.\\n"\n                "2) Enter the Guild Photo Booth (Take Card Photo). Open Settings and change the background to the image you uploaded. If the custom image does not appear, check the tip below.\\n"\n                "3) Select an emote that hides your character. Any lying-down emote works; freeze the emote, then press F to hide the UI.\\n"\n                "4) Drag the picture capture window to the top of the screen.\\n"\n                "5) Click the Card Photo button under Helpful Tools again, then drag the picture capture window back to the top.\\n"\n                "6) Repeat Steps 4 and 5 until the app says ‘Card photo setup: step 5 of 5 ready.’ Then press V and save the photo.\\n"\n                "7) Click Restore Window Size, then upload the image you captured.\\n"\n                "8) Click Finish — Restore Original Game File."\n            )\n        else:\n            self.capture_help_var.set(\n                "Square photo:\\n"\n                "1) Open Helpful Tools below and click Set Window for Square Photo.\\n"\n                "2) Enter the Guild Photo Booth (Take Portrait). Open Settings and change the background to the image you uploaded. If the custom image does not appear, check the tip below.\\n"\n                "3) Select an emote that hides your character. Any lying-down emote works; freeze the emote, then press F to hide the UI.\\n"\n                "4) Drag the picture capture window to the top of the screen, then press V and save the photo.\\n"\n                "5) Click Restore Window Size, then upload the image you captured.\\n"\n                "6) Click Finish — Restore Original Game File."\n            )\n'''
s = s[:start] + new_capture + s[end:]

old_restore = '''    def restore_window_size(self) -> None:\n        try:\n            resize_bpsr(1920, 1080)\n            self.reset_card_steps()\n            self.emit_log("BPSR window restored to 1920×1080. Card photo steps reset to Step 1.")\n        except Exception as exc:\n            messagebox.showerror(APP_NAME, str(exc))\n'''
new_restore = '''    def restore_window_size(self) -> None:\n        try:\n            resize_bpsr(1600, 900)\n            self.reset_card_steps()\n            self.emit_log("BPSR window restored to 1600×900. Card photo steps reset to Step 1.")\n        except Exception as exc:\n            messagebox.showerror(APP_NAME, str(exc))\n'''
if old_restore not in s:
    raise SystemExit('restore size anchor not found')
s = s.replace(old_restore, new_restore, 1)

app_path.write_text(s, encoding='utf-8')

readme = Path('README.md')
r = readme.read_text(encoding='utf-8')
insert = '''\n## v0.3.5 — clearer capture guide\n\n- Shows the currently selected BPSR game folder directly under Auto Find / manual selection, which is useful for Steam, launcher, and alternate-drive installs.\n- Rewords the pre-Apply warning to explain that staying at the Guild Photo Booth helps reduce random crashes while game files are temporarily changed.\n- Rewrites the full Square and Card capture walkthrough into the exact in-game sequence: choose the uploaded background, hide the character with a frozen lying-down emote, press F, position the capture window, save with V, upload the captured image, then restore the original game file.\n- Restore Window Size now returns BPSR to 1600×900 and resets the Card Photo sequence to Step 1/5.\n\n'''
if '## v0.3.5 — clearer capture guide' not in r:
    marker = '## v0.3.4 — scrollable guided UI\n'
    if marker in r:
        r = r.replace(marker, insert + marker, 1)
    else:
        r = insert + r
readme.write_text(r, encoding='utf-8')
