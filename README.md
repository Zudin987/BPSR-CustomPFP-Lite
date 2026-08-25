# BPSR Custom PFP Lite

A beginner-first Windows tool that turns the community custom portrait / card method for **Blue Protocol: Star Resonance** into a guided app.

**Website:** https://zudin987.github.io/projects/custompfp/

> **Important:** This is an unofficial client-file modification. The app makes and verifies backups, but the method is not officially supported and is **not guaranteed ban-safe**.

## What changed in v1.1

v1.1 is a safety + UI/UX hardening release. The default screen is intentionally written for people with **zero IT knowledge**: one numbered box at a time, plain-language buttons, and technical details hidden unless they are needed.

The app now also preserves Unity bundle compression, keeps backups separate for different BPSR installs, refuses unsafe restores, recovers interrupted Apply operations, prefers the original guide's `bg_3` / `m79.pkg` / `file593` path when it still matches, preserves your original source image when recropping, handles phone-photo EXIF rotation, is DPI-aware, remembers the real BPSR window position/size, and adds automated safety tests.

## Baby-step quick start

1. **Find BPSR**
   - Open the app.
   - Click **Find BPSR Automatically**.
   - If it cannot find your game, click **I Will Choose the BPSR Folder** and choose the `StreamingAssets\container` folder that contains many `m*.pkg` files.

2. **Pick your picture**
   - Choose **Square profile picture** or **Tall card picture**.
   - Click **Choose My Picture**.
   - Drag to move the picture and use the mouse wheel to zoom.
   - Click **Looks Good — Use This**.

3. **Get BPSR ready**
   - Open BPSR.
   - Go to **Guild Center → Guild Photo Booth** and stay there.
   - Put BPSR in **Windowed** mode.
   - Tick both confirmation boxes in the app.
   - **Card only:** before changing BPSR to `1600×900`, click **Card only — Remember My Normal BPSR Window**. Then set BPSR to Windowed `1600×900` in BPSR Settings.

4. **Apply temporarily**
   - Click **Apply Picture to BPSR**.
   - Wait until the app says it succeeded.
   - Do **not** update/verify BPSR while the temporary picture file is active.

5. **Take and save the photo in BPSR**
   - Follow the exact Square/Card instructions that appear in Step 5.
   - The app includes the old WindowResizer sizes as one-click helpers.
   - Save the portrait/card with **V** before continuing.

6. **Restore the original BPSR file**
   - Click **I'm Done — Restore Original BPSR File**.
   - The app only restores when the live file matches a modification that this app knows it installed.

## Square capture

After Apply succeeds:

1. Click **Resize BPSR for Square Photo**.
2. In the Photo Booth choose **Take Portrait → Settings** and select your custom background.
3. Use a lying-down / hidden-character emote, freeze it, then press **F** to hide the UI.
4. Move the BPSR picture/capture window to the top.
5. Press **V** and save the portrait.
6. Click **Restore My Previous BPSR Window**.
7. Finish with Step 6 in the app.

## Card capture

Before starting the Card resize sequence, use BPSR's own Settings to put the game in **Windowed 1600×900**. The app can remember your normal window size first so it can restore it afterward.

Then:

1. Click **Card Resize — Step 1/5**.
2. In the Photo Booth choose **Take Card Photo → Settings** and select your custom background.
3. Use a lying-down / hidden-character emote, freeze it, then press **F**.
4. Move the picture/capture window to the top.
5. Click the Card Resize button again.
6. After every resize, move the picture/capture window back to the top.
7. Continue through all five sizes: `545×2152`, `545×3130`, `545×4000`, `545×5000`, `545×6191`.
8. Press **V** and save the card.
9. Click **Restore My Previous BPSR Window**.
10. Finish with Step 6 in the app.

## What the app automates

The original community guide used QuickBMS, a UnityFS script, UABEA, a manual `m79.pkg` repack, and WindowResizer. The release build does not require you to install or operate those tools separately.

Internally, the app:

- tries the last verified location first;
- tries the original guide's known `m79.pkg → file593 → personalzone_player_bg_3` route as a fast hint;
- falls back to scanning supported `personalzone_player_bg_1` through `_20` slots when game updates move the asset;
- preserves the bundle's original compression when UnityPy supports it, with compact LZ4 fallback;
- validates the rebuilt UnityFS structure before replacing the live file;
- records the intended modified SHA-256 before the live-file commit so interrupted Apply operations can be recovered safely.

## Backup and restore safety

App data is stored under:

```text
%LOCALAPPDATA%\BPSR-CustomPFP-Lite
```

Backups are separated by BPSR installation, so Steam / Haoplay / multiple-region installs with the same package filename do not share the same clean backup.

The app will **refuse** to restore an old backup over a live BPSR file that it does not recognize. If BPSR updated or another tool changed the file while a custom-picture session was active, the safe recovery path is normally:

1. Close BPSR.
2. Use the launcher / Steam **Verify Files** or repair function.
3. Reopen this app.
4. Use **Advanced Options → Search Again** if needed.

## Troubleshooting

**The app cannot find BPSR automatically**

Choose the game folder manually. You want the `StreamingAssets\container` folder containing many files such as `m1.pkg`, `m2.pkg`, `m79.pkg`.

**Apply is disabled**

Read the numbered boxes from the top. The app requires a valid game folder, a finished crop, the Guild Photo Booth confirmation, and Windowed-mode confirmation.

**The custom background is missing in the Photo Booth**

Leave the booth, go **Homestead**, return to **Guild**, then reopen the Photo Booth.

**The resize button says BPSR did not stay at the requested size**

Make sure BPSR is in **Windowed** mode, not Borderless or Fullscreen.

**I closed the app before restoring**

Open it again with the same BPSR installation selected. v1.1 detects a known active temporary modification and guides you back to Step 5/6 instead of encouraging another Apply.

**BPSR updated while the custom picture was active**

Do not force an old backup over the update. Let the app refuse the restore, close BPSR, then Verify/Repair the game files.

## Privacy, licensing, and disclaimer

Selected images, crops, hashes, and backups remain local. The app does not ask for BPSR login credentials.

The release uses **UnityPy**, **Pillow**, Windows APIs, PyInstaller, and their runtime dependencies. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This repository currently has **no project-wide `LICENSE` file**. Third-party licenses do not automatically license this project's original source/assets.

This project is unofficial and is not affiliated with or endorsed by the BPSR developers/publishers. Game updates, integrity checks, anti-cheat behavior, or policy changes may break the method or change its risk.
