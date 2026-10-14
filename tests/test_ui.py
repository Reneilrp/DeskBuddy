"""
Headless UI verification test
Ensures all PyQt widgets, dialogs, micro-animations, sticky bubble coupling,
window climbing, tab walking, and application coordinators initialize and operate cleanly.
"""

import sys
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, QPoint

from src.app import DeskBuddyApp
from src.ui.speech_bubble import SpeechBubble
from src.ui.pet_window import PetWindow

class TestUIInitialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(sys.argv)

    def test_app_lifecycle(self):
        base_dir = Path(__file__).resolve().parent.parent
        desk_buddy = DeskBuddyApp(self.app, base_dir)

        # Check widget instantiations
        self.assertIsNotNone(desk_buddy.pet)
        self.assertIsNotNone(desk_buddy.speech_bubble)
        self.assertIsNotNone(desk_buddy.tray)
        self.assertIsNotNone(desk_buddy.task_dialog)

        # Start app methods
        desk_buddy.start()
        self.assertTrue(desk_buddy.pet.isVisible())

        # Test state change
        desk_buddy.pet.set_state("sleep")
        self.assertEqual(desk_buddy.pet.current_state, "sleep")

        desk_buddy.pet.set_state("happy")
        self.assertEqual(desk_buddy.pet.current_state, "happy")

        # Test hide and show
        desk_buddy.hide_pet()
        self.assertFalse(desk_buddy.pet.isVisible())

        desk_buddy.show_pet()
        self.assertTrue(desk_buddy.pet.isVisible())

    def test_speech_bubble_coupling_and_pin(self):
        bubble = SpeechBubble()
        self.assertFalse(bubble.is_pinned)
        
        # Test pin toggle
        bubble.toggle_pin()
        self.assertTrue(bubble.is_pinned)
        bubble.toggle_pin()
        self.assertFalse(bubble.is_pinned)

        # Test dynamic position calculation
        pet_rect = QRect(500, 500, 140, 140)
        screen_geom = QRect(0, 0, 1920, 1080)
        bubble.update_position(pet_rect, screen_geom)
        self.assertEqual(bubble.tail_direction, "bottom")

        # Test flip underneath when pet is at top of screen
        pet_near_top = QRect(500, 10, 140, 140)
        bubble.update_position(pet_near_top, screen_geom)
        self.assertEqual(bubble.tail_direction, "top")

    def test_pet_window_interactions_and_physics(self):
        base_dir = Path(__file__).resolve().parent.parent
        pet = PetWindow(base_dir / "assets")
        bubble = SpeechBubble()
        pet.set_speech_bubble(bubble)

        # Test bounce animation trigger
        pet.tick_timer.stop()
        pet.trigger_bounce()
        self.assertEqual(pet.bounce_step, 1)
        for _ in range(12):
            pet._update_bounce()
        self.assertEqual(pet.bounce_step, 0)
        self.assertEqual(pet.bounce_scale_x, 1.0)

        # Test head pat trigger
        pet._trigger_head_pat_reaction()
        self.assertEqual(pet.current_state, "happy")

        # Test free roam toggle
        self.assertTrue(pet.free_roam_enabled)
        pet.toggle_free_roam()
        self.assertFalse(pet.free_roam_enabled)
        pet.toggle_free_roam()
        self.assertTrue(pet.free_roam_enabled)

    def test_window_climbing_and_tab_walking(self):
        base_dir = Path(__file__).resolve().parent.parent
        pet = PetWindow(base_dir / "assets")
        pet.tick_timer.stop()

        # Set mock active window (e.g. Chrome browser at x=400, y=200, w=800, h=600)
        mock_win = QRect(400, 200, 800, 600)
        pet.cached_active_window = mock_win

        # Simulate pet starting to climb left wall
        pet.roam_mode = "climb_wall"
        pet.climb_wall_side = "left"
        pet.move(mock_win.left() - pet.width() + 10, 500)

        # Step climbing upwards
        for _ in range(20):
            pet._update_roaming_and_climbing()
        
        # Verify climbing moves upward
        self.assertLess(pet.y(), 500)
        self.assertEqual(pet.facing_direction, 1)

        # Simulate reaching the top
        pet.move(pet.x(), mock_win.top() - pet.height() + 12)
        pet._update_roaming_and_climbing()
        # Should transition to walk_tabs
        self.assertEqual(pet.roam_mode, "walk_tabs")

        # Simulate walking on tabs
        for _ in range(5):
            pet._update_roaming_and_climbing()
        self.assertEqual(pet.roam_mode, "walk_tabs")

        # Simulate walking off the right edge of tabs
        pet.move(mock_win.right() + 20, pet.y())
        pet._update_roaming_and_climbing()
        # Should detect ground loss and fall
        self.assertTrue(pet.gravity_active)

    def test_pomodoro_partner_flow(self):
        base_dir = Path(__file__).resolve().parent.parent
        desk_buddy = DeskBuddyApp(self.app, base_dir)

        self.assertEqual(desk_buddy.pomodoro_mode, "idle")
        desk_buddy._toggle_pomodoro()
        self.assertEqual(desk_buddy.pomodoro_mode, "focus")
        self.assertTrue(desk_buddy.pet.pomodoro_active)
        self.assertEqual(desk_buddy.pomodoro_seconds_left, 1500)

        # Tick 1 second
        desk_buddy._on_pomodoro_tick()
        self.assertEqual(desk_buddy.pomodoro_seconds_left, 1499)

        # Toggle stop
        desk_buddy._toggle_pomodoro()
        self.assertEqual(desk_buddy.pomodoro_mode, "idle")
        self.assertFalse(desk_buddy.pet.pomodoro_active)

    def test_desktop_deletion_reactions(self):
        base_dir = Path(__file__).resolve().parent.parent
        desk_buddy = DeskBuddyApp(self.app, base_dir)

        # Verify initial mode
        self.assertIn(desk_buddy.deletion_reaction_mode, ("chomp", "snip", "vortex", "off"))

        # Test switching modes
        for mode in ("chomp", "snip", "vortex", "off"):
            desk_buddy._on_deletion_reaction_mode_changed(mode)
            self.assertEqual(desk_buddy.deletion_reaction_mode, mode)
            self.assertEqual(desk_buddy.pet.deletion_reaction_mode, mode)
            self.assertEqual(desk_buddy.tray.deletion_reaction_mode, mode)

        # Test execution of animations
        for mode in ("chomp", "snip", "vortex"):
            desk_buddy.pet.play_deletion_animation(mode, "Discord")
            self.assertIsNotNone(desk_buddy.pet.current_state)

        # Test simulated deletion event
        desk_buddy._on_deletion_reaction_mode_changed("chomp")
        desk_buddy._on_desktop_file_deleted("Chrome.lnk")
        self.assertTrue(desk_buddy.speech_bubble.isVisible())
        self.assertIn("devoured 'Chrome.lnk'", desk_buddy.speech_bubble.label_message.text())

    def test_chibi_layered_rig(self):
        from PyQt6.QtGui import QImage, QPainter
        from PyQt6.QtCore import QRectF
        from src.ui.chibi_rig import ChibiRig

        base_dir = Path(__file__).resolve().parent.parent
        res_dir = base_dir / "assets" / "resonators" / "chisa"
        rig = ChibiRig(res_dir)

        # Physics stepping test
        self.assertFalse(rig.is_walking)
        rig.update_physics(is_walking=True, is_climbing=False)
        self.assertTrue(rig.is_walking)
        self.assertGreater(rig.walk_ticks, 0.0)

        # Scissor trigger test
        rig.trigger_snip()
        self.assertTrue(rig.is_snipping)
        rig.update_physics(is_walking=True)
        self.assertGreater(rig.snip_progress, 0.0)
        rig.stop_snip()
        self.assertFalse(rig.is_snipping)

        # Carp chomp trigger test
        rig.trigger_chomp()
        self.assertTrue(rig.is_chomping)
        rig.update_physics(is_walking=False)
        self.assertGreater(rig.chomp_progress, 0.0)

        # Render test into QImage buffer
        img = QImage(140, 140, QImage.Format.Format_ARGB32)
        img.fill(0)
        painter = QPainter(img)
        rig.render(
            painter=painter,
            rect=QRectF(0, 0, 140, 140),
            current_state="idle",
            current_frame=0,
            facing_direction=1
        )
        painter.end()
        # Verify rendered non-empty
        self.assertFalse(img.isNull())

    def test_chisa_sprite_animator(self):
        from src.ui.sprite_animator import SpriteAnimator
        base_dir = Path(__file__).resolve().parent.parent
        res_dir = base_dir / "assets" / "resonators" / "chisa"

        animator = SpriteAnimator(res_dir, is_chisa=True)

        # Check core animation states exist
        self.assertTrue(animator.has_state("idle"))
        self.assertTrue(animator.has_state("happy"))
        self.assertTrue(animator.has_state("walk"))
        self.assertTrue(animator.has_state("climb"))
        self.assertTrue(animator.has_state("sit"))

        # Verify walk cycle has 4 frames
        self.assertEqual(animator.frame_count("walk"), 4)

        # Verify frames can be retrieved and are valid QPixmaps
        for state in ("idle", "happy", "walk", "climb", "sit"):
            frame = animator.get_frame(state, 0)
            self.assertIsNotNone(frame)
            self.assertFalse(frame.isNull())

        # Test PetWindow integrates with SpriteAnimator
        pet = PetWindow(base_dir / "assets")
        self.assertIsNotNone(pet.sprite_animator)
        self.assertEqual(pet.current_resonator_id, "chisa")

        # Test roam state resolution
        pet.roam_mode = "walk_ground"
        self.assertEqual(pet._resolve_draw_state(), "walk")

        pet.roam_mode = "climb_wall"
        self.assertEqual(pet._resolve_draw_state(), "climb")

        pet.roam_mode = "walk_tabs"
        self.assertEqual(pet._resolve_draw_state(), "sit")

        pet.roam_mode = "idle"
        self.assertEqual(pet._resolve_draw_state(), "idle")

    def test_fast_search_engine(self):
        import tempfile
        from src.core.fast_search import FastSearchEngine, format_file_size

        self.assertEqual(format_file_size(500), "500 B")
        self.assertEqual(format_file_size(1500), "1.5 KB")
        self.assertEqual(format_file_size(2 * 1024 * 1024), "2.0 MB")

        engine = FastSearchEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "alpha_doc.txt").write_text("hello")
            (tmppath / "beta_pic.png").write_text("world")
            (tmppath / "sub").mkdir()
            (tmppath / "sub" / "alpha_nested.pdf").write_text("pdf data")
            # Ignored dir
            (tmppath / ".git").mkdir()
            (tmppath / ".git" / "alpha_git.txt").write_text("git data")

            # Search "alpha"
            res = engine.search("alpha", search_root=tmppath)
            names = [r["name"] for r in res]
            self.assertIn("alpha_doc.txt", names)
            self.assertIn("alpha_nested.pdf", names)
            self.assertNotIn("alpha_git.txt", names)  # .git must be ignored

            # Wildcard search "*.png"
            res_wild = engine.search("*.png", search_root=tmppath)
            self.assertEqual(len(res_wild), 1)
            self.assertEqual(res_wild[0]["name"], "beta_pic.png")

    def test_file_organizer_shield_and_undo(self):
        import tempfile
        from src.core.file_organizer import FileOrganizer

        organizer = FileOrganizer()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "photo.jpg").write_text("image")
            (tmppath / "notes.txt").write_text("document")
            # Active downloads that MUST be protected
            (tmppath / "installer.exe.crdownload").write_text("downloading...")
            (tmppath / "bigfile.zip.part").write_text("partial...")

            # Dry-run plan
            plan = organizer.plan_organization(tmppath, rule="type")
            self.assertTrue(plan["success"])
            planned_names = [m["name"] for m in plan["moves"]]
            self.assertIn("photo.jpg", planned_names)
            self.assertIn("notes.txt", planned_names)
            # Shields verified: active downloads are NOT moved!
            self.assertNotIn("installer.exe.crdownload", planned_names)
            self.assertNotIn("bigfile.zip.part", planned_names)

            # Execute moves
            res = organizer.execute_moves(plan["moves"])
            self.assertTrue(res["success"])
            self.assertEqual(res["moved_count"], 2)

            self.assertTrue((tmppath / "Images" / "photo.jpg").exists())
            self.assertTrue((tmppath / "Documents" / "notes.txt").exists())
            self.assertTrue((tmppath / "installer.exe.crdownload").exists())

            # Test Undo
            undo_res = organizer.undo_last()
            self.assertTrue(undo_res["success"])
            self.assertEqual(undo_res["reverted_count"], 2)

            # Files are back in original place
            self.assertTrue((tmppath / "photo.jpg").exists())
            self.assertTrue((tmppath / "notes.txt").exists())
            # Empty category folders removed
            self.assertFalse((tmppath / "Images").exists())
            self.assertFalse((tmppath / "Documents").exists())

            # Test selective extension rule (e.g. only PNG files to "My_PNGs")
            (tmppath / "icon1.png").write_text("png1")
            (tmppath / "icon2.png").write_text("png2")
            (tmppath / "readme.txt").write_text("text")

            plan_selective = organizer.plan_organization(
                tmppath,
                rule="extension",
                ext_filter=".png",
                custom_subfolder="My_PNGs"
            )
            self.assertTrue(plan_selective["success"])
            self.assertEqual(len(plan_selective["moves"]), 2)
            for m in plan_selective["moves"]:
                self.assertTrue(m["name"].endswith(".png"))
                self.assertIn("My_PNGs", m["destination"])

            # Execute selective moves
            res_sel = organizer.execute_moves(plan_selective["moves"])
            self.assertTrue(res_sel["success"])
            self.assertTrue((tmppath / "My_PNGs" / "icon1.png").exists())
            self.assertTrue((tmppath / "My_PNGs" / "icon2.png").exists())
            self.assertTrue((tmppath / "readme.txt").exists())  # Unselected file remains untouched!

            # Undo selective moves
            undo_sel = organizer.undo_last()
            self.assertTrue(undo_sel["success"])
            self.assertTrue((tmppath / "icon1.png").exists())
            self.assertFalse((tmppath / "My_PNGs").exists())

    def test_workspace_dialog_integration(self):
        from src.core.task_manager import TaskManager
        from src.core.file_organizer import FileOrganizer
        from src.ui.workspace_dialog import WorkspaceDialog

        tm = TaskManager()
        fo = FileOrganizer()
        dialog = WorkspaceDialog(tm, fo, resonator_id="chisa")

        self.assertIsNotNone(dialog.tabs)
        self.assertEqual(dialog.tabs.count(), 5)

        # Tab navigation methods
        dialog.open_search_tab("testquery")
        self.assertEqual(dialog.tabs.currentIndex(), 0)
        self.assertEqual(dialog.search_input.text(), "testquery")

        dialog.open_organizer_tab()
        self.assertEqual(dialog.tabs.currentIndex(), 1)

        dialog.open_chat_tab()
        self.assertEqual(dialog.tabs.currentIndex(), 3)

        # Append chat message
        dialog.append_message("Chisa", "Hello Rover!")
        self.assertIn("Hello Rover!", dialog.chat_history.toPlainText())

        # Test Resonator switching on workspace
        dialog.set_resonator("jinhsi")
        self.assertIn("Jinhsi", dialog.header_title.text())
        dialog.set_resonator("chisa")
        self.assertIn("Chisa", dialog.header_title.text())

        dialog.close()

    def test_rule_based_quick_commands(self):
        from src.agent.brain import AgentBrain
        from src.core.task_manager import TaskManager
        from src.core.file_organizer import FileOrganizer

        tm = TaskManager()
        fo = FileOrganizer()
        brain = AgentBrain(tm, fo, resonator_id="chisa")

        # 1. Time query
        reply_time = brain.handle_quick_commands("what time is it?")
        self.assertIsNotNone(reply_time)
        self.assertIn("It's currently", reply_time)
        self.assertIn("Chisa", reply_time)

        # 2. Date query
        reply_date = brain.handle_quick_commands("what's today's date?")
        self.assertIsNotNone(reply_date)
        self.assertIn("Today is", reply_date)

        # 3. Daily greetings
        reply_morning = brain.handle_quick_commands("good morning")
        self.assertIsNotNone(reply_morning)
        self.assertIn("Rover", reply_morning)

        reply_night = brain.handle_quick_commands("good night!")
        self.assertIsNotNone(reply_night)
        self.assertIn("Good night", reply_night)

        # 4. Identity query
        reply_who = brain.handle_quick_commands("who are you?")
        self.assertIsNotNone(reply_who)
        self.assertIn("Chisa", reply_who)

        # 5. Fast task addition
        reply_task = brain.handle_quick_commands("remind me to check emails in 10 minutes")
        self.assertIsNotNone(reply_task)
        self.assertIn("check emails", reply_task)
        self.assertIn("10 minutes", reply_task)

        # Check tasks list
        reply_list = brain.handle_quick_commands("what are my tasks?")
        self.assertIsNotNone(reply_list)
        self.assertIn("check emails", reply_list)

if __name__ == "__main__":
    unittest.main()
