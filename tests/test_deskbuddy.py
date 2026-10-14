"""
Unit & Integration Tests for DeskBuddy Core & UI Components
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.core.task_manager import TaskManager
from src.core.file_organizer import FileOrganizer
from src.agent.brain import AgentBrain

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_tasks.db"
        self.manager = TaskManager(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_list_tasks(self):
        tid = self.manager.add_task(title="Water the plants", priority="high")
        self.assertIsInstance(tid, int)

        tasks = self.manager.list_tasks(status="pending")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Water the plants")
        self.assertEqual(tasks[0]["priority"], "high")

    def test_complete_and_delete_task(self):
        tid = self.manager.add_task(title="Read chapter 1")
        self.assertTrue(self.manager.complete_task(tid))

        pending = self.manager.list_tasks(status="pending")
        self.assertEqual(len(pending), 0)

        all_tasks = self.manager.list_tasks(status=None)
        self.assertEqual(len(all_tasks), 1)
        self.assertEqual(all_tasks[0]["status"], "completed")

        self.assertTrue(self.manager.delete_task(tid))
        self.assertEqual(len(self.manager.list_tasks(status=None)), 0)

    def test_due_reminders(self):
        past_time = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        future_time = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

        tid1 = self.manager.add_task(title="Overdue task", due_at=past_time)
        tid2 = self.manager.add_task(title="Future task", due_at=future_time)

        due = self.manager.get_due_reminders()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["id"], tid1)

        self.manager.mark_reminded(tid1)
        due_after = self.manager.get_due_reminders()
        self.assertEqual(len(due_after), 0)


class TestFileOrganizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.work_path = Path(self.temp_dir)
        self.organizer = FileOrganizer()

        # Create sample files
        (self.work_path / "photo.png").write_text("dummy image")
        (self.work_path / "notes.txt").write_text("dummy doc")
        (self.work_path / "archive.zip").write_text("dummy zip")
        (self.work_path / ".hidden").write_text("hidden file")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_directory(self):
        scanned = self.organizer.scan_directory(self.work_path)
        self.assertEqual(len(scanned["Images"]), 1)
        self.assertEqual(len(scanned["Documents"]), 1)
        self.assertEqual(len(scanned["Archives"]), 1)
        # Hidden files should be ignored
        all_found = sum(len(files) for files in scanned.values())
        self.assertEqual(all_found, 3)

    def test_organize_directory(self):
        res = self.organizer.organize_directory(self.work_path)
        self.assertTrue(res["success"])
        self.assertEqual(res["moved_count"], 3)

        # Check moved paths
        self.assertTrue((self.work_path / "Images" / "photo.png").exists())
        self.assertTrue((self.work_path / "Documents" / "notes.txt").exists())
        self.assertTrue((self.work_path / "Archives" / "archive.zip").exists())
        self.assertTrue((self.work_path / ".hidden").exists())  # Unmoved


class TestAgentBrain(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "brain_test.db"
        self.task_mgr = TaskManager(self.db_path)
        self.file_org = FileOrganizer()
        self.brain = AgentBrain(self.task_mgr, self.file_org)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_quick_reminder_parsing(self):
        reply = self.brain.handle_quick_commands("remind me to call Mom in 15 minutes")
        self.assertIn("call Mom", reply)
        self.assertIn("15 minutes", reply)

        tasks = self.task_mgr.list_tasks(status="pending")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "call Mom")
        self.assertIsNotNone(tasks[0]["due_at"])

    def test_show_tasks_command(self):
        self.task_mgr.add_task(title="Buy coffee")
        reply = self.brain.handle_quick_commands("show my tasks")
        self.assertIn("Buy coffee", reply)

if __name__ == "__main__":
    unittest.main()
