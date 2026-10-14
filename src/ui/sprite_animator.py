"""
DeskBuddy - Sprite Sheet Animator for Chisa (and all Resonators)

Loads frame-by-frame PNG sprites for each animation state.
Replaces the procedural ChibiRig for Chisa with actual 2D art frames.
Still keeps the ChibiRig as a companion overlay for the scissors/carp.

Animation States:
  idle      - 2 frames  (idle_new_0.png, idle_new_1.png)
  happy     - 2 frames  (happy_new_0.png, happy_new_1.png)
  sleep     - 2 frames  (sleep_new_0.png, sleep_new_1.png) [fallback to idle if missing]
  walk      - 4 frames  (walk_0.png .. walk_3.png)
  climb     - 2 frames  (climb_0.png, climb_1.png)
  snip      - 3 frames  (snip_0.png, snip_1.png, snip_2.png) [deletion anim]
  sit       - 2 frames  (sit_0.png, sit_1.png)   [tab-top dangling]
"""

from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtGui import QPixmap


# Per-state frame file patterns
CHISA_FRAME_SPECS: Dict[str, List[str]] = {
    "idle":   ["idle_new_0.png", "idle_new_1.png"],
    "happy":  ["happy_new_0.png", "happy_new_1.png"],
    "sleep":  ["sleep_new_0.png", "sleep_new_1.png"],
    "walk":   ["walk_0.png", "walk_1.png", "walk_2.png", "walk_3.png"],
    "climb":  ["climb_0.png", "climb_1.png"],
    "snip":   ["snip_0.png", "snip_1.png", "snip_2.png"],
    "sit":    ["sit_0.png", "sit_1.png"],
}

# Legacy fallback specs for non-Chisa resonators (old sticker names)
LEGACY_FRAME_SPECS: Dict[str, List[str]] = {
    "idle":   ["pet_idle_0.png", "pet_idle_1.png"],
    "happy":  ["pet_happy_0.png", "pet_happy_1.png"],
    "sleep":  ["pet_sleep_0.png", "pet_sleep_1.png"],
}


class SpriteAnimator:
    """
    Loads and serves sprite frames for a resonator.
    Supports Chisa's full frame set or legacy sticker sprites for others.
    """

    def __init__(self, resonator_dir: Path, is_chisa: bool = False):
        self.resonator_dir = resonator_dir
        self.is_chisa = is_chisa
        self.frames: Dict[str, List[QPixmap]] = {}
        self._load_sprites()

    def _load_sprites(self):
        """Load all available sprite frames. Missing files are skipped gracefully."""
        specs = CHISA_FRAME_SPECS if self.is_chisa else LEGACY_FRAME_SPECS

        for state, filenames in specs.items():
            loaded = []
            for fname in filenames:
                path = self.resonator_dir / fname
                if path.exists():
                    pix = QPixmap(str(path))
                    if not pix.isNull():
                        loaded.append(pix)
            if loaded:
                self.frames[state] = loaded

        # If sleep has no frames, fall back to idle
        if "sleep" not in self.frames and "idle" in self.frames:
            self.frames["sleep"] = self.frames["idle"]

        # For Chisa: if snip has no frames, fall back to happy
        if self.is_chisa and "snip" not in self.frames and "happy" in self.frames:
            self.frames["snip"] = self.frames["happy"]

        # For Chisa: if sit has no frames, fall back to idle
        if self.is_chisa and "sit" not in self.frames and "idle" in self.frames:
            self.frames["sit"] = self.frames["idle"]

        # For Chisa: if climb has no frames, fall back to walk (rotated by paintEvent)
        if self.is_chisa and "climb" not in self.frames and "walk" in self.frames:
            self.frames["climb"] = self.frames["walk"][:2]

    def has_state(self, state: str) -> bool:
        return state in self.frames and len(self.frames[state]) > 0

    def get_frame(self, state: str, frame_idx: int) -> Optional[QPixmap]:
        """Return the QPixmap for a given state and frame index (wraps around)."""
        frames = self.frames.get(state)
        if not frames:
            frames = self.frames.get("idle", [])
        if not frames:
            return None
        return frames[frame_idx % len(frames)]

    def frame_count(self, state: str) -> int:
        return len(self.frames.get(state, []))
