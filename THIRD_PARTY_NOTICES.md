# Third-party notices

BPSR Custom PFP Lite is built as a standalone Windows executable from Python packages and their required runtime dependencies.

Primary components used by this project include:

- **UnityPy** — MIT License — Unity asset reading/writing used by the picture replacement workflow.
- **Pillow** — HPND License — image loading, crop, resize, preview, and icon preparation.
- **fmod_toolkit** — MIT License for the Python package — bundled as a UnityPy runtime dependency. The package itself includes FMOD Engine runtime libraries; those FMOD binaries remain subject to FMOD's own applicable licensing terms.
- **archspec** — Apache-2.0 OR MIT — bundled runtime dependency.
- **PyInstaller** — GPL-2.0-or-later with the PyInstaller bootloader exception — used by GitHub Actions to create the standalone executable.
- **CPython** — Python Software Foundation License — runtime used by the frozen application.

The app also uses standard Windows APIs for administrator elevation and BPSR window management.

The project does not bundle the standalone QuickBMS, UABEA, or WindowResizer applications. It automates the equivalent community workflow inside this application instead.

For full license texts and copyright notices, refer to the upstream package/project metadata and the licenses distributed by those upstream projects. Third-party components retain their own licenses and notices.
