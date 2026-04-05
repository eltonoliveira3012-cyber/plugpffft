from __future__ import annotations

import math
import random
import shutil
import struct
import wave
import zlib
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ModuleNotFoundError:
    Image = None
    ImageDraw = None
    ImageFilter = None
    ImageFont = None


ROOT = Path(__file__).resolve().parent.parent
APP_ASSETS_DIR = ROOT / "assets" / "app"
AUDIO_ASSETS_DIR = ROOT / "assets" / "audio"
WEBSITE_DIR = ROOT / "website"
BUILD_DIR = ROOT / "build"
ICONSET_DIR = APP_ASSETS_DIR / "plugpffft.iconset"

EMOJI_FONT_PATHS = [
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "/System/Library/Fonts/AppleColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
]

DISPLAY_FONT_PATHS = [
    "/System/Library/Fonts/Avenir Next Condensed.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Avenir.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

BODY_FONT_PATHS = [
    "/System/Library/Fonts/Avenir.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

EMOJI_FONT_FALLBACK_SIZES = [160, 96, 64, 52, 48, 40, 32, 26, 20]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def lerp(start: float, end: float, alpha: float) -> float:
    return start + ((end - start) * alpha)


def blend_channel(dst: int, src: int, dst_alpha: float, src_alpha: float, out_alpha: float) -> int:
    if out_alpha <= 0.0:
        return 0
    return int(((src * src_alpha) + (dst * dst_alpha * (1.0 - src_alpha))) / out_alpha)


class Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.data = bytearray(width * height * 4)

    def blend_pixel(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return

        src_r, src_g, src_b, src_a = color
        if src_a <= 0:
            return

        index = (y * self.width + x) * 4
        dst_r = self.data[index]
        dst_g = self.data[index + 1]
        dst_b = self.data[index + 2]
        dst_a = self.data[index + 3] / 255.0
        src_alpha = src_a / 255.0
        out_alpha = src_alpha + (dst_a * (1.0 - src_alpha))

        self.data[index] = blend_channel(dst_r, src_r, dst_a, src_alpha, out_alpha)
        self.data[index + 1] = blend_channel(dst_g, src_g, dst_a, src_alpha, out_alpha)
        self.data[index + 2] = blend_channel(dst_b, src_b, dst_a, src_alpha, out_alpha)
        self.data[index + 3] = int(out_alpha * 255.0)

    def fill_rounded_gradient(
        self,
        start_color: tuple[int, int, int],
        end_color: tuple[int, int, int],
        radius_ratio: float,
    ) -> None:
        radius = self.width * radius_ratio
        max_x = self.width - 1
        max_y = self.height - 1

        for y in range(self.height):
            y_mix = y / max(max_y, 1)
            for x in range(self.width):
                x_mix = x / max(max_x, 1)
                mix = clamp((x_mix * 0.58) + (y_mix * 0.42), 0.0, 1.0)
                r = int(lerp(start_color[0], end_color[0], mix))
                g = int(lerp(start_color[1], end_color[1], mix))
                b = int(lerp(start_color[2], end_color[2], mix))

                dx = max(abs(x - (self.width / 2.0)) - ((self.width / 2.0) - radius), 0.0)
                dy = max(abs(y - (self.height / 2.0)) - ((self.height / 2.0) - radius), 0.0)
                if (dx * dx) + (dy * dy) > radius * radius:
                    continue

                self.blend_pixel(x, y, (r, g, b, 255))

    def draw_radial_glow(
        self,
        cx: float,
        cy: float,
        radius: float,
        color: tuple[int, int, int],
        alpha: float,
    ) -> None:
        x0 = max(0, int((cx - radius) * self.width))
        x1 = min(self.width - 1, int((cx + radius) * self.width))
        y0 = max(0, int((cy - radius) * self.height))
        y1 = min(self.height - 1, int((cy + radius) * self.height))
        scaled_radius = radius * self.width
        center_x = cx * self.width
        center_y = cy * self.height

        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                distance = math.hypot(x - center_x, y - center_y)
                if distance > scaled_radius:
                    continue
                strength = 1.0 - (distance / scaled_radius)
                self.blend_pixel(x, y, (*color, int(alpha * 255.0 * strength * strength)))

    def draw_circle(self, cx: float, cy: float, radius: float, color: tuple[int, int, int, int]) -> None:
        center_x = cx * self.width
        center_y = cy * self.height
        scaled_radius = radius * self.width
        radius_sq = scaled_radius * scaled_radius

        x0 = max(0, int(center_x - scaled_radius))
        x1 = min(self.width - 1, int(center_x + scaled_radius))
        y0 = max(0, int(center_y - scaled_radius))
        y1 = min(self.height - 1, int(center_y + scaled_radius))

        for y in range(y0, y1 + 1):
            dy = y - center_y
            for x in range(x0, x1 + 1):
                dx = x - center_x
                if (dx * dx) + (dy * dy) <= radius_sq:
                    self.blend_pixel(x, y, color)

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        width_ratio: float,
        color: tuple[int, int, int, int],
    ) -> None:
        x1 = start[0] * self.width
        y1 = start[1] * self.height
        x2 = end[0] * self.width
        y2 = end[1] * self.height
        radius = (width_ratio * self.width) / 2.0

        min_x = max(0, int(min(x1, x2) - radius))
        max_x = min(self.width - 1, int(max(x1, x2) + radius))
        min_y = max(0, int(min(y1, y2) - radius))
        max_y = min(self.height - 1, int(max(y1, y2) + radius))

        dx = x2 - x1
        dy = y2 - y1
        length_sq = (dx * dx) + (dy * dy)

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if length_sq == 0:
                    distance = math.hypot(x - x1, y - y1)
                else:
                    projection = (((x - x1) * dx) + ((y - y1) * dy)) / length_sq
                    projection = clamp(projection, 0.0, 1.0)
                    nearest_x = x1 + (projection * dx)
                    nearest_y = y1 + (projection * dy)
                    distance = math.hypot(x - nearest_x, y - nearest_y)

                if distance <= radius:
                    self.blend_pixel(x, y, color)

    def draw_rect(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        color: tuple[int, int, int, int],
    ) -> None:
        x0 = max(0, int(left * self.width))
        x1 = min(self.width - 1, int(right * self.width))
        y0 = max(0, int(top * self.height))
        y1 = min(self.height - 1, int(bottom * self.height))

        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.blend_pixel(x, y, color)


def write_png(path: Path, width: int, height: int, rgba_bytes: bytes) -> None:
    raw = bytearray()
    stride = width * 4
    for row in range(height):
        raw.append(0)
        start = row * stride
        raw.extend(rgba_bytes[start:start + stride])

    def png_chunk(tag: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw), level=9)

    with path.open("wb") as file:
        file.write(b"\x89PNG\r\n\x1a\n")
        file.write(png_chunk(b"IHDR", header))
        file.write(png_chunk(b"IDAT", compressed))
        file.write(png_chunk(b"IEND", b""))


def pillow_ready() -> bool:
    return all(module is not None for module in (Image, ImageDraw, ImageFilter, ImageFont))


def ensure_existing_assets(paths: list[Path], description: str) -> None:
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing {description} assets ({', '.join(missing)}) and Pillow/font rendering is unavailable to regenerate them."
        )


def find_font(paths: list[str]) -> str:
    for raw_path in paths:
        if Path(raw_path).exists():
            return raw_path
    raise FileNotFoundError(f"No usable font found in: {paths}")


def load_emoji_font(preferred_size: int):
    if ImageFont is None:
        raise RuntimeError("Pillow is required for tray icon generation")

    font_path = find_font(EMOJI_FONT_PATHS)
    candidate_sizes = [preferred_size, *sorted(EMOJI_FONT_FALLBACK_SIZES, key=lambda size: abs(size - preferred_size))]
    attempted: set[int] = set()

    for size in candidate_sizes:
        if size in attempted:
            continue
        attempted.add(size)
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue

    raise OSError(f"Unable to load emoji font at a usable size from {font_path}")


def get_resample_filter():
    if Image is None:
        raise RuntimeError("Pillow is required for resampling")
    if hasattr(Image, "Resampling"):
        return Image.Resampling.LANCZOS
    return Image.LANCZOS


def create_linear_gradient(
    size: tuple[int, int],
    start_color: tuple[int, int, int],
    end_color: tuple[int, int, int],
) -> "Image.Image":
    if Image is None:
        raise RuntimeError("Pillow is required for installer art generation")

    width, height = size
    image = Image.new("RGBA", size, (*start_color, 255))
    pixels = image.load()

    for y in range(height):
        y_mix = y / max(height - 1, 1)
        for x in range(width):
            x_mix = x / max(width - 1, 1)
            mix = clamp((x_mix * 0.6) + (y_mix * 0.4), 0.0, 1.0)
            r = int(lerp(start_color[0], end_color[0], mix))
            g = int(lerp(start_color[1], end_color[1], mix))
            b = int(lerp(start_color[2], end_color[2], mix))
            pixels[x, y] = (r, g, b, 255)

    return image


def add_glow(
    image: "Image.Image",
    box: tuple[int, int, int, int],
    color: tuple[int, int, int, int],
    blur_radius: int,
) -> None:
    if Image is None or ImageDraw is None or ImageFilter is None:
        raise RuntimeError("Pillow is required for installer art generation")

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse(box, fill=color)
    image.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius)))


def wrap_text(draw: "ImageDraw.ImageDraw", text: str, font: "ImageFont.FreeTypeFont", max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        candidate = word if not current_line else f"{current_line} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current_line = candidate
            continue

        if current_line:
            lines.append(current_line)
        current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def draw_text_block(
    draw: "ImageDraw.ImageDraw",
    text: str,
    *,
    x: int,
    y: int,
    font: "ImageFont.FreeTypeFont",
    fill: tuple[int, int, int, int],
    max_width: int,
    line_gap: int,
) -> int:
    lines = wrap_text(draw, text, font, max_width)
    cursor_y = y

    for line in lines:
        draw.text((x, cursor_y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, cursor_y), line, font=font)
        cursor_y = bbox[3] + line_gap

    return cursor_y


def draw_peach(
    canvas: Canvas,
    center_x: float,
    center_y: float,
    scale: float,
    fruit_color: tuple[int, int, int, int],
    stem_color: tuple[int, int, int, int],
    leaf_color: tuple[int, int, int, int],
) -> None:
    # Two big round "cheeks" — the emoji butt shape
    left_cheek = (-0.14, 0.04, 0.22)
    right_cheek = (0.14, 0.04, 0.22)
    # Bridge at top connecting the cheeks
    top_bridge = (0.0, -0.10, 0.17)
    # Fill bottom gap
    bottom_fill = (0.0, 0.12, 0.18)

    for dx, dy, radius in [left_cheek, right_cheek, top_bridge, bottom_fill]:
        canvas.draw_circle(center_x + (dx * scale), center_y + (dy * scale), radius * scale, fruit_color)

    # Short stem
    canvas.draw_line(
        (center_x, center_y - (0.26 * scale)),
        (center_x - (0.02 * scale), center_y - (0.18 * scale)),
        0.025 * scale,
        stem_color,
    )
    # Small leaf
    canvas.draw_circle(center_x + (0.06 * scale), center_y - (0.27 * scale), 0.05 * scale, leaf_color)
    canvas.draw_circle(center_x + (0.10 * scale), center_y - (0.29 * scale), 0.04 * scale, leaf_color)


def draw_wind_lines(
    canvas: Canvas,
    origin_x: float,
    origin_y: float,
    line_color: tuple[int, int, int, int],
    line_width: float,
    num_lines: int = 3,
    spread: float = 0.10,
    length: float = 0.18,
    gap: float = 0.04,
) -> None:
    """Draw wavy wind/gas lines emanating to the right."""
    for i in range(num_lines):
        y_offset = spread * (i - (num_lines - 1) / 2.0)
        sx = origin_x + gap
        sy = origin_y + y_offset
        # Draw each wind line as 3 connected short segments for a wavy look
        seg_len = length / 3.0
        wave_amp = 0.015
        points = []
        for j in range(4):
            px = sx + (seg_len * j)
            py = sy + (wave_amp * (1 if j % 2 == 1 else -1) * (0.5 if j == 0 or j == 3 else 1.0))
            points.append((px, py))
        for j in range(len(points) - 1):
            canvas.draw_line(points[j], points[j + 1], line_width, line_color)


def draw_gas_cloud(
    canvas: Canvas,
    cx: float,
    cy: float,
    cloud_color: tuple[int, int, int, int],
) -> None:
    """Draw a small green-ish gas cloud puff."""
    canvas.draw_circle(cx, cy, 0.035, cloud_color)
    canvas.draw_circle(cx + 0.03, cy - 0.015, 0.025, cloud_color)
    canvas.draw_circle(cx + 0.025, cy + 0.02, 0.022, cloud_color)
    canvas.draw_circle(cx - 0.02, cy - 0.01, 0.020, cloud_color)


def render_brand_icon(size: int) -> bytes:
    canvas = Canvas(size, size)
    canvas.fill_rounded_gradient((255, 247, 240), (255, 214, 186), radius_ratio=0.23)
    canvas.draw_radial_glow(0.15, 0.14, 0.22, (255, 255, 249), 0.80)
    canvas.draw_radial_glow(0.85, 0.86, 0.28, (255, 176, 138), 0.30)

    shadow_color = (210, 120, 100, 255)
    fruit_color = (255, 170, 130, 255)
    blush_color = (255, 130, 120, 135)
    crease_color = (230, 105, 85, 220)
    highlight_color = (255, 220, 200, 120)
    stem_color = (100, 65, 40, 255)
    leaf_color = (90, 175, 85, 255)

    # Gas cloud (behind the peach, to the right)
    gas_color = (180, 210, 140, 100)
    draw_gas_cloud(canvas, 0.72, 0.56, gas_color)

    # Wind lines (behind the peach shadow, creating depth)
    wind_color = (200, 180, 150, 180)
    draw_wind_lines(canvas, 0.58, 0.55, wind_color, 0.028, num_lines=4, spread=0.14, length=0.26, gap=0.04)

    # Peach shadow
    draw_peach(canvas, 0.352, 0.555, 0.92, shadow_color, shadow_color, shadow_color)
    # Main peach body
    draw_peach(canvas, 0.34, 0.53, 0.84, fruit_color, stem_color, leaf_color)

    # Crease line down the middle
    canvas.draw_line((0.34, 0.32), (0.335, 0.68), 0.014, crease_color)

    # Blush on each cheek
    canvas.draw_circle(0.23, 0.57, 0.10, blush_color)
    canvas.draw_circle(0.44, 0.56, 0.10, blush_color)

    # Highlight/shine
    canvas.draw_circle(0.26, 0.38, 0.05, highlight_color)
    canvas.draw_circle(0.30, 0.34, 0.03, (255, 240, 230, 160))

    # Foreground wind lines (brighter, on top)
    wind_fg = (255, 250, 240, 220)
    draw_wind_lines(canvas, 0.56, 0.54, wind_fg, 0.032, num_lines=3, spread=0.12, length=0.22, gap=0.06)

    return bytes(canvas.data)


def render_emoji_glyph(size: int) -> "Image.Image":
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is required for tray icon generation")

    resample_filter = get_resample_filter()
    scale = 6
    canvas_size = size * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    font = load_emoji_font(int(canvas_size * 0.74))
    bbox = draw.textbbox((0, 0), "💨", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = ((canvas_size - text_width) // 2) - bbox[0]
    y = ((canvas_size - text_height) // 2) - bbox[1]
    draw.text((x, y), "💨", font=font, embedded_color=True)

    return image.resize((size, size), resample_filter)


def render_tray_template_icon(size: int) -> "Image.Image":
    if Image is None:
        raise RuntimeError("Pillow is required for tray icon generation")

    emoji = render_emoji_glyph(size)
    alpha = emoji.getchannel("A")
    boosted_alpha = alpha.point(lambda value: min(255, int(value * 1.35)))
    template = Image.new("RGBA", emoji.size, (0, 0, 0, 0))
    template.paste((0, 0, 0, 255), (0, 0), boosted_alpha)
    return template


def render_windows_tray_icon(size: int) -> "Image.Image":
    if Image is None:
        raise RuntimeError("Pillow is required for tray icon generation")

    return render_emoji_glyph(size)


def build_ico(png_paths: list[Path], target_path: Path) -> None:
    payloads = [png_path.read_bytes() for png_path in png_paths]
    count = len(payloads)
    header = struct.pack("<HHH", 0, 1, count)
    directory = bytearray()
    offset = 6 + (16 * count)

    for png_path, payload in zip(png_paths, payloads):
        size = int(png_path.stem.split("-")[-1])
        icon_size = 0 if size >= 256 else size
        directory.extend(struct.pack("<BBBBHHII", icon_size, icon_size, 0, 0, 1, 32, len(payload), offset))
        offset += len(payload)

    with target_path.open("wb") as ico_file:
        ico_file.write(header)
        ico_file.write(directory)
        for payload in payloads:
            ico_file.write(payload)


def build_icns(icon_entries: list[tuple[str, Path]], target_path: Path) -> None:
    chunks: list[bytes] = []
    total_length = 8

    for icon_type, png_path in icon_entries:
        payload = png_path.read_bytes()
        chunk = icon_type.encode("ascii") + struct.pack(">I", len(payload) + 8) + payload
        chunks.append(chunk)
        total_length += len(chunk)

    with target_path.open("wb") as icns_file:
        icns_file.write(b"icns")
        icns_file.write(struct.pack(">I", total_length))
        for chunk in chunks:
            icns_file.write(chunk)


def save_icon_assets() -> None:
    for stale_file in (APP_ASSETS_DIR / "icon-source.svg", APP_ASSETS_DIR / "tray-source.svg"):
        if stale_file.exists():
            stale_file.unlink()

    # Brand icon PNGs are pre-generated (💨 emoji) and committed to the repo.
    # Only regenerate if a PNG is missing — never overwrite committed icons.
    brand_sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    for size in brand_sizes:
        png_path = APP_ASSETS_DIR / f"icon-{size}.png"
        if not png_path.exists():
            rgba_bytes = render_brand_icon(size)
            write_png(png_path, size, size, rgba_bytes)

    shutil.copy2(APP_ASSETS_DIR / "icon-1024.png", APP_ASSETS_DIR / "brand-mark.png")
    shutil.copy2(APP_ASSETS_DIR / "icon-1024.png", WEBSITE_DIR / "brand-mark.png")
    shutil.copy2(APP_ASSETS_DIR / "icon-256.png", WEBSITE_DIR / "favicon.png")

    build_ico(
        [
            APP_ASSETS_DIR / "icon-16.png",
            APP_ASSETS_DIR / "icon-32.png",
            APP_ASSETS_DIR / "icon-48.png",
            APP_ASSETS_DIR / "icon-64.png",
            APP_ASSETS_DIR / "icon-128.png",
            APP_ASSETS_DIR / "icon-256.png",
        ],
        APP_ASSETS_DIR / "icon.ico",
    )

    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    for base_size in (16, 32, 128, 256, 512):
        shutil.copy2(APP_ASSETS_DIR / f"icon-{base_size}.png", ICONSET_DIR / f"icon_{base_size}x{base_size}.png")
        shutil.copy2(APP_ASSETS_DIR / f"icon-{base_size * 2}.png", ICONSET_DIR / f"icon_{base_size}x{base_size}@2x.png")

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

    save_tray_assets()


def save_tray_assets() -> None:
    tray_paths = [
        APP_ASSETS_DIR / "trayTemplate.png",
        APP_ASSETS_DIR / "trayTemplate@2x.png",
        APP_ASSETS_DIR / "tray.png",
    ]

    if not pillow_ready():
        ensure_existing_assets(tray_paths, "tray")
        return

    try:
        render_tray_template_icon(18).save(tray_paths[0])
        render_tray_template_icon(36).save(tray_paths[1])
        render_windows_tray_icon(32).save(tray_paths[2])
    except FileNotFoundError:
        ensure_existing_assets(tray_paths, "tray")


def paste_brand_mark(image: "Image.Image", *, x: int, y: int, max_width: int, max_height: int) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required for installer art generation")

    resample_filter = get_resample_filter()
    brand_mark = Image.open(APP_ASSETS_DIR / "brand-mark.png").convert("RGBA")
    scale = min(max_width / brand_mark.width, max_height / brand_mark.height)
    target_size = (max(1, int(brand_mark.width * scale)), max(1, int(brand_mark.height * scale)))
    resized = brand_mark.resize(target_size, resample_filter)
    image.alpha_composite(resized, (x, y))


def render_dmg_background() -> "Image.Image":
    if not pillow_ready():
        raise RuntimeError("Pillow is required for DMG background generation")

    image = create_linear_gradient((720, 460), (12, 15, 24), (31, 37, 54))
    draw = ImageDraw.Draw(image)

    add_glow(image, (-40, -120, 280, 180), (255, 201, 49, 150), 60)
    add_glow(image, (500, 230, 760, 520), (97, 132, 255, 85), 80)

    headline_font = ImageFont.truetype(find_font(DISPLAY_FONT_PATHS), 40)
    subhead_font = ImageFont.truetype(find_font(BODY_FONT_PATHS), 18)
    note_font = ImageFont.truetype(find_font(BODY_FONT_PATHS), 15)

    paste_brand_mark(image, x=42, y=38, max_width=92, max_height=92)

    draw_text_block(
        draw,
        "Drag FartPort into Applications",
        x=156,
        y=54,
        font=headline_font,
        fill=(245, 247, 250, 255),
        max_width=470,
        line_gap=8,
    )
    next_y = draw_text_block(
        draw,
        "Then eject the disk image. If macOS gets grumpy on first launch, the download page has the quick fix.",
        x=156,
        y=150,
        font=subhead_font,
        fill=(198, 206, 218, 255),
        max_width=485,
        line_gap=7,
    )

    badge_top = next_y + 22
    draw.rounded_rectangle((44, badge_top, 278, badge_top + 38), radius=18, fill=(255, 204, 51, 34), outline=(255, 211, 92, 96))
    draw.text((64, badge_top + 10), "Tiny app. Big pfft.", font=note_font, fill=(255, 231, 154, 255))

    for offset in range(3):
        top = 286 + (offset * 20)
        draw.line((138, top, 530, top - 6), fill=(255, 215, 105, 70), width=3)

    return image


def render_installer_sidebar(title: str, body: str, footer: str) -> "Image.Image":
    if not pillow_ready():
        raise RuntimeError("Pillow is required for NSIS art generation")

    image = create_linear_gradient((164, 314), (11, 13, 20), (27, 31, 44))
    draw = ImageDraw.Draw(image)

    add_glow(image, (-30, -40, 130, 120), (255, 204, 51, 120), 36)
    add_glow(image, (60, 160, 210, 340), (80, 108, 220, 80), 48)

    title_font = ImageFont.truetype(find_font(DISPLAY_FONT_PATHS), 20)
    body_font = ImageFont.truetype(find_font(BODY_FONT_PATHS), 13)
    footer_font = ImageFont.truetype(find_font(BODY_FONT_PATHS), 10)

    paste_brand_mark(image, x=22, y=22, max_width=74, max_height=74)
    draw_text_block(
        draw,
        title,
        x=22,
        y=124,
        font=title_font,
        fill=(248, 249, 251, 255),
        max_width=118,
        line_gap=4,
    )
    draw_text_block(
        draw,
        body,
        x=22,
        y=176,
        font=body_font,
        fill=(206, 212, 224, 255),
        max_width=120,
        line_gap=5,
    )

    draw.rounded_rectangle((18, 248, 146, 304), radius=14, fill=(255, 203, 42, 26), outline=(255, 211, 92, 92))
    draw_text_block(
        draw,
        footer,
        x=28,
        y=258,
        font=footer_font,
        fill=(255, 236, 180, 255),
        max_width=94,
        line_gap=3,
    )

    return image


def render_installer_header() -> "Image.Image":
    if not pillow_ready():
        raise RuntimeError("Pillow is required for NSIS art generation")

    image = create_linear_gradient((150, 57), (12, 15, 24), (32, 35, 46))
    draw = ImageDraw.Draw(image)

    add_glow(image, (-12, -18, 74, 74), (255, 204, 51, 96), 18)
    paste_brand_mark(image, x=10, y=10, max_width=36, max_height=36)

    title_font = ImageFont.truetype(find_font(DISPLAY_FONT_PATHS), 18)
    subtitle_font = ImageFont.truetype(find_font(BODY_FONT_PATHS), 11)
    draw.text((56, 10), "FartPort", font=title_font, fill=(247, 248, 250, 255))
    draw.text((56, 31), "Tiny utility. Big pfft.", font=subtitle_font, fill=(208, 214, 223, 255))

    return image


def save_installer_art() -> None:
    required_paths = [
        BUILD_DIR / "dmg-background.png",
        BUILD_DIR / "installerSidebar.bmp",
        BUILD_DIR / "uninstallerSidebar.bmp",
        BUILD_DIR / "installerHeader.bmp",
    ]

    if not pillow_ready():
        ensure_existing_assets(required_paths, "installer")
        return

    try:
        render_dmg_background().save(required_paths[0])
        render_installer_sidebar(
            "Install FartPort",
            "Charger drama in. Punchline out.",
            "SmartScreen? More info, then Run anyway.",
        ).convert("RGB").save(required_paths[1])
        render_installer_sidebar(
            "Pulling the plug?",
            "Removing FartPort brings peace back to your power menu.",
            "You can always reinstall when the room needs more nonsense.",
        ).convert("RGB").save(required_paths[2])
        render_installer_header().convert("RGB").save(required_paths[3])
    except FileNotFoundError:
        ensure_existing_assets(required_paths, "installer")


def synthesize_fart(
    output_path: Path,
    *,
    duration_seconds: float,
    start_frequency: float,
    end_frequency: float,
    tone_mix: float,
    noise_mix: float,
    pop_mix: float,
    sparkle_mix: float,
    seed: int,
) -> None:
    sample_rate = 44_100
    total_samples = int(sample_rate * duration_seconds)
    rng = random.Random(seed)
    phase = 0.0
    noise = 0.0
    samples: list[float] = []

    for index in range(total_samples):
        time = index / sample_rate
        progress = time / duration_seconds

        attack = min(1.0, time / 0.028)
        decay = max(0.0, 1.0 - progress) ** 1.34
        envelope = attack * decay

        frequency_curve = progress ** 1.18
        base_frequency = max(
            end_frequency,
            start_frequency - ((start_frequency - end_frequency) * frequency_curve) + (10.0 * math.sin(2 * math.pi * 2.4 * time)),
        )
        phase += (2 * math.pi * base_frequency) / sample_rate

        body = 0.76 * math.sin(phase) + 0.24 * math.sin((phase * 1.93) + 0.38)

        noise = (noise * 0.86) + (rng.uniform(-1.0, 1.0) * 0.14)
        rasp = noise * (0.62 if 0.035 < time < (duration_seconds * 0.72) else 0.22)

        pop = math.sin(2 * math.pi * 64.0 * time) * math.exp(-24.0 * time)
        sparkle = math.sin(2 * math.pi * (7.0 + (3.0 * math.sin(2 * math.pi * 0.8 * time))) * time) * math.sin(phase * 0.28)

        sample = ((body * tone_mix) + (rasp * noise_mix) + (pop * pop_mix) + (sparkle * sparkle_mix)) * envelope * 0.94
        samples.append(sample)

    peak = max(max(samples), abs(min(samples)), 1e-6)
    frames = [int(clamp(sample / peak, -1.0, 1.0) * 32767.0) for sample in samples]

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(struct.pack("<h", frame) for frame in frames))


def generate_fart_sounds() -> None:
    # Audio files (plugged-fart.mp3 and unplugged-fart.mp3) are pre-supplied
    # in assets/audio/ — no synthesis needed.
    for expected in ("plugged-fart.mp3", "unplugged-fart.mp3"):
        if not (AUDIO_ASSETS_DIR / expected).exists():
            raise FileNotFoundError(f"Missing audio asset: {AUDIO_ASSETS_DIR / expected}")


def ensure_dirs() -> None:
    for directory in (APP_ASSETS_DIR, AUDIO_ASSETS_DIR, WEBSITE_DIR, BUILD_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def main() -> None:
    ensure_dirs()
    print("Generating icon assets...", flush=True)
    save_icon_assets()
    print("Generating installer artwork...", flush=True)
    save_installer_art()
    print("Generating audio assets...", flush=True)
    generate_fart_sounds()
    print("Generated FartPort icon and audio assets.", flush=True)


if __name__ == "__main__":
    main()
