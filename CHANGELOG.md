# Changelog

## 1.1.0 — Safety + beginner UI/UX hardening

### Beginner-first UI/UX

- Reworked the main flow around six plain-language numbered steps for users with zero IT knowledge.
- Added dynamic “where am I?” guidance and a stronger next-action status.
- Locks setup/advanced controls while a temporary custom-picture file is active so users do not accidentally derail the capture/restore sequence.
- Detects a known active temporary modification after reopening the app and guides the user back to capture/restore.
- Keeps technical package/bundle details inside Advanced/Log areas.
- Added clearer manual-folder guidance and clearer error recovery messages.
- Added an explicit Card-only “Remember My Normal BPSR Window” step before switching BPSR to 1600×900.

### File safety

- Backups are namespaced by BPSR install path instead of package filename alone.
- Clean backup metadata is written atomically.
- Apply records a pending modified SHA-256 before the live-file commit so a crash can be recovered without poisoning the clean backup.
- Restore now refuses to overwrite a current BPSR file unless it matches the clean file or a known modification installed by this app.
- Missing/corrupt backup metadata no longer causes the app to guess that an unknown live file is a game update.
- Keeps a small number of recovery snapshots and cleans stale temporary/crop files.
- Builds the validated replacement beside the live package and commits it with an atomic same-filesystem replace, removing an extra full-package copy.
- Adds a free-space check before rebuilding.

### Unity / target correctness

- Uses `env.file.save("original")` so UnityFS compression flags are preserved instead of silently writing an uncompressed bundle.
- Falls back to compact LZ4 only when UnityPy cannot reproduce an uncommon original flag combination.
- Prefers a cached verified slot, then the original guide's `personalzone_player_bg_3`, then validated alternate `_1.._20` slots.
- Tries the original community `m79.pkg → file593 → bg_3` location as a fast hint, with full safe fallback scanning.
- Caches verified segment offset/size plus package fingerprint for faster repeat runs.

### Picture handling

- Keeps the original selected image separately from generated crops.
- Switching Square/Card or choosing Adjust Crop always starts from the original source image instead of repeatedly cropping a previous crop.
- Applies EXIF orientation so phone photos appear the right way up.

### Window helpers

- Enables Windows DPI awareness so 545×2152 and other exact helper sizes are physical pixels at 125%/150% display scaling.
- Preserves the current BPSR monitor/position while resizing.
- Remembers and restores the user's real pre-helper BPSR window rectangle instead of forcing a hard-coded 1600×900 or 1920×1080 size.
- Verifies that BPSR actually accepted the requested helper size.

### Detection / maintainability / release

- Adds targeted Steam + common Haoplay/non-Steam auto-detection, including shallow `*_Data\StreamingAssets\container` detection for launcher/region naming differences.
- Splits settings, Unity parsing, backup transactions, package detection, game/window helpers, crop UI, UI state, and UI actions into small modules instead of one large file.
- Adds automated tests for backup isolation, restore refusal, crash recovery, active-session detection, slot preference, speed-hint parsing, and atomic config writes.
- Pins current release dependencies for reproducible builds.
- GitHub Actions now compiles/tests before packaging, publishes SHA-256 checksums, and fails if code changes reuse an already-published version tag.

## 1.0.0 — First stable release

BPSR Custom PFP Lite 1.0.0 turned the manual community custom portrait / namecard workflow into one guided Windows application.

### Main features

- Beginner-oriented, scrollable step-by-step UI.
- Automatic BPSR game-folder detection with manual folder override.
- Automatic search for supported `personalzone_player_bg_1` through `_20` texture slots.
- Optional `fileNNN` speed hint.
- Built-in Square and Card crop / zoom / reposition workflow.
- Automatic package backup, rebuild verification, installation, and restore.
- Built-in BPSR window resizing for Square and five-step Card photo capture.
- Guild Photo Booth readiness safeguard.
- Standalone Windows build; normal users do not need Python, QuickBMS, UABEA, or WindowResizer installed separately.
