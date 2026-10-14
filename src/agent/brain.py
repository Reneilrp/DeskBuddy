"""
DeskBuddy - Agent Brain
Interfaces with Antigravity (AGY) SDK or CLI for natural language understanding,
with built-in tools for Task Management and File Organization.
"""

import os
import re
import json
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from ..core.task_manager import TaskManager
from ..core.file_organizer import FileOrganizer
from ..core.resonators import get_resonator, RESONATORS

class AgentBrain:
    def __init__(self, task_manager: Optional[TaskManager] = None, file_organizer: Optional[FileOrganizer] = None, resonator_id: str = "changli"):
        self.task_manager = task_manager or TaskManager()
        self.file_organizer = file_organizer or FileOrganizer()
        self.current_resonator_id = resonator_id
        self.current_resonator = get_resonator(resonator_id)
        self._has_sdk = False
        try:
            import google.antigravity
            self._has_sdk = True
        except ImportError:
            self._has_sdk = False

    def set_resonator(self, res_id: str):
        """Switches the active Resonator personality and lore."""
        self.current_resonator_id = res_id
        self.current_resonator = get_resonator(res_id)

    def get_system_instructions(self) -> str:
        res = self.current_resonator
        return f"""
{res['personality']}
Guidelines:
1. Always keep your replies concise (1-3 sentences maximum) suitable for a cute desktop speech bubble.
2. Address the user respectfully as 'Rover'.
3. Maintain your signature voice, element ({res['element']}), and theme ({res['motif']}).
4. If the user asks for reminders or tasks, confirm that you have saved them.
5. If the user asks to tidy or organize files, confirm with your characteristic style.
"""

    def handle_quick_commands(self, text: str) -> Optional[str]:
        """
        Fast local pattern matching for common commands (instant response without API latency).
        Handles time, date, greetings, identity, tasks, reminders, and organization.
        """
        raw_text = text.strip()
        text_lower = raw_text.lower().rstrip("?!.,")
        res = self.current_resonator
        res_name = res["name"]
        now = datetime.now()

        # 1. TIME COMMANDS (e.g. "what time is it", "what's the time", "current time", "the time")
        time_triggers = [
            "what time is it", "what's the time", "whats the time", "current time",
            "tell me the time", "time please", "what time", "check time", "the time"
        ]
        if any(trigger == text_lower or text_lower.startswith(trigger) or text_lower.endswith(trigger) for trigger in time_triggers) or text_lower == "time":
            time_str = now.strftime("%I:%M %p")
            hour = now.hour
            if 5 <= hour < 12:
                flavor = "Morning has brightened your desk! Hope you have a wonderful start, Rover."
            elif 12 <= hour < 17:
                flavor = "Afternoon is in full swing! Stay hydrated and keep up the great work, Rover."
            elif 17 <= hour < 22:
                flavor = "Evening has arrived. Time to wrap up loose ends, Rover."
            else:
                flavor = "It's late into the night! Don't strain your eyes and remember to rest soon, Rover. (🌙)"
            return f"⏰ It's currently {time_str}!\n{flavor} (✨ {res_name})"

        # 2. DATE & DAY COMMANDS (e.g. "what's the date", "what day is today", "today's date")
        date_triggers = [
            "what is the date", "what's the date", "whats the date", "today's date", "todays date",
            "what day is today", "what day is it", "what day", "current date", "today's day", "whats today", "what's today"
        ]
        if any(trigger in text_lower for trigger in date_triggers) or text_lower in ("date", "today"):
            date_str = now.strftime("%A, %B %d, %Y")
            return f"📅 Today is {date_str}, Rover! (✨ {res_name})"

        # 3. DAILY GREETINGS (Time-Aware & Resonator Personality)
        # Good morning
        if any(g in text_lower for g in ["good morning", "morning rover", "morning chisa", "morning!", "gm"]):
            if now.hour < 12:
                return f"🌅 Good morning, Rover! The morning light feels wonderful today. Let's make today productive and calm! (✨ {res_name})"
            else:
                return f"☀️ Hello Rover! It's already past noon, but I hope your day is going wonderfully! (✨ {res_name})"

        # Good afternoon
        if "good afternoon" in text_lower:
            return f"☀️ Good afternoon, Rover! Make sure to take a brief stretch and rest your eyes if you've been working hard. (✨ {res_name})"

        # Good evening
        if "good evening" in text_lower:
            return f"🌆 Good evening, Rover! Another day well-spent. Ready to review what we accomplished? (✨ {res_name})"

        # Good night / Bedtime
        if any(g in text_lower for g in ["good night", "goodnight", "gn", "going to sleep", "sleep well", "sweet dreams"]):
            return f"🌙 Good night, Rover! Sleep well and restore your frequencies. I'll watch over your desktop while you dream. (💤✨ {res_name})"

        # General Greetings (Hello / Hi / Hey)
        if text_lower in ["hello", "hi", "hey", "hello there", "hi there", "hey there", "sup", "yo", "greetings"]:
            return f"\"{res['greeting']}\"\nAlways here by your side, Rover! What would you like to do? (✨)"

        # 4. IDENTITY & STATUS
        # "who are you", "what are you", "introduce yourself"
        if any(q in text_lower for q in ["who are you", "what are you", "introduce yourself", "tell me about yourself"]):
            title = res.get("title", res.get("motif", "Companion"))
            return f"✨ I am {res_name}, {title} ({res['element']} element).\n{res['personality'][:130]}...\nReady to assist you on your journey, Rover!"

        # "how are you", "how are you feeling"
        if any(q in text_lower for q in ["how are you", "how are you doing", "how do you feel", "how's it going", "hows it going"]):
            return f"I'm feeling great and always happy to be on your desktop, Rover! (◕‿◕✨) How are you holding up today?"

        # "thank you", "thanks"
        if any(t in text_lower for t in ["thank you", "thanks", "thx", "arigato", "ty"]):
            return f"You're very welcome, Rover! Assisting you is my highest honor. (💖 {res_name})"

        # 5. TASKS & REMINDERS
        # Show tasks
        if any(cmd in text_lower for cmd in [
            "show tasks", "list tasks", "what are my tasks", "view tasks", "my tasks",
            "what tasks do i have", "any tasks", "do i have tasks", "task list", "check tasks"
        ]):
            tasks = self.task_manager.list_tasks(status="pending")
            if not tasks:
                return f"You don't have any pending tasks right now, Rover! (★ω★) Enjoy your peaceful free time!"
            lines = [f"📋 Here are your pending tasks, Rover:"]
            for i, t in enumerate(tasks[:5], 1):
                due_info = f" (Due: {t['due_at']})" if t.get('due_at') else ""
                lines.append(f"{i}. {t['title']}{due_info}")
            if len(tasks) > 5:
                lines.append(f"...and {len(tasks) - 5} more in your Task Board!")
            return "\n".join(lines)

        # Reminder with relative minutes: "remind me to <task> in <X> minutes"
        in_min_match = re.search(r"remind me to (.+?) in (\d+)\s*(?:min|minute|minutes)", raw_text, re.IGNORECASE)
        if in_min_match:
            task_title = in_min_match.group(1).strip()
            minutes = int(in_min_match.group(2))
            due_time = (now + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
            self.task_manager.add_task(title=task_title, due_at=due_time)
            return f"⏰ Reminder set! I'll remind you to '{task_title}' in {minutes} minute{'s' if minutes > 1 else ''}! (•ω•)"

        # Reminder with relative hours: "remind me to <task> in <X> hours"
        in_hr_match = re.search(r"remind me to (.+?) in (\d+)\s*(?:hr|hour|hours)", raw_text, re.IGNORECASE)
        if in_hr_match:
            task_title = in_hr_match.group(1).strip()
            hours = int(in_hr_match.group(2))
            due_time = (now + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            self.task_manager.add_task(title=task_title, due_at=due_time)
            return f"⏰ Reminder set! I'll remind you to '{task_title}' in {hours} hour{'s' if hours > 1 else ''}! (•ω•)"

        # Generic task add: "remind me to <task>" or "add task <task>"
        remind_match = re.search(r"(?:remind me to|add task|todo:?|new task)\s+(.+)", raw_text, re.IGNORECASE)
        if remind_match:
            task_title = remind_match.group(1).strip()
            self.task_manager.add_task(title=task_title)
            return f"📝 Noted! Added '{task_title}' to your task list, Rover! (＾▽＾)"

        # Complete task: "complete task <id>"
        complete_match = re.search(r"(?:complete|finish|done with)\s+task\s+(\d+)", raw_text, re.IGNORECASE)
        if complete_match:
            tid = int(complete_match.group(1))
            if self.task_manager.complete_task(tid):
                return f"🎉 Awesome work! Marked task #{tid} as completed, Rover! ＼(＾▽＾)／"
            return f"Hmm, I couldn't find pending task #{tid}. (•́へ•́╬)"

        # 6. FILE ORGANIZATION
        if "organize desktop" in text_lower or "clean desktop" in text_lower or "tidy desktop" in text_lower:
            desktop_path = Path.home() / "Desktop"
            if not desktop_path.exists():
                desktop_path = Path.home()
            res_org = self.file_organizer.organize_directory(desktop_path)
            if res_org.get("success"):
                moved = res_org.get("moved_count", 0)
                if moved == 0:
                    return "Your Desktop is already in pristine harmony, Rover! No loose files found. (◕‿◕)"
                return f"{res.get('organize_quote', 'Tidied up!')}\nSorted {moved} file{'s' if moved > 1 else ''} into neat folders! (Undo available in Workspace)"
            return f"Oops! Couldn't organize desktop: {res_org.get('error', 'Unknown error')}"

        if "organize downloads" in text_lower or "clean downloads" in text_lower or "tidy downloads" in text_lower:
            dl_path = Path.home() / "Downloads"
            if dl_path.exists():
                res_org = self.file_organizer.organize_directory(dl_path)
                if res_org.get("success"):
                    moved = res_org.get("moved_count", 0)
                    if moved == 0:
                        return "Your Downloads folder is already clean and tidy, Rover! (◕‿◕)"
                    return f"Cleaned up Downloads! Sorted {moved} file{'s' if moved > 1 else ''} into neat folders! (*^▽^*)"
            return "Could not find your Downloads directory. (•́へ•́)"

        return None

    async def chat_async(self, user_message: str) -> str:
        """
        Process chat through local quick actions or through the AGY SDK/CLI.
        """
        # First check fast local commands
        quick_reply = self.handle_quick_commands(user_message)
        if quick_reply:
            return quick_reply

        # Try Google Antigravity Python SDK if available
        if self._has_sdk:
            try:
                from google.antigravity import Agent, LocalAgentConfig
                config = LocalAgentConfig(
                    system_instructions=self.get_system_instructions()
                )
                async with Agent(config) as agent:
                    response = await agent.chat(user_message)
                    tokens = []
                    async for token in response:
                        tokens.append(token)
                    reply = "".join(tokens).strip()
                    if reply:
                        return reply
            except Exception as e:
                # Fall through to CLI or fallback
                pass

        # Try agy CLI fallback
        try:
            prompt = f"{self.get_system_instructions()}\nRover: {user_message}\n{self.current_resonator['name']}:"
            proc = await asyncio.create_subprocess_exec(
                "agy", "-p", prompt,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0 and stdout:
                return stdout.decode().strip()
        except Exception:
            pass

        # Resonator-themed local conversational fallback
        return f"\"{self.current_resonator['greeting']}\" What would you like to plan or organize next, Rover?"
