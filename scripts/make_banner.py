"""Generate dark/light animated GitHub profile banners.

Usage: python scripts/make_banner.py
Requires source-photo.jpg and source-mask.png from prep_photo.py.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parent.parent
PHOTO = ROOT / "source-photo.jpg"
MASK = ROOT / "source-mask.png"
DATA = ROOT / "data"

GRID_W, GRID_H = 300, 340
CANVAS_W, CANVAS_H = 1180, 610
PORTRAIT_COLOR = {"dark": "#A78BFA", "light": "#7C3AED"}
CHROME = "#10B981"
ACCENT = {"dark": "#22D3EE", "light": "#0891B2"}
BACKGROUND = {"dark": "#0A101F", "light": "#F4F7FB"}
PANEL = {"dark": "#0D1424", "light": "#FFFFFF"}
TEXT = {"dark": "#E6EDF3", "light": "#172033"}
MUTED = {"dark": "#8290A4", "light": "#667085"}
DOT_SIZE = 1
INTRO_GROUPS = 60
DRIFT_BANDS = 94
TRAVELLER_COUNT = 900
LOOP_SECONDS = 14.2
FRAME_X, FRAME_Y, FRAME_W, FRAME_H = 28, 82, 420, 500
IMAGE_Y, IMAGE_SCALE = 119, 1.18
SEED = 650

# Profile details reused from the existing info card and confirmed by the user.
DISPLAY_NAME = "Shad"
USERNAME = "shaad0650"
ROLE = "Backend Intern @ Harman International"
ORIGIN = "Kozhikode"
EDUCATION = "IIIT DM Jabalpur, class of 2027"
STATUS = "Building · Learning · Shipping"
TOOLCHAIN = "VS Code · Git"
LANGUAGES = "TypeScript · JavaScript"
FRONTEND = "Next.js · React Native/Expo"
BACKEND = "Node.js · Socket.io"
DATABASE = "PostgreSQL/PostGIS · Redis"
GITHUB = "github.com/shaad0650"

EVENT_SECONDS = np.array([0.0, 3.0, 4.3, 6.3, 7.6, 9.6, 10.9, 12.9, LOOP_SECONDS])
KEY_TIMES = ";".join(f"{v / LOOP_SECONDS:.5f}" for v in EVENT_SECONDS)


def crop_to_grid_aspect(image: Image.Image, mask: Image.Image) -> tuple[Image.Image, Image.Image]:
    target_ratio = GRID_W / GRID_H
    width, height = image.size
    if width / height > target_ratio:
        crop_w = round(height * target_ratio)
        left = (width - crop_w) // 2
        box = (left, 0, left + crop_w, height)
    else:
        crop_h = round(width / target_ratio)
        top = max(0, min(height - crop_h, round(height * 0.04)))
        box = (0, top, width, top + crop_h)

    image = image.crop(box).resize((GRID_W, GRID_H), Image.Resampling.LANCZOS)
    mask = mask.crop(box).resize((GRID_W, GRID_H), Image.Resampling.LANCZOS)
    return image, mask


def clean_subject_mask(mask_image: Image.Image) -> np.ndarray:
    raw = np.asarray(mask_image.convert("L"), dtype=np.uint8)
    mask = np.where(raw >= 112, 255, 0).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    flood = mask.copy()
    flood_pad = np.zeros((GRID_H + 2, GRID_W + 2), dtype=np.uint8)
    cv2.floodFill(flood, flood_pad, (0, 0), 255)
    mask = cv2.bitwise_or(mask, cv2.bitwise_not(flood))

    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count <= 1:
        raise ValueError("The source mask contains no foreground subject.")
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    cleaned = np.where(labels == largest, 255, 0).astype(np.uint8)
    return cleaned > 0


def prepare_raster() -> tuple[np.ndarray, np.ndarray]:
    if not PHOTO.is_file():
        raise FileNotFoundError(f"Portrait photo not found: {PHOTO}")
    if not MASK.is_file():
        raise FileNotFoundError(
            f"Subject mask not found: {MASK}. Run scripts/prep_photo.py first."
        )

    image = Image.open(PHOTO).convert("RGB")
    mask_image = Image.open(MASK).convert("L")
    if image.size != mask_image.size:
        raise ValueError("source-photo.jpg and source-mask.png must have matching dimensions.")

    image, mask_image = crop_to_grid_aspect(image, mask_image)
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.3)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=3, percent=140))
    subject = clean_subject_mask(mask_image)
    return np.asarray(gray, dtype=np.uint8), subject


def floyd_steinberg(gray: np.ndarray, foreground: np.ndarray | None, dark_mode: bool) -> np.ndarray:
    source = gray.astype(np.float32)
    work = 255.0 - source if dark_mode else source.copy()
    if foreground is None:
        foreground = np.ones(work.shape, dtype=bool)
    dots = np.zeros(work.shape, dtype=bool)
    height, width = work.shape

    for y in range(height):
        forward = (y % 2) == 0
        xs = range(width) if forward else range(width - 1, -1, -1)
        direction = 1 if forward else -1
        for x in xs:
            if not foreground[y, x]:
                work[y, x] = 255.0
                continue

            old = float(np.clip(work[y, x], 0.0, 255.0))
            new = 0.0 if old < 128.0 else 255.0
            dots[y, x] = new == 0.0
            error = old - new
            neighbors = (
                (x + direction, y, 7 / 16),
                (x - direction, y + 1, 3 / 16),
                (x, y + 1, 5 / 16),
                (x + direction, y + 1, 1 / 16),
            )
            for nx, ny, weight in neighbors:
                if 0 <= nx < width and ny < height and foreground[ny, nx]:
                    work[ny, nx] += error * weight

    return dots


def logo_masks() -> tuple[list[np.ndarray], list[str]]:
    labels = ["NODE.JS", "TYPESCRIPT", "NEXT.JS"]
    masks: list[np.ndarray] = []
    for kind in range(3):
        canvas = Image.new("L", (GRID_W, GRID_H), 0)
        draw = ImageDraw.Draw(canvas)
        cx, cy = GRID_W // 2, GRID_H // 2
        if kind == 0:
            nodes = [(cx, cy - 38), (cx - 34, cy + 22), (cx + 34, cy + 22)]
            draw.line([nodes[0], nodes[1]], fill=255, width=8)
            draw.line([nodes[0], nodes[2]], fill=255, width=8)
            draw.line([nodes[1], nodes[2]], fill=255, width=8)
            for x, y in nodes:
                draw.ellipse((x - 11, y - 11, x + 11, y + 11), fill=255)
        elif kind == 1:
            draw.line([(cx - 48, cy - 35), (cx - 78, cy), (cx - 48, cy + 35)],
                      fill=255, width=10, joint="curve")
            draw.line([(cx + 48, cy - 35), (cx + 78, cy), (cx + 48, cy + 35)],
                      fill=255, width=10, joint="curve")
            draw.line([(cx + 19, cy - 43), (cx - 19, cy + 43)], fill=255, width=9)
        else:
            draw.line([(cx - 35, cy + 40), (cx - 35, cy - 40),
                       (cx + 35, cy + 40), (cx + 35, cy - 40)],
                      fill=255, width=11, joint="curve")
        masks.append(np.asarray(canvas, dtype=np.uint8) > 0)
    return masks, labels


def sample_shape(mask: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    yx = np.argwhere(mask)
    if len(yx) == 0:
        raise ValueError("A logo morph target has no drawable pixels.")
    selected = rng.choice(len(yx), size=count, replace=len(yx) < count)
    return yx[selected][:, ::-1].astype(np.float32)


def optimally_match_shapes(masks: list[np.ndarray], rng: np.random.Generator) -> np.ndarray:
    shapes = [sample_shape(mask, TRAVELLER_COUNT, rng) for mask in masks]
    matched = [shapes[0]]
    for source, target in zip(shapes, shapes[1:] + shapes[:1]):
        delta = source[:, None, :] - target[None, :, :]
        cost = np.sqrt(np.sum(delta * delta, axis=2))
        rows, cols = linear_sum_assignment(cost)
        ordered = np.empty_like(target)
        ordered[rows] = target[cols]
        matched.append(ordered)
    return np.stack(matched)


def path_for_points(points: np.ndarray) -> str:
    if len(points) == 0:
        return ""
    rows: dict[int, list[int]] = {}
    for x, y in points:
        rows.setdefault(int(y), []).append(int(x))

    commands: list[str] = []
    for y in sorted(rows):
        xs = sorted(set(rows[y]))
        start = previous = xs[0]
        for x in xs[1:] + [GRID_W + 2]:
            if x != previous + 1:
                run = previous - start + 1
                commands.append(f"M{start},{y + 0.5}h{run}")
                start = x
            previous = x
    return "".join(commands)


def band_labels(points: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    logo_center = np.array([GRID_W / 2, GRID_H / 2], dtype=np.float32)
    direction = logo_center - points.mean(axis=0)
    if np.linalg.norm(direction) < 1:
        direction = np.array([1.0, 0.0], dtype=np.float32)
    direction /= np.linalg.norm(direction)
    projection = points @ direction + rng.normal(0, 4, len(points))
    order = np.argsort(projection)
    labels = np.empty(len(points), dtype=np.int16)
    labels[order] = np.minimum(
        np.arange(len(points)) * DRIFT_BANDS // len(points), DRIFT_BANDS - 1
    )
    return labels


def evenness_metric(points: np.ndarray, groups: np.ndarray) -> float:
    if len(points) == 0:
        return 0.0
    bounds_x = np.linspace(0, GRID_W + 1, 5)
    bounds_y = np.linspace(0, GRID_H + 1, 5)
    global_hist, _, _ = np.histogram2d(points[:, 1], points[:, 0], bins=(bounds_y, bounds_x))
    global_dist = global_hist.ravel() / global_hist.sum()
    scores = []
    for group in np.unique(groups):
        subset = points[groups == group]
        hist, _, _ = np.histogram2d(subset[:, 1], subset[:, 0], bins=(bounds_y, bounds_x))
        scores.append(np.abs(hist.ravel() / hist.sum() - global_dist).sum() / 2)
    return float(np.mean(scores))


def interleaved_group_labels(points: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    labels = np.empty(len(points), dtype=np.int16)
    cell_x = np.minimum(points[:, 0] * 10 // GRID_W, 9)
    cell_y = np.minimum(points[:, 1] * 10 // GRID_H, 9)
    offsets = rng.integers(0, INTRO_GROUPS, 100)
    for y in range(10):
        for x in range(10):
            indices = np.flatnonzero((cell_x == x) & (cell_y == y))
            rng.shuffle(indices)
            labels[indices] = (np.arange(len(indices)) + offsets[y * 10 + x]) % INTRO_GROUPS
    return labels


def svg_path(path: str, color: str, extra: str = "") -> str:
    return (
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{DOT_SIZE}" '
        f'stroke-linecap="butt" shape-rendering="crispEdges" {extra}/>'
    )


def rows_for_theme(theme: str) -> str:
    rows = [
        ("Subject", DISPLAY_NAME),
        ("Role", ROLE),
        ("Origin", ORIGIN),
        ("Education", EDUCATION),
        ("Status", STATUS),
        ("ToolChain", TOOLCHAIN),
        ("Core.Lang", LANGUAGES),
        ("Core.Frontend", FRONTEND),
        ("Core.Backend", BACKEND),
        ("Core.Database", DATABASE),
        ("Grid.GitHub", GITHUB),
    ]
    panel_text = TEXT[theme]
    muted = MUTED[theme]
    left_x, right_x, row_y, line_h = 505, 1138, 175, 23
    parts: list[str] = []
    for index, (label, value) in enumerate(rows):
        y = row_y + index * line_h
        value_chars = len(value)
        value_width = min(436, max(24, value_chars * 8.4))
        value_x = right_x - value_width
        label_width = len(label) * 8.4
        leader_start = left_x + label_width + 10
        leader_end = value_x - 12
        leader_count = max(0, int((leader_end - leader_start) / 16.8))
        leaders = "· " * leader_count
        parts.append(
            f'<text x="{left_x}" y="{y}" font-size="14" fill="{muted}">{label}</text>'
            f'<text x="{leader_start}" y="{y}" font-size="14" fill="{muted}" '
            f'>{leaders}</text>'
            f'<text x="{right_x}" y="{y}" text-anchor="end" textLength="{value_width:.1f}" '
            f'lengthAdjust="spacingAndGlyphs" font-size="14" fill="{panel_text}">{value}</text>'
        )
    return "\n".join(parts)


def make_svg(theme: str, ink_points: np.ndarray,
             logo_points: np.ndarray, logo_labels: list[str], rng: np.random.Generator) -> str:
    background, panel, text = BACKGROUND[theme], PANEL[theme], TEXT[theme]
    muted, ink, accent = MUTED[theme], PORTRAIT_COLOR[theme], ACCENT[theme]
    scale = IMAGE_SCALE
    offset_x = FRAME_X + (FRAME_W - GRID_W * scale) / 2
    loop_groups = band_labels(ink_points, rng)
    intro_groups = interleaved_group_labels(ink_points, rng)

    loop_paths: list[str] = []
    for group in range(DRIFT_BANDS):
        subset = ink_points[loop_groups == group]
        path = path_for_points(subset)
        if not path:
            continue
        center = subset.mean(axis=0)
        logo_center = logo_points[0].mean(axis=0)
        dx, dy = (logo_center - center) * 0.42
        group_attrs = (
            f'<animate attributeName="opacity" values="1;1;0;0;0;0;0;0;1" '
            f'keyTimes="{KEY_TIMES}" dur="{LOOP_SECONDS}s" begin="3.2s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;0 0;{dx:.2f} {dy:.2f};{dx:.2f} {dy:.2f};'
            f'{dx:.2f} {dy:.2f};{dx:.2f} {dy:.2f};{dx:.2f} {dy:.2f};'
            f'{dx:.2f} {dy:.2f};0 0" keyTimes="{KEY_TIMES}" dur="{LOOP_SECONDS}s" '
            'begin="3.2s" repeatCount="indefinite"/>'
        )
        loop_paths.append(
            f'<g>{svg_path(path, ink)}{group_attrs}</g>'
        )

    intro_paths: list[str] = []
    for group in range(INTRO_GROUPS):
        path = path_for_points(ink_points[intro_groups == group])
        if not path:
            continue
        end = 0.55 + 1.45 * group / max(INTRO_GROUPS - 1, 1)
        anim = (
            f'<animate attributeName="opacity" values="0;1;1;0" '
            f'keyTimes="0;{end / 3.2:.5f};0.94;1" dur="3.2s" fill="freeze"/>'
        )
        intro_paths.append(f'<g>{svg_path(path, ink)}{anim}</g>')

    labels = []
    for index, name in enumerate(logo_labels):
        values = ["0"] * 9
        values[2 * index + 2] = "1"
        values[2 * index + 3] = "1"
        labels.append(
            f'<text x="{GRID_W / 2:.0f}" y="{GRID_H - 7}" text-anchor="middle" '
            f'font-size="9" letter-spacing="2" fill="{accent}" opacity="0">{name}'
            f'<animate attributeName="opacity" values="{";".join(values)}" '
            f'keyTimes="{KEY_TIMES}" dur="{LOOP_SECONDS}s" begin="3.2s" '
            'repeatCount="indefinite"/></text>'
        )

    traveller_parts = []
    for index in range(TRAVELLER_COUNT):
        x0, y0 = logo_points[0, index]
        x1, y1 = logo_points[1, index]
        x2, y2 = logo_points[2, index]
        x3, y3 = logo_points[3, index]
        x_values = [x0, x0, x0, x0, x1, x1, x2, x2, x3]
        y_values = [y0, y0, y0, y0, y1, y1, y2, y2, y3]
        traveller_parts.append(
            f'<circle r="1.35" fill="{accent}" cx="{x0:.1f}" cy="{y0:.1f}">'
            f'<animate attributeName="cx" values="{";".join(f"{v:.1f}" for v in x_values)}" '
            f'keyTimes="{KEY_TIMES}" dur="{LOOP_SECONDS}s" begin="3.2s" repeatCount="indefinite"/>'
            f'<animate attributeName="cy" values="{";".join(f"{v:.1f}" for v in y_values)}" '
            f'keyTimes="{KEY_TIMES}" dur="{LOOP_SECONDS}s" begin="3.2s" repeatCount="indefinite"/>'
            '</circle>'
        )

    header = f"""
      <rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="18"
            fill="{background}" stroke="{CHROME}" stroke-opacity=".42"/>
      <path d="M18 58H1162" stroke="{CHROME}" stroke-opacity=".45"/>
      <circle cx="30" cy="30" r="5" fill="#EF4444">
        <animate attributeName="opacity" values="1;.35;1" dur="1.2s" repeatCount="indefinite"/>
      </circle>
      <text x="48" y="35" font-size="13" fill="{text}" letter-spacing="2">VISUAL.MAP</text>
      <text x="930" y="35" text-anchor="end" font-size="13" fill="{muted}">profile.sh --live</text>
      <text x="1008" y="35" text-anchor="end" font-size="12" fill="#EF4444">LIVE</text>
      <rect x="1030" y="17" width="124" height="28" rx="14" fill="{CHROME}" fill-opacity=".14"
            stroke="{CHROME}" stroke-opacity=".65"/>
      <text x="1092" y="36" text-anchor="middle" font-size="14" fill="{CHROME}">@{USERNAME}</text>
      <rect x="{FRAME_X}" y="{FRAME_Y}" width="{FRAME_W}" height="{FRAME_H}" rx="14"
            fill="{panel}" stroke="{CHROME}" stroke-opacity=".55"/>
      <rect x="474" y="{FRAME_Y}" width="678" height="{FRAME_H}" rx="14"
            fill="{panel}" stroke="{CHROME}" stroke-opacity=".3"/>
      <text x="505" y="121" font-size="13" fill="{accent}" letter-spacing="2">SYSTEM.INFO</text>
      <text x="1138" y="121" text-anchor="end" font-size="12" fill="{muted}">PROFILE.READOUT</text>
      <text x="58" y="568" font-size="11" fill="{muted}" letter-spacing="1">MORPH / NODE.JS · TYPESCRIPT · NEXT.JS</text>
      <text x="505" y="548" font-size="12" fill="{muted}" letter-spacing="1">
        {DISPLAY_NAME.upper()} · {ORIGIN.upper()} · GITHUB.COM/{USERNAME.upper()}
      </text>
    """

    intro_start = (
        f'<g transform="translate({offset_x:.1f},{IMAGE_Y}) scale({scale})">'
        + "".join(intro_paths)
        + "</g>"
    )
    loop_portrait = (
        f'<g transform="translate({offset_x:.1f},{IMAGE_Y}) scale({scale})">'
        + "".join(loop_paths)
        + f'<animate attributeName="opacity" values="1;1;0;0;0;0;0;0;1" '
          f'keyTimes="{KEY_TIMES}" dur="{LOOP_SECONDS}s" begin="3.2s" repeatCount="indefinite"/>'
        + "</g>"
    )
    travellers = (
        f'<g transform="translate({offset_x:.1f},{IMAGE_Y}) scale({scale})" opacity="0">'
        f'<animate attributeName="opacity" values="0;0;1;1;1;1;1;1;0" '
        f'keyTimes="{KEY_TIMES}" dur="{LOOP_SECONDS}s" begin="3.2s" repeatCount="indefinite"/>'
        + "".join(labels)
        + "".join(traveller_parts)
        + "</g>"
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}"
      viewBox="0 0 {CANVAS_W} {CANVAS_H}">
      <style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}</style>
      <title>{DISPLAY_NAME} · GitHub profile · {theme} theme</title>
      <rect width="{CANVAS_W}" height="{CANVAS_H}" fill="{background}"/>
      {header}
      {intro_start}
      {loop_portrait}
      {travellers}
      {rows_for_theme(theme)}
    </svg>"""
    return "\n".join(line.rstrip() for line in svg.splitlines()).strip() + "\n"


def main() -> None:
    rng = np.random.default_rng(SEED)
    gray, subject = prepare_raster()
    dark_dots = floyd_steinberg(gray, subject, dark_mode=True)
    light_dots = floyd_steinberg(gray, None, dark_mode=False)
    np.save(DATA / "banner_dark_points.npy", dark_dots)
    np.save(DATA / "banner_light_points.npy", light_dots)
    np.save(DATA / "banner_gray.npy", gray)
    np.save(DATA / "banner_mask.npy", subject)

    logo_mask_list, logo_labels = logo_masks()
    logo_points = optimally_match_shapes(logo_mask_list, rng)
    np.save(DATA / "banner_logo_points.npy", logo_points)

    for theme, dots in (
        ("dark", np.argwhere(dark_dots)[:, ::-1]),
        ("light", np.argwhere(light_dots)[:, ::-1]),
    ):
        svg = make_svg(theme, dots, logo_points, logo_labels, rng)
        output = ROOT / f"{theme}.svg"
        output.write_text(svg, encoding="utf-8")
        print(f"wrote {output.name}: {output.stat().st_size:,} bytes, {len(dots):,} portrait dots")

    points = np.argwhere(dark_dots)[:, ::-1]
    groups = interleaved_group_labels(points, np.random.default_rng(SEED))
    print(f"dark intro interleaving deviation: {evenness_metric(points, groups):.4f}")
    print(f"dark portrait drift bands: {DRIFT_BANDS}; logo travellers: {TRAVELLER_COUNT}")


if __name__ == "__main__":
    main()
