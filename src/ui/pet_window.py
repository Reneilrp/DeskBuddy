"""
DeskBuddy - Main Transparent Desktop Pet Window
Renders the animated sprite, handles drag-and-drop movement,
sine-wave idle breathing, natural blinking, squish-and-stretch click bounce,
desktop roaming, active window climbing, tab walking, drop gravity physics,
and interactive head-patting.

For Chisa: Uses SpriteAnimator with real 2D frame PNGs + ChibiRig overlay
           for the scissors & paper-carp companion.
For others: Uses legacy sticker sprites via SpriteAnimator.
"""

import math
import random
import time
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QRect, QRectF, QMimeData, QUrl
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QApplication, QPushButton
from PyQt6.QtGui import QPixmap, QAction, QCursor, QTransform, QPainter, QDrag

from .speech_bubble import SpeechBubble
from .chibi_rig import ChibiRig
from .sprite_animator import SpriteAnimator
from ..core.window_detector import WindowDetector


# Walk animation runs at ~8 FPS → advance frame every 4 ticks at 30FPS
_WALK_TICKS_PER_FRAME   = 4
# Climb animation at ~6 FPS
_CLIMB_TICKS_PER_FRAME  = 5
# Sit dangle at ~4 FPS (gentle)
_SIT_TICKS_PER_FRAME    = 7
# Snip rapid fire at ~10 FPS
_SNIP_TICKS_PER_FRAME   = 3


class DraggableBagBadge(QPushButton):
    """
    Floating pocket badge docked directly onto the companion.
    - Click: Opens the Stash Bag Dialog.
    - Drag: Directly initiates native OS file drag (QDrag) in 1 fluid motion without clicking buttons!
    """
    bag_clicked = pyqtSignal()
    drag_initiated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_start_pos = None
        self.files_supplier = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("🎒 Stashed Files\n• Click: Open Bag Dialog\n• Drag: 1-drag drop into Discord, Browser, or Explorer!")
        self.setStyleSheet("""
            QPushButton {
                background: #E53E3E;
                color: #FFFFFF;
                border: 2px solid #FFFFFF;
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
                padding: 1px 6px;
            }
            QPushButton:hover {
                background: #C53030;
            }
        """)
        self.hide()

    def set_file_count(self, count: int):
        if count <= 0:
            self.hide()
        else:
            self.setText(f"🎒 {count}")
            self.adjustSize()
            self.show()
            self.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_start_pos:
            dist = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                files = self.files_supplier() if self.files_supplier else []
                if files:
                    self.drag_initiated.emit()
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in files])
                    drag.setMimeData(mime)
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                    self.drag_start_pos = None
                    drag.exec(Qt.DropAction.CopyAction)
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drag_start_pos and event.button() == Qt.MouseButton.LeftButton:
            dist = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
            if dist < QApplication.startDragDistance():
                self.bag_clicked.emit()
        self.drag_start_pos = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mouseReleaseEvent(event)


class PetWindow(QWidget):
    clicked = pyqtSignal()
    open_workspace_requested = pyqtSignal()
    open_tasks_requested = pyqtSignal()
    open_resonators_requested = pyqtSignal()
    organize_desktop_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    open_pocket_requested = pyqtSignal()

    # Signals
    position_changed = pyqtSignal(QRect)
    free_roam_toggled = pyqtSignal(bool)
    pomodoro_toggled = pyqtSignal()
    head_pat_triggered = pyqtSignal()
    deletion_reaction_changed = pyqtSignal(str)
    files_stashed = pyqtSignal(list)

    def __init__(self, assets_dir: Path, parent=None):
        super().__init__(parent)
        self.assets_dir = assets_dir
        self.drag_position = QPoint()
        self.mouse_press_pos = QPoint()
        self.is_dragging = False
        self.stashed_files: List[Path] = []
        self.speech_bubble: Optional[SpeechBubble] = None

        # Animation state machine
        # States: 'idle', 'happy', 'sleep', 'walk', 'climb', 'sit', 'snip'
        self.current_state = "idle"
        self.current_frame = 0
        self.current_resonator_id = "default"

        # Directional Facing & Tilting
        self.facing_direction = 1   # 1: right, -1: left (mirrored)
        self.tilt_angle = 0.0       # Degrees

        # Animation & Physics Variables
        self.tick_count = 0
        self.anim_tick = 0          # Per-state animation clock
        self.bounce_step = 0
        self.bounce_scale_x = 1.0
        self.bounce_scale_y = 1.0

        # Snip deletion animation state
        self._snipping = False
        self._snip_ticks = 0
        self._snip_frame_dir = 1    # ping-pong 0→1→2→1→0

        # Gravity Physics
        self.gravity_active = False
        self.gravity_velocity = 0.0

        # Window & Tab Surface Detector
        self.window_detector = WindowDetector()
        self.cached_active_window: Optional[QRect] = None

        # Free Roam & Climbing State Machine
        self.free_roam_enabled = True  # Enabled by default for active pet behavior
        self.roam_mode = "idle"        # "idle", "walk_ground", "climb_wall", "walk_tabs"
        self.roam_timer = 90
        self.roam_direction = 1        # 1: right, -1: left
        self.roam_step_count = 0
        self.climb_wall_side = "left"  # "left" or "right"

        # Head-Patting Gesture Tracking
        self.head_pat_strokes = 0
        self.last_stroke_time = 0.0
        self.last_stroke_x = 0
        self.last_stroke_dir = 0

        # Pomodoro State
        self.pomodoro_active = False
        self.pomodoro_remaining_sec = 0

        # Deletion Reaction Mode ('chomp', 'snip', 'vortex', 'off')
        self.deletion_reaction_mode = "chomp"

        # Sprite Animator (real 2D frames for Chisa, legacy stickers for others)
        self.sprite_animator: Optional[SpriteAnimator] = None

        # Chibi Layered Puppet Rig (scissors + paper-carp overlay ONLY — no sticker body)
        self.chibi_rig: Optional[ChibiRig] = None

        # Legacy sprites dict (for non-Chisa fallback path via _update_sprite)
        self.sprites: Dict[str, List[QPixmap]] = {}

        self._setup_window()
        self._setup_ui()
        self._setup_timers()
        self.load_resonator_sprites("chisa")

    def set_speech_bubble(self, bubble: SpeechBubble):
        """Attaches speech bubble for synchronous real-time dragging."""
        self.speech_bubble = bubble

    # ─────────────────────────────────────────────────────────────────────────
    # Sprite & Rig Loading
    # ─────────────────────────────────────────────────────────────────────────

    def load_resonator_sprites(self, res_id: str):
        """Swaps active pet sprites/animator to the selected Resonator."""
        res_dir = self.assets_dir / "resonators" / res_id
        self.current_resonator_id = res_id

        is_chisa = (res_id == "chisa")

        if res_dir.exists():
            self.sprite_animator = SpriteAnimator(res_dir, is_chisa=is_chisa)
        else:
            self.sprite_animator = None

        # Chibi rig is kept for ALL resonators (renders scissors+carp overlay)
        # but only when using the Chisa sprite animator (has the right frames)
        if is_chisa and res_dir.exists():
            self.chibi_rig = ChibiRig(res_dir)
        else:
            self.chibi_rig = None

        # Legacy sprites fallback (for _update_sprite when not using animator)
        if res_dir.exists():
            self.sprites = self._build_legacy_sprites(res_dir)
        else:
            self.sprites = self._build_legacy_sprites(self.assets_dir)

        self.current_state = "idle"
        self.current_frame = 0
        self.anim_tick = 0
        self._update_sprite()

    def _build_legacy_sprites(self, base_dir: Path) -> Dict[str, List[QPixmap]]:
        def safe_pix(path):
            p = QPixmap(str(path))
            return p if not p.isNull() else QPixmap()

        return {
            "idle": [safe_pix(base_dir / "pet_idle_0.png"), safe_pix(base_dir / "pet_idle_1.png")],
            "happy": [safe_pix(base_dir / "pet_happy_0.png"), safe_pix(base_dir / "pet_happy_1.png")],
            "sleep": [safe_pix(base_dir / "pet_sleep_0.png"), safe_pix(base_dir / "pet_sleep_1.png")],
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Qt Window Setup
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(140, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def _setup_ui(self):
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(0, 4, 0, 4)
        self.sprite_label = QLabel(self)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_main.addWidget(self.sprite_label)

        # Floating Draggable Pocket Badge
        self.bag_badge = DraggableBagBadge(self)
        self.bag_badge.files_supplier = lambda: self.stashed_files
        self.bag_badge.bag_clicked.connect(self.open_pocket_requested.emit)
        self.bag_badge.move(self.width() - 48, 6)

    def update_stashed_files(self, files: List[Path]):
        self.stashed_files = files
        self.bag_badge.set_file_count(len(files))
        if len(files) > 0:
            bw = self.bag_badge.width()
            self.bag_badge.move(max(0, self.width() - bw - 6), 6)
            self.bag_badge.raise_()

    def _setup_timers(self):
        # 30 FPS tick timer (33ms) for breathing, bounce, gravity, roaming, & climbing
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(33)
        self.tick_timer.timeout.connect(self._on_tick)
        self.tick_timer.start()

        # Natural Blink & Expression Timer
        self.blink_timer = QTimer(self)
        self.blink_timer.setSingleShot(True)
        self.blink_timer.timeout.connect(self._trigger_blink)
        self._schedule_next_blink()

        # Cheerful Frame Flip Timer for Happy state
        self.happy_anim_timer = QTimer(self)
        self.happy_anim_timer.setInterval(280)
        self.happy_anim_timer.timeout.connect(self._on_happy_frame_tick)

    # ─────────────────────────────────────────────────────────────────────────
    # Paint — renders real 2D frames + scissors/carp overlay
    # ─────────────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.sprite_animator is None:
            return  # legacy path handled via QLabel

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2

        # Choose the correct animation state for the current roam mode
        draw_state = self._resolve_draw_state()

        pix = self.sprite_animator.get_frame(draw_state, self.current_frame)
        if pix is None or pix.isNull():
            return

        # Scale to fit the widget (200x200 source → 140x140 display with squish)
        target_w = max(1, int(w * self.bounce_scale_x))
        target_h = max(1, int(h * self.bounce_scale_y))
        scaled = pix.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Build transform: center → face direction → tilt
        painter.save()
        painter.translate(cx, cy)
        if self.facing_direction == -1:
            painter.scale(-1.0, 1.0)
        if abs(self.tilt_angle) > 0.1:
            painter.rotate(self.tilt_angle)

        # For climbing: rotate sprite 90° so Chisa is sideways on the wall
        if draw_state == "climb":
            painter.rotate(-90 if self.climb_wall_side == "left" else 90)

        # Draw the centered sprite
        painter.drawPixmap(
            int(-scaled.width() / 2),
            int(-scaled.height() / 2),
            scaled
        )
        painter.restore()

        # Overlay: paper-carp companion (ChibiRig, no duplicate body/boots)
        if self.chibi_rig:
            is_walking  = draw_state in ("walk", "sit")
            is_climbing = draw_state == "climb"
            self.chibi_rig.update_physics(is_walking, is_climbing)
            self.chibi_rig.render(
                painter=painter,
                rect=QRectF(self.rect()),
                current_state=draw_state,
                current_frame=self.current_frame,
                facing_direction=self.facing_direction,
                body_tilt=self.tilt_angle,
                bounce_scale_x=self.bounce_scale_x,
                bounce_scale_y=self.bounce_scale_y,
                draw_boots=False,
                draw_body=False,
                draw_scissors=False,
                draw_companion=True,
            )

    def _resolve_draw_state(self) -> str:
        """Map roam mode + animation state to the correct sprite state key."""
        if self._snipping:
            return "snip"
        if self.roam_mode == "walk_ground":
            return "walk"
        if self.roam_mode == "climb_wall":
            return "climb"
        if self.roam_mode == "walk_tabs":
            return "sit"
        # Dragging: use idle
        if self.is_dragging:
            return "idle"
        return self.current_state  # idle / happy / sleep

    # ─────────────────────────────────────────────────────────────────────────
    # Animation Frame Advancement
    # ─────────────────────────────────────────────────────────────────────────

    def _advance_anim_frame(self, state: str):
        """Advance current_frame based on the active state's frame rate."""
        self.anim_tick += 1
        ticks_needed = {
            "walk":  _WALK_TICKS_PER_FRAME,
            "climb": _CLIMB_TICKS_PER_FRAME,
            "sit":   _SIT_TICKS_PER_FRAME,
            "snip":  _SNIP_TICKS_PER_FRAME,
        }.get(state, 10)  # default slow for idle/happy/sleep (managed by blink_timer)

        if self.anim_tick >= ticks_needed:
            self.anim_tick = 0
            if self.sprite_animator:
                n = self.sprite_animator.frame_count(state)
                if n > 0:
                    self.current_frame = (self.current_frame + 1) % n
            elif self.sprites.get(state):
                n = len(self.sprites[state])
                self.current_frame = (self.current_frame + 1) % n

    def _schedule_next_blink(self):
        if self.current_state == "idle":
            delay_ms = random.randint(3200, 5800)
            self.blink_timer.start(delay_ms)

    def _trigger_blink(self):
        if self.current_state == "idle" and not self.is_dragging:
            self.current_frame = 1
            self._update_sprite()
            QTimer.singleShot(220, self._finish_blink)
        else:
            self._schedule_next_blink()

    def _finish_blink(self):
        if self.current_state == "idle":
            self.current_frame = 0
            self._update_sprite()
        self._schedule_next_blink()

    def _on_happy_frame_tick(self):
        if self.current_state == "happy":
            if self.sprite_animator and self.sprite_animator.has_state("happy"):
                n = self.sprite_animator.frame_count("happy")
                self.current_frame = (self.current_frame + 1) % n
            elif self.sprites.get("happy"):
                n = len(self.sprites["happy"])
                self.current_frame = (self.current_frame + 1) % n
            self._update_sprite()

    # ─────────────────────────────────────────────────────────────────────────
    # Main Tick
    # ─────────────────────────────────────────────────────────────────────────

    def _on_tick(self):
        self.tick_count += 1

        # Periodic active window poll (every ~1 sec / 30 ticks)
        if self.tick_count % 30 == 0:
            self.cached_active_window = self.window_detector.get_active_window_rect()

        # 1. Sine-Wave Idle Breathing (when not climbing/walking/falling)
        bob_y = 0
        if not self.is_dragging and not self.gravity_active and self.roam_mode == "idle":
            if self.current_state == "idle":
                bob_y = int(round(math.sin(self.tick_count * 0.12) * 2.5))
            elif self.current_state == "sleep":
                bob_y = int(round(math.sin(self.tick_count * 0.06) * 1.5))
            elif self.current_state == "happy":
                bob_y = int(round(math.sin(self.tick_count * 0.28) * 3.5))

        # 2. Click Squish-and-Stretch Animation Update
        if self.bounce_step > 0:
            self._update_bounce()

        # Apply breathing margin offset
        top_m = max(0, 4 + bob_y)
        bot_m = max(0, 4 - bob_y)
        self.layout_main.setContentsMargins(0, top_m, 0, bot_m)

        # 3. Drop Gravity Settling
        if self.gravity_active:
            self._update_gravity()

        # 4. Roaming, Window Climbing, & Tab Walking Logic
        if self.free_roam_enabled and not self.is_dragging and not self.gravity_active:
            self._update_roaming_and_climbing()

        # 5. Advance sprite frame for motion states
        draw_state = self._resolve_draw_state()
        if draw_state in ("walk", "climb", "sit", "snip"):
            self._advance_anim_frame(draw_state)

        # 6. Repaint (sprite_label is hidden when using sprite_animator)
        if self.sprite_animator:
            self.update()   # triggers paintEvent
        else:
            self._update_sprite()

    def _update_bounce(self):
        curves = [
            (1.10, 0.88),  # Squish down
            (1.12, 0.86),
            (1.06, 0.94),
            (0.95, 1.08),  # Rebound stretch
            (0.93, 1.10),
            (0.97, 1.04),
            (1.02, 0.98),  # Settle
            (1.01, 0.99),
            (1.00, 1.00),
        ]
        if 1 <= self.bounce_step <= len(curves):
            sx, sy = curves[self.bounce_step - 1]
            self.bounce_scale_x = sx
            self.bounce_scale_y = sy
            if not self.sprite_animator:
                self._update_sprite()
            self.bounce_step += 1
        else:
            self.bounce_step = 0
            self.bounce_scale_x = 1.0
            self.bounce_scale_y = 1.0
            if not self.sprite_animator:
                self._update_sprite()

    def trigger_bounce(self):
        """Starts squish-and-stretch tactile click bounce."""
        self.bounce_step = 1

    def _update_gravity(self):
        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        ground_y = screen_geom.bottom() - self.height() - 20

        # Check if landing on active window tab strip
        target_y = ground_y
        if self.cached_active_window:
            win = self.cached_active_window
            tab_y = win.top() - self.height() + 10
            if win.left() - 20 <= self.x() <= win.right() - self.width() + 20:
                if self.y() < tab_y + 10:
                    target_y = tab_y

        self.gravity_velocity += 1.8
        new_y = self.y() + int(self.gravity_velocity)

        if new_y >= target_y:
            new_y = target_y
            if abs(self.gravity_velocity) > 4.0:
                self.gravity_velocity = -self.gravity_velocity * 0.32
                self.trigger_bounce()
            else:
                self.gravity_active = False
                self.gravity_velocity = 0.0
                self.trigger_bounce()
                if self.cached_active_window and abs(target_y - (self.cached_active_window.top() - self.height() + 10)) < 5:
                    self.roam_mode = "walk_tabs"
                    self.roam_timer = 90
                else:
                    self.roam_mode = "idle"
                    self.roam_timer = 90

        self.move(self.x(), new_y)
        self._notify_position_change()

    def _update_roaming_and_climbing(self):
        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        win = self.cached_active_window

        if self.roam_mode == "idle":
            self.tilt_angle = 0.0
            self.roam_timer -= 1
            if self.roam_timer <= 0:
                self.roam_mode = "walk_ground"
                self.roam_direction = 1 if random.random() > 0.5 else -1
                self.facing_direction = self.roam_direction
                self.roam_step_count = random.randint(40, 120)
                self.current_frame = 0
                self.anim_tick = 0

        elif self.roam_mode == "walk_ground":
            self.facing_direction = self.roam_direction
            # Gentle walking waddle tilt
            self.tilt_angle = math.sin(self.tick_count * 0.28) * 4.2
            new_x = self.x() + (self.roam_direction * 1)
            left_limit  = screen_geom.left() + 20
            right_limit = screen_geom.right() - self.width() - 20

            if new_x <= left_limit:
                new_x = left_limit
                self.roam_direction = 1
                self.roam_mode = "idle"
                self.roam_timer = 90
            elif new_x >= right_limit:
                new_x = right_limit
                self.roam_direction = -1
                self.roam_mode = "idle"
                self.roam_timer = 90
            else:
                if win:
                    if self.roam_direction == 1 and abs(new_x - (win.left() - self.width())) < 15:
                        if win.top() < self.y() and random.random() < 0.65:
                            self.roam_mode = "climb_wall"
                            self.climb_wall_side = "left"
                            new_x = win.left() - self.width() + 10
                            self.current_frame = 0
                            self.anim_tick = 0
                    elif self.roam_direction == -1 and abs(new_x - win.right()) < 15:
                        if win.top() < self.y() and random.random() < 0.65:
                            self.roam_mode = "climb_wall"
                            self.climb_wall_side = "right"
                            new_x = win.right() - 10
                            self.current_frame = 0
                            self.anim_tick = 0

                self.roam_step_count -= 1
                if self.roam_step_count <= 0:
                    self.roam_mode = "idle"
                    self.roam_timer = random.randint(60, 180)

            self.move(new_x, self.y())
            self._notify_position_change()

        elif self.roam_mode == "climb_wall":
            if not win:
                self.roam_mode = "idle"
                self.gravity_active = True
                self.tilt_angle = 0.0
                return

            if self.climb_wall_side == "left":
                self.facing_direction = 1
                self.tilt_angle = -75.0
            else:
                self.facing_direction = -1
                self.tilt_angle = 75.0

            new_y = self.y() - 2
            tab_top_y = win.top() - self.height() + 10

            if new_y <= tab_top_y:
                new_y = tab_top_y
                if self.climb_wall_side == "left":
                    new_x = win.left() + 5
                else:
                    new_x = win.right() - self.width() - 5
                self.roam_mode = "walk_tabs"
                self.tilt_angle = 0.0
                self.roam_direction = 1 if self.climb_wall_side == "left" else -1
                self.facing_direction = self.roam_direction
                self.roam_step_count = random.randint(50, 140)
                self.current_frame = 0
                self.anim_tick = 0
                self.trigger_bounce()
                if self.speech_bubble and not self.speech_bubble.isVisible():
                    self.speech_bubble.say("✂️ Snip snip! Made it onto your window tabs!", auto_hide_seconds=4)
                self.move(new_x, new_y)
            else:
                self.move(self.x(), new_y)
            self._notify_position_change()

        elif self.roam_mode == "walk_tabs":
            if not win:
                self.roam_mode = "idle"
                self.gravity_active = True
                self.tilt_angle = 0.0
                return

            self.facing_direction = self.roam_direction
            self.tilt_angle = math.sin(self.tick_count * 0.28) * 4.0
            new_x = self.x() + (self.roam_direction * 1)
            new_y = win.top() - self.height() + 10

            win_left  = win.left()
            win_right = win.right() - self.width()

            if new_x < win_left:
                self.roam_mode = "idle"
                self.gravity_active = True
                self.tilt_angle = 0.0
            elif new_x > win_right:
                self.roam_mode = "idle"
                self.gravity_active = True
                self.tilt_angle = 0.0
            else:
                self.roam_step_count -= 1
                if self.roam_step_count <= 0:
                    self.roam_mode = "idle"
                    self.roam_timer = random.randint(90, 200)

            self.move(new_x, new_y)
            self._notify_position_change()

    def _notify_position_change(self):
        geom = self.frameGeometry()
        self.position_changed.emit(geom)
        if self.speech_bubble and self.speech_bubble.isVisible():
            self.speech_bubble.update_position(geom)

    # ─────────────────────────────────────────────────────────────────────────
    # Legacy Sprite Label Update (non-Chisa resonators)
    # ─────────────────────────────────────────────────────────────────────────

    def _update_sprite(self):
        """Update QLabel sprite (legacy path for non-Chisa resonators)."""
        if self.sprite_animator:
            # Using paintEvent path — hide the label
            self.sprite_label.setVisible(False)
            return

        self.sprite_label.setVisible(True)
        frames = self.sprites.get(self.current_state, self.sprites.get("idle", []))
        if frames:
            frame_idx = self.current_frame % len(frames)
            pix = frames[frame_idx]
            if not pix.isNull():
                target_w = max(1, int(self.width() * self.bounce_scale_x))
                target_h = max(1, int(self.height() * self.bounce_scale_y))
                scaled = pix.scaled(
                    target_w, target_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                transform = QTransform()
                if self.facing_direction == -1:
                    transform.scale(-1, 1)
                if abs(self.tilt_angle) > 0.1:
                    transform.rotate(self.tilt_angle)
                transformed = scaled.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                self.sprite_label.setPixmap(transformed)

    # ─────────────────────────────────────────────────────────────────────────
    # State Management
    # ─────────────────────────────────────────────────────────────────────────

    def set_state(self, state: str, revert_seconds: int = 0):
        # Validate state exists
        valid = False
        if self.sprite_animator:
            valid = self.sprite_animator.has_state(state) or state in ("idle", "happy", "sleep")
        elif self.sprites:
            valid = state in self.sprites
        else:
            valid = state in ("idle", "happy", "sleep", "walk", "climb", "sit", "snip")
        
        if not valid:
            state = "idle"

        self.current_state = state
        self.current_frame = 0
        self.anim_tick = 0

        if state == "happy":
            self.happy_anim_timer.start()
        else:
            self.happy_anim_timer.stop()

        self._update_sprite()
        if revert_seconds > 0:
            QTimer.singleShot(revert_seconds * 1000, lambda: self.set_state("idle"))

    # ─────────────────────────────────────────────────────────────────────────
    # Mouse & Drag Interaction
    # ─────────────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.mouse_press_pos = event.globalPosition().toPoint()
            self.is_dragging = False
            self.gravity_active = False
            self.tilt_angle = 0.0
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = (event.globalPosition().toPoint() - self.mouse_press_pos).manhattanLength()
            if delta > 4:
                # If Shift or Alt is held AND we have stashed files, immediately start QDrag!
                if (event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.AltModifier)) and self.stashed_files:
                    self.start_drag_out(self.stashed_files)
                    self.is_dragging = False
                    return

                self.is_dragging = True
                new_pos = event.globalPosition().toPoint() - self.drag_position
                self.move(new_pos)
                self._notify_position_change()
            event.accept()
        else:
            self._check_head_pat(event.position().toPoint())
            event.accept()

    def _check_head_pat(self, pos: QPoint):
        is_head_zone = (pos.y() < self.height() * 0.42) and (self.width() * 0.20 <= pos.x() <= self.width() * 0.80)
        now = time.time()

        if is_head_zone:
            if now - self.last_stroke_time > 1.8:
                self.head_pat_strokes = 0
                self.last_stroke_dir = 0

            cur_x = pos.x()
            if self.last_stroke_x != 0:
                dx = cur_x - self.last_stroke_x
                if abs(dx) > 12:
                    current_dir = 1 if dx > 0 else -1
                    if self.last_stroke_dir != 0 and current_dir != self.last_stroke_dir:
                        self.head_pat_strokes += 1
                        self.last_stroke_time = now
                        if self.head_pat_strokes >= 3:
                            self._trigger_head_pat_reaction()
                            self.head_pat_strokes = 0
                    self.last_stroke_dir = current_dir

            self.last_stroke_x = cur_x
        else:
            self.last_stroke_x = 0

    def _trigger_head_pat_reaction(self):
        """Called when user lovingly pats the companion's head."""
        self.trigger_bounce()
        self.set_state("happy", revert_seconds=4)
        self.head_pat_triggered.emit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.is_dragging:
                self.trigger_bounce()
                self.clicked.emit()
            else:
                screen = QApplication.primaryScreen()
                screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
                ground_y = screen_geom.bottom() - self.height() - 20
                if self.y() < ground_y - 30:
                    self.gravity_active = True
                    self.gravity_velocity = 0.0
                else:
                    self.trigger_bounce()
            self.is_dragging = False
            event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.trigger_bounce()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.files_stashed.emit(paths)
                self.set_state("happy", revert_seconds=4)
                self.trigger_bounce()
                event.acceptProposedAction()

    def start_drag_out(self, files: List[Path]):
        """Initiates a native OS drag-out of stashed files into other applications."""
        if not files:
            return
        from PyQt6.QtGui import QDrag
        from PyQt6.QtCore import QMimeData, QUrl
        drag = QDrag(self)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in files])
        drag.setMimeData(mime)
        self.trigger_bounce()
        drag.exec(Qt.DropAction.CopyAction)

    # ─────────────────────────────────────────────────────────────────────────
    # Free Roam, Context Menu, Deletion Reactions
    # ─────────────────────────────────────────────────────────────────────────

    def toggle_free_roam(self):
        self.free_roam_enabled = not self.free_roam_enabled
        self.roam_mode = "idle"
        self.roam_timer = 60
        self.free_roam_toggled.emit(self.free_roam_enabled)

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                color: #2D3748;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #FFEACC;
                color: #4A2E18;
            }
            QMenu::item:disabled {
                color: #A0AEC0;
            }
        """)

        act_workspace = QAction("🖥️ Open Companion Workspace", menu, triggered=self.open_workspace_requested.emit)
        act_chat      = QAction("💬 Talk with Companion", menu, triggered=self.clicked.emit)
        act_companion = QAction("✨ Switch Resonator", menu, triggered=self.open_resonators_requested.emit)
        act_tasks     = QAction("📋 Tasks & Reminders", menu, triggered=self.open_tasks_requested.emit)
        act_tidy      = QAction("🧹 Tidy Desktop Now", menu, triggered=self.organize_desktop_requested.emit)

        roam_label = "🐾 Free Roam Mode (ON)" if self.free_roam_enabled else "🐾 Free Roam Mode (OFF)"
        act_roam   = QAction(roam_label, menu, triggered=self.toggle_free_roam)

        pomo_label = "⏹️ Stop Pomodoro Focus" if self.pomodoro_active else "⏱️ Start Pomodoro (25m Focus)"
        act_pomo   = QAction(pomo_label, menu, triggered=self.pomodoro_toggled.emit)

        if self.current_state == "sleep":
            act_sleep = QAction("⏰ Wake Up", menu, triggered=lambda: self.set_state("idle"))
        else:
            act_sleep = QAction("💤 Nap Time (Sleep)", menu, triggered=lambda: self.set_state("sleep"))

        sub_deletion = menu.addMenu("🗑️ App Deletion Reaction")
        m = self.deletion_reaction_mode
        act_o = QAction("❌ Disabled" + ("  ✓" if m == "off" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("off"))
        act_c = QAction("🐠 Paper-Carp Chomp (Eat Trash) — (Soon)" + ("  ✓" if m == "chomp" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("chomp"))
        act_s = QAction("✂️ Scissor Shredder (Confetti) — (Soon)" + ("  ✓" if m == "snip" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("snip"))
        act_v = QAction("🕳️ Void Vortex (Universal) — (Soon)" + ("  ✓" if m == "vortex" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("vortex"))

        # Greyed out / disabled as requested
        act_c.setEnabled(False)
        act_s.setEnabled(False)
        act_v.setEnabled(False)

        sub_deletion.addAction(act_o)
        sub_deletion.addSeparator()
        sub_deletion.addAction(act_c)
        sub_deletion.addAction(act_s)
        sub_deletion.addAction(act_v)

        act_pat  = QAction("💖 Pat on the Head", menu, triggered=self._trigger_head_pat_reaction)
        act_hide = QAction("🙈 Hide to Tray", menu, triggered=self.hide_requested.emit)
        act_quit = QAction("🚪 Quit", menu, triggered=self.quit_requested.emit)

        menu.addAction(act_workspace)
        menu.addAction(act_chat)
        menu.addAction(act_companion)
        menu.addAction(act_tasks)
        menu.addAction(act_tidy)
        if self.stashed_files:
            act_pocket = QAction(f"🎒 Open Pocket ({len(self.stashed_files)} files)...", menu, triggered=self.open_pocket_requested.emit)
            menu.addAction(act_pocket)
        menu.addSeparator()
        menu.addAction(act_roam)
        menu.addAction(act_pomo)
        menu.addMenu(sub_deletion)
        menu.addAction(act_pat)
        menu.addAction(act_sleep)
        menu.addSeparator()
        menu.addAction(act_hide)
        menu.addAction(act_quit)

        menu.exec(global_pos)

    def set_deletion_reaction_mode(self, mode: str):
        self.deletion_reaction_mode = mode
        self.deletion_reaction_changed.emit(mode)

    def play_deletion_animation(self, mode: str, file_name: str = ""):
        """Executes the selected animation when an app/file is deleted from Desktop."""
        if mode == "chomp":
            # Chisa's Kirigami Paper-Carp Chomp!
            if self.chibi_rig:
                self.chibi_rig.trigger_chomp()
            self.set_state("happy", revert_seconds=4)
            self.trigger_bounce()
            QTimer.singleShot(180, self.trigger_bounce)

        elif mode == "snip":
            # Snip frame-by-frame animation using real snip_0/1/2 frames
            self._snipping = True
            self._snip_ticks = 0
            self.current_frame = 0
            self.anim_tick = 0
            if self.chibi_rig:
                self.chibi_rig.trigger_snip()
            # Run 4 full cycles of the snip animation then finish
            total_frames = 3  # snip_0, snip_1, snip_2
            cycle_ms = _SNIP_TICKS_PER_FRAME * 33  # ms per frame
            total_ms = total_frames * cycle_ms * 4  # 4 full cycles
            QTimer.singleShot(total_ms, self._finish_snip)

        elif mode == "vortex":
            # Void Vortex spin & singularity squish
            self.tilt_angle = 180.0
            self.bounce_scale_x = 0.5
            self.bounce_scale_y = 0.5
            if not self.sprite_animator:
                self._update_sprite()
            self.update()
            QTimer.singleShot(150, self._finish_vortex)

    def _finish_snip(self):
        self._snipping = False
        if self.chibi_rig:
            self.chibi_rig.stop_snip()
        self.current_frame = 0
        self.anim_tick = 0
        self.set_state("happy", revert_seconds=3)
        self.trigger_bounce()

    def _finish_vortex(self):
        self.tilt_angle = 0.0
        self.bounce_scale_x = 1.0
        self.bounce_scale_y = 1.0
        self.set_state("happy", revert_seconds=3)
        self.trigger_bounce()
