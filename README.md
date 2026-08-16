# BPSR Custom PFP Lite

A small Windows utility that simplifies the community custom portrait / card-photo method for **Blue Protocol: Star Resonance**.

## What it automates

Instead of manually extracting `mXX.pkg`, finding the current `fileNNN.unity3d`, opening UABEA, replacing `personalzone_player_bg_3`, rebuilding, and copying files back, this tool does the repetitive file work for you.

- Standalone Windows EXE — **no Python install required**
- Auto-finds Steam BPSR when possible
- Lets you choose the current `mXX.pkg` from the Discord guide
- Optional `fileNNN` hint from Discord for a fast run
- If `fileNNN` is left blank, **Auto Scan** searches the package for `personalzone_player_bg_3`
- Replaces the texture using UnityPy
- Rebuilds the outer BPSR package directly
- Creates clean + timestamped backups
- Restore Original button
- Built-in BPSR window-size helper for the guild photo booth

## Download

Open **Releases → Latest Windows build** and download:

`BPSR-CustomPFP-Lite-Windows.zip`

Extract it, then run `BPSR-CustomPFP-Lite.exe`.

You do **not** need Python, QuickBMS, UABEA, or WindowResizer installed locally for this version.

## Simple portrait workflow

1. Open BPSR and stand near the Guild photo booth.
2. Open `BPSR-CustomPFP-Lite.exe`.
3. Click **Auto Find**. If it fails, browse to BPSR's `StreamingAssets\container` folder.
4. Choose the **current `mXX.pkg`** listed by the custom-PFP Discord/community guide.
5. Optional: type the current `fileNNN` from Discord. If you leave it blank, the tool searches automatically.
6. Select a **1:1** portrait image.
7. Click **APPLY CUSTOM IMAGE**.
8. Put BPSR in Windowed mode and click **Portrait 545×2152**.
9. In the photo booth, use an emote that hides your character, drag the photo window to the top, and press `V` to capture.
10. Click **Restore 1920×1080**, then confirm/save the picture in BPSR.

## Card photo

Use an image at **468×774** or the same aspect ratio. After applying it, use **Next Card Size**. Each click advances through the sizes used by the community guide:

`545×2152 → 545×3130 → 545×4000 → 545×5000 → 545×6191`

Drag the photo window to the top after each step. At the final size, press `V`, then restore to `1920×1080` and save.

## When BPSR updates

The package and bundle numbers may change, for example:

`m79.pkg / file593` → `m84.pkg / file731`

You only need to select the new `m84.pkg`. You may enter `file731` as a fast hint, but it is optional — Auto Scan can discover the correct bundle by looking for the texture name.

If a game patch changes a package that the tool has already modified, the next run detects the new package hash and refreshes its clean baseline automatically.

## Backups

Backups are stored under:

`%LOCALAPPDATA%\BPSR-CustomPFP-Lite\backups`

Use **Restore Original** if you want to put the clean package back. If the game ever fails to load after a mod, restoring or verifying game files is the safest recovery path.

## Important notes

This is an **unofficial client-file modification**. Community use is not the same thing as an official publisher guarantee that the method is permitted forever. Avoid NSFW/offensive images and use at your own risk.

The tool does not inject into the game process and does not automate gameplay. It edits the same Unity asset used by the community custom-PFP workflow, then helps resize the normal BPSR window for the photo-booth capture.

## Build

GitHub Actions builds the Windows EXE with PyInstaller. Python and build dependencies run on GitHub's Windows runner, not on the end user's PC.

Runtime source dependencies are listed in `requirements.txt`.
