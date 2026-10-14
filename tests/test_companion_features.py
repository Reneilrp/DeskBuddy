import os
import tempfile
import time
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from src.core.stash_manager import StashManager
from src.core.clipboard_assistant import ClipboardAssistant, safe_eval_math
from src.core.cleanup_hunter import CleanupHunter, compute_chunk_hash
from src.core.ergonomics_tracker import ErgonomicsTracker
from src.core.download_watcher import DownloadWatcher


class TestStashManager(unittest.TestCase):
    def setUp(self):
        self.sm = StashManager()

    def test_add_and_get_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "test1.txt"
            f2 = Path(tmpdir) / "test2.png"
            f1.write_text("hello")
            f2.write_bytes(b"\x89PNG\r\n\x1a\n")

            added = self.sm.add_files([str(f1), str(f2)])
            self.assertEqual(added, 2)
            self.assertEqual(self.sm.count(), 2)
            self.assertIn(Path(f1).resolve(), self.sm.get_files())
            self.assertIn(Path(f2).resolve(), self.sm.get_files())

            # Test summary
            summary = self.sm.summary()
            self.assertIn("Holding 2 files", summary)

            # Test remove single
            self.sm.remove_file(str(f1))
            self.assertEqual(self.sm.count(), 1)

            # Test clear
            self.sm.clear()
            self.assertEqual(self.sm.count(), 0)
            self.assertEqual(self.sm.summary(), "Pocket is empty.")


class TestClipboardAssistant(unittest.TestCase):
    def setUp(self):
        self.ca = ClipboardAssistant()

    def test_safe_math_evaluator(self):
        self.assertEqual(safe_eval_math("10 + 20 * 3"), 70)
        self.assertEqual(safe_eval_math("(100 - 20) / 4"), 20.0)
        self.assertEqual(safe_eval_math("2 ^ 8"), 256)
        self.assertEqual(safe_eval_math("15% of 200"), 30.0)
        # Invalid math syntax should safely return None
        self.assertIsNone(safe_eval_math("import os"))
        self.assertIsNone(safe_eval_math("__import__('os').system('ls')"))
        self.assertIsNone(safe_eval_math("not a math string"))

    def test_clipboard_inspect_math(self):
        res = self.ca.inspect_text("1280 * 720 / 60")
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "math")
        self.assertEqual(res["result"], "15,360")

    def test_clipboard_inspect_hex_color(self):
        res = self.ca.inspect_text("#FF8B77")
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "color")
        self.assertEqual(res["hex"], "#FF8B77")
        self.assertEqual(res["rgb"], "rgb(255, 139, 119)")

    def test_clipboard_inspect_json(self):
        raw_json = '{"name":"Chisa","element":"Havoc","role":"Companion"}'
        res = self.ca.inspect_text(raw_json)
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "json")
        self.assertIn('"name": "Chisa"', res["action_value"])

    def test_clipboard_inspect_plain_text(self):
        res = self.ca.inspect_text("Hello there! Just normal typing.")
        self.assertIsNone(res)


class TestCleanupHunter(unittest.TestCase):
    def setUp(self):
        self.hunter = CleanupHunter()

    def test_duplicate_downloads_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = Path(tmpdir) / "document.pdf"
            dupe = Path(tmpdir) / "document (1).pdf"
            diff = Path(tmpdir) / "different.pdf"

            content = b"Sample duplicate payload contents" * 50
            orig.write_bytes(content)
            dupe.write_bytes(content)
            diff.write_bytes(b"Different contents entirely")

            dupes = self.hunter.scan_duplicate_downloads(tmpdir)
            self.assertEqual(len(dupes), 1)
            self.assertEqual(dupes[0]["duplicate_name"], "document (1).pdf")
            self.assertEqual(dupes[0]["original_path"], str(orig))

    def test_delete_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "trash.tmp"
            f.write_text("to delete")
            self.assertTrue(f.exists())

            result = self.hunter.delete_items([str(f)])
            self.assertTrue(result["success"])
            self.assertEqual(result["deleted_count"], 1)
            self.assertFalse(f.exists())


class TestErgonomicsTracker(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.tracker = ErgonomicsTracker(break_interval_minutes=1)

    def test_hydration_counter(self):
        initial = self.tracker.water_glasses
        glasses = self.tracker.add_water_glass()
        self.assertEqual(glasses, initial + 1)
        self.assertEqual(self.tracker.get_water_glasses(), initial + 1)

    def test_activity_and_trigger(self):
        # Verify reminder signal triggers
        fired = []
        self.tracker.reminder_triggered.connect(lambda p: fired.append(p))
        self.tracker.session_count = 0
        self.tracker.active_seconds = 60
        self.tracker._on_tick()
        self.assertEqual(len(fired), 1)
        self.assertIn("message", fired[0])
        self.assertEqual(fired[0]["session_count"], 1)


class TestStashBagUI(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.sm = StashManager()

    def test_stash_dialog_lifecycle(self):
        from src.ui.stash_dialog import StashBagDialog

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "doc1.txt"
            f2 = Path(tmpdir) / "image.png"
            f1.write_text("sample")
            f2.write_bytes(b"\x89PNG")

            self.sm.add_files([str(f1), str(f2)])
            dialog = StashBagDialog(self.sm, resonator_name="Chisa")

            self.assertEqual(dialog.badge_count.text(), "2 files")
            self.assertEqual(dialog.list_widget.count(), 2)
            self.assertTrue(dialog.drag_all_zone.isEnabled())

            # Test remove selected
            dialog.list_widget.setCurrentRow(0)
            dialog._remove_selected()
            self.assertEqual(dialog.list_widget.count(), 1)
            self.assertEqual(self.sm.count(), 1)

            # Test clear all
            dialog._clear_all()
            self.assertEqual(self.sm.count(), 0)
            self.assertEqual(dialog.badge_count.text(), "0 files")
            self.assertFalse(dialog.drag_all_zone.isEnabled())
            dialog.close()

    def test_pet_window_bag_badge(self):
        from src.ui.pet_window import PetWindow
        base_dir = Path(__file__).resolve().parent.parent / "assets"
        pet = PetWindow(base_dir)

        # Initially hidden when empty
        pet.update_stashed_files([])
        self.assertTrue(pet.bag_badge.isHidden())

        # Shows badge with count when files exist
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "sample.pdf"
            f.write_text("test")
            pet.update_stashed_files([f])

            self.assertFalse(pet.bag_badge.isHidden())
            self.assertEqual(pet.bag_badge.text(), "🎒 1")

            pet.update_stashed_files([])
            self.assertTrue(pet.bag_badge.isHidden())
        pet.close()


if __name__ == "__main__":
    unittest.main()
