# BPSR Custom PFP Lite

A beginner-friendly Windows tool for the community custom portrait/namecard method in **Blue Protocol: Star Resonance**.

> **Important:** This is an unofficial client-file modification. The app keeps backups and restores the original package, but the method is not officially supported and is **not guaranteed ban-safe**.

## Quick start

1. Run the app, allow the Administrator prompt, then use **Find Game Automatically** or **Choose Folder Manually**.
2. Choose **Square** or **Card**, select/crop your image, open BPSR's **Guild Center → Guild Photo Booth**, tick the readiness box, then choose **Apply Picture to BPSR**.
3. Capture/save the portrait or card in-game, then click **Finish — Restore Original Game File**.

No separate Python, QuickBMS, UABEA, or WindowResizer installation is required for the release build.

## What it does

- Finds common BPSR installations with manual-folder fallback.
- Searches supported `personalzone_player_bg_1` through `_20` picture slots.
- Crops, zooms, and repositions Square/Card images.
- Rebuilds and validates the required Unity package data.
- Keeps a clean original plus timestamped backups.
- Provides Square/Card window-size helpers.
- Restores the original game package when you finish.

## Capture tips

For **Square**, use **Helpful Tools → Set Window for Square Photo**, choose the custom Photo Booth background, position the shot, press **V**, then restore the window size.

For **Card**, use **Helpful Tools → Card Photo Step 1/5** and follow the helper through all five steps before taking the photo. **Restore Window Size** returns BPSR to `1600×900` and resets the helper.

If the custom background does not appear, go **Homestead → Guild → reopen Guild Photo Booth**.

## Game folder and picture detection

Auto-detection is only a convenience; **Choose Folder Manually** always overrides it. For manual selection, choose the BPSR `StreamingAssets\container` folder containing the `m*.pkg` files.

The app remembers the last working package/bundle/slot. If a game update moves it, use **Advanced Options → Search Again**. An optional `fileNNN` hint can speed up searching but does not replace normal fallback detection.

## Backup and restore

Backups and app data are stored under:

```text
%LOCALAPPDATA%\BPSR-CustomPFP-Lite
```

Do not delete the clean backup while you still use the tool. Always use **Finish — Restore Original Game File** after the game photo has been saved/uploaded.

## Troubleshooting

- **Auto Find chose the wrong game:** use **Choose Folder Manually**.
- **Apply is disabled:** confirm the folder, crop, and Photo Booth readiness checkbox.
- **Window resize fails:** keep BPSR open in Windowed mode and allow the Administrator prompt.
- **Game updated:** use **Search Again** if automatic re-detection has not already handled it.
- **Need to undo:** select the correct game folder and use **Finish — Restore Original Game File**.

## Privacy, licensing, and disclaimer

Selected images and backups remain local. The project does not request BPSR login credentials. Generated EXE/ZIP builds belong in GitHub Actions/Releases rather than source control.

The release uses **UnityPy**, **Pillow**, Windows APIs, PyInstaller, and their runtime dependencies. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This repository currently has **no project-wide `LICENSE` file**. Third-party licenses do not automatically license this project's original source/assets.

This project is unofficial and is not affiliated with or endorsed by the BPSR developers/publishers. Game updates, integrity checks, or policy changes may break the method or change its risk.
