"""
DeskBuddy - Articulated 2D Chibi Layered Puppet Rig Engine
Renders an articulated 2D Chibi Chisa with independent moving feet,
snipping scissors, head-bobbing physics, and an origami paper-carp companion.
"""

import math
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QPainterPath, QTransform
)

class ChibiRig:
    def __init__(self, resonator_dir: Path):
        self.resonator_dir = resonator_dir
        self.is_active = True

        # Joint & Physics State
        self.walk_ticks = 0.0
        self.is_walking = False
        self.is_climbing = False
        self.is_snipping = False
        self.is_chomping = False

        self.snip_progress = 0.0     # 0.0 (closed) to 1.0 (fully open)
        self.chomp_progress = 0.0    # 0.0 to 1.0 leap progression
        self.snip_direction = 1

        self.carp_float_tick = 0.0
        self.carp_tail_angle = 0.0

        # Load Base Character Sprites
        self.sprites: Dict[str, List[QPixmap]] = {
            "idle": [
                QPixmap(str(resonator_dir / "pet_idle_0.png")),
                QPixmap(str(resonator_dir / "pet_idle_1.png")),
            ],
            "happy": [
                QPixmap(str(resonator_dir / "pet_happy_0.png")),
                QPixmap(str(resonator_dir / "pet_happy_1.png")),
            ],
            "sleep": [
                QPixmap(str(resonator_dir / "pet_sleep_0.png")),
                QPixmap(str(resonator_dir / "pet_sleep_1.png")),
            ]
        }

    def update_physics(self, is_walking: bool, is_climbing: bool = False):
        """Advances physics clock for walking stride, carp undulation, and scissor animation."""
        self.is_walking = is_walking
        self.is_climbing = is_climbing

        if self.is_walking or self.is_climbing:
            self.walk_ticks += 0.32
        else:
            # Settle feet to rest
            self.walk_ticks = 0.0

        # Paper-carp ambient swimming oscillation
        self.carp_float_tick += 0.08
        self.carp_tail_angle = math.sin(self.carp_float_tick * 2.2) * 22.0

        # Scissor snipping animation cycle
        if self.is_snipping:
            self.snip_progress += 0.18 * self.snip_direction
            if self.snip_progress >= 1.0:
                self.snip_progress = 1.0
                self.snip_direction = -1
            elif self.snip_progress <= 0.0:
                self.snip_progress = 0.0
                self.snip_direction = 1

        # Chomp leap animation
        if self.is_chomping:
            self.chomp_progress += 0.06
            if self.chomp_progress >= 1.0:
                self.is_chomping = False
                self.chomp_progress = 0.0

    def trigger_snip(self, duration_steps: int = 20):
        """Triggers rapid cutting motion of the scissors."""
        self.is_snipping = True
        self.snip_progress = 0.0
        self.snip_direction = 1

    def stop_snip(self):
        self.is_snipping = False
        self.snip_progress = 0.0

    def trigger_chomp(self):
        """Triggers paper-carp lunging chomp leap."""
        self.is_chomping = True
        self.chomp_progress = 0.0

    def render(
        self,
        painter: QPainter,
        rect: QRectF,
        current_state: str,
        current_frame: int,
        facing_direction: int = 1,
        body_tilt: float = 0.0,
        bounce_scale_x: float = 1.0,
        bounce_scale_y: float = 1.0,
        draw_boots: bool = True,
        draw_body: bool = True,
        draw_scissors: bool = True,
        draw_companion: bool = True,
    ):
        """Renders the layered articulated chibi puppet with smooth procedural joints."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cx = rect.center().x()
        cy = rect.center().y()

        # Global translation to center of pet window
        painter.translate(cx, cy)

        # Apply horizontal facing flip (facing left or right)
        if facing_direction == -1:
            painter.scale(-1, 1)

        # Apply click bounce squish/stretch
        painter.scale(bounce_scale_x, bounce_scale_y)

        # Apply body tilt
        if abs(body_tilt) > 0.1:
            painter.rotate(body_tilt)

        # Calculate walking stride offsets
        walk_stride = math.sin(self.walk_ticks)
        walk_lift = math.cos(self.walk_ticks)

        # 1. LAYER: Articulated Stepping Boots (Feet)
        if draw_boots:
            if self.is_walking:
                # Left boot stride
                foot_l_x = -14 + (walk_stride * 9.0)
                foot_l_y = 52 - max(0.0, walk_lift * 6.5)
                foot_l_rot = walk_stride * 14.0

                # Right boot stride (opposite phase)
                foot_r_x = 12 - (walk_stride * 9.0)
                foot_r_y = 52 - max(0.0, -walk_lift * 6.5)
                foot_r_rot = -walk_stride * 14.0
            elif self.is_climbing:
                climb_stride = math.sin(self.walk_ticks * 1.5)
                foot_l_x = -14
                foot_l_y = 52 - max(0.0, climb_stride * 8.0)
                foot_l_rot = -10.0
                foot_r_x = 12
                foot_r_y = 52 - max(0.0, -climb_stride * 8.0)
                foot_r_rot = 10.0
            else:
                # Idle resting feet position
                foot_l_x = -12
                foot_l_y = 52
                foot_l_rot = 0.0
                foot_r_x = 12
                foot_r_y = 52
                foot_r_rot = 0.0

            # Draw Back Foot (Left)
            self._draw_boot(painter, foot_l_x, foot_l_y, foot_l_rot)
            # Draw Front Foot (Right)
            self._draw_boot(painter, foot_r_x, foot_r_y, foot_r_rot)

        # 2. LAYER: Main Chibi Body & Head Sprite
        if draw_body:
            frames = self.sprites.get(current_state, self.sprites.get("idle", []))
            if frames:
                pix = frames[current_frame % len(frames)]
                if not pix.isNull():
                    pw = rect.width()
                    ph = rect.height()
                    # Vertical breathing/wobble bob
                    body_y_bob = 0
                    if self.is_walking:
                        body_y_bob = -abs(math.sin(self.walk_ticks)) * 2.5
                    painter.drawPixmap(
                        int(-pw / 2),
                        int(-ph / 2 + body_y_bob),
                        int(pw),
                        int(ph),
                        pix
                    )

        # 3. LAYER: Articulated Kirigami Scissors
        if draw_scissors:
            self._draw_scissors(painter, current_state)

        # 4. LAYER: Floating Origami Paper-Carp Companion
        if draw_companion:
            self._draw_paper_carp(painter)

        painter.restore()

    def _draw_boot(self, painter: QPainter, x: float, y: float, angle: float):
        """Draws an articulated ninja tabi boot with crimson laces."""
        painter.save()
        painter.translate(x, y)
        painter.rotate(angle)

        # Boot body (dark charcoal)
        path = QPainterPath()
        path.addRoundedRect(QRectF(-6, -7, 12, 14), 4, 4)
        painter.fillPath(path, QBrush(QColor("#24292E")))
        painter.strokePath(path, QPen(QColor("#1A202C"), 1.5))

        # Sole / Tabi toe (white rim)
        sole = QPainterPath()
        sole.addRoundedRect(QRectF(-6.5, 4.5, 13, 3), 1.5, 1.5)
        painter.fillPath(sole, QBrush(QColor("#F7FAFC")))

        # Crimson ribbon lace
        painter.setPen(QPen(QColor("#E53E3E"), 1.8))
        painter.drawLine(-4, 0, 4, 0)

        painter.restore()

    def _draw_scissors(self, painter: QPainter, current_state: str):
        """Draws articulated twin scissor blades that open and cut."""
        painter.save()
        # Pivot point: Chisa's right hand holding the shears
        painter.translate(28, 14)

        spread_angle = 8.0  # Default resting angle
        if self.is_snipping:
            spread_angle = 8.0 + (self.snip_progress * 34.0)

        # Blade A (Top)
        painter.save()
        painter.rotate(-spread_angle / 2)
        self._draw_scissor_blade(painter, is_upper=True)
        painter.restore()

        # Blade B (Bottom)
        painter.save()
        painter.rotate(spread_angle / 2)
        self._draw_scissor_blade(painter, is_upper=False)
        painter.restore()

        # Center Pivot Screw (Gold)
        painter.setBrush(QBrush(QColor("#ECC94B")))
        painter.setPen(QPen(QColor("#B7791F"), 1))
        painter.drawEllipse(QPointF(0, 0), 2.5, 2.5)

        painter.restore()

    def _draw_scissor_blade(self, painter: QPainter, is_upper: bool):
        """Renders one scissor blade with crimson finger loop and polished silver steel."""
        # Crimson Handle Loop
        painter.setBrush(QBrush(QColor("#E53E3E")))
        painter.setPen(QPen(QColor("#9B2C2C"), 1.2))
        painter.drawEllipse(QPointF(-12, 0), 5.5, 4.5)
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
        painter.drawEllipse(QPointF(-12, 0), 2.5, 2.0)

        # Steel Blade
        blade = QPainterPath()
        blade.moveTo(0, -1.5 if is_upper else 1.5)
        blade.lineTo(16, -0.5 if is_upper else 0.5)
        blade.lineTo(18, 0)
        blade.lineTo(0, 1.5 if is_upper else -1.5)
        blade.closeSubpath()

        painter.fillPath(blade, QBrush(QColor("#EDF2F7")))
        painter.strokePath(blade, QPen(QColor("#CBD5E0"), 1.0))

    def _draw_paper_carp(self, painter: QPainter):
        """Renders the Kirigami origami paper-carp floating and swimming beside Chisa."""
        painter.save()

        # Default floating position (behind left shoulder)
        carp_base_x = -42.0
        carp_base_y = -28.0 + (math.sin(self.carp_float_tick) * 5.0)

        if self.is_chomping:
            # Leap forward animation during app deletion
            leap_factor = math.sin(self.chomp_progress * math.pi)
            carp_base_x += leap_factor * 65.0
            carp_base_y += -leap_factor * 20.0
            scale = 1.0 + (leap_factor * 0.45)
            painter.scale(scale, scale)

        painter.translate(carp_base_x, carp_base_y)

        # Origami Carp Body (Faceted Diamond in Red & White)
        body = QPainterPath()
        body.moveTo(14, 0)        # Nose
        body.lineTo(4, -8)        # Top dorsal fold
        body.lineTo(-10, 0)       # Tail root
        body.lineTo(4, 7)         # Belly fold
        body.closeSubpath()

        painter.fillPath(body, QBrush(QColor("#E53E3E")))
        painter.strokePath(body, QPen(QColor("#FFFFFF"), 1.5))

        # Top White Kirigami Fold Accent
        accent = QPainterPath()
        accent.moveTo(14, 0)
        accent.lineTo(4, -8)
        accent.lineTo(0, 0)
        accent.closeSubpath()
        painter.fillPath(accent, QBrush(QColor("#FFFFFF")))

        # Black Eye Bead
        painter.setBrush(QBrush(QColor("#1A202C")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(9, -2), 1.6, 1.6)

        # Swimming Tail Fin (Swinging on pivot)
        painter.save()
        painter.translate(-10, 0)
        painter.rotate(self.carp_tail_angle)

        tail = QPainterPath()
        tail.moveTo(0, 0)
        tail.lineTo(-9, -6)
        tail.lineTo(-6, 0)
        tail.lineTo(-9, 6)
        tail.closeSubpath()

        painter.fillPath(tail, QBrush(QColor("#FED7D7")))
        painter.strokePath(tail, QPen(QColor("#E53E3E"), 1.0))
        painter.restore()

        painter.restore()
