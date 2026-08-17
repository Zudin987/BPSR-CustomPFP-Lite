# BPSR Custom PFP Lite

A beginner-friendly Windows tool for the community custom portrait / namecard method in **Blue Protocol: Star Resonance**.

## Download

Open **Releases** and choose:

- `BPSR-CustomPFP-Lite-v1.0.0.exe` — standalone app.
- `BPSR-CustomPFP-Lite-Windows.zip` — EXE + README + notices.

No Python, QuickBMS, UABEA, or WindowResizer installation is required.

## Quick Start

1. Run the app and allow the Administrator prompt.
2. Click **Find Game Automatically**. If it picks the wrong install, use **Choose Folder Manually**.
3. Choose **Square** or **Card**, select your image, then crop/reposition it.
4. Open BPSR → **Guild Center → Guild Photo Booth**, stay there, tick the readiness checkbox, then click **Apply Picture to BPSR**.
5. Expand the matching capture guide below, save/upload the photo, then click **Finish — Restore Original Game File**.

> **Background not showing?** Go to **Homestead → back to Guild → reopen the Guild Photo Booth**.

> **Important:** This is an unofficial client-file modification. The app keeps backups and restores the original package, but the method is not officially supported or guaranteed ban-safe.

<details>
<summary><strong>Square photo — full capture steps</strong></summary>

1. Open **Helpful Tools** and click **Set Window for Square Photo**.
2. Enter Photo Booth → **Take Portrait** → **Settings**, then choose the background image you uploaded.
3. Use an emote that hides your character. A lying-down emote can work. Freeze the emote, then press **F** to hide the UI.
4. Drag the picture capture window to the top, press **V**, and save the photo.
5. Click **Restore Window Size**, then upload the image you captured.
6. Click **Finish — Restore Original Game File**.

</details>

<details>
<summary><strong>Card photo — full capture steps</strong></summary>

1. Open **Helpful Tools** and click **Card Photo Step 1/5**.
2. Enter Photo Booth → **Take Card Photo** → **Settings**, then choose the background image you uploaded.
3. Use an emote that hides your character. A lying-down emote can work. Freeze the emote, then press **F** to hide the UI.
4. Drag the picture capture window to the top.
5. Click the **Card Photo** button under Helpful Tools again, then drag the picture capture window back to the top.
6. Repeat Steps 4–5 until the app says **Card photo setup: step 5 of 5 ready.** Then press **V** and save the photo.
7. Click **Restore Window Size**, then upload the image you captured.
8. Click **Finish — Restore Original Game File**.

**Restore Window Size** returns BPSR to `1600×900` and resets Card Photo back to **Step 1/5**.

</details>

<details>
<summary><strong>Game folder / Steam / launcher installs</strong></summary>

The app shows the selected **Current game folder** on the main screen.

- Auto Find is only a convenience.
- **Choose Folder Manually** always overrides it.
- Use manual selection if you have multiple Steam libraries, another drive, or a launcher install.
- Select the BPSR `StreamingAssets\container` folder containing the `m*.pkg` files.

</details>

<details>
<summary><strong>What this app combines</strong></summary>

The original manual workflow usually involves separate steps/tools for package extraction/rebuilding, Unity texture editing, image preparation, BPSR window resizing, and restoring the original game files.

This app combines those jobs into one guided flow:

- game-folder detection with manual fallback,
- automatic search for `personalzone_player_bg_1` through `_20`,
- crop / zoom / reposition for Square and Card images,
- Unity asset reading and texture replacement,
- package rebuild + validation,
- automatic clean and timestamped backups,
- Square / Card window resize helpers,
- one-click restore.

The manual community method commonly uses **QuickBMS**, **UABEA**, and **WindowResizer**. This project automates the equivalent workflow internally rather than launching or bundling those programs.

Internally it uses **UnityPy**, **Pillow**, Windows APIs, and PyInstaller for the standalone release build. See `THIRD_PARTY_NOTICES.md` for dependency notes.

</details>

<details>
<summary><strong>How automatic detection works</strong></summary>

Normal users do not need to know `mXX.pkg`, `fileNNN`, Unity bundle names, or texture names.

The app searches for the first usable slot from `personalzone_player_bg_1` through `personalzone_player_bg_20` and stops as soon as one works.

It remembers the last working package, bundle, and slot. If a game update changes them, it searches again automatically.

If Discord gives you something like `file593`, you can optionally paste it into **Advanced Options → Speed hint**. If the hint is outdated, normal search still takes over.

</details>

<details>
<summary><strong>Backup and restore</strong></summary>

Before changing the live package, the app keeps:

- a persistent clean original,
- a timestamped backup,
- a separately rebuilt package that must pass validation before installation.

After the in-game photo is saved, click **Finish — Restore Original Game File**.

Backups and app data are stored under:

`%LOCALAPPDATA%\BPSR-CustomPFP-Lite`

</details>

<details>
<summary><strong>Troubleshooting</strong></summary>

**Auto Find chose the wrong game**  
Use **Choose Folder Manually**.

**Apply is disabled**  
Make sure the game folder is valid, the image has been cropped, and the Guild Photo Booth readiness box is ticked.

**Window resize does not work**  
Keep BPSR open in Windowed mode and allow the Administrator prompt.

**Custom background is missing**  
Go to **Homestead → Guild → reopen the Guild Photo Booth**.

**Game updated**  
The app normally searches again automatically. You can also use **Advanced Options → Search Again**.

**Need to undo the change**  
Use **Finish — Restore Original Game File** with the correct game folder selected.

</details>

<details>
<summary><strong>Advanced Options</strong></summary>

Most users can ignore this section. It includes:

- editable game-folder path,
- manual package priority,
- optional `fileNNN` speed hint,
- detected package / bundle / picture slot,
- **Search Again**,
- detailed activity log.

</details>

<details>
<summary><strong>Source / release notes</strong></summary>

The repository keeps source and build configuration only. Generated EXE/ZIP files are published through GitHub Releases instead of being committed into the source tree.

The Windows build runs a frozen-dependency self-test before publishing.

See `CHANGELOG.md` for version history.

</details>

## Reminder

This project is unofficial and is not affiliated with the BPSR developers or publishers. Avoid offensive / NSFW custom images.
