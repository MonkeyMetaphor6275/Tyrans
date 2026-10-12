from __future__ import annotations

import argparse
import base64
import csv
import tempfile
import mimetypes
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageEnhance, ImageFont, ImageOps

renderPM = None

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import A4
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    from svglib.svglib import svg2rlg
    HAS_SVGLIB = True
except ImportError:
    HAS_SVGLIB = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


ROOT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT_DIR / "ressources" / "card_assets" / "template"
BACKGROUND_PATH = TEMPLATE_DIR / "Tyrant_Card_Template_bg_custom_4.png"
MARGINS_TEMPLATE_PATH = TEMPLATE_DIR / "Margins.png"
SEPARATOR_PATH = TEMPLATE_DIR / "Separator2.png"
SET_ICON_DIR = ROOT_DIR / "ressources" / "card_assets" / "logos"

TITLE_FONT_PATH = TEMPLATE_DIR / "Fonts" / "Modesto Condensed Bold.ttf"
TYPE_FONT_PATH = TEMPLATE_DIR / "Fonts" / "Modesto Expanded.ttf"
BODY_FONT_PATH = TEMPLATE_DIR / "Fonts" / "ScalaSans-Regular.otf"
BODY_BOLD_FONT_PATH = TEMPLATE_DIR / "Fonts" / "Modesto Expanded.ttf"
FLAVOR_FONT_PATH = TEMPLATE_DIR / "Fonts" / "ScalaSans-RegularLFItalic.otf"
VP_FONT_PATH = TEMPLATE_DIR / "Fonts" / "Modesto Condensed Bold.ttf"
ICON_DIR = TEMPLATE_DIR / "Icons"
ATTAQUE_ICON_PATH = ICON_DIR / "attaque.png"
MONNAIE_ICON_PATH = ICON_DIR / "monnaie.png"
AMBITION_ICON_PATH = ICON_DIR / "ambition.png"
CONQUETE_ICON_PATH = ICON_DIR / "conquete.png"
RUSE_ICON_PATH = ICON_DIR / "ruse.png"
MALICE_ICON_PATH = ICON_DIR / "malice.png"
OBEISSANCE_ICON_PATH = ICON_DIR / "obeissance.png"

SET_ICON_ALIASES: dict[str, str] = {
    "faerie": "Faerie",
    "juiblex": "juiblex",
    "kuo-toa": "Kuo-Toa",
    "kuo_toa": "Kuo-Toa",
    "siege": "Siege",
    "spiderkin": "spiderkin",
    "svirfneblin": "svirfneblin",
    "yugoloth": "yugoloth",
    "elementals": "elementals",
    "dragon": "dragon",
    "drow": "Drow",
    "cohort": "arbalete",
    "aberrations": "aberrations",
    "undead": "undead",
    "fungus": "fungus",

}
SET_ICON_SIZE = 80

TYPE1_ICON_ALIASES = {
    "ambition": "ambition",
    "conquete": "conquete",
    "conquest": "conquete",
    "ruse": "ruse",
    "malice": "malice",
    "obeissance": "obeissance",
}

CARD_WIDTH = 796
CARD_HEIGHT = 1082

IMAGE_BOX = (60, 172, 678, 550)
IMAGE_MIN_HEIGHT = 280   # minimum illustration area height (pixels)
IMAGE_MAX_HEIGHT = 690   # maximum illustration area height (pixels)
SEPARATOR_BENEFIT_GAP = -12  # pixels between separator bottom and benefit box top (negative = overlap)
BENEFIT_BOX = (68, 744, 658, 210)
BENEFIT_BOTTOM_PADDING = 40  # extra white fill below benefit box bottom before card decorations
TITLE_BOX = (70, 34, 500, 90)
TYPE1_BOX = (150, 133, 320, 42)
TYPE2_BOX = (514, 133, 220, 42)
TYPE1_ICON_SIZE = 84
TYPE1_ICON_X = TYPE1_BOX[0] - TYPE1_ICON_SIZE - 5
TYPE1_ICON_Y = TYPE1_BOX[1] + 3
TYPE1_ICON_SIZE_OVERRIDES = {
    "obeissance": 70,
}
TYPE1_ICON_OFFSETS = {
    "malice": (-1, 3),
    "ambition": (2, 0),
    "obeissance": (-7.5, 3),
}

SET_POS = (94, 1018)
VP1_POS = (597, 1012)
VP2_POS = (678, 1012)
VP1_MAX_WIDTH = 56
VP2_MAX_WIDTH = 74
VP_X_SCALE = 1
VP_Y_SCALE = 1.08
COUNT_CENTER_X = 398
COUNT_Y = 1018
COUNT_RADIUS = 8
COUNT_GAP = 34

TOP_TEXT_FILL = "#ffffff"
BOTTOM_TEXT_FILL = "#ffffff"
BODY_TEXT_FILL = "#111111"
BULLET_FONT_SCALE = 1.45
BENEFIT_ICON_PATTERN = re.compile(r"(?i)\b(\d+)\s*(?:x\s*)?(attaque|monnaie)s?\b\.?")
BENEFIT_ICON_TOKEN_PATTERN = re.compile(r"^\[\[icon:(attaque|monnaie):(\d+)\]\]$")
BENEFIT_ICON_TOKEN_AFFIX_PATTERN = re.compile(r"^([\(\[\{\"']*)(\[\[icon:(attaque|monnaie):(\d+)\]\])([,.;:!?\)\]\}\"']*)$")
MAX_INLINE_ICON_REPEAT = 12
BENEFIT_ICON_SCALE = 1.80
BENEFIT_ICON_LINE_EXTRA_ABOVE_SCALE = 0.35  # extra vertical gap added above icon-containing lines
EFFECT_ARROW_TOKEN = "►"
EFFECT_ARROW_EXTRA_SPACE_SCALE = 0.5

# PDF layout constants for A4 printable cards
PDF_CARD_WIDTH_INCHES = 2.5
PDF_CARD_HEIGHT_INCHES = 3.5
PDF_CARDS_PER_ROW = 3
PDF_CARDS_PER_COL = 3
PDF_CARDS_PER_PAGE = PDF_CARDS_PER_ROW * PDF_CARDS_PER_COL
PDF_MARGIN_INCHES = 0.35
PDF_HORIZONTAL_GAP_INCHES = 0.1
PDF_VERTICAL_GAP_INCHES = 0.1
PDF_RASTER_DPI = 300
TOP_MARGIN_RGBA = (0x35, 0x23, 0x63, 0xFF)
BOTTOM_MARGIN_RGBA = (0x05, 0x03, 0x03, 0xFF)

SVG_RENDERER_CANDIDATES = [
    "inkscape",
    "rsvg-convert",
]


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def slugify(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return text.strip("_") or "card"


def encode_file_as_data_uri(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def font_face(name: str, path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "font/otf"
    suffix = path.suffix.lower()
    if suffix == ".ttf":
        font_format = "truetype"
    elif suffix == ".otf":
        font_format = "opentype"
    elif suffix == ".woff":
        font_format = "woff"
    elif suffix == ".woff2":
        font_format = "woff2"
    else:
        font_format = "opentype"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f"@font-face {{ font-family: '{name}'; src: url('data:{mime_type};base64,{data}') format('{font_format}'); }}"
    )


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def read_image_size(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            return image.size
    except OSError:
        return None


def measure_width(font: ImageFont.FreeTypeFont, text: str) -> float:
    return font.getlength(text)


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}


def get_first(row: dict[str, str], keys: Sequence[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key.lower(), "")
        if value:
            return value
    return default


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def split_paragraph_words(text: str) -> list[list[str]]:
    paragraphs = [paragraph.strip() for paragraph in text.replace("\r", "").split("\n")]
    return [paragraph.split() if paragraph else [] for paragraph in paragraphs]


def load_benefit_icon_data_uris() -> dict[str, str]:
    icons: dict[str, str] = {}
    for name, path in {
        "attaque": ATTAQUE_ICON_PATH,
        "monnaie": MONNAIE_ICON_PATH,
    }.items():
        if path.exists():
            icons[name] = encode_file_as_data_uri(path)
    return icons


def load_type1_icon_data_uris() -> dict[str, str]:
    icons: dict[str, str] = {}
    for name, path in {
        "ambition": AMBITION_ICON_PATH,
        "conquete": CONQUETE_ICON_PATH,
        "ruse": RUSE_ICON_PATH,
        "malice": MALICE_ICON_PATH,
        "obeissance": OBEISSANCE_ICON_PATH,
    }.items():
        if path.exists():
            icons[name] = encode_file_as_data_uri(path)
    return icons


def load_set_icon_data_uris() -> dict[str, str]:
    icons: dict[str, str] = {}
    for normalized_name, filename in SET_ICON_ALIASES.items():
        path = SET_ICON_DIR / f"{filename}.png"
        if path.exists():
            # Composite the logo on a black background to handle transparency
            icons[normalized_name] = encode_logo_with_black_background(path)
    return icons


def encode_logo_with_black_background(logo_path: Path) -> str:
    """Load a logo PNG, composite it on black background, and return as data URI.
    
    This ensures that transparent areas of the logo match the black card background.
    """
    try:
        with Image.open(logo_path) as img:
            # Convert to RGBA if needed
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            # Create black background of same size
            background = Image.new("RGB", img.size, color=(0, 0, 0))
            
            # Composite the logo on the black background
            background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            
            # Convert back to the original format for data URI encoding
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                background.save(tmp_path, "PNG")
                data_uri = encode_file_as_data_uri(tmp_path)
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
                return data_uri
    except Exception:
        # Fallback to original if compositing fails
        return encode_file_as_data_uri(logo_path)


def load_margin_strip(width: int, height: int, mirror: bool = False) -> Image.Image | None:
    if width <= 0 or height <= 0 or not MARGINS_TEMPLATE_PATH.exists():
        return None

    try:
        with Image.open(MARGINS_TEMPLATE_PATH) as template:
            strip = template.convert("RGBA").resize((width, height), Image.LANCZOS)
            return ImageOps.mirror(strip) if mirror else strip
    except OSError:
        return None


def expand_png_with_custom_margins(
    output_image: Image.Image,
    vertical_margin: int,
    horizontal_margin: int,
) -> Image.Image:
    expanded = Image.new(
        "RGBA",
        (
            output_image.width + (2 * horizontal_margin),
            output_image.height + (2 * vertical_margin),
        ),
        (0, 0, 0, 0),
    )

    if vertical_margin > 0:
        expanded.paste(TOP_MARGIN_RGBA, (0, 0, expanded.width, vertical_margin))
        expanded.paste(
            BOTTOM_MARGIN_RGBA,
            (0, expanded.height - vertical_margin, expanded.width, expanded.height),
        )

    if horizontal_margin > 0:
        center_y = vertical_margin
        left_strip = load_margin_strip(horizontal_margin, output_image.height)
        right_strip = load_margin_strip(horizontal_margin, output_image.height, mirror=True)
        if left_strip:
            expanded.paste(left_strip, (0, center_y), left_strip)
        if right_strip:
            expanded.paste(right_strip, (horizontal_margin + output_image.width, center_y), right_strip)

    expanded.paste(output_image, (horizontal_margin, vertical_margin), output_image)
    return expanded


def normalize_keyword(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def resolve_type1_icon_name(type1: str) -> str | None:
    key = normalize_keyword(type1)
    return TYPE1_ICON_ALIASES.get(key)


def replace_icon_phrases(text: str, available_icons: set[str]) -> str:
    def replacement(match: re.Match[str]) -> str:
        count = parse_int(match.group(1), default=0)
        icon_name = match.group(2).lower()
        if count <= 0 or icon_name not in available_icons:
            return match.group(0)
        clamped_count = min(count, MAX_INLINE_ICON_REPEAT)
        return f"[[icon:{icon_name}:{clamped_count}]]"

    return BENEFIT_ICON_PATTERN.sub(replacement, text)


def parse_icon_token(token: str) -> tuple[str, int] | None:
    match = BENEFIT_ICON_TOKEN_PATTERN.match(token)
    if not match:
        return None
    return match.group(1).lower(), parse_int(match.group(2), default=0)


def parse_icon_token_with_affixes(token: str) -> tuple[str, int, str, str] | None:
    base = parse_icon_token(token)
    if base:
        icon_name, count = base
        return icon_name, count, "", ""

    match = BENEFIT_ICON_TOKEN_AFFIX_PATTERN.match(token)
    if not match:
        return None

    prefix = match.group(1)
    icon_name = match.group(3).lower()
    count = parse_int(match.group(4), default=0)
    suffix = match.group(5)
    return icon_name, count, prefix, suffix


def split_paragraph_tokens(text: str, available_icons: set[str]) -> list[list[str]]:
    with_tokens = replace_icon_phrases(text, available_icons)
    paragraphs = [paragraph.strip() for paragraph in with_tokens.replace("\r", "").split("\n")]
    return [paragraph.split() if paragraph else [] for paragraph in paragraphs]


def measure_token_width(token: str, font: ImageFont.FreeTypeFont, font_size: int) -> float:
    icon_token = parse_icon_token_with_affixes(token)
    if not icon_token:
        return measure_width(font, token)

    _, count, prefix, suffix = icon_token
    icon_size = max(12, int(font_size * BENEFIT_ICON_SCALE))
    icon_gap = max(2, int(font_size * 0.14))
    affix_width = 0.0
    if prefix:
        affix_width += measure_width(font, prefix)
    if suffix:
        affix_width += measure_width(font, suffix)
    return affix_width + count * icon_size + max(0, count - 1) * icon_gap


def measure_line_tokens(
    tokens: list[str],
    font: ImageFont.FreeTypeFont,
    font_size: int,
    bullet_first_width: float | None = None,
    arrow_extra: int = 0,
) -> float:
    if not tokens:
        return 0
    space_width = measure_width(font, " ")
    width = 0.0
    for index, token in enumerate(tokens):
        if index > 0:
            width += space_width
            if tokens[index - 1] == EFFECT_ARROW_TOKEN:
                width += arrow_extra
        if index == 0 and token == "\u2022" and bullet_first_width is not None:
            width += bullet_first_width
        else:
            width += measure_token_width(token, font, font_size)
    return width


def wrap_tokens_to_lines(text: str, font_path: Path, font_size: int, max_width: int, available_icons: set[str]) -> list[list[str]]:
    font = load_font(font_path, font_size)
    # Pre-compute bullet and arrow metrics so measure_line_tokens matches build_benefit.
    bullet_font = load_font(font_path, int(font_size * BULLET_FONT_SCALE))
    bullet_first_width: float = measure_width(bullet_font, "\u2022") + 4
    arrow_extra: int = max(1, int(font_size * EFFECT_ARROW_EXTRA_SPACE_SCALE))
    wrapped_lines: list[list[str]] = []

    for tokens in split_paragraph_tokens(text, available_icons):
        if not tokens:
            wrapped_lines.append([])
            continue

        current_line = [tokens[0]]
        for token in tokens[1:]:
            candidate = [*current_line, token]
            if measure_line_tokens(candidate, font, font_size, bullet_first_width, arrow_extra) <= max_width:
                current_line = candidate
            else:
                wrapped_lines.append(current_line)
                current_line = [token]
        wrapped_lines.append(current_line)

    return wrapped_lines or [[]]


def _benefit_rendered_height(lines: list[list[str]], font_size: int) -> int:
    """Compute the actual rendered height matching build_benefit's layout logic."""
    line_step = int(font_size * 1.22)
    icon_line_step = int(font_size * 1.75)
    icon_extra_above = max(2, int(font_size * BENEFIT_ICON_LINE_EXTRA_ABOVE_SCALE))
    total = 0
    for i, tokens in enumerate(lines):
        has_icon = any(parse_icon_token_with_affixes(t) for t in tokens)
        if has_icon and i > 0:
            total += icon_extra_above
        total += icon_line_step if has_icon else line_step
    return total


def fit_benefit_tokens(
    text: str,
    font_path: Path,
    start_size: int,
    min_size: int,
    max_width: int,
    max_height: int,
    line_height: float,
    available_icons: set[str],
) -> tuple[int, list[list[str]]]:
    for font_size in range(start_size, min_size - 1, -1):
        lines = wrap_tokens_to_lines(text, font_path, font_size, max_width, available_icons)
        if _benefit_rendered_height(lines, font_size) <= max_height:
            return font_size, lines
    return min_size, wrap_tokens_to_lines(text, font_path, min_size, max_width, available_icons)


def wrap_text_to_lines(text: str, font_path: Path, font_size: int, max_width: int) -> list[str]:
    font = load_font(font_path, font_size)
    wrapped_lines: list[str] = []

    for words in split_paragraph_words(text):
        if not words:
            wrapped_lines.append("")
            continue

        current_line = words[0]
        for word in words[1:]:
            candidate = f"{current_line} {word}"
            if measure_width(font, candidate) <= max_width:
                current_line = candidate
            else:
                wrapped_lines.append(current_line)
                current_line = word
        wrapped_lines.append(current_line)

    return wrapped_lines or [""]


def fit_text(text: str, font_path: Path, start_size: int, min_size: int, max_width: int, max_height: int, line_height: float) -> tuple[int, list[str]]:
    for font_size in range(start_size, min_size - 1, -1):
        lines = wrap_text_to_lines(text, font_path, font_size, max_width)
        if len(lines) * int(font_size * line_height) <= max_height:
            return font_size, lines
    return min_size, wrap_text_to_lines(text, font_path, min_size, max_width)


def layout_text_in_boxes(
    text: str,
    font_path: Path,
    font_size: int,
    boxes: list[tuple[int, int, int, int]],
    line_height: float,
    box_alignments: Sequence[str] | None = None,
) -> list[tuple[int, int, str]] | None:
    font = load_font(font_path, font_size)
    line_step = max(1, int(font_size * line_height))

    box_capacities = [max(0, height // line_step) for _, _, _, height in boxes]
    assigned_lines: list[tuple[int, str]] = []
    used_lines_per_box = [0 for _ in boxes]
    box_index = 0

    def normalize_alignment(index: int) -> str:
        if not box_alignments or index >= len(box_alignments):
            return "top"
        value = (box_alignments[index] or "top").strip().lower()
        return "bottom" if value == "bottom" else "top"

    def move_to_next_available_box() -> bool:
        nonlocal box_index
        while box_index < len(boxes):
            if box_capacities[box_index] > 0 and used_lines_per_box[box_index] < box_capacities[box_index]:
                return True
            box_index += 1
        return False

    def current_box_width() -> int | None:
        if not move_to_next_available_box():
            return None
        return boxes[box_index][2]

    def place_line(line: str) -> bool:
        if not move_to_next_available_box():
            return False
        assigned_lines.append((box_index, line))
        used_lines_per_box[box_index] += 1
        return True

    for words in split_paragraph_words(text):
        if not words:
            if not place_line(""):
                return None
            continue

        current_line = words[0]
        for word in words[1:]:
            width = current_box_width()
            if width is None:
                return None
            candidate = f"{current_line} {word}"
            if measure_width(font, candidate) <= width:
                current_line = candidate
            else:
                if not place_line(current_line):
                    return None
                current_line = word

        width = current_box_width()
        if width is None:
            return None
        if measure_width(font, current_line) > width and current_line:
            if not place_line(current_line):
                return None
        elif not place_line(current_line):
            return None

    start_line_per_box: list[int] = []
    for idx, capacity in enumerate(box_capacities):
        used = used_lines_per_box[idx]
        if normalize_alignment(idx) == "bottom":
            start_line_per_box.append(max(0, capacity - used))
        else:
            start_line_per_box.append(0)

    placements: list[tuple[int, int, str]] = []
    local_line_index_per_box = [0 for _ in boxes]
    for assigned_box_index, line in assigned_lines:
        x, y, _, _ = boxes[assigned_box_index]
        local_idx = local_line_index_per_box[assigned_box_index]
        baseline_y = y + font_size + (start_line_per_box[assigned_box_index] + local_idx) * line_step
        placements.append((x, baseline_y, line))
        local_line_index_per_box[assigned_box_index] += 1

    return placements


def fit_text_in_boxes(
    text: str,
    font_path: Path,
    start_size: int,
    min_size: int,
    boxes: list[tuple[int, int, int, int]],
    line_height: float,
    box_alignments: Sequence[str] | None = None,
) -> tuple[int, list[tuple[int, int, str]]]:
    if not text.strip() or not boxes:
        return min_size, []

    for font_size in range(start_size, min_size - 1, -1):
        placements = layout_text_in_boxes(text, font_path, font_size, boxes, line_height, box_alignments)
        if placements is not None:
            return font_size, placements

    placements = layout_text_in_boxes(text, font_path, min_size, boxes, line_height, box_alignments)
    return min_size, placements or []


def fit_single_line(text: str, font_path: Path, start_size: int, min_size: int, max_width: int) -> int:
    for font_size in range(start_size, min_size - 1, -1):
        font = load_font(font_path, font_size)
        if measure_width(font, text) <= max_width:
            return font_size
    return min_size


def normalize_benefit_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    choose_match = re.search(r"(?i)\bchoose\b[^:\n]{0,40}:", normalized)
    if not choose_match:
        return normalized

    prefix_end = choose_match.end()
    prefix = normalized[:prefix_end].rstrip()
    suffix = normalized[prefix_end:].strip()

    if not re.search(r"(?:^|\n|\s)-\s+", suffix):
        return normalized

    suffix = re.sub(r"\n\s*-\s+", "\n• ", suffix)
    suffix = re.sub(r"^\s*-\s+", "• ", suffix)
    suffix = re.sub(r"\s+-\s+", "\n• ", suffix)
    return f"{prefix}\n{suffix.lstrip()}"


@dataclass
class CardRecord:
    name: str
    count: int
    cost: str
    vp1: str
    vp2: str
    set_name: str
    benefit: str
    ambiance: str
    type1: str
    type2: str
    image_path: str


def row_to_card(row: dict[str, str]) -> CardRecord:
    name = get_first(row, ["nom", "name", "title"])
    count = parse_int(get_first(row, ["nombre", "count"], default="1"), default=1)
    cost = get_first(row, ["coût modif", "coût", "cost"])
    vp1 = get_first(row, ["pv deck modif", "point de victoire deck", "vp1", "points in deck"])
    vp2 = get_first(row, ["pv cénacle modif", "point de victoire cénacle", "vp2", "points in inner circle"])
    set_name = get_first(row, ["set", "faction"])
    benefit = get_first(row, ["texte modif", "texte", "benefit", "ability text"])
    ambiance = get_first(row, ["texte d'ambiance", "texte d’ambiance", "flavor text", "flavour text"])
    type1 = get_first(row, ["type1", "type"])
    type2 = get_first(row, ["type2"])
    image_path = get_first(row, ["path to image", "image_path", "image", "path"])

    return CardRecord(
        name=name,
        count=max(0, count),
        cost=cost,
        vp1=vp1,
        vp2=vp2,
        set_name=set_name,
        benefit=benefit,
        ambiance=ambiance,
        type1=type1,
        type2=type2,
        image_path=image_path,
    )


def resolve_image_path(raw_value: str, csv_path: Path) -> Path | None:
    if not raw_value:
        return None
    candidate = Path(raw_value)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    relative = (csv_path.parent / raw_value).resolve()
    if relative.exists():
        return relative
    return None


def build_title(card: CardRecord) -> str:
    font_size = fit_single_line(card.name, TITLE_FONT_PATH, start_size=58, min_size=30, max_width=TITLE_BOX[2])
    x = TITLE_BOX[0]
    y = TITLE_BOX[1] + font_size
    return (
        f"  <text x=\"{x}\" y=\"{y}\" class=\"title\" font-size=\"{font_size}\">"
        f"{escape_xml(card.name)}</text>"
    )


def build_types(card: CardRecord) -> list[str]:
    parts: list[str] = []
    if card.type1:
        font_size = fit_single_line(card.type1, TYPE_FONT_PATH, start_size=28, min_size=18, max_width=TYPE1_BOX[2])
        y = TYPE1_BOX[1] + font_size
        parts.append(
            f"  <text x=\"{TYPE1_BOX[0]}\" y=\"{y}\" class=\"top-label\" font-size=\"{font_size}\">{escape_xml(card.type1)}</text>"
        )
    if card.type2:
        font_size = fit_single_line(card.type2, TYPE_FONT_PATH, start_size=28, min_size=18, max_width=TYPE2_BOX[2])
        y = TYPE2_BOX[1] + font_size
        parts.append(
            f"  <text x=\"{TYPE2_BOX[0] + TYPE2_BOX[2]}\" y=\"{y}\" class=\"top-label\" font-size=\"{font_size}\" text-anchor=\"end\">{escape_xml(card.type2)}</text>"
        )
    return parts


def build_type1_icon(card: CardRecord, type1_icon_data_uris: dict[str, str]) -> str:
    icon_name = resolve_type1_icon_name(card.type1)
    if not icon_name:
        return ""
    icon_data_uri = type1_icon_data_uris.get(icon_name)
    if not icon_data_uri:
        return ""
    icon_size = TYPE1_ICON_SIZE_OVERRIDES.get(icon_name, TYPE1_ICON_SIZE)
    dx, dy = TYPE1_ICON_OFFSETS.get(icon_name, (0, 0))
    icon_x = TYPE1_BOX[0] - icon_size - 5
    icon_y = TYPE1_ICON_Y + ((TYPE1_ICON_SIZE - icon_size) // 2)
    return (
        f'  <image href="{icon_data_uri}" x="{icon_x + dx}" y="{icon_y + dy}" '
        f'width="{icon_size}" height="{icon_size}" preserveAspectRatio="xMidYMid meet" />'
    )


def build_cost(card: CardRecord) -> str:
    font_size = fit_single_line(card.cost, TITLE_FONT_PATH, start_size=72, min_size=30, max_width=72)
    return (
        f"  <text x=\"730\" y=\"{35 + font_size}\" class=\"cost\" font-size=\"{font_size}\" text-anchor=\"end\">"
        f"{escape_xml(card.cost)}</text>"
    )


def build_benefit(
    card: CardRecord,
    icon_data_uris: dict[str, str],
    benefit_box: tuple[int, int, int, int],
) -> str:
    benefit_text = normalize_benefit_text(card.benefit)
    ambiance_text = card.ambiance.strip()
    benefit_start_size = 32
    benefit_min_size = 24
    ambiance_start_size = 31
    ambiance_min_size = 23

    ambiance_font_size = ambiance_start_size
    ambiance_placements: list[tuple[int, int, str]] = []
    if benefit_text:
        font_size, lines = fit_benefit_tokens(
            benefit_text,
            BODY_FONT_PATH,
            start_size=benefit_start_size,
            min_size=benefit_min_size,
            max_width=benefit_box[2],
            max_height=benefit_box[3],
            line_height=1.22,
            available_icons=set(icon_data_uris.keys()),
        )
    else:
        font_size = benefit_start_size
        lines = []

    font = load_font(BODY_FONT_PATH, font_size)
    x = benefit_box[0]
    y = benefit_box[1] + font_size
    line_step = int(font_size * 1.22)
    icon_line_step = int(font_size * 1.75)
    icon_extra_above = max(2, int(font_size * BENEFIT_ICON_LINE_EXTRA_ABOVE_SCALE))
    bullet_font_size = int(font_size * BULLET_FONT_SCALE)
    icon_size = max(12, int(font_size * BENEFIT_ICON_SCALE))
    icon_gap = max(2, int(font_size * 0.14))
    icon_baseline_offset = max(2, int(font_size * 1.18))
    space_width = measure_width(font, " ")
    arrow_extra_space = max(1, int(font_size * EFFECT_ARROW_EXTRA_SPACE_SCALE))
    bullet_width = measure_width(load_font(BODY_FONT_PATH, bullet_font_size), "•")

    benefit_block_height = 0
    for i, tokens in enumerate(lines):
        has_icon = any(parse_icon_token_with_affixes(t) for t in tokens)
        if has_icon and i > 0:
            benefit_block_height += icon_extra_above
        benefit_block_height += icon_line_step if has_icon else line_step

    if ambiance_text:
        gap_above_ambiance = max(6, int(font_size * 0.45)) if lines else 0
        benefit_bottom = benefit_box[1] + benefit_block_height
        primary_ambiance_y = benefit_bottom + gap_above_ambiance
        primary_ambiance_height = max(0, (benefit_box[1] + benefit_box[3]) - primary_ambiance_y)

        if primary_ambiance_height > 0:
            upper_box = (benefit_box[0], primary_ambiance_y, benefit_box[2], primary_ambiance_height)
            ambiance_font_size, ambiance_placements = fit_text_in_boxes(
                ambiance_text,
                FLAVOR_FONT_PATH,
                start_size=ambiance_start_size,
                min_size=ambiance_min_size,
                boxes=[upper_box],
                line_height=1.18,
                box_alignments=["top"],
            )

    parts: list[str] = ["  <g>"]

    baseline_ys: list[int] = []
    current_y = y
    vertical_offset = 0

    first_line_has_icon = bool(lines) and any(parse_icon_token_with_affixes(t) for t in lines[0])

    if lines and not ambiance_text:
        rendered_height = 0
        for i, tokens in enumerate(lines):
            has_icon = any(parse_icon_token_with_affixes(t) for t in tokens)
            if has_icon and i > 0:
                rendered_height += icon_extra_above
            rendered_height += icon_line_step if has_icon else line_step
        gap = max(0, benefit_box[3] - rendered_height)
        # Center when the first line has an icon, or when the unused gap is small
        # (tight fit: text nearly fills the box). For large gaps without icons,
        # top-align so the gap doesn't appear as a visible top padding.
        if first_line_has_icon or gap <= line_step * 2:
            top_padding = gap // 2
        else:
            top_padding = 0
        current_y = benefit_box[1] + top_padding + font_size

    if lines and ambiance_text and ambiance_placements:
        if ambiance_placements:
            ambiance_bottom_y = max(ay for _, ay, _ in ambiance_placements)
            total_used = ambiance_bottom_y - benefit_box[1]
            unused_space = benefit_box[3] - total_used
            if unused_space > 0 and (first_line_has_icon or unused_space <= line_step * 2):
                vertical_offset = unused_space // 2
                current_y = benefit_box[1] + vertical_offset + font_size

    for i, tokens in enumerate(lines):
        has_icon = any(parse_icon_token_with_affixes(t) for t in tokens)
        if has_icon and i > 0:
            current_y += icon_extra_above
        baseline_ys.append(current_y)
        current_y += icon_line_step if has_icon else line_step

    for line_index, tokens in enumerate(lines):
        baseline_y = baseline_ys[line_index]
        cursor_x = float(x)
        line_tokens = list(tokens)

        if line_tokens and line_tokens[0] == "•":
            parts.append(
                f"    <text x=\"{cursor_x:.2f}\" y=\"{baseline_y}\" class=\"benefit\" font-size=\"{bullet_font_size}\">{escape_xml('•')}</text>"
            )
            cursor_x += bullet_width + 4
            line_tokens = line_tokens[1:]

        for token_index, token in enumerate(line_tokens):
            if token_index > 0:
                cursor_x += space_width
                if line_tokens[token_index - 1] == EFFECT_ARROW_TOKEN:
                    cursor_x += arrow_extra_space

            parsed_icon = parse_icon_token_with_affixes(token)
            if parsed_icon:
                icon_name, icon_count, icon_prefix, icon_suffix = parsed_icon
                icon_data_uri = icon_data_uris.get(icon_name)
                if not icon_data_uri or icon_count <= 0:
                    parts.append(
                        f"    <text x=\"{cursor_x:.2f}\" y=\"{baseline_y}\" class=\"benefit\" font-size=\"{font_size}\">{escape_xml(token)}</text>"
                    )
                    cursor_x += measure_width(font, token)
                    continue

                if icon_prefix:
                    parts.append(
                        f"    <text x=\"{cursor_x:.2f}\" y=\"{baseline_y}\" class=\"benefit\" font-size=\"{font_size}\">{escape_xml(icon_prefix)}</text>"
                    )
                    cursor_x += measure_width(font, icon_prefix)

                icon_y = baseline_y - icon_baseline_offset
                for icon_idx in range(icon_count):
                    parts.append(
                        f"    <image href=\"{icon_data_uri}\" x=\"{cursor_x:.2f}\" y=\"{icon_y}\" width=\"{icon_size}\" height=\"{icon_size}\" preserveAspectRatio=\"xMidYMid meet\" />"
                    )
                    cursor_x += icon_size
                    if icon_idx < icon_count - 1:
                        cursor_x += icon_gap

                if icon_suffix:
                    parts.append(
                        f"    <text x=\"{cursor_x:.2f}\" y=\"{baseline_y}\" class=\"benefit\" font-size=\"{font_size}\">{escape_xml(icon_suffix)}</text>"
                    )
                    cursor_x += measure_width(font, icon_suffix)
                continue

            parts.append(
                f"    <text x=\"{cursor_x:.2f}\" y=\"{baseline_y}\" class=\"benefit\" font-size=\"{font_size}\">{escape_xml(token)}</text>"
            )
            cursor_x += measure_width(font, token)

    if ambiance_placements:
        adjusted_placements = [
            (line_x, line_y + vertical_offset, line_text)
            for line_x, line_y, line_text in ambiance_placements
        ]
        for line_x, line_y, line_text in adjusted_placements:
            parts.append(
                f"    <text x=\"{line_x}\" y=\"{line_y}\" class=\"benefit-flavor\" font-size=\"{ambiance_font_size}\">{escape_xml(line_text)}</text>"
            )

    parts.append("  </g>")
    return "\n".join(parts)


def build_set(card: CardRecord, set_icon_data_uris: dict[str, str]) -> str:
    normalized = normalize_keyword(card.set_name)
    icon_data_uri = set_icon_data_uris.get(normalized)
    if icon_data_uri:
        icon_x = SET_POS[0] - (SET_ICON_SIZE / 2)
        icon_y = SET_POS[1] - (SET_ICON_SIZE / 2)
        return (
            f'  <image href="{icon_data_uri}" x="{icon_x}" y="{icon_y}" '
            f'width="{SET_ICON_SIZE}" height="{SET_ICON_SIZE}" preserveAspectRatio="xMidYMid meet" />'
        )
    font_size = fit_single_line(card.set_name, BODY_BOLD_FONT_PATH, start_size=28, min_size=16, max_width=190)
    return (
        f"  <text x=\"{SET_POS[0]}\" y=\"{SET_POS[1]}\" class=\"bottom-label\" font-size=\"{font_size}\">"
        f"{escape_xml(card.set_name)}</text>"
    )


def build_vp_text(value: str, x: int, y: int, max_width: int) -> str:
    fit_width = int(max_width / VP_X_SCALE)
    font_size = fit_single_line(value, VP_FONT_PATH, start_size=60, min_size=36, max_width=fit_width)
    transform = f"translate({x} {y}) scale({VP_X_SCALE} {VP_Y_SCALE}) translate(-{x} -{y})"
    return (
        f"  <text x=\"{x}\" y=\"{y}\" class=\"vp\" font-size=\"{font_size}\" text-anchor=\"middle\" transform=\"{transform}\">"
        f"{escape_xml(value)}</text>"
    )


def build_count_dots(count: int) -> list[str]:
    if count <= 0:
        return []
    if count > 7:
        return []
    total_width = (count - 1) * COUNT_GAP
    start_x = COUNT_CENTER_X - total_width / 2
    circles = []
    for index in range(count):
        circles.append(
            f"  <circle cx=\"{start_x + index * COUNT_GAP:.1f}\" cy=\"{COUNT_Y}\" r=\"{COUNT_RADIUS}\" fill=\"#ffffff\" />"
        )
    return circles


def compute_fitted_image_rect(image_path: Path | None) -> tuple[float, float, float, float]:
    x, y, width, height = IMAGE_BOX
    if not image_path:
        return float(x), float(y), float(width), float(height)

    image_size = read_image_size(image_path)
    if not image_size:
        return float(x), float(y), float(width), float(height)

    image_width, image_height = image_size
    if image_width <= 0 or image_height <= 0:
        return float(x), float(y), float(width), float(height)

    scale = min(width / image_width, height / image_height)
    rendered_width = image_width * scale
    rendered_height = image_height * scale
    rendered_x = x + (width - rendered_width) / 2
    rendered_y = y
    return rendered_x, rendered_y, rendered_width, rendered_height


def estimate_text_area_height(card: CardRecord, icon_data_uris: dict[str, str], max_benefit_height: int = 9999) -> int:
    """Estimate the total pixel height needed for the card's text content.

    Pass *max_benefit_height* (the maximum possible benefit-box height, derived
    from the separator position at its minimum) so the estimate uses the same
    font size that build_benefit will actually use.  This prevents the separator
    from being pushed all the way to its minimum when a slightly smaller box
    would fit the text just as well.
    """
    benefit_text = normalize_benefit_text(card.benefit)
    ambiance_text = card.ambiance.strip()
    if not benefit_text and not ambiance_text:
        return 0

    text_width = BENEFIT_BOX[2]
    total = 0
    # Use the same font sizes as build_benefit so the estimate drives the
    # separator position accurately.
    benefit_font_size = 32  # matches build_benefit's benefit_start_size

    if benefit_text:
        font_size, lines = fit_benefit_tokens(
            benefit_text,
            BODY_FONT_PATH,
            start_size=32,
            min_size=24,
            max_width=text_width,
            max_height=max_benefit_height,
            line_height=1.22,
            available_icons=set(icon_data_uris.keys()),
        )
        benefit_font_size = font_size
        line_step = int(font_size * 1.22)
        icon_line_step = int(font_size * 1.75)
        icon_extra_above = max(2, int(font_size * BENEFIT_ICON_LINE_EXTRA_ABOVE_SCALE))
        for i, tokens in enumerate(lines):
            has_icon = any(parse_icon_token_with_affixes(t) for t in tokens)
            if has_icon and i > 0:
                total += icon_extra_above
            total += icon_line_step if has_icon else line_step

    if ambiance_text:
        if total > 0:
            total += max(6, int(benefit_font_size * 0.45))
        ambiance_lines = wrap_text_to_lines(ambiance_text, FLAVOR_FONT_PATH, 31, text_width)
        total += len(ambiance_lines) * int(31 * 1.18)

    return total


def build_artwork(image_path: Path | None, image_box: tuple[int, int, int, int]) -> tuple[str, float]:
    x, y, width, height = image_box
    if not image_path:
        return "", float(y + height)

    data_uri = encode_file_as_data_uri(image_path)
    return (
        "\n".join(
            [
                "  <defs>",
                '    <clipPath id="art-clip">',
                f'      <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="0" ry="0" />',
                "    </clipPath>",
                "  </defs>",
                f'  <image href="{data_uri}" x="{x}" y="{y}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" clip-path="url(#art-clip)" />',
            ]
        ),
        float(y + height),
    )


def compute_benefit_box(separator_bottom_y: float) -> tuple[int, int, int, int]:
    top_y = int(round(separator_bottom_y))
    bottom_y = BENEFIT_BOX[1] + BENEFIT_BOX[3]
    height = max(0, bottom_y - top_y)
    return BENEFIT_BOX[0], top_y, BENEFIT_BOX[2], height


def build_colored_rect(
    x: int | float,
    y: int | float,
    width: int | float,
    height: int | float,
    color: str = "#000000",
    opacity: float = 0.2,
    stroke: str | None = None,
    stroke_width: float = 1.5,
    stroke_opacity: float = 1.0,
) -> str:
    """Return an SVG rect element filled with *color* at the given *opacity* (0–1)."""
    stroke_attrs = ""
    if stroke:
        stroke_attrs = (
            f' stroke="{stroke}" stroke-width="{stroke_width}" stroke-opacity="{stroke_opacity:.2f}"'
        )
    return (
        f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'fill="{color}" fill-opacity="{opacity:.2f}"{stroke_attrs} />'
    )


def build_layout_debug_boxes() -> list[str]:
    bx, by, bw, bh = BENEFIT_BOX
    return (
        f'  <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="#0000ff" fill-opacity="0.18" stroke="#0000ff" stroke-width="2" />'
    )


def build_image_box_debug_square() -> str:
    x, y, width, height = IMAGE_BOX
    return (
        f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'fill="#ff0000" fill-opacity="0.18" stroke="#ff0000" stroke-width="2" />'
    )


def build_svg(
    card: CardRecord,
    background_data_uri: str,
    separator_data_uri: str,
    separator_size: tuple[int, int],
    csv_path: Path,
) -> str:
    image_path = resolve_image_path(card.image_path, csv_path)
    icon_data_uris = load_benefit_icon_data_uris()
    type1_icon_data_uris = load_type1_icon_data_uris()
    set_icon_data_uris = load_set_icon_data_uris()
    style_block = "\n".join(
        [
            "  <style>",
            f"    {font_face('TyrantsTitle', TITLE_FONT_PATH)}",
            f"    {font_face('TyrantsType', TYPE_FONT_PATH)}",
            f"    {font_face('TyrantsBody', BODY_FONT_PATH)}",
            f"    {font_face('TyrantsBodyBold', BODY_BOLD_FONT_PATH)}",
            f"    {font_face('TyrantsFlavor', FLAVOR_FONT_PATH)}",
            f"    {font_face('TyrantsVp', VP_FONT_PATH)}",
            "    .title { font-family: 'TyrantsTitle'; fill: #ffffff; letter-spacing: 0.5px; }",
            "    .top-label { font-family: 'TyrantsType'; fill: #ffffff; letter-spacing: 0.4px; }",
            "    .cost { font-family: 'TyrantsTitle'; fill: #ffffff; }",
            "    .benefit { font-family: 'TyrantsBody'; fill: #111111; }",
            "    .benefit-flavor { font-family: 'TyrantsFlavor'; fill: #111111; font-style: italic; }",
            "    .bottom-label { font-family: 'TyrantsBodyBold'; fill: #ffffff; }",
            "    .vp { font-family: 'TyrantsVp'; fill: #ffffff; dominant-baseline: middle; }",
            "  </style>",
        ]
    )

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}">',
        f"  <title>{escape_xml(card.name)}</title>",
        style_block,
    ]

    separator_width, separator_height = separator_size

    # Maximum benefit-box height when the separator is at its lowest allowed position.
    # Passing this to the estimator ensures it uses the same font build_benefit will use,
    # so the separator is never pushed to its minimum unnecessarily.
    max_benefit_height = max(1, int(
        BENEFIT_BOX[1] + BENEFIT_BOX[3]
        - (IMAGE_BOX[1] + IMAGE_MIN_HEIGHT + separator_height / 2 + SEPARATOR_BENEFIT_GAP)
    ))

    # Size the illustration dynamically: more text → smaller image, less text → larger image.
    text_height = estimate_text_area_height(card, icon_data_uris, max_benefit_height)
    desired_sep_bottom = float(BENEFIT_BOX[1] + BENEFIT_BOX[3] - text_height)
    min_sep_bottom = float(IMAGE_BOX[1] + IMAGE_MIN_HEIGHT) + separator_height / 2
    max_sep_bottom = float(IMAGE_BOX[1] + IMAGE_MAX_HEIGHT) + separator_height / 2
    separator_bottom_y = max(min_sep_bottom, min(max_sep_bottom, desired_sep_bottom))
    dynamic_image_height = max(IMAGE_MIN_HEIGHT, int(round(separator_bottom_y - separator_height / 2 - IMAGE_BOX[1])))
    dynamic_image_box = (IMAGE_BOX[0], IMAGE_BOX[1], IMAGE_BOX[2], dynamic_image_height)

    artwork, artwork_bottom_y = build_artwork(image_path, dynamic_image_box)
    if artwork:
        parts.append(artwork)

    separator_x = ((CARD_WIDTH - separator_width) / 2)
    separator_y = artwork_bottom_y - (separator_height / 2)
    separator_bottom_y = separator_y + separator_height

    text_area_bottom = BENEFIT_BOX[1] + BENEFIT_BOX[3] + BENEFIT_BOTTOM_PADDING
    white_rect_top = int(round(artwork_bottom_y))
    white_rect_height = max(0, text_area_bottom - white_rect_top)
    if white_rect_height > 0:
        parts.append(
            f'  <rect x="{IMAGE_BOX[0]}" y="{white_rect_top}" width="{IMAGE_BOX[2]}" height="{white_rect_height}" fill="#ffffff" />'
        )

    if separator_data_uri:
        parts.append(
            f'  <image href="{separator_data_uri}" x="{separator_x:.2f}" y="{separator_y:.2f}" width="{separator_width}" height="{separator_height}" preserveAspectRatio="none" />'
        )

    benefit_box = compute_benefit_box(separator_bottom_y + SEPARATOR_BENEFIT_GAP)

    # Draw the template above artwork so only the framed card area reveals the image.
    parts.append(f'  <image href="{background_data_uri}" x="0" y="0" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" />')
    # parts.append(build_image_box_debug_square())

    parts.append(build_title(card))
    parts.append(build_type1_icon(card, type1_icon_data_uris))
    parts.extend(build_types(card))
    parts.append(build_cost(card))
    parts.append(build_benefit(card, icon_data_uris, benefit_box))
    parts.append(build_set(card, set_icon_data_uris))
    parts.extend(build_count_dots(card.count))
    parts.append(build_vp_text(card.vp1, VP1_POS[0], VP1_POS[1], VP1_MAX_WIDTH))
    parts.append(build_vp_text(card.vp2, VP2_POS[0], VP2_POS[1], VP2_MAX_WIDTH))
    # bx, by, bw, bh = benefit_box
    # parts.append(build_colored_rect(bx, by, bw, bh, color="#ffff00", opacity=0.15, stroke="#ff0000", stroke_width=1.5))
    parts.append("</svg>")

    return "\n".join(part for part in parts if part)


def iter_cards(csv_path: Path) -> Iterable[CardRecord]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row = normalize_row(raw_row)
            if not any(row.values()):
                continue
            card = row_to_card(row)
            if not card.name:
                continue
            yield card


def svg_to_png(
    svg_path: Path,
    png_path: Path,
    width_px: int,
    height_px: int,
    background_color: str = "transparent",
    png_dpi: int = 400,
    vertical_margin_px: int = 0,
    horizontal_margin_px: int = 0,
) -> bool:
    """Convert SVG to PNG, prioritizing font-faithful browser rendering first."""

    def finalize_png_with_dpi() -> bool:
        if not (png_path.exists() and png_path.stat().st_size > 0):
            return False
        try:
            dpi_value = max(1, int(png_dpi))
            vertical_margin = max(0, int(vertical_margin_px))
            horizontal_margin = max(0, int(horizontal_margin_px))
            with Image.open(png_path) as rendered:
                output_image = rendered.convert("RGBA")
                if vertical_margin > 0 or horizontal_margin > 0:
                    output_image = expand_png_with_custom_margins(
                        output_image,
                        vertical_margin,
                        horizontal_margin,
                    )
                output_image.save(png_path, format="PNG", dpi=(dpi_value, dpi_value))
            return png_path.exists() and png_path.stat().st_size > 0
        except Exception:
            return False

    if HAS_PLAYWRIGHT:
        try:
            svg_text = svg_path.read_text(encoding="utf-8")
            with sync_playwright() as p:
                browser = None
                launch_attempts = [
                    {"channel": "msedge", "headless": True},
                    {"channel": "chrome", "headless": True},
                    {"headless": True},
                ]
                for kwargs in launch_attempts:
                    try:
                        browser = p.chromium.launch(**kwargs)
                        break
                    except Exception:
                        continue
                if browser is None:
                    return False
                page = browser.new_page(viewport={"width": width_px, "height": height_px})
                html = (
                    "<html><head><meta charset='utf-8'></head>"
                    f"<body style='margin:0; padding:0; overflow:hidden; background:{background_color};'>"
                    f"{svg_text}"
                    "</body></html>"
                )
                page.set_content(html, wait_until="load")
                page.evaluate(
                    """
                    ([w, h]) => {
                        const svg = document.querySelector('svg');
                        if (!svg) return;
                        svg.setAttribute('width', String(w));
                        svg.setAttribute('height', String(h));
                        svg.setAttribute('viewBox', svg.getAttribute('viewBox') || `0 0 ${w} ${h}`);
                        svg.setAttribute('preserveAspectRatio', 'none');
                        svg.style.width = `${w}px`;
                        svg.style.height = `${h}px`;
                        svg.style.background = "transparent";
                        svg.style.display = 'block';
                    }
                    """,
                    [width_px, height_px],
                )
                page.evaluate(
                    """
                    async () => {
                        if (document.fonts && document.fonts.ready) {
                            await document.fonts.ready;
                        }
                    }
                    """
                )
                page.screenshot(path=str(png_path), type="png")
                browser.close()
            return finalize_png_with_dpi()
        except Exception:
            pass

    for renderer in SVG_RENDERER_CANDIDATES:
        executables: list[str] = []
        from_path = shutil.which(renderer)
        if from_path:
            executables.append(from_path)
        if renderer == "inkscape":
            for candidate in [
                Path("C:/Program Files/Inkscape/bin/inkscape.com"),
                Path("C:/Program Files/Inkscape/bin/inkscape.exe"),
                Path("C:/Program Files (x86)/Inkscape/bin/inkscape.com"),
                Path("C:/Program Files (x86)/Inkscape/bin/inkscape.exe"),
            ]:
                if candidate.exists():
                    executables.append(str(candidate))

        if not executables:
            continue

        for executable in executables:
            if renderer == "inkscape":
                command = [
                    executable,
                    str(svg_path),
                    "--export-type=png",
                    f"--export-filename={png_path}",
                    f"--export-width={width_px}",
                    f"--export-height={height_px}",
                ]
            else:
                command = [
                    executable,
                    "-w",
                    str(width_px),
                    "-h",
                    str(height_px),
                    "-o",
                    str(png_path),
                    str(svg_path),
                ]

            try:
                subprocess.run(command, check=True, capture_output=True)
                if png_path.exists() and png_path.stat().st_size > 0:
                    return finalize_png_with_dpi()
            except (subprocess.SubprocessError, OSError):
                continue

    if HAS_SVGLIB:
        try:
            from reportlab.graphics import renderPM as rl_renderPM
            drawing = svg2rlg(str(svg_path))
            if not drawing:
                return False
            drawing.width = width_px
            drawing.height = height_px
            rl_renderPM.drawToFile(drawing, str(png_path), fmt="PNG", dpi=PDF_RASTER_DPI)
            return finalize_png_with_dpi()
        except Exception:
            pass

    return False


def png_to_jpg(
    png_path: Path,
    jpg_path: Path,
    quality: int = 90,
) -> bool:
    """Convert PNG to JPG with specified quality.
    
    Args:
        png_path: Path to source PNG file
        jpg_path: Path to save JPG file
        quality: JPG quality (1-100, default 90)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with Image.open(png_path) as img:
            # Convert RGBA to RGB for JPG compatibility
            if img.mode in {"RGBA", "LA", "P"}:
                # Create white background
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode in {"RGBA", "LA"} else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            
            # Save as JPG with quality setting
            img.save(jpg_path, "JPEG", quality=min(100, max(1, quality)))
            return jpg_path.exists() and jpg_path.stat().st_size > 0
    except Exception:
        return False


def generate_pdf_from_cards(
    cards_with_counts: list[tuple[CardRecord, Path]],
    output_path: Path,
    temp_dir: Path,
    pdf_brightness: float = 1.0,
) -> bool:
    """Generate A4 PDF with cards arranged 3x3 per page, respecting card count.
    
    Args:
        cards_with_counts: List of (card_record, svg_path) tuples
        output_path: Where to save the PDF
        temp_dir: Temporary directory for PNG conversions
    
    Returns:
        True if successful, False otherwise
    """
    if not HAS_REPORTLAB:
        return False
    
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.units import inch
        from reportlab.lib.pagesizes import A4
        
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Collect all card instances respecting counts
        card_list = []
        for card, svg_path in cards_with_counts:
            for _ in range(max(1, card.count)):
                card_list.append((card, svg_path))
        
        if not card_list:
            return False
        
        # Rasterize each unique SVG once, then place PNGs into the PDF grid.
        png_cache: dict[Path, Path] = {}
        card_width_px = int(PDF_CARD_WIDTH_INCHES * PDF_RASTER_DPI)
        card_height_px = int(PDF_CARD_HEIGHT_INCHES * PDF_RASTER_DPI)

        for card, svg_path in card_list:
            if svg_path in png_cache:
                continue

            png_path = temp_dir / f"{svg_path.stem}_{card_width_px}x{card_height_px}.png"
            # Always rerender to avoid stale cached PNGs from previous pipeline variants.
            if png_path.exists():
                try:
                    png_path.unlink()
                except OSError:
                    pass
            if not svg_to_png(svg_path, png_path, card_width_px, card_height_px, background_color="#ffffff"):
                return False

            if abs(pdf_brightness - 1.0) > 1e-6:
                # Apply optional brightness compensation only for PDF raster assets.
                with Image.open(png_path) as rendered:
                    if rendered.mode not in {"RGB", "RGBA"}:
                        rendered = rendered.convert("RGBA" if "A" in rendered.getbands() else "RGB")
                    brighter = ImageEnhance.Brightness(rendered).enhance(pdf_brightness)
                    brighter.save(png_path)

            png_cache[svg_path] = png_path
        
        # Create PDF
        pdf = rl_canvas.Canvas(str(output_path), pagesize=A4)
        page_width, page_height = A4
        
        card_width = PDF_CARD_WIDTH_INCHES * inch
        card_height = PDF_CARD_HEIGHT_INCHES * inch
        margin = PDF_MARGIN_INCHES * inch
        h_gap = PDF_HORIZONTAL_GAP_INCHES * inch
        v_gap = PDF_VERTICAL_GAP_INCHES * inch
        
        # Calculate grid layout
        total_width = PDF_CARDS_PER_ROW * card_width + (PDF_CARDS_PER_ROW - 1) * h_gap
        total_height = PDF_CARDS_PER_COL * card_height + (PDF_CARDS_PER_COL - 1) * v_gap
        start_x = (page_width - total_width) / 2
        start_y = page_height - margin - card_height
        
        for card_idx, (card, svg_path) in enumerate(card_list):
            page_pos = card_idx % PDF_CARDS_PER_PAGE
            if page_pos == 0 and card_idx > 0:
                pdf.showPage()
                start_y = page_height - margin - card_height
            
            row = page_pos // PDF_CARDS_PER_ROW
            col = page_pos % PDF_CARDS_PER_ROW
            
            x = start_x + col * (card_width + h_gap)
            y = start_y - row * (card_height + v_gap)

            png_path = png_cache[svg_path]
            pdf.drawImage(str(png_path), x, y, width=card_width, height=card_height, preserveAspectRatio=False, mask="auto")
        
        pdf.save()
        return True
    
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Tyrants card SVG files from a CSV.")
    parser.add_argument("csv_path", type=Path, help="CSV file with columns like name,count,cost,vp1,vp2,set,benefit,type1,type2,path to image")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "output",
        help="Directory where SVG files will be created",
    )
    parser.add_argument(
        "--pdf-output",
        type=Path,
        default=None,
        help="If provided, generate an A4 PDF with all cards (respecting count field)",
    )
    parser.add_argument(
        "--pdf-brightness",
        type=float,
        default=1.0,
        help="Brightness multiplier applied only to PDF rasterization (1.0=unchanged, 1.1=brighter)",
    )
    parser.add_argument(
        "--png-output",
        type=Path,
        default=None,
        help="If provided, save individual PNG files in this directory",
    )
    parser.add_argument(
        "--jpg-output",
        type=Path,
        default=None,
        help="If provided, save individual JPG files in this directory",
    )
    parser.add_argument(
        "--image-width",
        type=int,
        default=796*2,
        help="Width in pixels for PNG/JPG output (default: 796)",
    )
    parser.add_argument(
        "--image-height",
        type=int,
        default=1082*2,
        help="Height in pixels for PNG/JPG output (default: 1082)",
    )
    parser.add_argument(
        "--jpg-quality",
        type=int,
        default=90,
        help="Quality setting for JPG output (1-100, default: 90)",
    )
    parser.add_argument(
        "--png-dpi",
        type=int,
        default=400,
        help="DPI metadata for generated PNG files (default: 400)",
    )
    parser.add_argument(
        "--png-vertical-margin",
        type=int,
        default=60,
        help="Extra margin in pixels added to top and bottom of PNG outputs (default: 60, color: #272727)",
    )
    parser.add_argument(
        "--png-horizontal-margin",
        type=int,
        default=60,
        help="Extra margin in pixels added to left and right of PNG outputs (default: 60, color: #272727)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv_path.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    background_data_uri = encode_file_as_data_uri(BACKGROUND_PATH)
    separator_data_uri = encode_file_as_data_uri(SEPARATOR_PATH) if SEPARATOR_PATH.exists() else ""
    separator_size = read_image_size(SEPARATOR_PATH) or (IMAGE_BOX[2], 40)

    # Set up PNG/JPG output directories
    png_output_dir = None
    jpg_output_dir = None
    if args.png_output:
        png_output_dir = args.png_output.resolve()
        png_output_dir.mkdir(parents=True, exist_ok=True)
    if args.jpg_output:
        jpg_output_dir = args.jpg_output.resolve()
        jpg_output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    cards_for_pdf: list[tuple[CardRecord, Path]] = []
    
    for index, card in enumerate(iter_cards(csv_path), start=1):
        file_name = f"{index:03d}_{slugify(card.name)}.svg"
        svg_path = output_dir / file_name
        svg = build_svg(card, background_data_uri, separator_data_uri, separator_size, csv_path)
        svg_path.write_text(svg, encoding="utf-8")
        generated += 1
        
        if args.pdf_output:
            cards_for_pdf.append((card, svg_path))
        
        # Generate PNG if requested
        if png_output_dir:
            png_file_name = f"{index:03d}_{slugify(card.name)}.png"
            png_path = png_output_dir / png_file_name
            if svg_to_png(
                svg_path,
                png_path,
                args.image_width,
                args.image_height,
                background_color="#ffffff",
                png_dpi=args.png_dpi,
                vertical_margin_px=max(0, args.png_vertical_margin),
                horizontal_margin_px=max(0, args.png_horizontal_margin),
            ):
                pass  # Successfully created PNG
            else:
                print(f"Warning: Could not generate PNG for {card.name}")
        
        # Generate JPG if requested
        if jpg_output_dir:
            # First create a temporary PNG if we haven't already
            if png_output_dir:
                # Use existing PNG from png_output_dir
                png_path = png_output_dir / f"{index:03d}_{slugify(card.name)}.png"
            else:
                # Create temporary PNG
                temp_png_dir = output_dir / ".temp_png"
                temp_png_dir.mkdir(parents=True, exist_ok=True)
                png_path = temp_png_dir / f"{index:03d}_{slugify(card.name)}.png"
                if not svg_to_png(
                    svg_path,
                    png_path,
                    args.image_width,
                    args.image_height,
                    background_color="#ffffff",
                    png_dpi=args.png_dpi,
                    vertical_margin_px=max(0, args.png_vertical_margin),
                    horizontal_margin_px=max(0, args.png_horizontal_margin),
                ):
                    print(f"Warning: Could not generate temporary PNG for JPG conversion of {card.name}")
                    continue
            
            # Convert PNG to JPG
            jpg_file_name = f"{index:03d}_{slugify(card.name)}.jpg"
            jpg_path = jpg_output_dir / jpg_file_name
            if png_path.exists() and png_to_jpg(png_path, jpg_path, args.jpg_quality):
                pass  # Successfully created JPG
            else:
                print(f"Warning: Could not generate JPG for {card.name}")

    print(f"Generated {generated} cards in {output_dir}")
    
    if png_output_dir:
        print(
            f"Generated PNG cards ({args.image_width}x{args.image_height}, {args.png_dpi} DPI, "
            f"top/bottom margin={max(0, args.png_vertical_margin)}px, "
            f"left/right margin={max(0, args.png_horizontal_margin)}px, color=#272727) in {png_output_dir}"
        )
    
    if jpg_output_dir:
        print(f"Generated JPG cards ({args.image_width}x{args.image_height}, quality={args.jpg_quality}) in {jpg_output_dir}")
    
    # Generate PDF if requested
    if args.pdf_output and cards_for_pdf:
        pdf_path = args.pdf_output.resolve()
        temp_dir = output_dir / ".pdf_temp"
        if generate_pdf_from_cards(cards_for_pdf, pdf_path, temp_dir, pdf_brightness=max(0.1, args.pdf_brightness)):
            print(f"Generated PDF: {pdf_path}")
        else:
            if not HAS_REPORTLAB:
                print("Warning: reportlab not installed. Cannot generate PDF.")
                print("Install with: pip install reportlab")
            else:
                print("Warning: could not rasterize SVG cards for PDF.")
                print("Install one of these renderers for best results: Playwright Chromium, Inkscape, or librsvg (rsvg-convert).")
                print("Browser renderer setup: pip install playwright && python -m playwright install chromium")
                print("Fallback renderer also available via: pip install svglib")


if __name__ == "__main__":
    main()