"""Offline SVG route map for proposals (TD-012 / TD-025).

Draws the trip on a Web-Mercator map of the bundled Natural Earth borders:
visited countries in soft colours, neighbours in grey, a dashed route with
direction arrows, pins with city labels, optional round photos, arrival and
departure planes, a legend with flags, a compass and a scale bar. No tiles,
fonts or network access are needed, so it renders the same in the browser
preview and in headless Edge/Chromium.

Pure module: inputs are plain values, output is an SVG string.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path

MAP_FILE = Path(__file__).resolve().parents[1] / "assets" / "maps" / "europe.json"

# Soft fills for visited countries (in order of first visit); readable under dark labels.
VISITED_FILLS = ("#F6C177", "#A8D5A2", "#9CC3E6", "#C9B3E6", "#F7E08A", "#F4A7A0", "#9FD8D0", "#E7C1A3", "#B8D98B", "#D9B8D1")
SEA = "#DCEAF3"
LAND = "#ECEAE4"
BORDER = "#FFFFFF"


@dataclass(frozen=True)
class MapStop:
    name: str
    country: str
    iso: str
    lat: float
    lng: float
    image: str | None = None  # data URI shown in a round frame next to the pin


@dataclass(frozen=True)
class MapTheme:
    route: str = "#B3261E"
    pin: str = "#1F3B64"
    label_bg: str = "#1F3B64"
    label_fg: str = "#FFFFFF"
    font: str = "'Segoe UI', Arial, Helvetica, sans-serif"


@lru_cache(maxsize=1)
def _countries() -> list[dict]:
    return json.loads(MAP_FILE.read_text(encoding="utf-8"))["countries"]


def _merc(lng: float, lat: float) -> tuple[float, float]:
    lat = max(min(lat, 85.0), -85.0)
    return math.radians(lng), math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


class _View:
    """Fits a lat/lng box into width x height (keeping the aspect ratio)."""

    def __init__(self, stops: list[MapStop], width: int, height: int):
        xs, ys = zip(*(_merc(s.lng, s.lat) for s in stops))
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        # Minimum span (~3.5° of longitude) so a one-city trip still shows its surroundings.
        min_span = math.radians(3.5)
        if x1 - x0 < min_span:
            c = (x0 + x1) / 2
            x0, x1 = c - min_span / 2, c + min_span / 2
        if y1 - y0 < min_span * height / width:
            c = (y0 + y1) / 2
            half = min_span * height / width / 2
            y0, y1 = c - half, c + half
        # Padding: room for labels, photos and the arrival/departure planes.
        px, py = (x1 - x0) * 0.28, (y1 - y0) * 0.30
        x0, x1, y0, y1 = x0 - px, x1 + px, y0 - py, y1 + py
        # Match the output aspect ratio.
        if (x1 - x0) / (y1 - y0) < width / height:
            c, half = (x0 + x1) / 2, (y1 - y0) * width / height / 2
            x0, x1 = c - half, c + half
        else:
            c, half = (y0 + y1) / 2, (x1 - x0) * height / width / 2
            y0, y1 = c - half, c + half
        self.x0, self.y1 = x0, y1
        self.k = width / (x1 - x0)
        self.width, self.height = width, height
        self.lat_c = math.degrees(2 * math.atan(math.exp((y0 + y1) / 2)) - math.pi / 2)

    def xy(self, lng: float, lat: float) -> tuple[float, float]:
        mx, my = _merc(lng, lat)
        return (mx - self.x0) * self.k, (self.y1 - my) * self.k

    def km_per_px(self) -> float:
        return 6371.0 * math.cos(math.radians(self.lat_c)) / self.k


def _path(points: list[tuple[float, float]]) -> str:
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in points) + "Z"


def _boxes_overlap(a, b, gap=4) -> bool:
    return not (a[0] + a[2] + gap <= b[0] or b[0] + b[2] + gap <= a[0] or a[1] + a[3] + gap <= b[1] or b[1] + b[3] + gap <= a[1])


def _text_w(text: str, size: float) -> float:
    return len(text) * size * 0.56 + 4


PLANE = "M2,11 L9,9 L14,1 L17,1 L14,9 L21,8 L23,5 L25,5 L24,11 L25,17 L23,17 L21,14 L14,13 L17,21 L14,21 L9,13 L2,11 Z"


def render_route_map(
    stops: list[MapStop],
    *,
    arrival_label: str | None = None,
    departure_label: str | None = None,
    legend_title: str = "Proposed Travel Route",
    flag_for: Callable[[str], str | None] = lambda iso: None,
    theme: MapTheme = MapTheme(),
    width: int = 1000,
    height: int = 640,
) -> str:
    """Return an SVG route map. `stops` are in travel order (consecutive duplicates are ignored)."""
    route: list[MapStop] = []
    for s in stops:
        if not route or (route[-1].lat, route[-1].lng) != (s.lat, s.lng):
            route.append(s)
    if not route:
        return ""
    v = _View(route, width, height)
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
        f'role="img" aria-label="{escape(legend_title)}" font-family="{escape(theme.font)}">',
        f'<rect width="{width}" height="{height}" fill="{SEA}"/>',
    ]

    # Countries ---------------------------------------------------------------------------
    visited: list[str] = []
    for s in route:
        if s.iso not in visited:
            visited.append(s.iso)
    fills = {iso: VISITED_FILLS[i % len(VISITED_FILLS)] for i, iso in enumerate(visited)}
    labels: list[tuple[float, float, str, bool]] = []
    for c in _countries():
        paths = []
        span = [width, height, 0, 0]
        for ring in c["polygons"]:
            pts = [v.xy(x, y) for x, y in ring]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < 0 or min(xs) > width or max(ys) < 0 or min(ys) > height:
                continue
            paths.append(_path(pts))
            span = [min(span[0], min(xs)), min(span[1], min(ys)), max(span[2], max(xs)), max(span[3], max(ys))]
        if not paths:
            continue
        fill = fills.get(c["iso"], LAND)
        out.append(f'<path d="{"".join(paths)}" fill="{fill}" stroke="{BORDER}" stroke-width="1.2" stroke-linejoin="round"/>')
        lx, ly = c.get("label") or (None, None)
        if lx is not None and span[2] - span[0] > 60:  # tiny countries (Liechtenstein, Monaco...) stay unlabelled
            x, y = v.xy(lx, ly)
            if 40 < x < width - 40 and 20 < y < height - 20:
                labels.append((x, y, c["name"], c["iso"] in fills))

    occupied: list[tuple[float, float, float, float]] = []
    pin_xy = [v.xy(s.lng, s.lat) for s in route]
    for x, y in pin_xy:
        occupied.append((x - 10, y - 28, 20, 30))

    # Route ------------------------------------------------------------------------------
    route_parts = []
    arrows = []
    for (x1, y1), (x2, y2) in zip(pin_xy, pin_xy[1:]):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy) or 1
        bend = min(0.18 * length, 60)
        cx, cy = (x1 + x2) / 2 - dy / length * bend, (y1 + y2) / 2 + dx / length * bend
        route_parts.append(f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}")
        # Arrow at the curve midpoint, pointing along the tangent.
        mx, my = 0.25 * x1 + 0.5 * cx + 0.25 * x2, 0.25 * y1 + 0.5 * cy + 0.25 * y2
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        arrows.append(f'<path d="M-7,-5 L5,0 L-7,5 Z" fill="{theme.route}" transform="translate({mx:.1f},{my:.1f}) rotate({angle:.1f})"/>')
    if route_parts:
        out.append(f'<path d="{" ".join(route_parts)}" fill="none" stroke="{theme.route}" stroke-width="3" stroke-dasharray="9 7" stroke-linecap="round"/>')
        out.extend(arrows)

    # Arrival / departure planes, placed away from the middle of the route.
    cxm = sum(p[0] for p in pin_xy) / len(pin_xy)
    cym = sum(p[1] for p in pin_xy) / len(pin_xy)

    def plane(at: tuple[float, float], label: str, arriving: bool, nudge: float) -> None:
        ax, ay = at
        dx, dy = ax - cxm, ay - cym
        if math.hypot(dx, dy) < 1:
            dx, dy = (-1, -0.6) if arriving else (1, 0.6)
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        # Rotate slightly so arrival and departure at the same city don't collide.
        rot = math.radians(nudge)
        dx, dy = dx * math.cos(rot) - dy * math.sin(rot), dx * math.sin(rot) + dy * math.cos(rot)
        px = min(max(ax + dx * 110, 40), width - 40)
        py = min(max(ay + dy * 90, 40), height - 64)
        out.append(f'<path d="M{px:.1f},{py:.1f} L{ax:.1f},{ay:.1f}" stroke="{theme.pin}" stroke-width="2" stroke-dasharray="6 6" fill="none"/>')
        heading = math.degrees(math.atan2(ay - py, ax - px)) if arriving else math.degrees(math.atan2(py - ay, px - ax))
        out.append(f'<g transform="translate({px:.1f},{py:.1f}) rotate({heading:.1f}) translate(-13,-11)"><path d="{PLANE}" fill="{theme.pin}"/></g>')
        tw = _text_w(label, 13)
        tx = px - tw / 2
        ty = py + (22 if dy >= 0 else -30)
        out.append(f'<text x="{px:.1f}" y="{ty + 12:.1f}" font-size="13" font-weight="600" fill="{theme.pin}" text-anchor="middle">{escape(label)}</text>')
        occupied.append((px - 16, py - 14, 32, 28))
        occupied.append((tx, ty, tw, 16))

    if arrival_label:
        plane(pin_xy[0], arrival_label, True, -25 if (departure_label and len(pin_xy) == 1) else 0)
    if departure_label:
        plane(pin_xy[-1], departure_label, False, 25 if len(pin_xy) == 1 else 0)

    # Country names (after the route so pins and labels can avoid them; drawn underneath).
    name_svg = []
    for x, y, name, is_visited in labels:
        size = 15 if is_visited else 11
        text = name.upper()
        w = _text_w(text, size) * 0.95
        for ox, oy in ((0, 0), (0, -26), (0, 26), (-40, 0), (40, 0), (0, -48), (0, 48)):
            box = (x + ox - w / 2, y + oy - size, w, size + 4)
            if not any(_boxes_overlap(box, o, 2) for o in occupied):
                break
        else:
            continue
        x, y = x + ox, y + oy
        occupied.append(box)
        colour = "#3A3A3A" if is_visited else "#8C8C8C"
        weight = 700 if is_visited else 500
        name_svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" letter-spacing="0.6" fill="{colour}" text-anchor="middle">{escape(text)}</text>')

    # Pins, photos and city labels -------------------------------------------------------------
    pins_svg, photos_svg, label_svg = [], [], []
    defs = []
    seen_names: set[str] = set()
    for i, (s, (x, y)) in enumerate(zip(route, pin_xy)):
        pins_svg.append(
            f'<g transform="translate({x:.1f},{y:.1f})"><path d="M0,0 C-4,-8 -11,-13 -11,-21 A11,11 0 1 1 11,-21 C11,-13 4,-8 0,0 Z" '
            f'fill="{theme.pin}" stroke="#fff" stroke-width="1.5"/><circle cx="0" cy="-21" r="4.5" fill="#fff"/></g>'
        )
        if s.name in seen_names:
            continue
        seen_names.add(s.name)
        # Photo: try above-left, above-right, left, right.
        r = 36
        if s.image:
            for ox, oy in ((-46, -72), (46, -72), (-62, -30), (62, -30), (0, -86), (-46, 40), (46, 40)):
                box = (x + ox - r, y + oy - r, 2 * r, 2 * r)
                if 0 <= box[0] and box[0] + box[2] <= width and 0 <= box[1] and box[1] + box[3] <= height and not any(_boxes_overlap(box, o) for o in occupied):
                    occupied.append(box)
                    cid = f"ph{i}"
                    defs.append(f'<clipPath id="{cid}"><circle cx="{x + ox:.1f}" cy="{y + oy:.1f}" r="{r}"/></clipPath>')
                    photos_svg.append(
                        f'<circle cx="{x + ox:.1f}" cy="{y + oy:.1f}" r="{r + 3}" fill="#fff" stroke="rgba(0,0,0,.18)" stroke-width="1"/>'
                        f'<image href="{s.image}" x="{x + ox - r:.1f}" y="{y + oy - r:.1f}" width="{2 * r}" height="{2 * r}" '
                        f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>'
                    )
                    break
        size = 13
        w = _text_w(s.name, size) + 10
        h = 22
        for bx, by in ((x + 10, y - 8), (x - 10 - w, y - 8), (x - w / 2, y + 6), (x - w / 2, y - 56), (x + 10, y - 34), (x - 10 - w, y - 34)):
            box = (bx, by, w, h)
            if 0 <= bx and bx + w <= width and 0 <= by and by + h <= height and not any(_boxes_overlap(box, o, 2) for o in occupied):
                break
        occupied.append(box)
        label_svg.append(
            f'<rect x="{box[0]:.1f}" y="{box[1]:.1f}" width="{w:.1f}" height="{h}" rx="4" fill="{theme.label_bg}" stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{box[0] + w / 2:.1f}" y="{box[1] + 15.5:.1f}" font-size="{size}" font-weight="600" fill="{theme.label_fg}" text-anchor="middle">{escape(s.name)}</text>'
        )

    if defs:
        out.insert(1, "<defs>" + "".join(defs) + "</defs>")
    out.extend(name_svg)
    out.extend(photos_svg)
    out.extend(pins_svg)
    out.extend(label_svg)

    # Legend --------------------------------------------------------------------------------
    rows: list[tuple[str | None, str]] = []
    unique_stops = []
    for s in route:
        if not unique_stops or unique_stops[-1].name != s.name:
            unique_stops.append(s)
    for i, s in enumerate(unique_stops):
        prefix = "Arrival " if i == 0 and arrival_label else ""
        rows.append((s.iso, f"{prefix}{s.name}, {s.country}"))
    if departure_label:
        rows.append((None, departure_label))
    lw = max([_text_w(t, 12) for _, t in rows] + [_text_w(legend_title, 14)]) + 50
    lh = 38 + 21 * len(rows)
    lx, ly = 16, 16
    legend = [
        f'<g><rect x="{lx}" y="{ly}" width="{lw:.0f}" height="{lh}" rx="8" fill="#fff" fill-opacity="0.94" stroke="rgba(0,0,0,.12)"/>',
        f'<rect x="{lx}" y="{ly}" width="{lw:.0f}" height="28" rx="8" fill="{theme.label_bg}"/>',
        f'<rect x="{lx}" y="{ly + 20}" width="{lw:.0f}" height="8" fill="{theme.label_bg}"/>',
        f'<text x="{lx + 12}" y="{ly + 19}" font-size="14" font-weight="700" fill="{theme.label_fg}">{escape(legend_title)}</text>',
    ]
    for i, (iso, text) in enumerate(rows):
        yy = ly + 40 + i * 21
        flag = flag_for(iso) if iso else None
        if flag:
            legend.append(f'<image href="{flag}" x="{lx + 12}" y="{yy - 1}" width="20" height="15" preserveAspectRatio="none"/>'
                          f'<rect x="{lx + 12}" y="{yy - 1}" width="20" height="15" fill="none" stroke="rgba(0,0,0,.2)" stroke-width=".6"/>')
        elif iso is None:
            legend.append(f'<g transform="translate({lx + 10},{yy - 3}) scale(0.9)"><path d="{PLANE}" fill="{theme.pin}"/></g>')
        legend.append(f'<text x="{lx + 40}" y="{yy + 11}" font-size="12" fill="#333">{escape(text)}</text>')
    legend.append("</g>")
    out.extend(legend)

    # Compass and scale bar (bottom left) ---------------------------------------------------------
    cx0, cy0 = 44, height - 92
    out.append(
        f'<g transform="translate({cx0},{cy0})" fill="#555" font-size="11" font-weight="700" text-anchor="middle">'
        '<circle r="20" fill="#fff" fill-opacity=".85" stroke="#999"/>'
        '<path d="M0,-17 L5,0 L0,17 L-5,0 Z" fill="#555"/><path d="M0,-17 L5,0 L-5,0 Z" fill="#B3261E"/>'
        '<text y="-24">N</text></g>'
    )
    kpp = v.km_per_px()
    target = kpp * 140
    nice = next((n for n in (25, 50, 100, 150, 200, 250, 300, 500, 750, 1000) if n >= target * 0.6), 1000)
    bar = nice / kpp
    sx, sy = 24, height - 34
    out.append(
        f'<g font-size="11" fill="#444"><rect x="{sx - 6}" y="{sy - 18}" width="{bar + 24:.0f}" height="34" rx="4" fill="#fff" fill-opacity=".8"/>'
        f'<path d="M{sx},{sy} h{bar:.1f}" stroke="#444" stroke-width="2"/><path d="M{sx},{sy - 5} v10 M{sx + bar:.1f},{sy - 5} v10 M{sx + bar / 2:.1f},{sy - 3} v6" stroke="#444" stroke-width="1.5"/>'
        f'<text x="{sx}" y="{sy - 8}">0</text><text x="{sx + bar:.1f}" y="{sy - 8}" text-anchor="end">{nice} km</text></g>'
    )
    out.append(f'<text x="{width - 8}" y="{height - 8}" font-size="9" fill="#888" text-anchor="end">Map: Natural Earth · indicative route, not to scale for road distances</text>')
    out.append("</svg>")
    return "".join(out)
