# BPSR Custom PFP Lite

A beginner-friendly Windows utility that simplifies the community custom portrait / card-photo method for **Blue Protocol: Star Resonance**.

## v0.3.0 — simpler by default

The normal workflow is now only:

1. **Find Your Game** — the app tries automatically, but you can always choose another install folder manually.
2. **Pick Your Picture** — choose Square or Card, then drag/zoom the crop like a social-media profile picture uploader.
3. **Use This Picture** — the app finds a usable BPSR picture slot, creates a backup, verifies the rebuilt game file, and applies the picture.

You do **not** need to know `mXX.pkg`, `fileNNN`, Unity bundles, or texture names for normal use.

## Picture-slot detection

The app accepts the first valid Texture2D it finds from:

`personalzone_player_bg_1` through `personalzone_player_bg_20`

It stops searching as soon as one works.

For faster future runs it remembers the last working package, bundle number, and slot. If that location becomes stale after a game update, it automatically searches again. Recently modified packages are searched first.

If Discord gives you a `fileNNN` such as `file593`, you can optionally paste it under **Advanced Options** as a speed hint. It is not required.

## Game-folder fallback

**Find Game Automatically** is only a convenience. The selected game folder stays under your control:

- **Choose Folder Manually** is always available.
- Manual selection overrides the automatically found install.
- This is useful when you have multiple Steam libraries or multiple game installs.
- Advanced Options also keeps the folder path editable.

Choose the BPSR folder that contains the `m*.pkg` files, normally the game's `StreamingAssets\container` folder.

## Built-in crop / reposition

- **Square** outputs `1024×1024`.
- **Card** outputs `468×774`.
- Drag to reposition.
- Mouse wheel or buttons to zoom.
- **Fit** resets the image.
- The crop cannot be zoomed out far enough to leave blank space inside the final frame.

Cropped images are stored under `%LOCALAPPDATA%\BPSR-CustomPFP-Lite\crops`.

## Helpful Tools

The main screen hides window-resize helpers until you need them:

- Set Window for Square Photo
- Next Card Size
- Restore Window Size

BPSR must be open in Windowed mode for these helpers.

## Advanced Options

Advanced controls are hidden by default and include:

- manual game-folder path
- manual package priority
- optional Discord `fileNNN` speed hint
- detected package / bundle / picture slot
- force Search Again
- detailed activity log

## Safety / restore

Before replacing a game package, the app:

1. saves a clean original copy,
2. rebuilds the edited package separately,
3. checks that the package structure still parses and the target picture slot still exists,
4. only then replaces the live file.

Use **Restore Original** to put the clean backup back.

Backups and app data are stored under `%LOCALAPPDATA%\BPSR-CustomPFP-Lite`.

## Install

Download `BPSR-CustomPFP-Lite-Windows.zip` from **Releases**, extract it, and run `BPSR-CustomPFP-Lite.exe`.

No local Python installation is required.

## Important

This is an **unofficial client-file modification**. Backups reduce the chance of a frustrating recovery problem, but they do not make client modification officially supported or risk-free. Avoid offensive / NSFW custom images.
