"""
Generates complete chibi sprite packs and portraits for all Wuthering Waves Resonators
using PyQt6 QPainter.
"""

import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QImage, QPainter, QColor, QBrush, QPen, QPainterPath, QFont
from PyQt6.QtWidgets import QApplication

# Import registry
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.resonators import RESONATORS, ELEMENT_COLORS

def draw_resonator_chibi(res_id: str, data: dict, state: str, frame: int) -> QImage:
    # 128x128 transparent canvas
    img = QImage(128, 128, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    offset_y = 2 if frame == 1 else 0
    elem = data["element"]
    elem_colors = ELEMENT_COLORS.get(elem, ELEMENT_COLORS["Spectro"])

    hair_c = QColor(data["hair_color"])
    accent_c = QColor(data["accent_color"])
    skin_c = QColor("#FFF0E0")
    eye_c = QColor(data.get("accent_color", "#2D3748"))
    outline_c = QColor("#2D1D16")

    pen = QPen(outline_c, 2.5)
    p.setPen(pen)

    # 1. Back Element Aura / Wings / Motifs
    aura_c = QColor(elem_colors["primary"])
    aura_c.setAlpha(120 if frame == 0 else 180)
    p.setBrush(QBrush(aura_c))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(34, 38 + offset_y, 60, 58))

    # Special back hair / accessories
    p.setPen(pen)
    if res_id == "yinlin":
        # Twin tails
        p.setBrush(QBrush(hair_c))
        p.drawEllipse(QRectF(18, 45 + offset_y, 22, 42))
        p.drawEllipse(QRectF(88, 45 + offset_y, 22, 42))
    elif res_id == "changli":
        # Phoenix tail feathers
        p.setBrush(QBrush(accent_c))
        p.drawEllipse(QRectF(22, 50 + offset_y, 18, 38))
        p.drawEllipse(QRectF(88, 50 + offset_y, 18, 38))
    elif res_id == "shorekeeper":
        # Cosmic butterfly wings
        p.setBrush(QBrush(QColor("#A3EBFB")))
        p.drawEllipse(QRectF(20, 42 + offset_y, 24, 28))
        p.drawEllipse(QRectF(84, 42 + offset_y, 24, 28))

    # 2. Body / Clothing Outfit
    p.setBrush(QBrush(accent_c))
    p.drawRoundedRect(QRectF(44, 78 + offset_y, 40, 32), 10, 10)

    # Inner collar/chest
    p.setBrush(QBrush(QColor(elem_colors["glow"])))
    p.drawEllipse(QRectF(52, 79 + offset_y, 24, 16))

    # 3. Head / Face
    p.setBrush(QBrush(skin_c))
    p.drawEllipse(QRectF(36, 36 + offset_y, 56, 48))

    # 4. Hair Styles
    p.setBrush(QBrush(hair_c))
    hair_path = QPainterPath()
    hair_path.moveTo(34, 52 + offset_y)
    hair_path.quadTo(36, 26 + offset_y, 64, 26 + offset_y)
    hair_path.quadTo(92, 26 + offset_y, 94, 52 + offset_y)
    # Bangs
    hair_path.lineTo(84, 48 + offset_y)
    hair_path.lineTo(76, 56 + offset_y)
    hair_path.lineTo(64, 48 + offset_y)
    hair_path.lineTo(52, 56 + offset_y)
    hair_path.lineTo(44, 48 + offset_y)
    hair_path.closeSubpath()
    p.drawPath(hair_path)

    # Signature head ornaments
    if res_id in ("jinhsi", "jiyan"):
        # Dragon Horns
        p.setBrush(QBrush(accent_c))
        p.drawPolygon([QPointF(42, 34 + offset_y), QPointF(32, 20 + offset_y), QPointF(48, 30 + offset_y)])
        p.drawPolygon([QPointF(86, 34 + offset_y), QPointF(96, 20 + offset_y), QPointF(80, 30 + offset_y)])
    elif res_id == "encore":
        # Wooly horns
        p.setBrush(QBrush(QColor("#FFEACC")))
        p.drawEllipse(QRectF(30, 28 + offset_y, 14, 14))
        p.drawEllipse(QRectF(84, 28 + offset_y, 14, 14))
    elif res_id == "camellya":
        # Crimson flower hairpiece
        p.setBrush(QBrush(QColor("#E53E3E")))
        p.drawEllipse(QRectF(82, 32 + offset_y, 12, 12))

    # 5. Eyes & Expression
    if res_id == "sanhua":
        # Blindfold
        p.setPen(pen)
        p.setBrush(QBrush(QColor("#4A5568")))
        p.drawRoundedRect(QRectF(44, 52 + offset_y, 40, 10), 3, 3)
    elif state == "sleep":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(48, 54 + offset_y, 10, 8), 0, 180 * 16)
        p.drawArc(QRectF(70, 54 + offset_y, 10, 8), 0, 180 * 16)
        # Zzz text
        p.setPen(QPen(accent_c, 2))
        p.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        p.drawText(QPointF(96, 32 + (offset_y * 2)), "z")
        p.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        p.drawText(QPointF(104, 20 + (offset_y * 2)), "Z")
    elif state == "happy":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(48, 52 + offset_y, 10, 8), 0, 180 * 16)
        p.drawArc(QRectF(70, 52 + offset_y, 10, 8), 0, 180 * 16)
        # Blush
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 120, 120, 180)))
        p.drawEllipse(QRectF(44, 60 + offset_y, 8, 5))
        p.drawEllipse(QRectF(76, 60 + offset_y, 8, 5))
    else:  # Idle
        if frame == 1:
            p.setPen(pen)
            p.drawLine(48, 56 + offset_y, 58, 56 + offset_y)
            p.drawLine(70, 56 + offset_y, 80, 56 + offset_y)
        else:
            p.setPen(pen)
            p.setBrush(QBrush(eye_c))
            p.drawEllipse(QRectF(48, 51 + offset_y, 9, 10))
            p.drawEllipse(QRectF(71, 51 + offset_y, 9, 10))
            # Catchlight
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(Qt.GlobalColor.white))
            p.drawEllipse(QRectF(50, 53 + offset_y, 3, 3))
            p.drawEllipse(QRectF(73, 53 + offset_y, 3, 3))

    # Cute mouth
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if state == "happy":
        mouth = QPainterPath()
        mouth.moveTo(60, 64 + offset_y)
        mouth.quadTo(64, 70 + offset_y, 68, 64 + offset_y)
        p.drawPath(mouth)
    else:
        p.drawArc(QRectF(61, 62 + offset_y, 6, 4), 0, 180 * 16)

    # 6. Element Icon Gem on Chest
    gem_c = QColor(elem_colors["primary"])
    p.setPen(pen)
    p.setBrush(QBrush(gem_c))
    p.drawEllipse(QRectF(60, 88 + offset_y, 8, 8))

    # Paws / Hands
    p.setBrush(QBrush(skin_c))
    p.drawEllipse(QRectF(42, 90 + offset_y, 8, 8))
    p.drawEllipse(QRectF(78, 90 + offset_y, 8, 8))

    p.end()
    return img

def main():
    app = QApplication(sys.argv)
    base_assets = Path(__file__).resolve().parent / "resonators"
    base_assets.mkdir(parents=True, exist_ok=True)

    print(f"Generating sprite packs for {len(RESONATORS)} Resonators...")

    states = ["idle", "happy", "sleep"]
    for res_id, data in RESONATORS.items():
        res_dir = base_assets / res_id
        res_dir.mkdir(parents=True, exist_ok=True)

        for state in states:
            for f in range(2):
                img = draw_resonator_chibi(res_id, data, state, f)
                img.save(str(res_dir / f"pet_{state}_{f}.png"))

        # Icon preview (64x64)
        icon_img = draw_resonator_chibi(res_id, data, "idle", 0).scaled(
            64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        icon_img.save(str(res_dir / "icon.png"))
        print(f"✓ Created {data['name']} ({data['element']})")

    print("All Resonator sprites generated successfully!")

if __name__ == "__main__":
    main()
