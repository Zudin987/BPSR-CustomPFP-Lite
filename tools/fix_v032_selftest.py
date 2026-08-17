from pathlib import Path

p = Path('src/app.py')
s = p.read_text(encoding='utf-8')
old = '''        import UnityPy  # noqa: F401
        import fmod_toolkit
        import archspec

        dll = Path(fmod_toolkit.__file__).resolve().parent / "libfmod" / "Windows" / "x64" / "fmod.dll"
        if not dll.is_file():
            return 2

        cpu_db = Path(archspec.__file__).resolve().parent / "cpu" / "microarchitectures.json"
        if not cpu_db.is_file():
            return 4
        # Actually read the database so a broken one-file bundle fails in CI, not on the user's PC.
        json.loads(cpu_db.read_text(encoding="utf-8"))

        if not bundled_path("assets/app_icon.png").is_file():
'''
new = '''        import UnityPy  # noqa: F401
        import fmod_toolkit
        import archspec.cpu

        dll = Path(fmod_toolkit.__file__).resolve().parent / "libfmod" / "Windows" / "x64" / "fmod.dll"
        if not dll.is_file():
            return 2

        # Exercise Archspec's real lazy JSON loader. This catches the exact missing
        # microarchitectures.json class of frozen-build failure without hard-coding
        # Archspec's internal data directory layout.
        if len(archspec.cpu.TARGETS) == 0:
            return 4

        if not bundled_path("assets/app_icon.png").is_file():
'''
if old not in s:
    raise SystemExit('self-test block not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('fixed v0.3.2 Archspec self-test')
