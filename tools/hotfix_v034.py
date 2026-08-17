from pathlib import Path

app_path = Path('src/app.py')
s = app_path.read_text(encoding='utf-8')

s = s.replace('VERSION = "0.3.3"', 'VERSION = "0.3.4"', 1)

old_root = '''    def build_ui(self) -> None:\n        root = ttk.Frame(self)\n        root.pack(fill="both", expand=True, padx=16, pady=14)\n        root.columnconfigure(0, weight=1)\n'''
new_root = '''    def build_ui(self) -> None:\n        shell = ttk.Frame(self)\n        shell.pack(fill="both", expand=True)\n\n        canvas = tk.Canvas(shell, highlightthickness=0, borderwidth=0, background=self.cget("background"))\n        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)\n        canvas.configure(yscrollcommand=scrollbar.set)\n        scrollbar.pack(side="right", fill="y")\n        canvas.pack(side="left", fill="both", expand=True)\n\n        root = ttk.Frame(canvas, padding=(16, 14, 16, 14))\n        window_id = canvas.create_window((0, 0), window=root, anchor="nw")\n        root.columnconfigure(0, weight=1)\n\n        def sync_scroll_region(_event=None) -> None:\n            canvas.configure(scrollregion=canvas.bbox("all"))\n\n        def fit_content_width(event) -> None:\n            canvas.itemconfigure(window_id, width=event.width)\n\n        def mousewheel(event) -> None:\n            try:\n                if event.widget.winfo_toplevel() != self:\n                    return\n            except Exception:\n                return\n            if event.delta:\n                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")\n\n        root.bind("<Configure>", sync_scroll_region)\n        canvas.bind("<Configure>", fit_content_width)\n        self.bind_all("<MouseWheel>", mousewheel, add="+")\n'''
if old_root not in s:
    raise SystemExit('scroll root anchor not found')
s = s.replace(old_root, new_root, 1)

old_capture = '''    def show_capture_instructions(self, mode: Optional[str] = None) -> None:\n        mode = mode or self.mode_var.get()\n        if mode == "card":\n            self.capture_help_var.set(\n                "Card photo: 1) Open Helpful Tools and press Card Photo Step 1/5. "\n                "In the Guild Photo Booth, open Card Photo and hide your character. "\n                "2) Keep moving the BPSR window to the top of the screen and press the Card Photo button for Steps 2/5 through 5/5. "\n                "At the final size, press V and save the photo. 3) Click Restore Window Size. "\n                "4) When the photo is safely saved, click Finish — Restore Original Game File below."\n            )\n        else:\n            self.capture_help_var.set(\n                "Square photo: 1) Open Helpful Tools and click Set Window for Square Photo. "\n                "2) In the Guild Photo Booth, hide your character with the suitable pose/emote, move the BPSR window to the top of the screen, press V, and save the photo. "\n                "3) Click Restore Window Size. 4) When the photo is safely saved, click Finish — Restore Original Game File below."\n            )\n'''
new_capture = '''    def show_capture_instructions(self, mode: Optional[str] = None) -> None:\n        mode = mode or self.mode_var.get()\n        if mode == "card":\n            self.capture_help_var.set(\n                "Card photo:\\n"\n                "1) Open Helpful Tools and press Card Photo Step 1/5.\\n"\n                "2) In the Guild Photo Booth, open Card Photo and hide your character.\\n"\n                "3) Keep the BPSR window at the top of the screen, then press Card Photo Step 2/5 through Step 5/5.\\n"\n                "4) At the final size, press V and save the photo.\\n"\n                "5) Click Restore Window Size.\\n"\n                "6) When the photo is safely saved, click Finish — Restore Original Game File below."\n            )\n        else:\n            self.capture_help_var.set(\n                "Square photo:\\n"\n                "1) Open Helpful Tools and click Set Window for Square Photo.\\n"\n                "2) In the Guild Photo Booth, hide your character with a suitable pose/emote and move the BPSR window to the top of the screen.\\n"\n                "3) Press V and save the photo.\\n"\n                "4) Click Restore Window Size.\\n"\n                "5) When the photo is safely saved, click Finish — Restore Original Game File below."\n            )\n'''
if old_capture not in s:
    raise SystemExit('capture instructions anchor not found')
s = s.replace(old_capture, new_capture, 1)

app_path.write_text(s, encoding='utf-8')

readme = Path('README.md')
r = readme.read_text(encoding='utf-8')
insert = '''\n## v0.3.4 — scrollable guided UI\n\n- The main window is vertically scrollable, including mouse-wheel scrolling, so Helpful Tools and Advanced Options remain reachable on smaller displays.\n- Step 5 capture instructions are now one numbered action per line instead of a dense paragraph.\n- All v0.3.3 backup, restore, Guild Photo Booth preparation, Homestead refresh tip, and card-step reset behavior are kept.\n\n'''
if '## v0.3.4 — scrollable guided UI' not in r:
    marker = '## v0.3.0 — simpler by default\n'
    if marker in r:
        r = r.replace(marker, insert + marker, 1)
    else:
        r = r.replace('\n## ', insert + '## ', 1)
readme.write_text(r, encoding='utf-8')
