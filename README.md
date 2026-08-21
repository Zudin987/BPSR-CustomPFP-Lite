# BPSR Custom PFP Lite

A beginner-friendly Windows tool for the community custom portrait/namecard method in **Blue Protocol: Star Resonance**.

> **TL;DR:** Choose your BPSR game folder, choose/crop an image, let the app temporarily replace the supported Photo Booth background, capture your portrait/card in-game, then use **Finish — Restore Original Game File**.

> **Important:** This is an unofficial client-file modification. It keeps backups and restores the original package, but the method is not officially supported and is **not guaranteed ban-safe**.

## What this app does

- Finds a BPSR installation automatically with manual-folder fallback.
- Searches supported `personalzone_player_bg_1` through `_20` picture slots.
- Crops, zooms, and repositions Square/Card images.
- Reads/rebuilds the required Unity package data.
- Keeps a persistent clean original plus timestamped backups.
- Validates a rebuilt package before putting it into the game folder.
- Provides Square/Card window-size helpers for the capture workflow.
- Restores the original game file when you finish.

No separate Python, QuickBMS, UABEA, or WindowResizer installation is required for the release build.

## Quick Start — 1, 2, 3

1. Run the app, allow the Administrator prompt, and use **Find Game Automatically** or **Choose Folder Manually**.
2. Choose **Square** or **Card**, select/crop your image, open BPSR's **Guild Center → Guild Photo Booth**, tick the readiness box, then choose **Apply Picture to BPSR**.
3. Capture/save the in-game portrait or card, then click **Finish — Restore Original Game File**.

> **Background not showing?** Go to **Homestead → back to Guild → reopen the Guild Photo Booth**.

## Square photo capture

<details>
<summary><strong>Show steps</strong></summary>

1. Open **Helpful Tools** → **Set Window for Square Photo**.
2. In Photo Booth choose the background image you uploaded.
3. Use an emote/pose that hides your character if desired, freeze it, then press **F** to hide the UI.
4. Position the capture view, press **V**, and save the photo.
5. Use **Restore Window Size**.
6. Click **Finish — Restore Original Game File** after the game photo has been saved/uploaded.

</details>

## Card photo capture

<details>
<summary><strong>Show steps</strong></summary>

1. Open **Helpful Tools** → **Card Photo Step 1/5**.
2. In **Take Card Photo → Settings**, choose the custom background.
3. Use an emote/pose that hides your character if desired and press **F** to hide the UI.
4. Follow the Card Photo helper repeatedly until it reports **step 5 of 5 ready**.
5. Press **V** and save the card photo.
6. Use **Restore Window Size**, then **Finish — Restore Original Game File**.

**Restore Window Size** returns BPSR to `1600×900` and resets the Card helper to Step 1/5.

</details>

## Game folder selection

Auto-detection is only a convenience. **Choose Folder Manually** always overrides it.

Use manual selection when you have multiple Steam libraries, another drive, or a non-default launcher install. Select the BPSR `StreamingAssets\container` folder that contains the `m*.pkg` files.

## How automatic picture detection works

Normal users do not need to know package/bundle/file numbers.

The app searches for the first usable picture slot from:

```text
personalzone_player_bg_1
...
personalzone_player_bg_20
```

It remembers the last working package, bundle, and slot. If an update moves them, **Search Again** falls back to a fresh scan.

An optional `fileNNN` hint can be entered under **Advanced Options** to speed up a search, but an outdated hint does not replace normal fallback detection.

## Backup and restore safety

Before modifying the live package, the app keeps:

- a persistent clean original,
- a timestamped backup,
- a separately rebuilt package that must pass validation before installation.

App data/backups are kept under:

```text
%LOCALAPPDATA%\BPSR-CustomPFP-Lite
```

Do not manually delete the clean backup while you still use the tool.

## Troubleshooting

**Auto Find chose the wrong game**  
Use **Choose Folder Manually**.

**Apply is disabled**  
Confirm the game folder is valid, the image is cropped, and the Photo Booth readiness checkbox is enabled.

**Window resize does not work**  
Keep BPSR open in Windowed mode and allow the Administrator prompt.

**Custom background is missing**  
Go **Homestead → Guild → reopen Guild Photo Booth**.

**Game updated**  
Use **Advanced Options → Search Again** if automatic re-detection has not already run.

**Need to undo the change**  
Select the correct game folder and use **Finish — Restore Original Game File**.

## Privacy / repository safety

- Selected images and game-package backups are local files; they should not be committed to this repository.
- Generated EXE/ZIP builds belong in GitHub Actions/Releases, not the source tree.
- The project does not request BPSR login credentials.
- Avoid copyrighted/offensive/NSFW custom images you are not permitted to use.

## Third-party components

The release uses **UnityPy**, **Pillow**, Windows APIs, PyInstaller, and their runtime dependencies. It does not bundle the standalone QuickBMS, UABEA, or WindowResizer programs.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency licensing notes.

### Project source licensing

This repository currently does **not** contain a project-wide `LICENSE` file. The licences listed in `THIRD_PARTY_NOTICES.md` apply to their respective third-party components and do not by themselves grant a licence to this project's original source code/assets.

## Disclaimer

This project is unofficial and is not affiliated with or endorsed by the BPSR developers/publishers. Game updates, integrity checks, or account-policy changes can make this community method stop working or carry risk.
