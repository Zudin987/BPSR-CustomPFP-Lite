# v0.3.0 — Beginner-first redesign

- New 3-step main flow: Find Game → Pick Picture → Use This Picture.
- Auto-detect now accepts the first valid `personalzone_player_bg_1` through `_20` and stops immediately.
- “Use This Picture” performs detection automatically; no separate technical setup is required.
- Last successful package, bundle and slot are cached for faster repeat use.
- Optional Discord `fileNNN` hint checks that bundle across packages first, then falls back automatically if stale.
- Automatic game-folder detection remains optional; manual folder selection is always available and overrides auto-find.
- Social-style Square/Card cropper with drag, zoom, Fit and fixed final output sizes.
- Changing Square ↔ Card requires a matching crop before Apply can be used.
- Helpful window tools and technical package controls moved behind collapsed sections.
- Backup, rebuild verification and Restore Original remain available.
