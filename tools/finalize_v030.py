from pathlib import Path

p = Path('src/app.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
'''def find_in_one_package(
    pkg: Path,
    file_hint: Optional[int] = None,
    cached_file: Optional[int] = None,
    cached_slot: Optional[str] = None,
) -> Optional[Target]:''',
'''def find_in_one_package(
    pkg: Path,
    file_hint: Optional[int] = None,
    cached_file: Optional[int] = None,
    cached_slot: Optional[str] = None,
    only_preferred: bool = False,
) -> Optional[Target]:''')

s = s.replace(
'''        if slot and (not cached_slot or number != cached_file or slot == cached_slot or slot in TARGET_SET):
            return Target(pkg, seg, slot)

    # Cheap pass:''',
'''        if slot:
            return Target(pkg, seg, slot)

    if only_preferred:
        return None

    # Cheap pass:''')

old = '''    total = len(ordered)
    log("Looking for a usable picture slot...")
    for index, pkg in enumerate(ordered, 1):
        progress(index - 1, total)
        if index == 1 or index % 5 == 0:
            log(f"Searching game files... {index}/{total}")
        target = find_in_one_package(pkg, file_hint)
        if target:
            cfg["detected_package"] = pkg.name
            cfg["detected_file"] = target.segment.number
            cfg["detected_slot"] = target.slot_name
            cfg["package"] = pkg.name
            save_cfg(cfg)
            progress(total, total)
            log("Picture slot found.")
            return target

    raise RuntimeError("No usable picture slot was found in this game folder. Try choosing a different BPSR install folder.")'''

new = '''    total = len(ordered)

    # If Discord gave fileNNN, test exactly that bundle across packages first.
    # This avoids full-decompressing the wrong package just because it was checked first.
    if file_hint:
        log(f"Trying the optional file{file_hint} speed hint...")
        for index, pkg in enumerate(ordered, 1):
            progress(index - 1, total)
            target = find_in_one_package(pkg, file_hint=file_hint, only_preferred=True)
            if target:
                cfg["detected_package"] = pkg.name
                cfg["detected_file"] = target.segment.number
                cfg["detected_slot"] = target.slot_name
                cfg["package"] = pkg.name
                save_cfg(cfg)
                progress(total, total)
                log("Picture slot found.")
                return target
        log("That speed hint is outdated, so we’re searching normally...")

    log("Looking for a usable picture slot...")
    for index, pkg in enumerate(ordered, 1):
        progress(index - 1, total)
        if index == 1 or index % 5 == 0:
            log(f"Searching game files... {index}/{total}")
        target = find_in_one_package(pkg)
        if target:
            cfg["detected_package"] = pkg.name
            cfg["detected_file"] = target.segment.number
            cfg["detected_slot"] = target.slot_name
            cfg["package"] = pkg.name
            save_cfg(cfg)
            progress(total, total)
            log("Picture slot found.")
            return target

    raise RuntimeError("No usable picture slot was found in this game folder. Try choosing a different BPSR install folder.")'''

if old not in s:
    raise SystemExit('find_target block not found')
s = s.replace(old, new)

s = s.replace(
'''        self.cfg.pop("detected_slot", None)
        save_cfg(self.cfg)''',
'''        self.cfg.pop("detected_slot", None)
        self.cfg.pop("package", None)
        self.package_var.set("")
        save_cfg(self.cfg)''')

s = s.replace(
'''        elif not self.valid_image():
            self.apply_button.state(["disabled"])
            self.main_status.set("Choose a picture to continue.")''',
'''        elif not self.valid_image():
            self.apply_button.state(["disabled"])
            if self.image_var.get() and Path(self.image_var.get()).is_file():
                self.main_status.set("Adjust the crop to match the selected picture shape.")
            else:
                self.main_status.set("Choose a picture to continue.")''')

s = s.replace(
'''        if self.valid_image():
            self.picture_status.set("Picture shape changed — adjust the crop again before applying.")
        self.update_ready_state()''',
'''        if self.image_var.get() and Path(self.image_var.get()).is_file():
            self.picture_status.set("Picture shape changed — adjust the crop again before applying.")
        self.update_ready_state()''')

p.write_text(s, encoding='utf-8')
print('v0.3.0 final logic patch applied')
