from pathlib import Path

p = Path('src/app.py')
s = p.read_text(encoding='utf-8')

s = s.replace('import sys\n', 'import sys\nimport subprocess\n', 1)
s = s.replace('VERSION = "0.3.1"', 'VERSION = "0.3.2"', 1)

anchor = 'CARD_SIZES = [(545, 2152), (545, 3130), (545, 4000), (545, 5000), (545, 6191)]\n\n\n'
insert = '''CARD_SIZES = [(545, 2152), (545, 3130), (545, 4000), (545, 5000), (545, 6191)]\n\n\ndef bundled_path(relative: str) -> Path:\n    """Return a bundled resource path in both source and PyInstaller builds."""\n    frozen_root = getattr(sys, "_MEIPASS", None)\n    if frozen_root:\n        return Path(frozen_root) / relative\n    return Path(__file__).resolve().parent.parent / relative\n\n\ndef ensure_admin_or_relaunch() -> bool:\n    """Ask Windows for administrator permission once, then relaunch elevated."""\n    if os.name != "nt":\n        return True\n    try:\n        if ctypes.windll.shell32.IsUserAnAdmin():\n            return True\n    except Exception:\n        return True\n\n    if getattr(sys, "frozen", False):\n        executable = sys.executable\n        args = sys.argv[1:]\n    else:\n        executable = sys.executable\n        args = [str(Path(__file__).resolve()), *sys.argv[1:]]\n\n    params = subprocess.list2cmdline(args)\n    try:\n        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)\n    except Exception:\n        result = 0\n\n    if result <= 32:\n        try:\n            ctypes.windll.user32.MessageBoxW(\n                None,\n                "Administrator permission is needed so the app can resize the BPSR window and update the selected game file.",\n                APP_NAME,\n                0x10,\n            )\n        except Exception:\n            pass\n    return False\n\n\n'''
if anchor not in s:
    raise SystemExit('constants anchor not found')
s = s.replace(anchor, insert, 1)

old_init = '''        self.title(f"{APP_NAME} v{VERSION}")\n        self.geometry("790x850")\n        self.minsize(720, 700)\n        self.build_ui()\n'''
new_init = '''        self.title(f"{APP_NAME} v{VERSION}")\n        self._window_icon = None\n        try:\n            self._window_icon = tk.PhotoImage(file=str(bundled_path("assets/app_icon.png")))\n            self.iconphoto(True, self._window_icon)\n        except Exception:\n            pass\n        self.geometry("790x850")\n        self.minsize(720, 700)\n        self.build_ui()\n'''
if old_init not in s:
    raise SystemExit('App init anchor not found')
s = s.replace(old_init, new_init, 1)

old_test = '''def frozen_self_test() -> int:\n    """Verify native dependencies that the frozen EXE needs before a release is published."""\n    try:\n        import UnityPy  # noqa: F401\n        import fmod_toolkit\n\n        dll = Path(fmod_toolkit.__file__).resolve().parent / "libfmod" / "Windows" / "x64" / "fmod.dll"\n        return 0 if dll.is_file() else 2\n    except Exception:\n        return 3\n\n\nif __name__ == "__main__":\n    if "--self-test" in sys.argv:\n        raise SystemExit(frozen_self_test())\n    ensure_dirs()\n    App().mainloop()\n'''
new_test = '''def frozen_self_test() -> int:\n    """Verify packaged resources before GitHub publishes a Windows release."""\n    try:\n        import UnityPy  # noqa: F401\n        import fmod_toolkit\n        import archspec\n\n        dll = Path(fmod_toolkit.__file__).resolve().parent / "libfmod" / "Windows" / "x64" / "fmod.dll"\n        if not dll.is_file():\n            return 2\n\n        cpu_db = Path(archspec.__file__).resolve().parent / "cpu" / "microarchitectures.json"\n        if not cpu_db.is_file():\n            return 4\n        # Actually read the database so a broken one-file bundle fails in CI, not on the user's PC.\n        json.loads(cpu_db.read_text(encoding="utf-8"))\n\n        if not bundled_path("assets/app_icon.png").is_file():\n            return 5\n        return 0\n    except Exception:\n        return 3\n\n\nif __name__ == "__main__":\n    if "--self-test" in sys.argv:\n        raise SystemExit(frozen_self_test())\n    if not ensure_admin_or_relaunch():\n        raise SystemExit(0)\n    ensure_dirs()\n    App().mainloop()\n'''
if old_test not in s:
    raise SystemExit('self-test/main anchor not found')
s = s.replace(old_test, new_test, 1)

p.write_text(s, encoding='utf-8')
print('patched src/app.py for v0.3.2')
