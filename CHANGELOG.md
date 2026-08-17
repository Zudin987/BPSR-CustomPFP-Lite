# Changelog

## 1.0.0 — First stable release

BPSR Custom PFP Lite 1.0.0 turns the manual community custom portrait / namecard workflow into one guided Windows application.

### Main features

- Beginner-oriented, scrollable step-by-step UI.
- Automatic BPSR game-folder detection with manual folder override for launcher installs, extra Steam libraries, and secondary drives.
- Automatic search for the first usable `personalzone_player_bg_1` through `personalzone_player_bg_20` texture slot.
- Optional Discord `fileNNN` speed hint with automatic fallback when the hint is outdated.
- Built-in Square and Card crop / zoom / reposition workflow.
- Automatic package backup, rebuild verification, installation, and restore.
- Built-in BPSR window resizing for Square and five-step Card photo capture.
- Restore Window Size returns BPSR to `1600×900` and resets Card Photo to Step 1/5.
- Guild Photo Booth readiness safeguard before game-file replacement.
- Full in-app Square and Card capture instructions, including the Homestead → Guild refresh tip.
- Administrator elevation on launch for reliable game-file and window operations.
- Custom application / EXE icon.
- Standalone Windows build; normal users do not need Python or the separate manual workflow tools installed.

### Release packaging

The GitHub Release provides both:

- the standalone `.exe`, and
- a `.zip` containing the EXE, README, and third-party notices.

Generated binaries are kept out of the source tree and are published only as Release assets.

## Pre-1.0 development

Versions 0.1 through 0.3.5 were iterative development builds used to validate package detection, image replacement, frozen dependencies, backup/restore, window helpers, icon packaging, and the simplified guided UI.
