from __future__ import annotations

import sys
from pathlib import Path

from gui import App
from settings import APP_NAME, VERSION, bundled_path, ensure_admin_or_relaunch, ensure_dirs


def frozen_self_test() -> int:
    """Verify packaged resources before GitHub publishes a Windows release."""
    try:
        import UnityPy  # noqa: F401
        import fmod_toolkit
        import archspec.cpu

        dll = Path(fmod_toolkit.__file__).resolve().parent / "libfmod" / "Windows" / "x64" / "fmod.dll"
        if not dll.is_file():
            return 2
        if len(archspec.cpu.TARGETS) == 0:
            return 4
        if not bundled_path("assets/app_icon.png").is_file():
            return 5
        return 0
    except Exception:
        return 3


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(frozen_self_test())
    if not ensure_admin_or_relaunch():
        raise SystemExit(0)
    ensure_dirs()
    App().mainloop()
