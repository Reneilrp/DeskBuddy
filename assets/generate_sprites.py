"""
Generates clean, cute 2D pet sprites (a friendly cat/companion)
using PyQt6 QPainter and saves them into the assets folder.
"""

import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QImage, QPainter, QColor, QBrush, QPen, QPainterPath, QFont
from PyQt6.QtWidgets import QApplication

def create_sprite(state: str, frame: int) -> QImage:
    # 128x128 high DPI transparent canvas
    img = QImage(128, 128, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Bobbing effect
    offset_y = 2 if frame == 1 else 0

    # Colors
    body_color = QColor("#FFB049")       # Warm cat orange
    belly_color = QColor("#FFEACC")      # Cream belly
    ear_inner = QColor("#FF8B77")        # Pink inner ear
    outline_color = QColor("#4A2E18")    # Chocolate brown outline
    eye_color = QColor("#222222")

    pen = QPen(outline_color, 3)
    p.setPen(pen)

    # 1. Tail (waving)
    tail_path = QPainterPath()
    tail_path.moveTo(25, 95 + offset_y)
    tail_angle = -10 if frame == 0 else 10
    tail_path.quadTo(10, 80 + offset_y + tail_angle, 15, 60 + offset_y + tail_angle)
    p.setBrush(QBrush(body_color))
    p.drawPath(tail_path)

    # 2. Left & Right Ears
    left_ear = QPainterPath()
    left_ear.moveTo(38, 52 + offset_y)
    left_ear.lineTo(32, 28 + offset_y)
    left_ear.lineTo(55, 42 + offset_y)
    left_ear.closeSubpath()
    p.setBrush(QBrush(body_color))
    p.drawPath(left_ear)

    # Left inner ear
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(ear_inner))
    left_inner = QPainterPath()
    left_inner.moveTo(40, 50 + offset_y)
    left_inner.lineTo(35, 33 + offset_y)
    left_inner.lineTo(52, 43 + offset_y)
    p.drawPath(left_inner)

    # Right Ear
    p.setPen(pen)
    right_ear = QPainterPath()
    right_ear.moveTo(73, 42 + offset_y)
    right_ear.lineTo(96, 28 + offset_y)
    right_ear.lineTo(90, 52 + offset_y)
    right_ear.closeSubpath()
    p.setBrush(QBrush(body_color))
    p.drawPath(right_ear)

    # Right inner ear
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(ear_inner))
    right_inner = QPainterPath()
    right_inner.moveTo(76, 43 + offset_y)
    right_inner.lineTo(93, 33 + offset_y)
    right_inner.lineTo(88, 50 + offset_y)
    p.drawPath(right_inner)

    # 3. Main Round Body/Head
    p.setPen(pen)
    p.setBrush(QBrush(body_color))
    p.drawEllipse(QRectF(30, 38 + offset_y, 68, 62))

    # 4. Belly Patch
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(belly_color))
    p.drawEllipse(QRectF(44, 60 + offset_y, 40, 36))

    # 5. Face / State Variations
    p.setPen(pen)
    p.setBrush(QBrush(eye_color))

    if state == "sleep":
        # Closed eyes (arcs)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(46, 54 + offset_y, 10, 8), 0, 180 * 16)
        p.drawArc(QRectF(72, 54 + offset_y, 10, 8), 0, 180 * 16)
        # Zzz text
        p.setPen(QPen(QColor("#5A6BFF"), 2))
        p.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        p.drawText(QPointF(92, 38 + (offset_y * 2)), "z")
        p.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        p.drawText(QPointF(100, 24 + (offset_y * 2)), "Z")
    elif state == "happy":
        # Happy squinting curve eyes: ^ ^
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(46, 52 + offset_y, 10, 8), 0, 180 * 16)
        p.drawArc(QRectF(72, 52 + offset_y, 10, 8), 0, 180 * 16)
        # Blush cheeks
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 130, 130, 180)))
        p.drawEllipse(QRectF(40, 60 + offset_y, 8, 5))
        p.drawEllipse(QRectF(80, 60 + offset_y, 8, 5))
    else:  # idle / think
        if frame == 1 and state == "idle":
            # Blink
            p.drawLine(46, 56 + offset_y, 56, 56 + offset_y)
            p.drawLine(72, 56 + offset_y, 82, 56 + offset_y)
        else:
            # Big curious eyes
            p.drawEllipse(QRectF(46, 52 + offset_y, 8, 9))
            p.drawEllipse(QRectF(74, 52 + offset_y, 8, 9))
            # Catchlights
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(Qt.GlobalColor.white))
            p.drawEllipse(QRectF(48, 54 + offset_y, 3, 3))
            p.drawEllipse(QRectF(76, 54 + offset_y, 3, 3))

    # Cute nose and mouth
    p.setPen(pen)
    p.setBrush(QBrush(ear_inner))
    p.drawEllipse(QRectF(62, 60 + offset_y, 4, 3))

    # Cat mouth: :3
    p.setBrush(Qt.BrushStyle.NoBrush)
    mouth = QPainterPath()
    mouth.moveTo(58, 64 + offset_y)
    mouth.quadTo(61, 67 + offset_y, 64, 64 + offset_y)
    mouth.quadTo(67, 67 + offset_y, 70, 64 + offset_y)
    p.drawPath(mouth)

    # 6. Paws
    p.setBrush(QBrush(body_color))
    p.drawEllipse(QRectF(44, 94 + offset_y, 12, 10))
    p.drawEllipse(QRectF(72, 94 + offset_y, 12, 10))

    p.end()
    return img

def main():
    app = QApplication(sys.argv)
    out_dir = Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    states = ["idle", "happy", "sleep"]
    for state in states:
        for f in range(2):
            img = create_sprite(state, f)
            path = out_dir / f"pet_{state}_{f}.png"
            img.save(str(path))
            print(f"Generated {path}")

    # Generate tray icon (64x64)
    tray_img = create_sprite("idle", 0).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    tray_path = out_dir / "tray_icon.png"
    tray_img.save(str(tray_path))
    print(f"Generated {tray_path}")

if __name__ == "__main__":
    main()
