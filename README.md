# BPSR Custom PFP Lite

A beginner-friendly Windows utility that simplifies the community custom portrait and namecard workflow for **Blue Protocol: Star Resonance**.

Version **1.0.0** is the first stable release.

## Download

Open the repository's **Releases** section and choose either:

- `BPSR-CustomPFP-Lite-v1.0.0.exe` — standalone app, ready to run.
- `BPSR-CustomPFP-Lite-Windows.zip` — the same EXE packaged together with this README and the third-party notices.

You do **not** need Python, QuickBMS, UABEA, or WindowResizer installed on your PC.

Windows asks for Administrator permission when the app starts. This is used for reliable game-file replacement and BPSR window resizing.

## What this app combines

The original community workflow normally involves several separate jobs: locating the changing BPSR package, extracting or rebuilding Unity data, replacing the background texture, preparing the image at the correct ratio, resizing the BPSR window for the photo-booth trick, and restoring the original package afterward.

BPSR Custom PFP Lite combines those jobs into one guided app:

- automatic or manual BPSR install-folder selection,
- automatic search for a usable `personalzone_player_bg_1` through `personalzone_player_bg_20` slot,
- optional `fileNNN` speed hint for users following Discord updates,
- image crop, zoom, and repositioning,
- Unity asset reading and texture replacement,
- package rebuilding and safety checks,
- automatic clean backup plus timestamped backup,
- Square and Card window-resize helpers,
- one-click restore of the original game file.

The manual method is commonly performed with tools such as **QuickBMS**, **UABEA**, and **WindowResizer**. This project automates the equivalent workflow internally; it does not need to launch or bundle those standalone programs.

Under the hood, the app uses **UnityPy** for Unity asset handling, **Pillow** for image processing, and Windows APIs for window management. The distributable EXE is built by GitHub Actions with PyInstaller. See `THIRD_PARTY_NOTICES.md` for dependency notes.

## Before you start

This is an **unofficial client-file modification**. The app keeps backups and restores the original package after you finish, but that does not make the method officially supported or risk-free.

Before pressing **Apply Picture to BPSR**:

1. Open BPSR and keep it running.
2. Go to **Guild Center → Guild Photo Booth** and stay there.
3. If you will use the resize helpers, switch BPSR to **Windowed** mode first.
4. Tick **BPSR is open and I am at the Guild Photo Booth** in the app.

Do this before Apply to reduce the chance of random crashes while the app temporarily changes the game files.

## Full beginner workflow

### 1. Find Your Game

The app tries to find BPSR automatically and shows the selected **Current game folder** directly on the main screen.

If Auto Find chooses the wrong installation, or you use a launcher / another drive, click **Choose Folder Manually** and select the BPSR `StreamingAssets\container` folder that contains the `m*.pkg` files.

Manual selection always overrides Auto Find.

### 2. Pick Your Picture

Choose the picture shape:

- **Square** — profile portrait.
- **Card** — tall namecard image.

Click **Choose Picture**. The crop window opens automatically.

You can drag the image to reposition it, use the mouse wheel or buttons to zoom, and press **Fit** to reset the crop.

The app outputs:

- Square: `1024×1024`
- Card: `468×774`

If you change between Square and Card afterward, adjust the crop again before applying.

### 3. Get BPSR Ready Before Applying

Stay at the Guild Photo Booth, confirm the readiness checkbox, then continue.

### 4. Apply the Picture

Click **Apply Picture to BPSR**.

The app will automatically:

1. find a usable BPSR picture slot,
2. save a clean copy of the original game package,
3. create the edited package separately,
4. verify the rebuilt package before touching the live file,
5. create an additional timestamped backup,
6. replace the live package only after the checks succeed.

When the progress bar finishes, continue with the matching Square or Card instructions below.

## Square photo — in-game capture

1. Open **Helpful Tools** below and click **Set Window for Square Photo**.
2. Enter the Guild Photo Booth and choose **Take Portrait**. Open **Settings** and change the background to the image you uploaded. If the custom image does not appear, check the refresh tip below.
3. Select an emote that hides your character. Any lying-down emote can work. Freeze the emote, then press **F** to hide the UI.
4. Drag the picture capture window to the top of the screen, then press **V** and save the photo.
5. Click **Restore Window Size**, then upload the image you captured.
6. Click **Finish — Restore Original Game File**.

## Card photo — in-game capture

1. Open **Helpful Tools** below and click **Card Photo Step 1/5**.
2. Enter the Guild Photo Booth and choose **Take Card Photo**. Open **Settings** and change the background to the image you uploaded. If the custom image does not appear, check the refresh tip below.
3. Select an emote that hides your character. Any lying-down emote can work. Freeze the emote, then press **F** to hide the UI.
4. Drag the picture capture window to the top of the screen.
5. Click the **Card Photo** button under Helpful Tools again, then drag the picture capture window back to the top.
6. Repeat Steps 4 and 5 until the app says **Card photo setup: step 5 of 5 ready.** Then press **V** and save the photo.
7. Click **Restore Window Size**, then upload the image you captured.
8. Click **Finish — Restore Original Game File**.

**Restore Window Size** returns BPSR to `1600×900` and resets the Card Photo sequence back to **Step 1/5**.

## If the custom background does not appear

Go to **Homestead**, return to **Guild**, then reopen the Guild Photo Booth. This can refresh the background selection after the package was changed.

## How automatic picture-slot detection works

Normal users do not need to know `mXX.pkg`, `fileNNN`, Unity bundle names, or texture names.

The app searches for the first usable Texture2D named:

`personalzone_player_bg_1` through `personalzone_player_bg_20`

It stops as soon as one valid slot is found.

For faster later runs, the app remembers the last working package, bundle number, and slot. If the saved location becomes invalid after a game update, it searches again automatically. Recently modified packages are checked first.

If Discord gives you a value such as `file593`, you can optionally paste it into **Advanced Options → Speed hint**. The app tests that bundle across packages first; if the hint is outdated, it falls back to the normal search automatically.

## Helpful Tools

Helpful Tools are hidden by default so the main workflow stays simple.

They contain:

- **Set Window for Square Photo**
- **Card Photo Step 1/5 → 5/5**
- **Restore Window Size**

BPSR must be open in Windowed mode for resizing.

## Advanced Options

You normally do not need this section. It contains:

- editable game-folder path,
- manual game-package priority,
- optional `fileNNN` speed hint,
- detected package / bundle / picture slot,
- **Search Again**,
- detailed activity log.

## Backup and restore behavior

Backups and working files are kept under:

`%LOCALAPPDATA%\BPSR-CustomPFP-Lite`

Before the app replaces a live game package it keeps a persistent clean original and an additional timestamped backup.

After the in-game photo has been saved, use **Finish — Restore Original Game File**. The clean package is copied back into the game folder, while the backup remains available for recovery.

If BPSR receives an update and the package has genuinely changed, the app detects that and refreshes its clean baseline instead of blindly treating the old package as current.

## Troubleshooting

**Auto Find picked the wrong install**  
Use **Choose Folder Manually**. This is especially useful for launcher installs, extra Steam libraries, and secondary drives.

**The Apply button is disabled**  
Make sure a valid picture has been cropped, the game folder is valid, and the Guild Photo Booth readiness checkbox is ticked.

**Window resize does not work**  
Keep BPSR open, switch it to Windowed mode, and allow the Administrator prompt when starting this app.

**Custom background is missing in the booth**  
Go to Homestead, return to Guild, and reopen the Guild Photo Booth.

**Game updated and the old location no longer works**  
The app normally falls back to a new search. You can also open **Advanced Options** and use **Search Again**.

**Need to undo the game-file change**  
Use **Finish — Restore Original Game File** after capturing the photo. If you are recovering from an interrupted attempt, use the restore action while the correct game folder is selected.

## Build and source notes

The repository contains source code and build configuration only. Generated EXE and ZIP files are published as GitHub Release assets rather than committed into the source tree.

The release workflow builds a standalone Windows EXE, runs a frozen-dependency self-test, packages the optional ZIP, and publishes both release formats.

No local Python installation is required for normal users.

## Important

- This project is unofficial and is not affiliated with the BPSR developers or publishers.
- Client-file modification may carry game-account or stability risk even when backups are used.
- Do not use offensive or NSFW custom images.
- The project does not claim that this method is officially approved or guaranteed to be ban-safe.
