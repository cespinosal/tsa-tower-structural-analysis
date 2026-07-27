"""
Genera assets/icon.ico desde ico_TSA.png
y copia splash_TSA.png → assets/splash.png.
Requiere: Pillow  (pip install Pillow).
"""
import shutil
from pathlib import Path
from PIL import Image

ROOT   = Path(__file__).parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

# ── Ícono ──────────────────────────────────────────────────────────────────────
src_ico = ROOT / "ico_TSA.png"
dst_ico = ASSETS / "icon.ico"

img = Image.open(src_ico).convert("RGBA")

sizes = [256, 128, 64, 48, 32, 16]
frames = [img.resize((s, s), Image.LANCZOS) for s in sizes]

frames[0].save(
    dst_ico,
    format="ICO",
    append_images=frames[1:],
    sizes=[(s, s) for s in sizes],
)
print(f"OK icon.ico  -> {dst_ico}")

# ── Splash ─────────────────────────────────────────────────────────────────────
src_splash = ROOT / "splash_TSA.png"
dst_splash = ASSETS / "splash.png"

shutil.copy2(src_splash, dst_splash)
print(f"OK splash.png -> {dst_splash}")

print("Listo.")
