# BPSR Custom PFP Lite

A beginner-friendly Windows utility that simplifies the community custom portrait / card-photo method for **Blue Protocol: Star Resonance**.

## v0.3.4 — scrollable guided UI

- The main window is vertically scrollable, including mouse-wheel scrolling, so Helpful Tools and Advanced Options remain reachable on smaller displays.
- Step 5 capture instructions are now one numbered action per line instead of a dense paragraph.
- All v0.3.3 backup, restore, Guild Photo Booth preparation, Homestead refresh tip, and card-step reset behavior are kept.

## v0.3.3 — guided from start to finish

The normal workflow is now shown directly in the app:

1. **Find Your Game** — the app tries automatically, but you can choose another install folder manually.
2. **Pick Your Picture** — choose Square or Card, then drag/zoom the crop.
3. **Get BPSR Ready** — open BPSR, go to **Guild Center → Guild Photo Booth**, stay at the booth, and confirm the checkbox before Apply is enabled. Use Windowed mode if you plan to use the resize helpers.
4. **Apply the Picture** — the app saves a clean original backup, finds the correct picture slot, rebuilds and verifies the package, and only then replaces the live game file.
5. **Capture It In-Game, Then Finish** — follow the Square/Card instructions shown in the app, save the photo in BPSR, restore the BPSR window size, then click **Finish — Restore Original Game File**.

If the custom picture does not appear immediately, go to **Homestead**, then return to **Guild** and reopen the photo booth to refresh it.

You do **not** need to know `mXX.pkg`, `fileNNN`, Unity bundles, or texture names for normal use.

## Square photo

After Apply succeeds:

1. Open **Helpful Tools** and click **Set Window for Square Photo**.
2. In the Guild Photo Booth, hide your character using the suitable pose/emote.
3. Move the BPSR window to the top of the screen, press **V**, and save the photo.
4. Click **Restore Window Size**.
5. Click **Finish — Restore Original Game File**.

## Card photo

After Apply succeeds:

1. Open **Helpful Tools** and press **Card Photo Step 1/5**.
2. In the Guild Photo Booth, open Card Photo and hide your character.
3. Move the BPSR window to the top of the screen and continue the Card Photo button through Steps 2/5, 3/5, 4/5, and 5/5.
4. At the final size, press **V** and save the photo.
5. Click **Restore Window Size**, then **Finish — Restore Original Game File**.

**Restore Window Size** also resets the Card Photo sequence back to **Step 1/5**.

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

The main screen hides the resize helpers until you need them:

- **Set Window for Square Photo**
- **Card Photo Step 1/5 → 5/5**
- **Restore Window Size**

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

1. saves a persistent clean original copy,
2. also creates a timestamped backup of the live package,
3. rebuilds the edited package separately,
4. checks that the package structure still parses and the target picture slot still exists,
5. only then replaces the live file.

After you have saved the custom photo in-game, use **Finish — Restore Original Game File** to put the clean original package back.

Backups and app data are stored under `%LOCALAPPDATA%\BPSR-CustomPFP-Lite`.

## Install

Download `BPSR-CustomPFP-Lite-Windows.zip` from **Releases**, extract it, and run `BPSR-CustomPFP-Lite-v0.3.3.exe`.

The executable uses the same custom emblem for the Windows EXE icon and the app window icon. The versioned EXE filename also avoids Windows Explorer reusing an older cached icon from previous builds.

No local Python installation is required. Windows will request administrator permission when the app starts so the window-size helpers and game-file replacement can work reliably.

## Important

This is an **unofficial client-file modification**. Backups reduce the chance of a frustrating recovery problem, but they do not make client modification officially supported or risk-free. Avoid offensive / NSFW custom images.
