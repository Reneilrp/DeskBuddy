"""
DeskBuddy - Smart Clipboard Assistant (Paper-Cut Tools)
Passively monitors clipboard changes to provide instant, non-intrusive micro-tools:
1. Math Evaluation: Instant answer for arithmetic & percentages
2. Color Swatch: Visual preview & RGB conversion for hex/rgb color codes
3. 1-Click Image Saver: Direct download action for copied image URLs
4. JSON Beautifier: Fast 1-click format/pretty-print for minified JSON
"""

import ast
import re
import json
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

class SafeMathEvaluator(ast.NodeVisitor):
    ALLOWED_OPERATORS = (
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd, ast.FloorDiv
    )

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.Constant):  # Python 3.8+ numbers
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric constants allowed")
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) in self.ALLOWED_OPERATORS:
                operand = self.visit(node.operand)
                if isinstance(node.op, ast.USub):
                    return -operand
                return operand
            raise ValueError("Unsupported unary operator")
        elif isinstance(node, ast.BinOp):
            if type(node.op) in self.ALLOWED_OPERATORS:
                left = self.visit(node.left)
                right = self.visit(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    if right == 0:
                        raise ZeroDivisionError("Cannot divide by zero")
                    return left / right
                elif isinstance(node.op, ast.FloorDiv):
                    if right == 0:
                        raise ZeroDivisionError("Cannot divide by zero")
                    return left // right
                elif isinstance(node.op, ast.Mod):
                    return left % right
                elif isinstance(node.op, ast.Pow):
                    if abs(right) > 100:
                        raise ValueError("Exponent too large")
                    return left ** right
            raise ValueError("Unsupported binary operator")
        raise ValueError("Unsupported expression syntax")

def safe_eval_math(expr_str: str) -> Optional[float]:
    """Safely evaluates an arithmetic expression using AST without using eval()."""
    clean = expr_str.strip().replace("x", "*").replace("X", "*").replace("^", "**")
    
    # Handle percentage phrase: "X% of Y" -> (X / 100) * Y
    pct_match = re.match(r"^([\d\.]+)\s*%\s*(?:of|\*)\s*([\d\.]+)$", clean, re.IGNORECASE)
    if pct_match:
        try:
            pct = float(pct_match.group(1))
            val = float(pct_match.group(2))
            return (pct / 100.0) * val
        except ValueError:
            return None

    # Handle percentage: "X%" -> X / 100
    if clean.endswith("%") and clean[:-1].strip().replace(".", "", 1).isdigit():
        try:
            return float(clean[:-1].strip()) / 100.0
        except ValueError:
            return None

    # Must contain at least one math operator to prevent triggering on plain single numbers
    if not any(op in clean for op in ("+", "-", "*", "/", "%", "**")):
        return None

    try:
        parsed = ast.parse(clean, mode='eval')
        evaluator = SafeMathEvaluator()
        result = evaluator.visit(parsed)
        return result
    except Exception:
        return None

class ClipboardAssistant(QObject):
    action_ready = pyqtSignal(dict)  # Emits payload when useful pattern is copied

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_processed_text = ""
        self._enabled = True

    def start(self):
        clipboard = QApplication.clipboard()
        clipboard.dataChanged.connect(self._on_clipboard_changed)

    def stop(self):
        clipboard = QApplication.clipboard()
        try:
            clipboard.dataChanged.disconnect(self._on_clipboard_changed)
        except Exception:
            pass

    def _on_clipboard_changed(self):
        if not self._enabled:
            return

        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text or text == self._last_processed_text or len(text) > 4000:
            return

        self._last_processed_text = text
        payload = self.inspect_text(text)
        if payload:
            self.action_ready.emit(payload)

    def inspect_text(self, text: str) -> Optional[Dict[str, Any]]:
        raw = text.strip()

        # 1. Math Calculation
        if len(raw) <= 120:
            math_val = safe_eval_math(raw)
            if math_val is not None:
                # Format integer or rounded float
                if isinstance(math_val, float) and math_val.is_integer():
                    formatted = f"{int(math_val):,}"
                elif isinstance(math_val, float):
                    formatted = f"{math_val:,.4f}".rstrip("0").rstrip(".")
                else:
                    formatted = f"{math_val:,}"

                return {
                    "type": "math",
                    "title": "🧮 Math Result",
                    "query": raw,
                    "result": formatted,
                    "display_text": f"🧮 {raw} = **{formatted}**",
                    "action_label": "📋 Copy Result",
                    "action_value": str(formatted)
                }

        # 2. Hex / RGB Color Code
        hex_match = re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", raw)
        if hex_match:
            hex_code = raw.upper()
            if len(hex_code) == 4:  # #RGB to #RRGGBB
                hex_code = f"#{hex_code[1]*2}{hex_code[2]*2}{hex_code[3]*2}"
            
            r = int(hex_code[1:3], 16)
            g = int(hex_code[3:5], 16)
            b = int(hex_code[5:7], 16)

            return {
                "type": "color",
                "title": "🎨 Color Swatch",
                "hex": hex_code,
                "rgb": f"rgb({r}, {g}, {b})",
                "display_text": f"🎨 **{hex_code}** • `rgb({r}, {g}, {b})`",
                "action_label": "📋 Copy RGB",
                "action_value": f"rgb({r}, {g}, {b})"
            }

        # 3. Direct Image URL
        if raw.startswith("http://") or raw.startswith("https://"):
            lower_url = raw.lower()
            img_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg")
            if any(lower_url.split("?")[0].endswith(ext) for ext in img_exts):
                filename = Path(lower_url.split("?")[0]).name
                return {
                    "type": "image_url",
                    "title": "🖼️ Image Link",
                    "url": raw,
                    "filename": filename,
                    "display_text": f"🖼️ Image detected: `{filename}`",
                    "action_label": "💾 Save Image to Downloads",
                    "action_value": raw
                }

        # 4. JSON Formatter
        if (raw.startswith("{") and raw.endswith("}")) or (raw.startswith("[") and raw.endswith("]")):
            if "\n" not in raw and len(raw) > 20:
                try:
                    parsed = json.loads(raw)
                    formatted_json = json.dumps(parsed, indent=2)
                    return {
                        "type": "json",
                        "title": "📋 Minified JSON",
                        "display_text": "📋 Minified JSON detected!",
                        "action_label": "✨ Beautify JSON",
                        "action_value": formatted_json
                    }
                except Exception:
                    pass

        return None

    @staticmethod
    def save_image_url(url: str, dest_dir: Optional[Path] = None) -> Optional[Path]:
        """Downloads an image URL into the user's Downloads directory."""
        from .fast_search import get_user_shortcuts
        target_dir = dest_dir or get_user_shortcuts().get("Downloads", Path.home() / "Downloads")
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(url.split("?")[0]).name or "downloaded_image.png"
        target_path = target_dir / filename

        # Avoid collision
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{stem} ({counter}){suffix}"
            counter += 1

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DeskBuddy/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp, open(target_path, "wb") as f:
                f.write(resp.read())
            return target_path
        except Exception:
            return None
