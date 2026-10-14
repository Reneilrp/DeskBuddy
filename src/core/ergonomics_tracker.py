"""
DeskBuddy - Ergonomics & Health Focus Partner
Promotes healthy desk habits without irritating interruptions:
1. 20-20-20 Eye Strain Reminder: Every 45 minutes of active desk time,
   prompts to look 20 feet away for 20 seconds.
2. Hydration Partner: Tracks daily glasses of water.
3. Posture & Stretch Nudges: Plays stretch animation on companion.
"""

import time
from typing import Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class ErgonomicsTracker(QObject):
    reminder_triggered = pyqtSignal(dict)  # type: "eye_strain" | "posture" | "hydration", message, water_count

    def __init__(self, break_interval_minutes: int = 45, parent=None):
        super().__init__(parent)
        self.break_interval_seconds = break_interval_minutes * 60
        self.active_seconds = 0
        self.last_activity_time = time.time()
        self.water_glasses = 0
        self.session_count = 0

        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # 1-second tick
        self.timer.timeout.connect(self._on_tick)

    def start(self):
        self.active_seconds = 0
        self.last_activity_time = time.time()
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def note_activity(self):
        """Called on user interaction to prove active presence."""
        now = time.time()
        # If user was away for more than 10 minutes, reset active counter
        if now - self.last_activity_time > 600:
            self.active_seconds = 0
        self.last_activity_time = now

    def add_water_glass(self) -> int:
        self.water_glasses += 1
        return self.water_glasses

    def get_water_glasses(self) -> int:
        return self.water_glasses

    def _on_tick(self):
        now = time.time()
        # If inactive for > 10 mins, don't increment active screen time
        if now - self.last_activity_time > 600:
            return

        self.active_seconds += 1

        if self.active_seconds >= self.break_interval_seconds:
            self.active_seconds = 0
            self.session_count += 1
            self._trigger_nudge()

    def _trigger_nudge(self):
        messages = [
            "💧 Rover, time for the 20-20-20 rule! Look 20 feet away for 20 seconds, and drink a sip of water!",
            "🧘 Take a gentle breath, roll your shoulders back, and stretch your neck, Rover! (✨)",
            "👀 Rest your eyes for a quick moment! Staring at the screen too long dampens your frequency resonance."
        ]
        msg = messages[(self.session_count - 1) % len(messages)]
        self.reminder_triggered.emit({
            "message": msg,
            "session_count": self.session_count,
            "water_glasses": self.water_glasses
        })
