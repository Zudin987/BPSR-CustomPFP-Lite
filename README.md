# BPSR Custom PFP Lite

Standalone Windows tool for Blue Protocol: Star Resonance custom portrait / card workflow.

## What is new in v0.2

- **Auto Detect mXX + fileNNN**
  - Can search all `m*.pkg` files in `StreamingAssets\container`
  - Finds which package contains the `Texture2D` named `personalzone_player_bg_3`
  - Saves the detected result for faster future runs
  - If you know the Discord `fileNNN`, you can still paste it as a speed-up hint

- **Built-in crop / reposition tool**
  - Portrait mode uses **1:1** crop
  - Card mode uses **468:774** crop ratio
  - Lets you drag and zoom the image, similar to social-media profile picture cropping
  - Cropped images are saved under `%LOCALAPPDATA%\BPSR-CustomPFP-Lite\crops`

- **Still includes**
  - automatic BPSR container auto-find
  - package backup / restore
  - portrait / card photo-booth resize helper buttons
  - standalone GitHub Actions Windows build

## Basic usage

1. Download the latest Windows build from **Releases**.
2. Run `BPSR-CustomPFP-Lite.exe`.
3. Click **Auto Find** to locate the BPSR `StreamingAssets\container` folder.
4. Optional: click **Auto Detect mXX + fileNNN**.
   - If Discord posted a `fileNNN`, enter it first to make detection faster.
   - If not, leave it blank and let the tool scan.
5. Choose **Portrait** or **Card**.
6. Click **Select Image**.
7. Use the built-in crop dialog to drag / zoom / reposition the image.
8. Click **Apply Custom Image**.
9. Use the built-in photo booth helper buttons while doing the in-game capture step.

## Notes

- This is still an **unofficial client-file modification**.
- Keep backups and avoid offensive / NSFW images.
- If the game updates, use Auto Detect again.
- If something breaks, use **Restore Original**.
