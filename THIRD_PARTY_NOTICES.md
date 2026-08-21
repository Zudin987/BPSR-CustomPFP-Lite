# Third-party notices

BPSR Custom PFP Lite is built as a standalone Windows executable from Python packages and their required runtime dependencies.

Primary components used by this project include:

- **UnityPy** — MIT License — Unity asset reading/writing used by the picture replacement workflow.
- **Pillow** — HPND License — image loading, crop, resize, preview, and icon preparation.
- **fmod_toolkit** — MIT License for the Python package — pulled as a UnityPy runtime dependency. The package may include FMOD Engine runtime libraries; those FMOD binaries remain subject to FMOD's own applicable licensing/distribution terms and are not relicensed by this project.
- **archspec** — Apache-2.0 OR MIT — bundled runtime dependency where pulled by the packaged dependency set.
- **PyInstaller** — GPL-2.0-or-later with the PyInstaller bootloader exception — used by GitHub Actions to create the standalone executable.
- **CPython** — Python Software Foundation License — runtime used by the frozen application.

The app also uses standard Windows APIs for administrator elevation and BPSR window management.

The project does not bundle the standalone QuickBMS, UABEA, or WindowResizer applications. It automates the equivalent community workflow inside this application instead.

Third-party components retain their own copyright, licence, trademark, and redistribution terms. Refer to the upstream package/project distributions for the complete corresponding licence texts and notices.

## Project source licence status

This file documents **third-party** licensing only. The repository currently does not contain a project-wide `LICENSE` file for the original BPSR Custom PFP Lite source/assets, so no separate project-wide source licence should be inferred from the dependency licences listed above.
