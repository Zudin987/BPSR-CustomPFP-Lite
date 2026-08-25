from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Callable

from settings import atomic_write_json, backup_paths, load_json, sha256


def read_backup_state(pkg: Path) -> tuple[Path, Path, Path, dict]:
    clean, meta, folder = backup_paths(pkg)
    return clean, meta, folder, load_json(meta)


def write_backup_state(meta: Path, state: dict) -> None:
    atomic_write_json(meta, state)


def copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, tmp)
    os.replace(tmp, destination)


def clean_source(pkg: Path, log: Callable[[str], None]) -> Path:
    clean, meta, folder, state = read_backup_state(pkg)
    current_hash = sha256(pkg)

    if not clean.exists():
        log("Step 1/3: Making a safe copy of your original BPSR file...")
        copy_atomic(pkg, clean)
        state = {
            "clean": current_hash,
            "modified": None,
            "pending_modified": None,
            "container": str(pkg.parent),
            "package": pkg.name,
            "created": int(time.time()),
        }
        write_backup_state(meta, state)
        return clean

    had_valid_state = bool(state.get("clean"))
    clean_hash = state.get("clean") or sha256(clean)
    if sha256(clean) != clean_hash:
        raise RuntimeError(
            "The app's clean backup no longer matches its safety record. "
            "For safety, nothing was changed. Use BPSR/Steam Verify Files, then use Search Again."
        )

    modified_hash = state.get("modified")
    pending_hash = state.get("pending_modified")

    if current_hash != clean_hash and not had_valid_state:
        raise RuntimeError(
            "A clean backup exists, but its safety record is missing or damaged. "
            "The app will NOT guess and will NOT replace that backup. "
            "Close BPSR, verify/repair the game files, then use Search Again."
        )

    if current_hash == clean_hash:
        state["modified"] = None
        state["pending_modified"] = None
    elif modified_hash and current_hash == modified_hash:
        pass
    elif pending_hash and current_hash == pending_hash:
        # Recover safely from a crash after the live file was replaced but before state was committed.
        state["modified"] = pending_hash
        state["pending_modified"] = None
        log("Recovered a previous interrupted Apply safely.")
    elif modified_hash or pending_hash:
        raise RuntimeError(
            "BPSR changed this game file while a custom-picture session was active. "
            "The app will NOT overwrite your clean backup. Close BPSR, verify/repair the game files, "
            "then open this app and use Search Again."
        )
    else:
        # Clean session + unknown hash = a normal game update. Keep the previous clean copy as recovery.
        stamp = time.strftime("%Y%m%d-%H%M%S")
        folder.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(clean, folder / f"clean-before-update-{stamp}.bak")
        except Exception:
            pass
        log("A BPSR update was detected. Refreshing the safe original copy...")
        copy_atomic(pkg, clean)
        clean_hash = current_hash
        state = {
            "clean": clean_hash,
            "modified": None,
            "pending_modified": None,
            "container": str(pkg.parent),
            "package": pkg.name,
            "updated": int(time.time()),
        }

    state["clean"] = clean_hash
    write_backup_state(meta, state)
    return clean


def backup_session_status(pkg: Path) -> str:
    """Return none/clean/modified/unknown without changing any backup state."""
    clean, meta, _folder, state = read_backup_state(pkg)
    if not clean.exists():
        return "none"
    try:
        clean_hash = state.get("clean") or sha256(clean)
        if sha256(clean) != clean_hash:
            return "unknown"
        current_hash = sha256(pkg)
        if current_hash == clean_hash:
            return "clean"
        if current_hash in {state.get("modified"), state.get("pending_modified")}:
            return "modified"
        return "unknown"
    except Exception:
        return "unknown"


def restore_original(pkg: Path) -> str:
    clean, meta, _folder, state = read_backup_state(pkg)
    if not clean.exists():
        return "missing"

    clean_hash = state.get("clean") or sha256(clean)
    if sha256(clean) != clean_hash:
        raise RuntimeError(
            "The clean backup failed its safety check. Nothing was restored. "
            "Use BPSR/Steam Verify Files instead."
        )

    current_hash = sha256(pkg)
    if current_hash == clean_hash:
        state["modified"] = None
        state["pending_modified"] = None
        write_backup_state(meta, state)
        return "already"

    known_modified = {state.get("modified"), state.get("pending_modified")}
    known_modified.discard(None)
    if current_hash not in known_modified:
        raise RuntimeError(
            "BPSR's current file is not the file this app installed. It may have been updated or repaired. "
            "For safety, this app will not overwrite it with an older backup."
        )

    tmp = pkg.with_suffix(pkg.suffix + ".restore.tmp")
    shutil.copy2(clean, tmp)
    if sha256(tmp) != clean_hash:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Restore verification failed before installation. The live BPSR file was not changed.")
    os.replace(tmp, pkg)

    if sha256(pkg) != clean_hash:
        raise RuntimeError("Restore finished copying, but the final verification failed. Please verify BPSR files.")

    state["modified"] = None
    state["pending_modified"] = None
    write_backup_state(meta, state)
    return "restored"
