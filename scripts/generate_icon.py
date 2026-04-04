"""Generate FartPort icon assets using the 💨 emoji."""
from __future__ import annotations

import struct
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
APP_ASSETS_DIR = ROOT / "assets" / "app"
ICONSET_DIR = APP_ASSETS_DIR / "fartport.iconset"

# Dark background matching the app theme, yellow glow
BG_COLOR = (18, 20, 26, 255)       # near-black
GLOW_COLOR = (255, 213, 0, 60)     # yellow glow (low alpha)

EMOJI_FONT_PATHS = [
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "/System/Library/Fonts/AppleColorEmoji.ttf",
]


def find_emoji_font() -> str:
    for p in EMOJI_FONT_PATHS:
        if Path(p).exists():
            return p
    raise FileNotFoundError("Apple Color Emoji font not found")


def rounded_rect_mask(size: int, radius_ratio: float = 0.225) -> Image.Image:
    """Create an RGBA mask with a rounded rectangle (macOS icon shape)."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    r = int(size * radius_ratio)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    return mask


def render_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded background
    r = int(size * 0.225)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG_COLOR)

    # Yellow radial glow in center
    glow_size = int(size * 0.85)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    margin = (size - glow_size) // 2
    for i in range(8):
        factor = 1 - (i / 8)
        alpha = int(50 * factor)
        inset = i * (glow_size // 16)
        glow_draw.ellipse(
            [margin + inset, margin + inset, margin + glow_size - inset, margin + glow_size - inset],
            fill=(255, 213, 0, alpha)
        )
    img = Image.alpha_composite(img, glow)

    # Draw the 💨 emoji
    font_path = find_emoji_font()
    emoji_size = int(size * 0.72)
    font = ImageFont.truetype(font_path, emoji_size)

    # Measure and center
    tmp = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp)
    bbox = tmp_draw.textbbox((0, 0), "💨", font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]

    draw2 = ImageDraw.Draw(img)
    draw2.text((x, y), "💨", font=font, embedded_color=True)

    return img


def build_ico(png_paths: list[Path], target_path: Path) -> None:
    payloads = [p.read_bytes() for p in png_paths]
    count = len(payloads)
    header = struct.pack("<HHH", 0, 1, count)
    directory = bytearray()
    offset = 6 + (16 * count)
    for png_path, payload in zip(png_paths, payloads):
        size = int(png_path.stem.split("-")[-1])
        icon_size = 0 if size >= 256 else size
        directory.extend(struct.pack("<BBBBHHII", icon_size, icon_size, 0, 0, 1, 32, len(payload), offset))
        offset += len(payload)
    with target_path.open("wb") as f:
        f.write(header)
        f.write(directory)
        for payload in payloads:
            f.write(payload)


def build_icns(icon_entries: list[tuple[str, Path]], target_path: Path) -> None:
    chunks: list[bytes] = []
    total_length = 8
    for icon_type, png_path in icon_entries:
        payload = png_path.read_bytes()
        chunk = icon_type.encode("ascii") + struct.pack(">I", len(payload) + 8) + payload
        chunks.append(chunk)
        total_length += len(chunk)
    with target_path.open("wb") as f:
        f.write(b"icns")
        f.write(struct.pack(">I", total_length))
        for chunk in chunks:
            f.write(chunk)


def render_tray(size: int) -> Image.Image:
    """Minimal tray icon: just the emoji on transparent background."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    font_path = find_emoji_font()
    font = ImageFont.truetype(font_path, int(size * 0.85))
    tmp = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    bbox = ImageDraw.Draw(tmp).textbbox((0, 0), "💨", font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]
    ImageDraw.Draw(img).text((x, y), "💨", font=font, embedded_color=True)
    return img


def main() -> None:
    APP_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    brand_sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    print("Rendering icon sizes...")
    for size in brand_sizes:
        img = render_icon(size)
        img.save(APP_ASSETS_DIR / f"icon-{size}.png")
        print(f"  {size}x{size} ✓")

    shutil.copy2(APP_ASSETS_DIR / "icon-1024.png", APP_ASSETS_DIR / "brand-mark.png")

    # Build .ico for Windows
    build_ico(
        [APP_ASSETS_DIR / f"icon-{s}.png" for s in [16, 32, 48, 64, 128, 256]],
        APP_ASSETS_DIR / "icon.ico",
    )
    print("icon.ico ✓")

    # Build .icns for macOS
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)
    build_icns(
        [
            ("icp4", APP_ASSETS_DIR / "icon-16.png"),
            ("icp5", APP_ASSETS_DIR / "icon-32.png"),
            ("icp6", APP_ASSETS_DIR / "icon-64.png"),
            ("ic07", APP_ASSETS_DIR / "icon-128.png"),
            ("ic08", APP_ASSETS_DIR / "icon-256.png"),
            ("ic09", APP_ASSETS_DIR / "icon-512.png"),
            ("ic10", APP_ASSETS_DIR / "icon-1024.png"),
        ],
        APP_ASSETS_DIR / "icon.icns",
    )
    print("icon.icns ✓")

    # Tray icons (template = black silhouette for macOS menu bar)
    for size, name in [(18, "trayTemplate"), (36, "trayTemplate@2x"), (32, "tray")]:
        render_tray(size).save(APP_ASSETS_DIR / f"{name}.png")
    print("Tray icons ✓")

    print("\nAll FartPort icon assets generated.")


if __name__ == "__main__":
    main()
