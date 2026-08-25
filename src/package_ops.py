from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Callable, Optional

from backup_ops import clean_source, read_backup_state, write_backup_state
from settings import (
    KNOWN_FILE,
    KNOWN_PACKAGE,
    PREFERRED_SLOT,
    cleanup_temp_files,
    package_fingerprint,
    package_number,
    prune_before_backups,
    save_cfg,
    sha256,
)
from unity_ops import (
    Segment,
    Target,
    quick_blob_hint,
    read_segment,
    replace_texture,
    segments,
    target_name_from_blob,
)


def target_from_cached_offset(pkg: Path, cfg: dict) -> Optional[Target]:
    try:
        if cfg.get("detected_package") != pkg.name:
            return None
        if cfg.get("detected_fingerprint") != package_fingerprint(pkg):
            return None
        number = int(cfg["detected_file"])
        offset = int(cfg["detected_offset"])
        size = int(cfg["detected_size"])
        if number < 1 or offset < 0 or size <= 0 or offset + size > pkg.stat().st_size:
            return None
        seg = Segment(number, offset, size)
        slot = target_name_from_blob(read_segment(pkg, seg), cfg.get("detected_slot"))
        if not slot:
            return None
        return Target(pkg, seg, slot)
    except Exception:
        return None


def find_in_one_package(
    pkg: Path,
    file_hint: Optional[int] = None,
    cached_file: Optional[int] = None,
    cached_slot: Optional[str] = None,
    only_preferred: bool = False,
) -> Optional[Target]:
    ss = segments(pkg)
    if not ss:
        return None

    checked: set[int] = set()
    preferred: list[int] = []
    for number in (cached_file, file_hint):
        if number and 1 <= number <= len(ss) and number not in preferred:
            preferred.append(number)

    for number in preferred:
        checked.add(number)
        seg = ss[number - 1]
        blob = read_segment(pkg, seg)
        slot = target_name_from_blob(blob, cached_slot)
        if slot:
            return Target(pkg, seg, slot)

    if only_preferred:
        return None

    raw_candidates: list[tuple[Segment, bytes]] = []
    for seg in ss:
        if seg.number in checked:
            continue
        blob = read_segment(pkg, seg)
        if quick_blob_hint(blob):
            raw_candidates.append((seg, blob))

    for seg, blob in raw_candidates:
        checked.add(seg.number)
        slot = target_name_from_blob(blob, cached_slot)
        if slot:
            return Target(pkg, seg, slot)

    for seg in ss:
        if seg.number in checked:
            continue
        slot = target_name_from_blob(read_segment(pkg, seg), cached_slot)
        if slot:
            return Target(pkg, seg, slot)
    return None


def remember_target(cfg: dict, target: Target) -> None:
    cfg.update(
        package=target.package.name,
        detected_package=target.package.name,
        detected_file=target.segment.number,
        detected_slot=target.slot_name,
        detected_offset=target.segment.offset,
        detected_size=target.segment.size,
        detected_fingerprint=package_fingerprint(target.package),
    )
    save_cfg(cfg)


def find_target(
    container: Path,
    cfg: dict,
    file_hint: Optional[int],
    log: Callable[[str], None],
    progress: Callable[[float, float], None],
    force_rescan: bool = False,
) -> Target:
    packages = sorted(container.glob("m*.pkg"), key=package_number)
    if not packages:
        raise RuntimeError("No BPSR game files were found in that folder.")

    cached_pkg_name = None if force_rescan else cfg.get("detected_package")
    cached_file = None if force_rescan else cfg.get("detected_file")
    cached_slot = None if force_rescan else cfg.get("detected_slot")

    if cached_pkg_name:
        cached_pkg = container / cached_pkg_name
        if cached_pkg.exists():
            log("Checking the last working picture location...")
            target = target_from_cached_offset(cached_pkg, cfg)
            if target:
                progress(1, 1)
                return target
            target = find_in_one_package(cached_pkg, file_hint, cached_file, cached_slot)
            if target:
                remember_target(cfg, target)
                progress(1, 1)
                return target

    ordered: list[Path] = []
    seen: set[str] = set()

    selected = cfg.get("package")
    if selected:
        selected_path = container / selected
        if selected_path.exists():
            ordered.append(selected_path)
            seen.add(selected_path.name)

    # The original community guide uses m79.pkg/file593/bg_3. Try that first, but never depend on it.
    known = container / KNOWN_PACKAGE
    if known.exists() and known.name not in seen:
        ordered.append(known)
        seen.add(known.name)

    for pkg in sorted(packages, key=lambda p: p.stat().st_mtime, reverse=True):
        if pkg.name not in seen:
            ordered.append(pkg)
            seen.add(pkg.name)

    total = max(1, len(ordered))

    first_hint = file_hint or KNOWN_FILE
    if first_hint:
        friendly = f"file{first_hint}"
        log(f"Trying the fast known location ({friendly}) first...")
        for index, pkg in enumerate(ordered, 1):
            progress(index - 1, total)
            target = find_in_one_package(
                pkg,
                file_hint=first_hint,
                cached_slot=cached_slot or PREFERRED_SLOT,
                only_preferred=True,
            )
            if target:
                remember_target(cfg, target)
                progress(total, total)
                log("Picture location found.")
                return target

    log("The fast location did not match this game version. Searching safely...")
    for index, pkg in enumerate(ordered, 1):
        progress(index - 1, total)
        if index == 1 or index % 5 == 0:
            log(f"Searching BPSR files... {index}/{len(ordered)}")
        target = find_in_one_package(pkg, cached_slot=cached_slot)
        if target:
            remember_target(cfg, target)
            progress(total, total)
            log("Picture location found.")
            return target

    raise RuntimeError(
        "No supported picture background was found in this BPSR installation. "
        "The game may have changed. Try Advanced Options → Search Again after verifying the game files."
    )


def splice(clean: Path, target: Segment, new_blob: bytes, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with clean.open("rb") as src, output.open("wb") as dst:
        left = target.offset
        while left:
            block = src.read(min(left, 8 * 1024 * 1024))
            if not block:
                raise IOError("Unexpected end of BPSR file.")
            dst.write(block)
            left -= len(block)
        src.seek(target.size, 1)
        dst.write(new_blob)
        shutil.copyfileobj(src, dst, 8 * 1024 * 1024)


def check_free_space(pkg: Path, estimated_bytes: int) -> None:
    try:
        free = shutil.disk_usage(pkg.parent).free
        needed = estimated_bytes + max(128 * 1024 * 1024, pkg.stat().st_size // 4)
        if free < needed:
            raise RuntimeError(
                f"Not enough free space on the BPSR drive. Please free about "
                f"{(needed - free) / (1024**3):.1f} GB, then try again."
            )
    except OSError:
        pass


def apply_picture(
    target: Target,
    image_path: Path,
    log: Callable[[str], None],
    progress: Callable[[float, float], None],
) -> None:
    cleanup_temp_files()
    clean = clean_source(target.package, log)
    clean_segments = segments(clean)
    if target.segment.number > len(clean_segments):
        raise RuntimeError("BPSR updated while the app was open. Use Search Again, then retry.")

    clean_seg = clean_segments[target.segment.number - 1]
    clean_blob = read_segment(clean, clean_seg)
    slot = target_name_from_blob(clean_blob, target.slot_name)
    if slot != target.slot_name:
        raise RuntimeError("The saved picture location changed. Use Search Again, then retry.")

    log("Step 2/3: Building your custom picture safely...")
    new_blob = replace_texture(clean_blob, image_path, slot)

    # Build directly beside the live package. That keeps the final commit on one
    # filesystem, avoids an extra full-package copy, and makes os.replace atomic.
    output = target.package.with_suffix(target.package.suffix + ".pfp.build.tmp")
    output.unlink(missing_ok=True)
    check_free_space(target.package, target.package.stat().st_size + len(new_blob))
    splice(clean, clean_seg, new_blob, output)

    # Validate structure and the exact target before touching the live game file.
    rebuilt_segments = segments(output)
    if len(rebuilt_segments) != len(clean_segments):
        output.unlink(missing_ok=True)
        raise RuntimeError("Safety check failed. Your original BPSR file was not changed.")
    rebuilt_seg = rebuilt_segments[clean_seg.number - 1]
    if target_name_from_blob(read_segment(output, rebuilt_seg), slot) != slot:
        output.unlink(missing_ok=True)
        raise RuntimeError("Safety check failed. Your original BPSR file was not changed.")

    output_hash = sha256(output)
    clean_path, meta, backup_folder, state = read_backup_state(target.package)
    if not clean_path.exists():
        raise RuntimeError("The clean backup disappeared unexpectedly. Nothing was installed.")

    # Commit the intended modified hash BEFORE replacing the live file.
    state["pending_modified"] = output_hash
    state["modified"] = state.get("modified")
    state["clean"] = state.get("clean") or sha256(clean_path)
    write_backup_state(meta, state)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_folder.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(target.package, backup_folder / f"before-{stamp}.bak")
        prune_before_backups(backup_folder, keep=2)
    except Exception:
        pass

    log("Step 3/3: Installing the checked file into BPSR...")
    # output already passed a full SHA-256 and UnityFS validation above.
    os.replace(output, target.package)

    if sha256(target.package) != output_hash:
        raise RuntimeError(
            "The file was replaced but did not pass the final verification. "
            "Close BPSR and use Verify Files before continuing."
        )

    state["modified"] = output_hash
    state["pending_modified"] = None
    write_backup_state(meta, state)
    progress(1, 1)
    log("Picture applied. Do the in-game photo steps now, then restore the original file.")
