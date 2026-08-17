from pathlib import Path

p = Path('src/app.py')
s = p.read_text(encoding='utf-8')

s = s.replace('import threading\nimport time\n', 'import threading\nimport time\nimport sys\n', 1)
s = s.replace('VERSION = "0.3.0"', 'VERSION = "0.3.1"', 1)

old_button = '        ttk.Button(tool_buttons, text="Next Card Size", command=self.next_card_size).pack(side="left", padx=4)\n'
new_button = '''        self.card_button = ttk.Button(\n            tool_buttons,\n            text=f"Card Photo Step 1/{len(CARD_SIZES)}",\n            command=self.next_card_size,\n        )\n        self.card_button.pack(side="left", padx=4)\n'''
if old_button not in s:
    raise SystemExit('card button pattern not found')
s = s.replace(old_button, new_button, 1)

old_method = '''    def next_card_size(self) -> None:\n        width, height = CARD_SIZES[self.card_step]\n        self.resize_game(width, height)\n        self.card_step = (self.card_step + 1) % len(CARD_SIZES)\n\n\nif __name__ == "__main__":\n    ensure_dirs()\n    App().mainloop()\n'''
new_method = '''    def next_card_size(self) -> None:\n        step_number = self.card_step + 1\n        width, height = CARD_SIZES[self.card_step]\n        try:\n            resize_bpsr(width, height)\n            self.emit_log(f"Card photo setup: step {step_number} of {len(CARD_SIZES)} ready.")\n            self.card_step = (self.card_step + 1) % len(CARD_SIZES)\n            next_step = self.card_step + 1\n            self.card_button.configure(text=f"Card Photo Step {next_step}/{len(CARD_SIZES)}")\n        except Exception as exc:\n            messagebox.showerror(APP_NAME, str(exc))\n\n\ndef frozen_self_test() -> int:\n    """Verify native dependencies that the frozen EXE needs before a release is published."""\n    try:\n        import UnityPy  # noqa: F401\n        import fmod_toolkit\n\n        dll = Path(fmod_toolkit.__file__).resolve().parent / "libfmod" / "Windows" / "x64" / "fmod.dll"\n        return 0 if dll.is_file() else 2\n    except Exception:\n        return 3\n\n\nif __name__ == "__main__":\n    if "--self-test" in sys.argv:\n        raise SystemExit(frozen_self_test())\n    ensure_dirs()\n    App().mainloop()\n'''
if old_method not in s:
    raise SystemExit('next_card_size pattern not found')
s = s.replace(old_method, new_method, 1)

p.write_text(s, encoding='utf-8')
print('Patched src/app.py for v0.3.1')
