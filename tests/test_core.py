from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import settings  # noqa: E402
import backup_ops  # noqa: E402
import unity_ops  # noqa: E402


class CoreSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_backups = settings.BACKUPS
        self.old_work = settings.WORK
        self.old_crops = settings.CROPS
        settings.BACKUPS = self.root / "backups"
        settings.WORK = self.root / "work"
        settings.CROPS = self.root / "crops"
        settings.ensure_dirs()

    def tearDown(self):
        settings.BACKUPS = self.old_backups
        settings.WORK = self.old_work
        settings.CROPS = self.old_crops
        self.temp.cleanup()

    def make_pkg(self, install: str, content: bytes = b"clean-original") -> Path:
        folder = self.root / install / "StreamingAssets" / "container"
        folder.mkdir(parents=True, exist_ok=True)
        pkg = folder / "m79.pkg"
        pkg.write_bytes(content)
        return pkg

    def test_backup_is_namespaced_by_install(self):
        a = self.make_pkg("A")
        b = self.make_pkg("B")
        self.assertNotEqual(settings.backup_paths(a)[0], settings.backup_paths(b)[0])

    def test_restore_only_known_modified_file(self):
        pkg = self.make_pkg("A")
        clean = backup_ops.clean_source(pkg, lambda _text: None)
        self.assertEqual(clean.read_bytes(), b"clean-original")

        pkg.write_bytes(b"custom-known")
        _clean_path, meta, _folder, state = backup_ops.read_backup_state(pkg)
        state["modified"] = settings.sha256(pkg)
        state["pending_modified"] = None
        backup_ops.write_backup_state(meta, state)

        self.assertEqual(backup_ops.restore_original(pkg), "restored")
        self.assertEqual(pkg.read_bytes(), b"clean-original")

    def test_restore_refuses_unknown_new_file(self):
        pkg = self.make_pkg("A")
        backup_ops.clean_source(pkg, lambda _text: None)

        pkg.write_bytes(b"custom-known")
        _clean, meta, _folder, state = backup_ops.read_backup_state(pkg)
        state["modified"] = settings.sha256(pkg)
        backup_ops.write_backup_state(meta, state)

        pkg.write_bytes(b"game-updated-after-custom")
        with self.assertRaises(RuntimeError):
            backup_ops.restore_original(pkg)

    def test_clean_backup_is_not_poisoned_after_interrupted_session(self):
        pkg = self.make_pkg("A")
        clean = backup_ops.clean_source(pkg, lambda _text: None)
        original_hash = settings.sha256(clean)

        pkg.write_bytes(b"known-custom")
        _clean, meta, _folder, state = backup_ops.read_backup_state(pkg)
        state["modified"] = settings.sha256(pkg)
        backup_ops.write_backup_state(meta, state)

        pkg.write_bytes(b"unknown-update")
        with self.assertRaises(RuntimeError):
            backup_ops.clean_source(pkg, lambda _text: None)

        self.assertEqual(settings.sha256(clean), original_hash)
        self.assertEqual(clean.read_bytes(), b"clean-original")

    def test_session_status_tracks_clean_modified_and_unknown(self):
        pkg = self.make_pkg("A")
        backup_ops.clean_source(pkg, lambda _text: None)
        self.assertEqual(backup_ops.backup_session_status(pkg), "clean")

        pkg.write_bytes(b"known-custom")
        _clean, meta, _folder, state = backup_ops.read_backup_state(pkg)
        state["modified"] = settings.sha256(pkg)
        backup_ops.write_backup_state(meta, state)
        self.assertEqual(backup_ops.backup_session_status(pkg), "modified")

        pkg.write_bytes(b"unexpected-change")
        self.assertEqual(backup_ops.backup_session_status(pkg), "unknown")

    def test_crash_recovery_commits_pending_hash(self):
        pkg = self.make_pkg("A")
        backup_ops.clean_source(pkg, lambda _text: None)

        pkg.write_bytes(b"pending-custom")
        _clean, meta, _folder, state = backup_ops.read_backup_state(pkg)
        state["pending_modified"] = settings.sha256(pkg)
        state["modified"] = None
        backup_ops.write_backup_state(meta, state)

        backup_ops.clean_source(pkg, lambda _text: None)
        state = settings.load_json(meta)
        self.assertEqual(state["modified"], settings.sha256(pkg))
        self.assertIsNone(state["pending_modified"])


class DetectionTests(unittest.TestCase):
    def test_segment_and_target_value_objects_construct_cleanly(self):
        seg = unity_ops.Segment(593, 100, 200)
        target = unity_ops.Target(Path("m79.pkg"), seg, "personalzone_player_bg_3")
        self.assertEqual((seg.number, seg.offset, seg.size), (593, 100, 200))
        self.assertEqual(target.slot_name, "personalzone_player_bg_3")

    def test_preferred_bg3_wins(self):
        names = {"personalzone_player_bg_8", "personalzone_player_bg_3", "personalzone_player_bg_1"}
        self.assertEqual(unity_ops.choose_slot(names), "personalzone_player_bg_3")

    def test_cached_slot_wins_when_present(self):
        names = {"personalzone_player_bg_3", "personalzone_player_bg_9"}
        self.assertEqual(unity_ops.choose_slot(names, "personalzone_player_bg_9"), "personalzone_player_bg_9")

    def test_fallback_uses_lowest_numeric_slot(self):
        names = {"personalzone_player_bg_12", "personalzone_player_bg_7"}
        self.assertEqual(unity_ops.choose_slot(names), "personalzone_player_bg_7")

    def test_parse_file_hint_is_strict_but_beginner_friendly(self):
        self.assertEqual(settings.parse_file_hint("593"), 593)
        self.assertEqual(settings.parse_file_hint("file593"), 593)
        self.assertEqual(settings.parse_file_hint("file 593"), 593)
        self.assertIsNone(settings.parse_file_hint("   "))
        with self.assertRaises(ValueError):
            settings.parse_file_hint("Discord says file593 maybe")


class ConfigTests(unittest.TestCase):
    def test_atomic_json_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.json"
            settings.atomic_write_json(path, {"hello": "world", "n": 3})
            self.assertEqual(json.loads(path.read_text("utf-8")), {"hello": "world", "n": 3})
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
