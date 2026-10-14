"""
DeskBuddy - Application Coordinator
Wires together UI windows, the background agent brain worker,
the task reminder scheduler, dynamic Wuthering Waves Resonator companion switching,
micro-animations, zero-lag sticky speech bubble coupling, desktop app deletion reactions,
and Pomodoro focus partner.
"""

import re
import json
import asyncio
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication

from .core.fast_search import FastSearchEngine
from .core.task_manager import TaskManager
from .core.file_organizer import FileOrganizer
from .core.stash_manager import StashManager
from .core.clipboard_assistant import ClipboardAssistant
from .core.download_watcher import DownloadWatcher
from .core.cleanup_hunter import CleanupHunter
from .core.ergonomics_tracker import ErgonomicsTracker
from .core.resonators import (
    get_resonator, ELEMENT_COLORS, get_headpat_quote, get_pomodoro_quote
)
from .core.desktop_watcher import DesktopWatcher
from .agent.brain import AgentBrain
from .ui.pet_window import PetWindow
from .ui.speech_bubble import SpeechBubble
from .ui.tray import DeskBuddyTray
from .ui.task_dialog import TaskDialog
from .ui.resonator_dialog import ResonatorDialog
from .ui.workspace_dialog import WorkspaceDialog
from .ui.stash_dialog import StashBagDialog

CONFIG_FILE = Path.home() / ".deskbuddy" / "config.json"

class AgentChatWorker(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, brain: AgentBrain, message: str, parent=None):
        super().__init__(parent)
        self.brain = brain
        self.message = message

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.brain.chat_async(self.message))
            loop.close()
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(f"Sorry, I had a hiccup: {e}")

class DeskBuddyApp(QObject):
    def __init__(self, app: QApplication, base_dir: Path):
        super().__init__()
        self.app = app
        self.base_dir = base_dir
        self.assets_dir = base_dir / "assets"

        # Load Configuration
        self.config = self._load_config()
        self.current_resonator_id = self.config.get("resonator_id", "chisa")

        # Initialize Core Engines
        self.task_manager = TaskManager()
        self.file_organizer = FileOrganizer()
        self.brain = AgentBrain(self.task_manager, self.file_organizer, self.current_resonator_id)

        # High-Utility Companion Engines
        self.stash_manager = StashManager()
        self.clipboard_assistant = ClipboardAssistant()
        self.download_watcher = DownloadWatcher()
        self.cleanup_hunter = CleanupHunter()
        self.ergonomics_tracker = ErgonomicsTracker()

        # Initialize UI Components
        self.pet = PetWindow(self.assets_dir)
        self.speech_bubble = SpeechBubble()
        self.pet.stashed_files_supplier = self.stash_manager.get_files
        self.tray = DeskBuddyTray(self.assets_dir / "tray_icon.png")
        self.task_dialog = TaskDialog(self.task_manager)
        self.resonator_dialog = ResonatorDialog(self.current_resonator_id, self.assets_dir)
        self.workspace_dialog = WorkspaceDialog(self.task_manager, self.file_organizer, self.current_resonator_id)
        self.stash_dialog = StashBagDialog(self.stash_manager, resonator_name="Chisa")

        # Couple Speech Bubble to Pet Window for Zero-Lag Dragging
        self.pet.set_speech_bubble(self.speech_bubble)
        self.pet.free_roam_enabled = self.config.get("free_roam", True)

        # Desktop App Deletion Reaction Mode ('chomp', 'snip', 'vortex', 'off')
        self.deletion_reaction_mode = self.config.get("deletion_reaction", "off")
        self.pet.set_deletion_reaction_mode(self.deletion_reaction_mode)
        self.tray.set_deletion_reaction_mode(self.deletion_reaction_mode)

        # Real-Time Desktop Watcher
        self.desktop_watcher = DesktopWatcher()
        self.desktop_watcher.start()

        # Pomodoro Focus Partner State
        self.pomodoro_mode = "idle"  # "idle", "focus", "break"
        self.pomodoro_seconds_left = 0
        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.setInterval(1000)
        self.pomodoro_timer.timeout.connect(self._on_pomodoro_tick)

        self._current_worker = None

        self._connect_signals()
        self._setup_reminder_timer()
        self._position_initial_window()
        self._apply_companion(self.current_resonator_id, announce=False)

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"resonator_id": "chisa", "free_roam": True, "deletion_reaction": "chomp"}

    def _save_config(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self.config, indent=2), encoding="utf-8")

    def _connect_signals(self):
        # Pet Window Signals
        self.pet.clicked.connect(self.toggle_chat)
        self.pet.open_workspace_requested.connect(self.show_workspace_dialog)
        self.pet.open_tasks_requested.connect(self.show_task_dialog)
        self.pet.open_resonators_requested.connect(self.show_resonator_dialog)
        self.pet.organize_desktop_requested.connect(self.quick_tidy_desktop)
        self.pet.hide_requested.connect(self.hide_pet)
        self.pet.quit_requested.connect(self.quit_app)
        self.pet.free_roam_toggled.connect(self._on_free_roam_toggled)
        self.pet.head_pat_triggered.connect(self._on_head_pat)
        self.pet.pomodoro_toggled.connect(self._toggle_pomodoro)
        self.pet.deletion_reaction_changed.connect(self._on_deletion_reaction_mode_changed)

        # Tray Signals
        self.tray.show_requested.connect(self.show_pet)
        self.tray.hide_requested.connect(self.hide_pet)
        self.tray.toggle_requested.connect(self.toggle_pet_visibility)
        self.tray.workspace_requested.connect(self.show_workspace_dialog)
        self.tray.resonators_requested.connect(self.show_resonator_dialog)
        self.tray.tasks_requested.connect(self.show_task_dialog)
        self.tray.organize_requested.connect(self.quick_tidy_desktop)
        self.tray.quit_requested.connect(self.quit_app)
        self.tray.deletion_reaction_changed.connect(self._on_deletion_reaction_mode_changed)

        # Desktop Watcher Signals
        self.desktop_watcher.file_deleted.connect(self._on_desktop_file_deleted)

        # Speech Bubble Signals
        self.speech_bubble.message_sent.connect(self.handle_user_message)
        self.speech_bubble.expand_requested.connect(self.show_workspace_dialog)

        # Workspace Dialog Signals
        self.workspace_dialog.message_to_agent.connect(self.handle_workspace_message)

        # Resonator Dialog Signals
        self.resonator_dialog.companion_changed.connect(self._on_companion_selected)

        # Task Dialog Signals
        self.task_dialog.tasks_changed.connect(self._on_tasks_changed)

        # High-Utility Companion Signals
        self.pet.files_stashed.connect(self._on_files_stashed)
        self.pet.open_pocket_requested.connect(self.show_stash_dialog)
        self.stash_dialog.stash_changed.connect(self._on_stash_changed)
        self.clipboard_assistant.action_ready.connect(self._on_clipboard_action)
        self.download_watcher.file_downloaded.connect(self._on_download_arrived)
        self.ergonomics_tracker.reminder_triggered.connect(self._on_ergonomics_nudge)

    def _setup_reminder_timer(self):
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(5000)
        self.reminder_timer.timeout.connect(self._check_reminders)
        self.reminder_timer.start()

    def _position_initial_window(self):
        screen = self.app.primaryScreen().geometry()
        start_x = screen.right() - self.pet.width() - 40
        start_y = screen.bottom() - self.pet.height() - 60
        self.pet.move(start_x, start_y)

    def start(self):
        self.tray.show()
        self.pet.show()
        self.clipboard_assistant.start()
        self.download_watcher.start()
        self.ergonomics_tracker.start()
        res = get_resonator(self.current_resonator_id)
        # Greet on startup
        QTimer.singleShot(600, lambda: self._say(f"\"{res['greeting']}\" (Ready to assist you, Rover!)"))

    def _apply_companion(self, res_id: str, announce: bool = True):
        self.current_resonator_id = res_id
        self.config["resonator_id"] = res_id
        self._save_config()

        res = get_resonator(res_id)
        elem_colors = ELEMENT_COLORS.get(res["element"], ELEMENT_COLORS["Spectro"])

        # Update Pet Sprites
        self.pet.load_resonator_sprites(res_id)

        # Update Speech Bubble Header
        self.speech_bubble.set_speaker(res["name"], elem_colors["badge"])

        # Update Brain personality
        self.brain.set_resonator(res_id)

        # Update Workspace Dialog header & theme
        self.workspace_dialog.set_resonator(res_id)

        # Update Stash Bag Dialog
        self.stash_dialog.resonator_name = res["name"]
        self.stash_dialog.refresh_list()

        if announce:
            self.pet.set_state("happy", revert_seconds=4)
            self._say(f"✨ Companion switched to {res['name']}!\n\"{res['greeting']}\"")

    def show_resonator_dialog(self):
        self.resonator_dialog.current_res_id = self.current_resonator_id
        self.resonator_dialog._populate_list()
        self.resonator_dialog.show()
        self.resonator_dialog.raise_()
        self.resonator_dialog.activateWindow()

    def _on_companion_selected(self, res_id: str):
        self._apply_companion(res_id, announce=True)

    def _say(self, text: str, auto_hide_seconds: int = 15):
        self.speech_bubble.say(text, auto_hide_seconds)
        self.speech_bubble.update_position(self.pet.frameGeometry())

    def _on_free_roam_toggled(self, enabled: bool):
        self.config["free_roam"] = enabled
        self._save_config()
        if enabled:
            self._say("🐾 Free Roam Mode enabled! I'll wander and scale your windows! (◕‿◕)", auto_hide_seconds=4)
        else:
            self._say("🐾 Free Roam Mode disabled. I'll stay right here with you! (✨)", auto_hide_seconds=4)

    def _on_head_pat(self):
        quote = get_headpat_quote(self.current_resonator_id)
        self._say(quote, auto_hide_seconds=5)

    def _on_deletion_reaction_mode_changed(self, mode: str):
        self.deletion_reaction_mode = mode
        self.config["deletion_reaction"] = mode
        self._save_config()

        # Synchronize both UI components
        if self.pet.deletion_reaction_mode != mode:
            self.pet.deletion_reaction_mode = mode
        if self.tray.deletion_reaction_mode != mode:
            self.tray.deletion_reaction_mode = mode

        labels = {
            "chomp": "Option 1: Paper-Carp Chomp! (Devours deleted apps 🐠)",
            "snip": "Option 2: Scissor Shredder! (Cuts apps into confetti ✂️)",
            "vortex": "Option 3: Void Vortex! (Universal black hole 🕳️)",
            "off": "Disabled (No reaction)"
        }
        self._say(f"🗑️ Deletion reaction set to: {labels.get(mode, mode)}", auto_hide_seconds=4)

    def _on_desktop_file_deleted(self, file_name: str):
        if self.deletion_reaction_mode == "off":
            return

        self.pet.show()
        self.pet.play_deletion_animation(self.deletion_reaction_mode, file_name)

        if self.deletion_reaction_mode == "chomp":
            msg = f"Om nom nom! Chisa's paper-carp devoured '{file_name}'! Clean desk, happy tummy! (◕‿◕ 🐠)"
        elif self.deletion_reaction_mode == "snip":
            msg = f"Snip snip! '{file_name}' has been trimmed away into lovely kirigami paper confetti! (✂️✨)"
        elif self.deletion_reaction_mode == "vortex":
            if self.current_resonator_id == "chisa":
                msg = f"Whoosh! '{file_name}' vanished into the paper-cut rift! Desktop clean! (🕳️)"
            else:
                res = get_resonator(self.current_resonator_id)
                msg = f"Whoosh! '{file_name}' vanished into the void! {res['organize_quote']} (🕳️✨)"
        else:
            msg = f"Goodbye, '{file_name}'! Clean desktop! (✨)"

        self._say(msg, auto_hide_seconds=6)

    def _toggle_pomodoro(self):
        if self.pomodoro_mode == "idle":
            self.pomodoro_mode = "focus"
            self.pomodoro_seconds_left = 25 * 60
            self.pet.pomodoro_active = True
            self.pomodoro_timer.start()
            self.speech_bubble.set_status_badge("25:00 Focus", "#FF8B77")
            quote = get_pomodoro_quote(self.current_resonator_id, "start")
            self._say(quote, auto_hide_seconds=8)
        else:
            self.pomodoro_mode = "idle"
            self.pet.pomodoro_active = False
            self.pomodoro_timer.stop()
            self.speech_bubble.set_status_badge("")
            self._say("Pomodoro session paused. Rest easy, Rover! (☕)", auto_hide_seconds=4)

    def _on_pomodoro_tick(self):
        self.pomodoro_seconds_left -= 1
        mins = max(0, self.pomodoro_seconds_left) // 60
        secs = max(0, self.pomodoro_seconds_left) % 60
        time_str = f"{mins:02d}:{secs:02d}"

        if self.pomodoro_mode == "focus":
            self.speech_bubble.set_status_badge(f"{time_str} Focus", "#E53E3E")
            if self.pomodoro_seconds_left <= 0:
                self.pomodoro_mode = "break"
                self.pomodoro_seconds_left = 5 * 60
                self.pet.set_state("happy", revert_seconds=8)
                quote = get_pomodoro_quote(self.current_resonator_id, "complete")
                self._say(quote, auto_hide_seconds=15)
                self.tray.show_message("DeskBuddy Pomodoro", "25-min focus completed! Take a 5-minute break!")
        elif self.pomodoro_mode == "break":
            self.speech_bubble.set_status_badge(f"{time_str} Break", "#38A169")
            if self.pomodoro_seconds_left <= 0:
                self.pomodoro_mode = "idle"
                self.pet.pomodoro_active = False
                self.pomodoro_timer.stop()
                self.speech_bubble.set_status_badge("")
                self._say("Break time is over, Rover! Ready for our next session whenever you are! (✨)", auto_hide_seconds=8)
                self.tray.show_message("DeskBuddy Pomodoro", "Break time is over! Ready to focus?")

    def toggle_chat(self):
        if self.speech_bubble.isVisible():
            self.speech_bubble.hide_bubble()
        else:
            res = get_resonator(self.current_resonator_id)
            self._say(f"\"{res['greeting']}\" What's on your mind, Rover?", auto_hide_seconds=0)

    def toggle_pet_visibility(self):
        if self.pet.isVisible():
            self.hide_pet()
        else:
            self.show_pet()

    def show_pet(self):
        self.pet.show()
        self.pet.set_state("happy", revert_seconds=2)
        res = get_resonator(self.current_resonator_id)
        self._say(f"I'm here by your side, Rover. (✨ {res['name']})", auto_hide_seconds=5)

    def hide_pet(self):
        self.speech_bubble.hide_bubble()
        self.pet.hide()
        res = get_resonator(self.current_resonator_id)
        self.tray.show_message("DeskBuddy", f"{res['name']} is resting in your system tray! Click to summon anytime.")

    def show_task_dialog(self):
        self.task_dialog.refresh_tasks()
        self.task_dialog.show()
        self.task_dialog.raise_()
        self.task_dialog.activateWindow()

    def quick_tidy_desktop(self):
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home()
        res_data = get_resonator(self.current_resonator_id)
        res = self.file_organizer.organize_directory(desktop)
        if res.get("success"):
            moved = res.get("moved_count", 0)
            if moved > 0:
                msg = f"{res_data['organize_quote']}\n(Tidied {moved} files into folders!)"
            else:
                msg = f"Your desktop is already in pristine harmony, Rover. No loose clutter found."
        else:
            msg = f"Couldn't organize desktop: {res.get('error')}"
        self.pet.set_state("happy", revert_seconds=3)
        self._say(msg)

    def show_workspace_dialog(self):
        self.workspace_dialog.refresh_tasks()
        self.workspace_dialog.show()
        self.workspace_dialog.raise_()
        self.workspace_dialog.activateWindow()

    def handle_workspace_message(self, message: str):
        res = get_resonator(self.current_resonator_id)
        worker = AgentChatWorker(self.brain, message)
        worker.response_ready.connect(lambda reply: self._on_workspace_agent_reply(res["name"], reply))
        worker.error_occurred.connect(lambda err: self.workspace_dialog.append_message(res["name"], f"⚠️ {err}"))
        worker.start()
        self._workspace_worker = worker

    def _on_workspace_agent_reply(self, res_name: str, reply: str):
        self.workspace_dialog.append_message(res_name, reply)
        # Also briefly acknowledge on the pet bubble if pet is active
        self.pet.set_state("happy", revert_seconds=3)

    def handle_user_message(self, message: str):
        msg_clean = message.strip()
        msg_lower = msg_clean.lower()

        # Quick Speed Grep Search command
        if msg_lower.startswith("find ") or msg_lower.startswith("search ") or msg_lower.startswith("grep "):
            parts = msg_clean.split(maxsplit=1)
            query = parts[1].strip() if len(parts) > 1 else ""
            if query:
                self.show_workspace_dialog()
                self.workspace_dialog.open_search_tab(query)
                self.pet.set_state("happy", revert_seconds=3)
                self._say(f"⚡ Speed Grep launched for '{query}' in our Workspace!")
                return

        # Selective extension/file gathering rule
        # e.g. "gather all png to Screenshots", "organize png", "collect all pdf"
        gather_match = re.search(r"(?:gather|organize|collect|move)\s+(?:all\s+)?(?:\*\.)?([a-zA-Z0-9]+)\s*(?:files?)?(?:\s+(?:to|into|in)\s+([a-zA-Z0-9_\- ]+))?", msg_lower)
        if gather_match and gather_match.group(1) not in ("desktop", "download", "downloads", "files", "everything"):
            ext = gather_match.group(1).lower()
            dest = gather_match.group(2).strip() if gather_match.group(2) else f"{ext.upper()} Files"
            self.show_workspace_dialog()
            self.workspace_dialog.open_organizer_tab(rule="extension", filter_text=f".{ext}", dest_folder=dest)
            self.pet.set_state("happy", revert_seconds=3)
            self._say(f"🎯 Selective rule ready: gathering all .{ext} files into '{dest}'! Review the preview and click 'Tidy Selected Files'.")
            return

        # Quick File Organizer command (general)
        if any(kw in msg_lower for kw in ("organize download", "tidy download", "organize desktop", "clean download", "organize files")):
            self.show_workspace_dialog()
            self.workspace_dialog.open_organizer_tab()
            self.pet.set_state("happy", revert_seconds=3)
            self._say("📁 Opened Smart File Organizer Studio! Review the dry-run moves and rules whenever you're ready.")
            return

        # Direct workspace modal request
        if msg_lower in ("workspace", "open workspace", "open modal", "expand"):
            self.show_workspace_dialog()
            self._say("🖥️ Opened Companion Workspace! (Press ⤢ anytime to expand!)")
            return

        # Small talk & General queries via background brain worker
        self._current_worker = AgentChatWorker(self.brain, message)
        self._current_worker.response_ready.connect(self._on_agent_reply)
        self._current_worker.error_occurred.connect(self._on_agent_error)
        self._current_worker.start()

    def _on_agent_reply(self, reply: str):
        self.pet.set_state("happy", revert_seconds=3)
        res = get_resonator(self.current_resonator_id)

        # If conversation response is extensive (> 220 chars or multiple paragraphs),
        # dynamically mirror the full conversation into the half-screen workspace!
        if len(reply) > 220 or reply.count("\n") >= 3:
            self.workspace_dialog.append_message(res["name"], reply)
            preview = reply.split("\n")[0][:140] + "..." if len(reply) > 140 else reply
            self._say(f"{preview}\n\n💡 (Detailed response in Workspace — click ⤢ to expand)")
        else:
            self._say(reply)

    def _on_agent_error(self, err: str):
        self._say(err)

    def _check_reminders(self):
        due = self.task_manager.get_due_reminders()
        for task in due:
            self.task_manager.mark_reminded(task["id"])
            title = task["title"]
            res = get_resonator(self.current_resonator_id)
            self.pet.show()
            self.pet.set_state("happy", revert_seconds=6)
            msg = f"⏰ {res['reminder_quote']}\nTask: '{title}'!"
            self._say(msg, auto_hide_seconds=20)
            self.tray.show_message(f"DeskBuddy ({res['name']})", f"Reminder: {title}")

    def _on_tasks_changed(self):
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # High-Utility Companion Handlers (Pocket, Clipboard, Downloads, Ergonomics)
    # ─────────────────────────────────────────────────────────────────────────

    def show_stash_dialog(self):
        self.stash_dialog.refresh_list()
        self.stash_dialog.show()
        self.stash_dialog.raise_()
        self.stash_dialog.activateWindow()

    def _on_stash_changed(self):
        files = self.stash_manager.get_files()
        self.pet.update_stashed_files(files)
        if not files:
            self.speech_bubble.clear_action_chips()

    def _on_files_stashed(self, paths: list):
        self.stash_manager.add_files(paths)
        files = self.stash_manager.get_files()
        self.pet.update_stashed_files(files)
        summary = self.stash_manager.summary()
        self.pet.set_state("happy", revert_seconds=4)
        actions = [
            ("🎒 Open Bag", self.show_stash_dialog),
            ("✕ Empty Pocket", self._clear_stash)
        ]
        self.speech_bubble.show_action_chip(
            f"🎒 {summary}\n💡 Tip: Drag the 🎒 badge or Shift-Drag me into Discord/Chrome in 1 drag!",
            actions=actions,
            auto_hide_seconds=15
        )

    def _clear_stash(self):
        self.stash_manager.clear()
        self.pet.update_stashed_files([])
        self.stash_dialog.refresh_list()
        self._say("Pocket emptied, Rover! Ready for new files. (✨)", auto_hide_seconds=3)

    def _on_clipboard_action(self, payload: dict):
        action_type = payload.get("type")
        display_text = payload.get("display_text", "")
        action_label = payload.get("action_label", "Action")
        action_val = payload.get("action_value", "")

        def execute_clip_action():
            if action_type in ("math", "color", "json"):
                QApplication.clipboard().setText(str(action_val))
                self._say(f"📋 Copied '{action_val[:40]}' to clipboard!", auto_hide_seconds=3)
            elif action_type == "image_url":
                saved = ClipboardAssistant.save_image_url(action_val)
                if saved:
                    self._say(f"💾 Saved image to 'Downloads/{saved.name}'!", auto_hide_seconds=4)
                else:
                    self._say("Couldn't download image.", auto_hide_seconds=3)

        self.speech_bubble.show_action_chip(
            display_text,
            actions=[(action_label, execute_clip_action), ("✕ Dismiss", self.speech_bubble.hide_bubble)],
            auto_hide_seconds=9
        )

    def _on_download_arrived(self, info: dict):
        path = info.get("path")
        category = info.get("category", "Others")
        name = info.get("name")
        size_str = info.get("size_formatted")

        def move_to_cat():
            p = Path(path)
            if p.exists():
                cat_dir = p.parent / category
                cat_dir.mkdir(parents=True, exist_ok=True)
                dest = cat_dir / p.name
                import shutil
                shutil.move(str(p), str(dest))
                self._say(f"📁 Moved '{name}' into '{category}/'!", auto_hide_seconds=4)

        actions = [
            ("📂 Reveal", lambda: FastSearchEngine.reveal_in_explorer(path)),
            (f"📁 Move to {category}", move_to_cat),
            ("🚀 Open", lambda: FastSearchEngine.open_file(path))
        ]
        self.speech_bubble.show_action_chip(
            f"📥 Downloaded: **{name}** ({size_str})",
            actions=actions,
            auto_hide_seconds=12
        )

    def _on_ergonomics_nudge(self, nudge: dict):
        msg = nudge.get("message")
        def log_water():
            glasses = self.ergonomics_tracker.add_water_glass()
            self._say(f"💧 Logged! You've had {glasses} glass{'es' if glasses > 1 else ''} of water today, Rover! (✨)", auto_hide_seconds=4)

        actions = [
            ("💧 +1 Glass of Water", log_water),
            ("🧘 Rest Eyes (Dismiss)", self.speech_bubble.hide_bubble)
        ]
        self.pet.set_state("happy", revert_seconds=4)
        self.speech_bubble.show_action_chip(msg, actions=actions, auto_hide_seconds=15)

    def quit_app(self):
        self.app.quit()
