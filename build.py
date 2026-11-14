#!/usr/bin/env python3
"""Генератор SVG для проекта «Головоломки на закономерность».

Запуск:  python3 build.py [номера задач]
Для каждой задачи пишет img/NN_task.svg и img/NN_solution.svg; при полной сборке — ещё index.html.
"""
import math
import sys
from itertools import combinations
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import ImageFont

OUT = Path(__file__).resolve().parent
IMG = OUT / "img"
W, H = 800, 600
MARGIN = 40

# --- палитра -----------------------------------------------------------------
RED, ORANGE, YELLOW, GREEN = "#E74C3C", "#F39C12", "#F1C40F", "#27AE60"
TEAL, BLUE, PURPLE, PINK = "#1ABC9C", "#3498DB", "#9B59B6", "#FF6FA8"
HIDDEN, LINE, TITLE, TEXT, WHITE = "#D0D3D8", "#222222", "#222222", "#444444", "#FFFFFF"
PASTELS = ["#FADBD8", "#D6EAF8", "#D4EFDF", "#FCF3CF", "#E8DAEF", "#FDEBD0"]
FONT = "Inter, Arial, sans-serif"

_FONT_FILES = {
    False: "/System/Library/Fonts/Supplemental/Arial.ttf",
    True: "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
}


def text_width(s, size, bold=False):
    return ImageFont.truetype(_FONT_FILES[bold], size).getlength(s)


def wrap(s, size, width=W - 2 * MARGIN, bold=False):
    lines, cur = [], ""
    for word in s.split():
        cand = f"{cur} {word}".strip()
        if cur and text_width(cand, size, bold) > width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    return lines + [cur] if cur else lines


def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


# --- примитивы -----------------------------------------------------------------
def text(x, y, s, size, fill=TEXT, weight="normal", anchor="start"):
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def shape(kind, cx, cy, size, fill, stroke=None, sw=0):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    if kind == "circle":
        return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(size / 2)}" fill="{fill}"{st}/>'
    rx = 0.3 * size if kind == "rsquare" else 0
    return (f'<rect x="{f(cx - size / 2)}" y="{f(cy - size / 2)}" width="{f(size)}" '
            f'height="{f(size)}" rx="{f(rx)}" fill="{fill}"{st}/>')


def center_label(cx, cy, s, size, fill=WHITE, weight="bold"):
    # dominant-baseline ненадёжен в разных рендерах — центрируем вручную (cap height ≈ 0.72em)
    return text(cx, cy + 0.36 * size, s, size, fill, weight, "middle")


def qmark(kind, cx, cy, size):
    """Ячейка «?»: тот же элемент, белый жирный «?» на 60 % высоты."""
    return [shape(kind, cx, cy, size, HIDDEN), center_label(cx, cy, "?", 0.6 * size)]


def green_frame(x, y, w, h, pad=5):
    return (f'<rect x="{f(x - pad)}" y="{f(y - pad)}" width="{f(w + 2 * pad)}" '
            f'height="{f(h + 2 * pad)}" fill="none" stroke="{GREEN}" stroke-width="5" rx="4"/>')


class Card:
    """Общий каркас картинки: заголовок, условие, тело, варианты, пояснение."""

    OPT_SIZE, OPT_Y = 110, 410

    def __init__(self, n, condition):
        self.n = n
        self.condition = condition
        self.solution_text = ""
        CARDS[n] = self
        self.head = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
                     text(MARGIN, 48, f"Задача {n}", 28, TITLE, "bold")]
        y = 80
        for line in wrap(condition, 18):
            self.head.append(text(MARGIN, y, line, 18, TEXT))
            y += 24
        self.body_top = y - 6
        self.body = []
        self.options = []  # (буква, элементы, x, y, size)

    def add_options(self, contents, size=None, y=None, gap=30):
        """contents: список функций (cx, cy, size) -> [svg]; рамки по центру, подписи A–F под ними."""
        k, s = len(contents), size or self.OPT_SIZE
        y = self.OPT_Y if y is None else y
        if k > 1:
            gap = min(gap, (W - 2 * MARGIN - k * s) / (k - 1))
        x0 = (W - (k * s + (k - 1) * gap)) / 2
        for i, draw in enumerate(contents):
            x = x0 + i * (s + gap)
            letter = "ABCDEF"[i]
            els = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(s)}" height="{f(s)}" rx="8" '
                   f'fill="{WHITE}" stroke="{HIDDEN}" stroke-width="2"/>']
            els += draw(x + s / 2, y + s / 2, s)
            els.append(text(x + s / 2, y + s + 24, letter, 20, TITLE, "bold", "middle"))
            self.options.append((letter, els, x, y, s))

    def render(self, solution=None, answer_option=None, extra=()):
        els = self.head + self.body + [e for o in self.options for e in o[1]]
        if solution is not None:
            self.solution_text = solution
            els += list(extra)
            for letter, _, x, y, s in self.options:
                if letter == answer_option:
                    els.append(green_frame(x, y, s, s, 3))
            lines = wrap(solution, 16, bold=True)
            for i, line in enumerate(lines):
                els.append(text(MARGIN, H - 12 - 21 * (len(lines) - 1 - i), line, 16, GREEN, "bold"))
        body = "\n  ".join(els)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}">\n  {DEFS}\n  {body}\n</svg>\n')


CARDS = {}
DEFS = ("<defs>" + "".join(
    f'<marker id="arr-{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
    f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{c}"/></marker>'
    for name, c in (("k", LINE), ("g", GREEN), ("h", "#9AA0A6"), ("r", RED), ("n", "#39FF6A"))) + "</defs>")


def save(n, task_svg, sol_svg):
    IMG.mkdir(exist_ok=True)
    (IMG / f"{n:02d}_task.svg").write_text(task_svg, encoding="utf-8")
    (IMG / f"{n:02d}_solution.svg").write_text(sol_svg, encoding="utf-8")


# =============================================================================
# Задача 1. Дни недели — шифр «цвет + форма»
# =============================================================================
CIPHER1 = {
    "П": (RED, "square"),     "О": (ORANGE, "circle"),  "Н": (BLUE, "square"),
    "Е": (GREEN, "circle"),   "Д": (GREEN, "square"),   "Л": (PURPLE, "rsquare"),
    "Ь": (RED, "circle"),     "И": (TEAL, "rsquare"),   "К": (YELLOW, "square"),
    "В": (BLUE, "circle"),    "Т": (PINK, "square"),    "Р": (ORANGE, "square"),
    "С": (YELLOW, "rsquare"), "А": (TEAL, "circle"),    "Ч": (PURPLE, "square"),
    "Г": (GREEN, "rsquare"),  "Я": (PINK, "circle"),    "Ц": (BLUE, "rsquare"),
    "У": (YELLOW, "circle"),  "Б": (ORANGE, "rsquare"),
}


def check_cipher(cipher, words):
    assert len(set(cipher.values())) == len(cipher), "пары «цвет + форма» не уникальны"
    missing = {c for w in words for c in w} - cipher.keys()
    assert not missing, f"нет кодов для букв {missing}"


def task01():
    words = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
    check_cipher(CIPHER1, words)
    assert len(CIPHER1) == 20
    cell, gap, cols = 44, 6, 11
    gw = cols * cell + (cols - 1) * gap
    x0 = (W - gw) / 2

    card = Card(1, "Каждой букве всегда соответствует одна и та же пара «цвет + форма». "
                   "Важны и цвет, и форма: жёлтый квадрат и жёлтый круг — разные буквы. "
                   "Открыта только одна буква — «Ч». Расшифруйте слова и назовите букву на месте «?».")
    y0 = card.body_top + 16
    task_els, sol_els, q_pos = [], [], None
    for r, word in enumerate(words):
        start = cols - len(word)  # выравнивание по правому краю
        for i, ch in enumerate(word):
            cx = x0 + (start + i) * (cell + gap) + cell / 2
            cy = y0 + r * (cell + gap) + cell / 2
            color, kind = CIPHER1[ch]
            if r == 6 and i == 3:
                q_pos = (cx, cy)
                task_els += qmark(kind, cx, cy, cell)
                sol_els += [shape(kind, cx, cy, cell, color), center_label(cx, cy, ch, 24),
                            green_frame(cx - cell / 2, cy - cell / 2, cell, cell, 4)]
                continue
            task_els.append(shape(kind, cx, cy, cell, color))
            if r == 3 and i == 0:
                task_els.append(center_label(cx, cy, ch, 24))
            sol_els += [shape(kind, cx, cy, cell, color), center_label(cx, cy, ch, 24)]
    assert words[6][3] == "К" and q_pos

    card.body = task_els
    task = card.render()
    card.body = sol_els
    sol = card.render("Ответ: К. Длины строк 11-7-5-7-7-7-11 и «Ч» в начале 4-й строки → ЧЕТВЕРГ, "
                      "значит строки — дни недели; «?» стоит в ВОСК…РЕСЕНЬЕ.")
    save(1, task, sol)
    return "К"


# =============================================================================
# Задача 8. Часы: +2 ч 15 мин
# =============================================================================
def clock(cx, cy, d, hm=None, hidden=False, stroke=4):
    r = d / 2
    els = [f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r - stroke / 2)}" '
           f'fill="{HIDDEN if hidden else WHITE}" stroke="{LINE}" stroke-width="{stroke}"/>']
    for k in range(12):
        a = math.radians(k * 30)
        long_tick = k % 3 == 0
        r1, r2 = r * (0.74 if long_tick else 0.8), r * 0.9
        els.append(f'<line x1="{f(cx + r1 * math.sin(a))}" y1="{f(cy - r1 * math.cos(a))}" '
                   f'x2="{f(cx + r2 * math.sin(a))}" y2="{f(cy - r2 * math.cos(a))}" '
                   f'stroke="{LINE}" stroke-width="{f(stroke * (0.75 if long_tick else 0.5))}" '
                   f'stroke-linecap="round"/>')
    if hidden:
        els.append(center_label(cx, cy, "?", 0.6 * d))
        return els
    if hm:
        h, m = hm
        hour_angle = (h % 12) * 30 + m * 0.5       # часовая стрелка точно по времени
        minute_angle = m * 6
        for ang, length, width in ((hour_angle, 0.5, stroke * 1.5), (minute_angle, 0.78, stroke * 0.75)):
            a = math.radians(ang)
            els.append(f'<line x1="{f(cx)}" y1="{f(cy)}" x2="{f(cx + r * length * math.sin(a))}" '
                       f'y2="{f(cy - r * length * math.cos(a))}" stroke="{LINE}" '
                       f'stroke-width="{f(width)}" stroke-linecap="round"/>')
        els.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(stroke * 1.2)}" fill="{LINE}"/>')
    return els


def task08():
    times = [(2, 15), (4, 30), (6, 45)]
    # проверка углов из описания: 67.5/90, 135/180, 202.5/270
    assert [(h * 30 + m * 0.5, m * 6) for h, m in times] == [(67.5, 90), (135, 180), (202.5, 270)]
    step = 2 * 60 + 15
    nxt = divmod(times[-1][0] * 60 + times[-1][1] + step, 60)
    assert nxt == (9, 0)
    options = [(9, 0), (8, 45), (9, 15), (8, 0)]
    answer = "ABCD"[options.index(nxt)]

    card = Card(8, "Какое время на последних часах?")
    d, gap = 150, 40
    x0 = (W - (4 * d + 3 * gap)) / 2
    cy = (card.body_top + Card.OPT_Y) / 2
    for i in range(4):
        cx = x0 + d / 2 + i * (d + gap)
        card.body += clock(cx, cy, d, times[i] if i < 3 else None, hidden=(i == 3))
        if i < 3:  # стрелка-переход между часами
            ax = cx + d / 2 + 8
            card.body.append(f'<path d="M{f(ax)} {f(cy)} h{gap - 16} m-7 -6 l7 6 l-7 6" fill="none" '
                             f'stroke="{HIDDEN}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    card.add_options([lambda x, y, s, t=t: clock(x, y, 0.8 * s, t, stroke=3) for t in options])
    task = card.render()
    sol_clock = clock(x0 + d / 2 + 3 * (d + gap), cy, d, nxt)
    sol = card.render("Ответ: A — 9:00. Каждый раз прибавляется 2 ч 15 мин: "
                      "2:15 → 4:30 → 6:45 → 9:00.", answer, extra=sol_clock)
    save(8, task, sol)
    return f"{answer} (9:00)"


# =============================================================================
# Задача 12. Круг Мозера
# =============================================================================
def _seg_intersect(p1, p2, p3, p4):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p1, p2, p3, p4
    den = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(den) < 1e-12:
        return None
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / den
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / den
    eps = 1e-9
    if eps < t < 1 - eps and eps < u < 1 - eps:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1)), t, u
    return None


def moser(angles_deg):
    """Разбиение единичного круга хордами. Возвращает точки, хорды и грани (многоугольники).

    Проверяет, что никакие три хорды не пересекаются в одной точке, и что число
    граней совпадает с формулой Эйлера.
    """
    pts = [(math.sin(math.radians(a)), math.cos(math.radians(a))) for a in angles_deg]  # 0° — сверху, по часовой
    n = len(pts)
    chords = list(combinations(range(n), 2))
    on_chord = {c: [(0.0, ("p", c[0])), (1.0, ("p", c[1]))] for c in chords}
    inter = []  # [точка, {хорды}]
    for c1, c2 in combinations(chords, 2):
        if set(c1) & set(c2):
            continue
        hit = _seg_intersect(pts[c1[0]], pts[c1[1]], pts[c2[0]], pts[c2[1]])
        if not hit:
            continue
        p, t, u = hit
        for k, (q, owners) in enumerate(inter):
            if math.dist(p, q) < 1e-7:
                owners.update((c1, c2))
                break
        else:
            k = len(inter)
            inter.append([p, {c1, c2}])
        on_chord[c1].append((t, ("x", k)))
        on_chord[c2].append((u, ("x", k)))
    triples = [o for _, o in inter if len(o) > 2]
    assert not triples, f"три хорды в одной точке: {triples}"

    # граф: вершины — точки на окружности, пересечения и промежуточные точки дуг
    coords = {("p", i): p for i, p in enumerate(pts)}
    coords.update({("x", k): p for k, (p, _) in enumerate(inter)})
    adj = {v: set() for v in coords}
    chord_edges = set()

    def link(a, b, chord=False):
        adj[a].add(b)
        adj[b].add(a)
        if chord:
            chord_edges.add(frozenset((a, b)))

    for c, lst in on_chord.items():
        lst.sort()
        for (_, a), (_, b) in zip(lst, lst[1:]):
            link(a, b, chord=True)
    order = sorted(range(n), key=lambda i: angles_deg[i] % 360)
    arc_steps = 24
    for j, i in enumerate(order):
        a0 = angles_deg[i] % 360
        a1 = angles_deg[order[(j + 1) % n]] % 360 if n > 1 else a0
        span = (a1 - a0) % 360 or 360
        prev = ("p", i)
        for s in range(1, arc_steps):
            ang = math.radians(a0 + span * s / arc_steps)
            v = ("a", i, s)
            coords[v] = (math.sin(ang), math.cos(ang))
            adj[v] = set()
            link(prev, v)
            prev = v
        link(prev, ("p", order[(j + 1) % n]))

    # обход граней по полурёбрам
    def ang(a, b):
        (ax, ay), (bx, by) = coords[a], coords[b]
        return math.atan2(by - ay, bx - ax)

    nbrs = {v: sorted(adj[v], key=lambda w: ang(v, w)) for v in adj}
    seen, faces = set(), []
    for u in adj:
        for v in adj[u]:
            if (u, v) in seen:
                continue
            face, a, b = [], u, v
            while (a, b) not in seen:
                seen.add((a, b))
                face.append(a)
                lst = nbrs[b]
                c = lst[(lst.index(a) - 1) % len(lst)]  # самый правый поворот
                a, b = b, c
            poly = [coords[x] for x in face]
            area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1])) / 2
            if area > 1e-9:  # внешняя грань имеет отрицательную площадь
                faces.append((face, poly, area))

    # контроль Эйлером: внутри круга F = E − V + 1
    n_v = n + len(inter)
    n_e = sum(len(l) - 1 for l in on_chord.values()) + (n if n > 0 else 0)
    expected = n_e - n_v + 1 if n > 0 else 1
    assert len(faces) == expected, (len(faces), expected)
    return pts, chords, faces, chord_edges


def _color_faces(faces, chord_edges):
    edge_faces = {}
    for idx, (face, _, _) in enumerate(faces):
        for a, b in zip(face, face[1:] + face[:1]):
            e = frozenset((a, b))
            if e in chord_edges:
                edge_faces.setdefault(e, set()).add(idx)
    neigh = {i: set() for i in range(len(faces))}
    for fs in edge_faces.values():
        for i in fs:
            neigh[i] |= fs - {i}
    colors = {}
    for i in sorted(neigh, key=lambda i: -len(neigh[i])):
        used = {colors.get(j) for j in neigh[i]}
        colors[i] = next(c for c in PASTELS if c not in used)
    return colors


def moser_drawing(cx, cy, r, angles, draw_chords=True, numbered=False):
    pts, chords, faces, chord_edges = moser(angles)
    T = lambda p: (cx + r * p[0], cy - r * p[1])
    els = []
    if draw_chords:
        colors = _color_faces(faces, chord_edges)
        labels = []
        for i, (_, poly, _) in enumerate(faces):
            d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in map(T, poly)) + " Z"
            els.append(f'<path d="{d}" fill="{colors[i]}"/>')
            if numbered:
                # полюс недоступности приблизим центроидом (грани выпуклые)
                gx = sum(p[0] for p in poly) / len(poly)
                gy = sum(p[1] for p in poly) / len(poly)
                inr = min(_dist_to_seg((gx, gy), a, b) for a, b in zip(poly, poly[1:] + poly[:1])) * r
                size = max(8, min(14, 1.5 * inr))
                labels.append((T((gx, gy)), size))
        for a, b in chords:
            (x1, y1), (x2, y2) = T(pts[a]), T(pts[b])
            els.append(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
                       f'stroke="{LINE}" stroke-width="1.5"/>')
        if numbered:
            labels.sort(key=lambda l: (round(l[0][1] / 12), l[0][0]))
            for k, ((x, y), size) in enumerate(labels, 1):
                els.append(text(x, y + 0.36 * size, str(k), f(size), LINE, "bold", "middle"))
    els.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="none" stroke="{LINE}" stroke-width="2.5"/>')
    for p in pts:
        x, y = T(p)
        els.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="5" fill="{LINE}"/>')
    return els, len(faces)


def _dist_to_seg(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def task12():
    sets = [[30], [40, 200], [20, 140, 250], [10, 105, 200, 290],
            [0, 65, 150, 215, 290], [0, 50, 115, 170, 235, 300]]
    card = Card(12, "На окружности отмечено n точек, каждая пара соединена хордой, никакие три хорды "
                    "не проходят через одну точку. На сколько частей разделится круг при 6 точках?")
    r = 85  # в описании 70; увеличено, чтобы в решении читались номера всех 31 областей
    cols = [125, 370, 615]
    rows = [card.body_top + 30 + r, card.body_top + 30 + 3 * r + 35]
    task_els, sol_els, counts = [], [], []
    for i, angles in enumerate(sets):
        cx, cy = cols[i % 3], rows[i // 3]
        last = i == 5
        els, cnt = moser_drawing(cx, cy, r, angles, draw_chords=not last)
        counts.append(cnt)
        task_els += els
        if last:
            sol, cnt6 = moser_drawing(cx, cy, r, angles, numbered=True)
            sol_els += sol
        else:
            sol_els += els
        lx = cx + r + 42  # подпись справа от круга
        if last:
            bw, bh = 60, 40
            box = f'<rect x="{f(lx - bw / 2)}" y="{f(cy - bh / 2)}" width="{bw}" height="{bh}" rx="12" fill="{{}}"/>'
            task_els += [box.format(HIDDEN), center_label(lx, cy, "?", 24)]
            sol_els += [box.format(GREEN), center_label(lx, cy, str(cnt6), 24)]
        else:
            lbl = center_label(lx, cy, str(cnt), 28, TITLE)
            task_els.append(lbl)
            sol_els.append(lbl)
    # отрисованные области = 1, 2, 4, 8, 16, а при 6 точках — 31
    assert counts[:5] == [1, 2, 4, 8, 16], counts
    assert cnt6 == 31 == math.comb(6, 4) + math.comb(6, 2) + 1, cnt6

    card.body = task_els
    task = card.render()
    card.body = sol_els
    sol = card.render("Ответ: 31, а не 32. Областей C(6,4) + C(6,2) + 1 = 15 + 15 + 1 = 31.")
    save(12, task, sol)
    return "31"




# =============================================================================
# Общие помощники для задач 2–24
# =============================================================================
def line(x1, y1, x2, y2, stroke=LINE, sw=2, extra=""):
    return (f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{stroke}" '
            f'stroke-width="{f(sw)}" stroke-linecap="round"{extra}/>')


def rect(x, y, w, h, fill, rx=0, stroke=None, sw=0, extra=""):
    st = f' stroke="{stroke}" stroke-width="{f(sw)}"' if stroke else ""
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" '
            f'fill="{fill}"{st}{extra}/>')


def polygon(pts, fill, stroke=None, sw=0):
    st = f' stroke="{stroke}" stroke-width="{f(sw)}" stroke-linejoin="round"' if stroke else ""
    return f'<polygon points="{" ".join(f"{f(x)},{f(y)}" for x, y in pts)}" fill="{fill}"{st}/>'


def ngon(cx, cy, r, n):
    """Правильный n-угольник с горизонтальным нижним ребром (ось y вниз)."""
    return [(cx + r * math.cos(math.pi / 2 + math.pi / n + 2 * math.pi * k / n),
             cy + r * math.sin(math.pi / 2 + math.pi / n + 2 * math.pi * k / n)) for k in range(n)]


def figure(kind, cx, cy, size, fill):
    """circle / square / rsquare / triangle / star размером size."""
    if kind == "triangle":
        h = size * math.sqrt(3) / 2
        return polygon([(cx, cy - h / 2 - 2), (cx + size / 2, cy + h / 2 - 2), (cx - size / 2, cy + h / 2 - 2)], fill)
    if kind == "star":
        pts = [(cx + (size / 2 if k % 2 == 0 else size * 0.21) * math.cos(-math.pi / 2 + k * math.pi / 5),
                cy + size * 0.06 + (size / 2 if k % 2 == 0 else size * 0.21) * math.sin(-math.pi / 2 + k * math.pi / 5))
               for k in range(10)]
        return polygon(pts, fill)
    return shape(kind, cx, cy, size * (0.88 if kind != "circle" else 1), fill)


def figure_row(kind, n, color, cx, cy, size=24, gap=6):
    x0 = cx - (n * size + (n - 1) * gap) / 2 + size / 2
    return [figure(kind, x0 + i * (size + gap), cy, size, color) for i in range(n)]


def hidden_box(cx, cy, w, h, label="?", fill=HIDDEN, size=None):
    return [rect(cx - w / 2, cy - h / 2, w, h, fill, 10), center_label(cx, cy, label, size or 0.6 * h)]


# --- собственные цифры (одинаково выглядят в любом шрифте и при повороте) -------
# бокс 10×16; петли — эллипсы, их можно залить
GLYPHS = {
    "0": ("", [(5, 8, 4.2, 7)]),
    "1": ("M5 1 V15", []),
    "2": ("M1.3 4.6 C1.3 2.4 3 1 5 1 C7.2 1 8.8 2.5 8.8 4.5 C8.8 6.8 6.8 8.6 1 15 H9.2", []),
    "3": ("M1.4 1 H8.6 L4.6 6.4 C7.2 6.2 9 8.2 9 10.7 C9 13.2 7.2 15 4.9 15 C3.1 15 1.8 14.2 1 12.8", []),
    "4": ("M7 15 V1 L1 10.6 H9.4", []),
    "5": ("M8.6 1 H2.3 L1.7 7.3 C2.7 6.6 3.8 6.3 5 6.3 C7.4 6.3 9 8.2 9 10.6 C9 13.2 7.2 15 5 15 "
          "C3.1 15 1.8 14.2 1 12.8", []),
    "6": ("M8.2 1.6 C4.4 1.8 1.1 4.6 1.1 11", [(5, 11, 3.9, 3.9)]),
    "7": ("M1 1 H9 L3.6 15", []),
    "8": ("", [(5, 4.5, 3.5, 3.5), (5, 11.5, 3.5, 3.5)]),
    "9": ("M1.8 14.4 C5.6 14.2 8.9 11.4 8.9 5", [(5, 5, 3.9, 3.9)]),  # ровно 6, повёрнутая на 180°
    "=": ("M1.5 6 H8.5 M1.5 10 H8.5", []),
}
LOOPS = {d: len(GLYPHS[d][1]) for d in "0123456789"}


def glyph_text(s, x, y, h, color, sw, loop_fill=None, adv=None):
    """Строка из GLYPHS; (x, y) — левый верхний угол. Возвращает (svg, ширина)."""
    k, adv = h / 16, adv or 0.8 * h
    els, cx = [], x
    for ch in s:
        if ch == " ":
            cx += adv * 0.45
            continue
        if ch == "?":
            els.append(text(cx + 5 * k, y + h, "?", f(h * 1.3), color, "bold", "middle"))
            cx += adv
            continue
        path, loops = GLYPHS[ch]
        g = [f'<g transform="translate({f(cx)} {f(y)}) scale({f(k)})" fill="none" stroke="{color}" '
             f'stroke-width="{f(sw / k)}" stroke-linecap="round" stroke-linejoin="round">']
        g += [f'<ellipse cx="{ex}" cy="{ey}" rx="{rx}" ry="{ry}" fill="{loop_fill or "none"}"/>'
              for ex, ey, rx, ry in loops]
        if path:
            g.append(f'<path d="{path}"/>')
        els.append("".join(g) + "</g>")
        cx += adv
    return els, cx - x - (adv - 10 * k)


# --- семисегментный индикатор -----------------------------------------------------
SEG = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc",
       5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg"}
MIRROR = str.maketrans("bcef", "fecb")  # отражение по вертикальной оси


def seven_seg(x, y, w, h, t, lit, on, off=None):
    rects = {"a": (x + .55 * t, y, w - 1.1 * t, t), "g": (x + .55 * t, y + h / 2 - t / 2, w - 1.1 * t, t),
             "d": (x + .55 * t, y + h - t, w - 1.1 * t, t),
             "f": (x, y + .55 * t, t, h / 2 - 1.1 * t), "b": (x + w - t, y + .55 * t, t, h / 2 - 1.1 * t),
             "e": (x, y + h / 2 + .55 * t, t, h / 2 - 1.1 * t), "c": (x + w - t, y + h / 2 + .55 * t, t, h / 2 - 1.1 * t)}
    return [rect(*r, on if k in lit else off, t / 2) for k, r in rects.items() if k in lit or off]


# =============================================================================
# Задача 2. Числительные ОДИН…ДЕСЯТЬ
# =============================================================================
CIPHER2 = {
    "О": (BLUE, "circle"),    "Д": (RED, "square"),     "И": (GREEN, "rsquare"),
    "Н": (ORANGE, "square"),  "В": (PURPLE, "circle"),  "А": (TEAL, "square"),
    "Т": (YELLOW, "rsquare"), "Р": (PINK, "square"),    "Ч": (GREEN, "square"),
    "Е": (YELLOW, "circle"),  "Ы": (PURPLE, "rsquare"), "П": (ORANGE, "circle"),
    "Я": (PINK, "rsquare"),   "Ь": (YELLOW, "square"),  "Ш": (RED, "circle"),
    "С": (TEAL, "circle"),    "М": (BLUE, "square"),
}


def task02():
    words = ["ОДИН", "ДВА", "ТРИ", "ЧЕТЫРЕ", "ПЯТЬ", "ШЕСТЬ", "СЕМЬ", "ВОСЕМЬ", "ДЕВЯТЬ", "ДЕСЯТЬ"]
    check_cipher(CIPHER2, words)
    cell, gap, cols = 40, 4, 6
    x0 = (W - (cols * cell + (cols - 1) * gap)) / 2
    card = Card(2, "То же правило: буква ↔ пара «цвет + форма». Открыта одна буква — «Ш». "
                   "Какая буква на месте «?»?")
    y0 = card.body_top - 4
    t_els, s_els = [], []
    for r, word in enumerate(words):
        for i, ch in enumerate(word):
            cx = x0 + (cols - len(word) + i) * (cell + gap) + cell / 2
            cy = y0 + r * (cell + gap) + cell / 2
            color, kind = CIPHER2[ch]
            if (r, i) == (9, 3):
                t_els += qmark(kind, cx, cy, cell)
                s_els += [shape(kind, cx, cy, cell, color), center_label(cx, cy, ch, 22),
                          green_frame(cx - cell / 2, cy - cell / 2, cell, cell, 4)]
                continue
            t_els.append(shape(kind, cx, cy, cell, color))
            if (r, i) == (5, 0):
                t_els.append(center_label(cx, cy, ch, 22))
            s_els += [shape(kind, cx, cy, cell, color), center_label(cx, cy, ch, 22)]
    assert words[9][3] == "Я" and words[5][0] == "Ш"
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: Я. Строки — числа ОДИН…ДЕСЯТЬ, «?» стоит в ДЕС(Я)ТЬ.")
    save(2, task, sol)
    return "Я"


# =============================================================================
# Задача 3. О Д Т Ч П Ш С ?
# =============================================================================
NUMBERS = ["один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь"]


def task03():
    letters = [w[0].upper() for w in NUMBERS]
    assert "".join(letters[:7]) == "ОДТЧПШС"
    card = Card(3, "Какая буква следующая?")
    t_els, s_els = [], []
    for i, ch in enumerate(letters):
        cx, cy = 85 + 90 * i, 300
        if i == 7:
            t_els += qmark("circle", cx, cy, 80)
            s_els += [shape("circle", cx, cy, 80, GREEN), center_label(cx, cy, ch, 40),
                      f'<circle cx="{cx}" cy="{cy}" r="46" fill="none" stroke="{GREEN}" stroke-width="5"/>']
        else:
            els = [shape("circle", cx, cy, 80, BLUE), center_label(cx, cy, ch, 40)]
            t_els += els
            s_els += els
        s_els.append(text(cx, cy + 72, NUMBERS[i], 15, TEXT, "normal", "middle"))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: В. Это первые буквы числительных: один, два, три … семь, восемь.")
    save(3, task, sol)
    return letters[7]


# =============================================================================
# Задачи 4 и 5. Кольцо месяцев
# =============================================================================
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]


def ring_pos(cx, cy, R, k):
    a = math.radians(30 * k)  # позиция 1 — «1 час», 12 — сверху
    return cx + R * math.sin(a), cy - R * math.cos(a)


def task04():
    letters = [m[0].upper() for m in MONTHS]
    assert "".join(letters[:7]) == "ЯФМАМИИ"
    card = Card(4, "Продолжите ряд.")
    cx, cy, R, d = 400, 326, 195, 60
    base = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#E5E7EA" stroke-width="2"/>']
    t_els, s_els = list(base), list(base)
    for k in range(1, 13):
        x, y = ring_pos(cx, cy, R, k)
        ch = letters[k - 1]
        if k <= 7:
            els = [shape("circle", x, y, d, ORANGE), center_label(x, y, ch, 28)]
            t_els += els
            s_els += els
        elif k == 8:
            t_els += qmark("circle", x, y, d)
            s_els += [shape("circle", x, y, d, ORANGE), center_label(x, y, ch, 28),
                      f'<circle cx="{f(x)}" cy="{f(y)}" r="{d / 2 + 6}" fill="none" stroke="{GREEN}" stroke-width="5"/>']
        else:
            ring = shape("circle", x, y, d - 3, WHITE, HIDDEN, 3)
            t_els.append(ring)
            s_els += [ring, center_label(x, y, ch, 28, "#B5BAC1")]
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: А. Это первые буквы месяцев: январь, февраль … июль, август.")
    save(4, task, sol)
    return letters[7]


def task05():
    letters = [m[-1].upper() for m in MONTHS]
    assert "".join(letters) == "ЬЬТЬЙЬЬТЬЬЬЬ"
    card = Card(5, "Одна буква заменена на «?». Какая?")
    cx, cy, R, d = 400, 334, 158, 60
    base = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#E5E7EA" stroke-width="2"/>']
    t_els, s_els = list(base), list(base)
    for k in range(1, 13):
        x, y = ring_pos(cx, cy, R, k)
        ch = letters[k - 1]
        if k == 5:
            t_els += qmark("circle", x, y, d)
            s_els += [shape("circle", x, y, d, PURPLE), center_label(x, y, ch, 28),
                      f'<circle cx="{f(x)}" cy="{f(y)}" r="{d / 2 + 6}" fill="none" stroke="{GREEN}" stroke-width="5"/>']
        else:
            els = [shape("circle", x, y, d, PURPLE), center_label(x, y, ch, 28)]
            t_els += els
            s_els += els
        lx, ly = ring_pos(cx, cy, R + 52, k)
        sa = math.sin(math.radians(30 * k))
        anchor = "middle" if abs(sa) < 0.3 else ("start" if sa > 0 else "end")
        m = MONTHS[k - 1]
        s_els.append(text(lx, ly + 5, m[:-1] + m[-1].upper(), 14, GREEN if k == 5 else TEXT,
                          "bold" if k == 5 else "normal", anchor))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: Й. Это последние буквы месяцев: январЬ, февралЬ, марТ, апрелЬ, маЙ…")
    save(5, task, sol)
    return letters[4]


# =============================================================================
# Задача 6. Клавиатура ЙЦУКЕН
# =============================================================================
def key(x, y, s, label, fill="#F2F2F2", stroke="#888888", color=LINE, size=None):
    return [rect(x, y + 4, s, s, "#888888", s / 7, extra=' opacity="0.3"'),
            rect(x, y, s, s, fill, s / 7, stroke, 1.5),
            center_label(x + s / 2, y + s / 2, label, size or 32 * s / 70, color)]


def task06():
    rows = ["ЙЦУКЕНГШЩЗХЪ", "ФЫВАПРОЛДЖЭ", "ЯЧСМИТЬБЮ"]
    seq = "".join(rows[r][c] for c in range(3) for r in range(3))
    assert seq == "ЙФЯЦЫЧУВС"
    card = Card(6, "Какая буква следующая?")
    s, gap = 70, 10
    x0, y0 = (W - (9 * s + 8 * gap)) / 2, card.body_top + 24
    t_els, s_els = [], []
    for i, ch in enumerate(seq):
        x = x0 + i * (s + gap)
        if i == 8:
            t_els += key(x, y0, s, "?", HIDDEN, HIDDEN, WHITE, 42)
            s_els += key(x, y0, s, ch, GREEN, GREEN, WHITE) + [green_frame(x, y0, s, s, 5)]
        else:
            els = key(x, y0, s, ch)
            t_els += els
            s_els += els
    # схема раскладки в решении
    ks, kg, rg = 46, 6, 22
    kx0 = (W - (12 * (ks + kg) - kg + 40)) / 2
    ky0 = y0 + s + 52
    hl = [RED, ORANGE, GREEN]
    centers = {}
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            x, y = kx0 + r * 20 + c * (ks + kg), ky0 + r * (ks + rg)
            centers[(r, c)] = (x + ks / 2, y, y + ks)
            if c < 3:
                s_els += key(x, y, ks, ch, hl[c], hl[c], WHITE, 22)
            else:
                s_els += key(x, y, ks, ch, size=20)
    for c in range(3):
        for r in range(2):
            (xa, _, ya), (xb, yb, _) = centers[(r, c)], centers[(r + 1, c)]
            s_els.append(f'<path d="M{f(xa)} {f(ya + 3)} L{f(xb)} {f(yb - 4)}" stroke="{LINE}" stroke-width="2.5" '
                         f'marker-end="url(#arr-k)"/>')
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: С. Буквы идут столбцами клавиатуры ЙЦУКЕН сверху вниз: Й-Ф-Я, Ц-Ы-Ч, У-В-С.")
    save(6, task, sol)
    return "С"


# =============================================================================
# Задача 7. Парковка
# =============================================================================
ROT180 = {"0": "0", "1": "1", "6": "9", "8": "8", "9": "6"}


def task07():
    nums = ["16", "06", "68", "88", None, "98"]
    turned = ["".join(ROT180[c] for c in reversed(n)) if n else None for n in reversed(nums)]
    known = [int(t) for t in turned if t]
    assert turned[1] is None and known == [86, 88, 89, 90, 91]
    answer = known[0] + 1

    card = Card(7, "Под каким номером стоит машина?")
    sw, sh, x0, y0 = 110, 200, 70, 165
    lot = [rect(50, y0 - 35, 700, sh + 70, "#3A3A3A", 14)]
    lot.append(line(x0, y0, x0 + 6 * sw, y0, WHITE, 6))
    for i in range(7):
        lot.append(line(x0 + i * sw, y0, x0 + i * sw, y0 + sh, WHITE, 6))
    for i, n in enumerate(nums):
        if n:
            els, wdt = glyph_text(n, 0, 0, 40, WHITE, 6, adv=30)
            gx = x0 + i * sw + sw / 2 - wdt / 2
            lot += glyph_text(n, gx, y0 + sh - 56, 40, WHITE, 6, adv=30)[0]
    cx = x0 + 4 * sw + 10
    car = [rect(cx, y0 + 15, 90, 170, RED, 20),
           rect(cx + 12, y0 + 45, 66, 30, "#9AD1F5", 8), rect(cx + 14, y0 + 140, 62, 22, "#9AD1F5", 6)]
    task_lot = lot + car + [center_label(cx + 45, y0 + 108, "?", 40)]
    card.body = task_lot
    task = card.render()
    seq = []
    for k in range(86, 92):
        col = GREEN if k == answer else TITLE
        seq.append(f'<tspan fill="{col}">{k}</tspan>')
    row = (f'<text x="400" y="{y0 + sh + 92}" font-family="{FONT}" font-size="30" font-weight="bold" '
           f'text-anchor="middle">{" · ".join(seq)}</text>')
    card.body = [f'<g transform="rotate(180 400 {y0 + sh / 2})">'] + lot + car + ["</g>", row]
    sol = card.render(f"Ответ: {answer}. Переверните картинку: места пронумерованы подряд 86, 87, 88, 89, 90, 91.")
    save(7, task, sol)
    return str(answer)


# =============================================================================
# Задача 9. Дырки в цифрах
# =============================================================================
def task09():
    data = [("8809", 6), ("7111", 0), ("2172", 0), ("6666", 4), ("1111", 0), ("3213", 0), ("7662", 2),
            ("9313", 1), ("0000", 4), ("2222", 0), ("3333", 0), ("5555", 0), ("8193", 3), ("8096", 5),
            ("7777", 0), ("9999", 4), ("7756", 1), ("6855", 3), ("9881", 5), ("5531", 0), ("2581", None)]
    loops = lambda s: sum(LOOPS[c] for c in s)
    for s_, v in data[:-1]:
        assert loops(s_) == v, s_
        assert "4" not in s_
    answer = loops("2581")
    assert answer == 2

    card = Card(9, "Найдите значение 2581.")
    cw, ch_, gx, gy = 220, 44, 20, 10
    x0, y0 = (W - (3 * cw + 2 * gx)) / 2, card.body_top + 14
    t_els, s_els = [], []
    for i, (left, val) in enumerate(data):
        col, row = divmod(i, 7)
        x, y = x0 + col * (cw + gx), y0 + row * (ch_ + gy)
        last = val is None
        bg = rect(x, y, cw, ch_, "#FFF3B0" if last else WHITE, 8, "#C8CCD1", 1.5)
        right = f" = {answer if last else val}"
        for target, fill, rtext in ((t_els, None, " = ?" if last else right), (s_els, PINK, right)):
            target.append(bg)
            a, w1 = glyph_text(left, x + 24, y + 10, 24, LINE, 3, fill, adv=17)
            b, _ = glyph_text(rtext, x + 24 + w1 + 4, y + 10, 24, LINE, 3, adv=17)
            target += a + b
        if last:
            s_els.append(green_frame(x, y, cw, ch_, 4))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: 2. Считаются замкнутые «петли»: у 0, 6 и 9 по одной, у 8 — две. "
                      "В 2581 петли есть только у восьмёрки.")
    save(9, task, sol)
    return str(answer)


# =============================================================================
# Задача 10. Калькулятор
# =============================================================================
def task10():
    seq = [8, 7, 3, 5]
    for a, b in zip(seq, seq[1:]):
        assert len(SEG[a]) == b
    answer = len(SEG[seq[-1]])
    assert answer == 5 and len(SEG[7]) == 3

    card = Card(10, "Какая цифра следующая?")
    on, off = "#39FF6A", "#14452D"
    py = card.body_top + 30
    dw, dh, gap = 90, 160, 40
    x0 = (W - (5 * dw + 4 * gap)) / 2
    dy = py + 70
    panel = [rect(60, py, 680, 270, "#0B2E1F", 18)]
    t_els, s_els = list(panel), list(panel)
    for i in range(5):
        x = x0 + i * (dw + gap)
        if i < 4:
            els = seven_seg(x, dy, dw, dh, 12, SEG[seq[i]], on, off)
            t_els += els
            s_els += els
            s_els.append(text(x + dw / 2, py + 40, str(len(SEG[seq[i]])), 22, on, "bold", "middle"))
            s_els.append(f'<path d="M{f(x + dw / 2 + 16)} {f(py + 33)} Q{f(x + dw + gap / 2)} {f(py + 14)} '
                         f'{f(x + dw + gap + dw / 2 - 6)} {f(dy - 10)}" fill="none" stroke="{on}" '
                         f'stroke-width="2" marker-end="url(#arr-n)"/>')
        else:
            t_els += seven_seg(x, dy, dw, dh, 12, "", on, off)
            t_els.append(center_label(x + dw / 2, dy + dh / 2, "?", 90))
            s_els += seven_seg(x, dy, dw, dh, 12, SEG[answer], on, off)
            s_els.append(green_frame(x - 8, dy - 8, dw + 16, dh + 16, 2))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: 5. Каждая цифра равна числу горящих сегментов предыдущей: 8 → 7 → 3 → 5 → 5.")
    save(10, task, sol)
    return str(answer)


# =============================================================================
# Задача 11. Смотри-и-говори
# =============================================================================
def look_and_say(s):
    out, i = "", 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out += f"{j - i}{s[i]}"
        i = j
    return out


def task11():
    rows = ["1"]
    for _ in range(5):
        rows.append(look_and_say(rows[-1]))
    assert rows[:5] == ["1", "11", "21", "1211", "111221"] and rows[5] == "312211"
    colors = {"1": "#9AD1F5", "2": ORANGE, "3": GREEN}
    card = Card(11, "Какое число следующее?")
    sq, gap, rh = 44, 8, 54
    y0 = card.body_top + 14
    t_els, s_els = [], []
    for r, row in enumerate(rows):
        x0 = (W - (len(row) * (sq + gap) - gap)) / 2
        y = y0 + r * rh
        for i, d in enumerate(row):
            x = x0 + i * (sq + gap)
            els = [rect(x, y, sq, sq, colors[d], 6), center_label(x + sq / 2, y + sq / 2, d, 26, LINE)]
            if r == 5:
                t_els += [rect(x, y, sq, sq, HIDDEN, 6), center_label(x + sq / 2, y + sq / 2, "?", 26)]
            else:
                t_els += els
            s_els += els
        if r == 5:
            s_els.append(green_frame(x0, y, len(row) * (sq + gap) - gap, sq, 6))
            for g, label in enumerate(["три единицы", "две двойки", "одна единица"]):
                xa, xb = x0 + g * 2 * (sq + gap), x0 + g * 2 * (sq + gap) + 2 * sq + gap
                by = y + sq + 14
                s_els.append(f'<path d="M{f(xa + 2)} {f(by)} v8 H{f(xb - 2)} v-8" fill="none" stroke="{LINE}" stroke-width="2"/>')
                s_els.append(text((xa + xb) / 2, by + 28, label, 13, TEXT, "normal", "middle"))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: 312211. Каждая строка «читает вслух» предыдущую: "
                      "111221 = три единицы, две двойки, одна единица.")
    save(11, task, sol)
    return rows[5]


# =============================================================================
# Задача 13. Матрица: распределение трёх
# =============================================================================
def task13():
    kinds = ["circle", "square", "triangle"]
    grid = [(RED, ["circle", "square", "triangle"]), (BLUE, ["square", "triangle", "circle"]),
            (GREEN, ["triangle", "circle", None])]
    missing = (set(kinds) - set(grid[2][1][:2])).pop()
    target = (3, GREEN, missing)
    opts = [(3, GREEN, "square"), (3, GREEN, "circle"), (2, GREEN, "square"),
            (3, RED, "square"), (3, GREEN, "triangle"), (3, BLUE, "square")]
    ans = "ABCDEF"[opts.index(target)]
    assert ans == "A"

    card = Card(13, "Какая фигура должна стоять на месте «?»?")
    c = 96
    x0, y0 = (W - 3 * c) / 2, card.body_top + 6
    t_els, s_els = [], []
    for r, (color, row) in enumerate(grid):
        for k, kind in enumerate(row):
            x, y = x0 + k * c, y0 + r * c
            cell = rect(x, y, c, c, WHITE, 0, LINE, 2)
            if kind is None:
                t_els += [cell, rect(x + 6, y + 6, c - 12, c - 12, HIDDEN, 8), center_label(x + c / 2, y + c / 2, "?", 60)]
                s_els += [cell] + figure_row(missing, 3, GREEN, x + c / 2, y + c / 2, 26) + \
                         [green_frame(x + 4, y + 4, c - 8, c - 8, 0)]
                continue
            els = [cell] + figure_row(kind, k + 1, color, x + c / 2, y + c / 2, 26)
            t_els += els
            s_els += els
    card.add_options([lambda x, y, s, o=o: figure_row(o[2], o[0], o[1], x, y, 26) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A. Цвет постоянен в строке, количество растёт 1-2-3, "
                      "каждая из трёх фигур встречается в строке ровно один раз.", ans)
    save(13, task, sol)
    return ans


# =============================================================================
# Задача 14. XOR линий
# =============================================================================
def xor_lines(cx, cy, inner, which, sw):
    a, b = cx - inner / 2, cx + inner / 2
    t, u = cy - inner / 2, cy + inner / 2
    seg = {"top": (a, t, b, t), "bottom": (a, u, b, u), "left": (a, t, a, u), "right": (b, t, b, u),
           "bs": (a, t, b, u), "sl": (a, u, b, t)}
    guide = rect(a, t, inner, inner, "none", 0, "#E5E7EA", 1.5)
    return [guide] + [line(*seg[k], LINE, sw) for k in sorted(which)]


def task14():
    grid = [[{"top", "left"}, {"left", "bs"}, {"top", "bs"}],
            [{"right", "bottom"}, {"bottom", "sl"}, {"right", "sl"}],
            [{"top", "sl"}, {"top", "right", "bs"}, None]]
    for row in grid[:2]:
        assert row[2] == row[0] ^ row[1]
    target = grid[2][0] ^ grid[2][1]
    opts = [{"sl", "right", "bs"}, {"top", "sl", "right", "bs"}, {"top"},
            {"sl", "right"}, {"right", "bs"}, {"sl", "bs", "bottom"}]
    ans = "ABCDEF"[opts.index(target)]
    assert ans == "A"

    card = Card(14, "Найдите недостающую клетку.")
    c = 96
    x0, y0 = (W - 3 * c) / 2, card.body_top + 6
    t_els, s_els = [], []
    for r, row in enumerate(grid):
        for k, which in enumerate(row):
            x, y = x0 + k * c, y0 + r * c
            cell = rect(x, y, c, c, WHITE, 0, LINE, 2)
            if which is None:
                t_els += [cell, rect(x + 6, y + 6, c - 12, c - 12, HIDDEN, 8), center_label(x + c / 2, y + c / 2, "?", 60)]
                s_els += [cell] + xor_lines(x + c / 2, y + c / 2, 70, target, 5) + [green_frame(x + 4, y + 4, c - 8, c - 8, 0)]
                continue
            els = [cell] + xor_lines(x + c / 2, y + c / 2, 70, which, 5)
            t_els += els
            s_els += els
    card.add_options([lambda x, y, s, o=o: xor_lines(x, y, 66, o, 4) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A. В третьей клетке остаются линии, которые есть ровно в одной из первых двух: "
                      "общие исчезают.", ans)
    save(14, task, sol)
    return ans


# =============================================================================
# Задача 15. Фигура в фигуре
# =============================================================================
def task15():
    pairs = [(4, 5), (3, 4), (6, 7), (5, 4), (5, 6)]  # (внешняя, внутренняя)
    odd = [i for i, (o, n) in enumerate(pairs) if n - o != 1]
    assert odd == [3]
    ans = "ABCDE"[odd[0]]
    card = Card(15, "Какая карточка лишняя?")

    def draw(o, n):
        return lambda x, y, s: [polygon(ngon(x, y + 4, s * 0.38, o), "none", BLUE, 4),
                                polygon(ngon(x, y + 4, s * 0.38 * 0.45, n), ORANGE)]

    card.add_options([draw(o, n) for o, n in pairs], size=130, y=card.body_top + 90)
    task = card.render()
    sol = card.render("Ответ: D. У внутренней фигуры обычно на одну сторону больше, чем у внешней, "
                      "а в D — на одну меньше.", ans)
    save(15, task, sol)
    return ans


# =============================================================================
# Задача 16. Точка и треугольник
# =============================================================================
CORNERS = ["TL", "TR", "BR", "BL"]  # по часовой
SIDES = ["top", "left", "bottom", "right"]  # против часовой


def dot_tri(cx, cy, s, corner, color, side):
    k = s / 120
    ins, r, ts = 20 * k + 12 * k, 12 * k, 18 * k
    dx = -1 if corner in ("TL", "BL") else 1
    dy = -1 if corner in ("TL", "TR") else 1
    els = [f'<circle cx="{f(cx + dx * (s / 2 - ins))}" cy="{f(cy + dy * (s / 2 - ins))}" r="{f(r)}" fill="{color}"/>']
    h = ts * math.sqrt(3) / 2
    e = s / 2 - 2 * k
    base = {"top": [(cx - ts / 2, cy - e), (cx + ts / 2, cy - e), (cx, cy - e + h)],
            "bottom": [(cx - ts / 2, cy + e), (cx + ts / 2, cy + e), (cx, cy + e - h)],
            "left": [(cx - e, cy - ts / 2), (cx - e, cy + ts / 2), (cx - e + h, cy)],
            "right": [(cx + e, cy - ts / 2), (cx + e, cy + ts / 2), (cx + e - h, cy)]}
    return els + [polygon(base[side], LINE)]


def task16():
    states = [(CORNERS[i % 4], [RED, BLUE][i % 2], SIDES[i % 4]) for i in range(5)]
    assert states[:4] == [("TL", RED, "top"), ("TR", BLUE, "left"), ("BR", RED, "bottom"), ("BL", BLUE, "right")]
    opts = [("TL", RED, "top"), ("TL", BLUE, "top"), ("TR", RED, "top"),
            ("TL", RED, "left"), ("BL", RED, "top"), ("TL", RED, "right")]
    ans = "ABCDEF"[opts.index(states[4])]
    assert ans == "A"

    card = Card(16, "Какой квадрат следующий?")
    s, gap = 120, 20
    x0, y0 = (W - (5 * s + 4 * gap)) / 2, card.body_top + 50
    t_els, s_els = [], []
    for i, (corner, color, side) in enumerate(states):
        x = x0 + i * (s + gap)
        cx, cy = x + s / 2, y0 + s / 2
        sq = rect(x, y0, s, s, WHITE, 0, LINE, 3)
        if i == 4:
            t_els += qmark("square", cx, cy, s)
            s_els += [sq] + dot_tri(cx, cy, s, corner, color, side) + [green_frame(x, y0, s, s, 6)]
            continue
        els = [sq] + dot_tri(cx, cy, s, corner, color, side)
        t_els += els
        s_els += els
    card.add_options([lambda x, y, sz, o=o: [rect(x - 40, y - 40, 80, 80, WHITE, 0, LINE, 2)] +
                      dot_tri(x, y, 80, o[0], o[1], o[2]) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A. Точка обходит углы по часовой стрелке, треугольник — стороны против часовой, "
                      "цвет точки чередуется.", ans)
    save(16, task, sol)
    return ans


# =============================================================================
# Задача 17. Змейка цветов
# =============================================================================
def task17():
    cmap = {"К": RED, "Ж": YELLOW, "С": BLUE}
    grid = ["КЖСК", "ЖКСЖ", "СКЖС", "К?ЖК"]
    path = [(r, c if r % 2 == 0 else 3 - c) for r in range(4) for c in range(4)]
    cycle = "КЖС"
    for k, (r, c) in enumerate(path):
        if grid[r][c] != "?":
            assert grid[r][c] == cycle[k % 3], (r, c)
    qk = next(k for k, (r, c) in enumerate(path) if grid[r][c] == "?")
    target = cmap[cycle[qk % 3]]
    assert qk + 1 == 15 and target == BLUE
    opts = [RED, YELLOW, BLUE, GREEN]
    ans = "ABCD"[opts.index(target)]

    card = Card(17, "Какого цвета клетка «?»?")
    c, gap = 68, 6
    x0, y0 = (W - (4 * c + 3 * gap)) / 2, card.body_top + 6
    pos = lambda r, k: (x0 + k * (c + gap), y0 + r * (c + gap))
    t_els, s_els = [], []
    for r in range(4):
        for k in range(4):
            x, y = pos(r, k)
            ch = grid[r][k]
            if ch == "?":
                t_els += [rect(x, y, c, c, HIDDEN, 6), center_label(x + c / 2, y + c / 2, "?", 0.6 * c)]
                s_els += [rect(x, y, c, c, target, 6), green_frame(x, y, c, c, 4)]
            else:
                els = [rect(x, y, c, c, cmap[ch], 6)]
                t_els += els
                s_els += els
    pts = []
    for n, (r, k) in enumerate(path, 1):
        x, y = pos(r, k)
        s_els.append(text(x + 8, y + 20, str(n), 15, WHITE, "bold"))
        pts.append((x + c / 2, y + c / 2 + 6))
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    s_els.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-dasharray="7 5" '
                 f'stroke-linejoin="round" marker-end="url(#arr-k)"/>')
    card.add_options([lambda x, y, s, col=col: [shape("circle", x, y, 60, col)] for col in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: C — синий. Цвета идут циклом К → Ж → С по «змейке»; «?» — 15-я клетка, "
                      "15 mod 3 = 0 → синий.", ans)
    save(17, task, sol)
    return f"{ans} (синий)"


# =============================================================================
# Задача 18. Зеркальные цифры
# =============================================================================
def mirror_pair(cx, cy, d, mode, w, h, t, gap=4):
    x = cx - (2 * w + gap) / 2
    y = cy - h / 2
    seg, mir = SEG[d], SEG[d].translate(MIRROR)
    left, right = {"mL": (mir, seg), "mR": (seg, mir), "none": (seg, seg)}[mode]
    return seven_seg(x, y, w, h, t, left, PURPLE) + seven_seg(x + w + gap, y, w, h, t, right, PURPLE)


def task18():
    seq = [1, 2, 3, 4]
    nxt = (seq[-1] + 1, "mL")
    opts = [(5, "mL"), (5, "mR"), (6, "mL"), (5, "none")]
    ans = "ABCD"[opts.index(nxt)]
    assert ans == "A"
    card = Card(18, "Какой символ следующий?")
    w, h, t, gap = 40, 72, 10, 46
    sw = 2 * w + 4
    x0 = (W - (5 * sw + 4 * gap)) / 2
    cy = card.body_top + 110
    t_els, s_els = [], []
    for i in range(5):
        cx = x0 + i * (sw + gap) + sw / 2
        if i < 4:
            els = mirror_pair(cx, cy, seq[i], "mL", w, h, t)
            t_els += els
            s_els += els
        else:
            t_els += hidden_box(cx, cy, sw, h + 10)
            s_els += mirror_pair(cx, cy, *nxt, w, h, t) + [green_frame(cx - sw / 2, cy - h / 2, sw, h, 8)]
    card.add_options([lambda x, y, s, o=o: mirror_pair(x, y, o[0], o[1], 30, 54, 7, 3) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A. Это цифры 1, 2, 3, 4, к каждой слева пристроено зеркальное отражение; "
                      "дальше идёт 5.", ans)
    save(18, task, sol)
    return ans


# =============================================================================
# Задача 19. Фигуры-числа
# =============================================================================
def task19():
    star = 30 / 3
    circ = (20 - star) / 2
    tri = (13 - circ) / 2
    answer = circ + star * tri
    assert (star, circ, tri, answer) == (10, 5, 4, 45) and (circ + star) * tri == 60
    vals = {"star": star, "circle": circ, "triangle": tri}
    cols = {"star": YELLOW, "circle": BLUE, "triangle": GREEN}
    rows = [["star", "+", "star", "+", "star", "=", "30"],
            ["star", "+", "circle", "+", "circle", "=", "20"],
            ["circle", "+", "triangle", "+", "triangle", "=", "13"],
            ["circle", "+", "star", "×", "triangle", "=", "?"]]
    card = Card(19, "Найдите значение последней строки.")
    t_els, s_els = [], []
    for r, row in enumerate(rows):
        cy = card.body_top + 52 + r * 88
        x = 200
        for item in row:
            if item in vals:
                fig = figure(item, x + 25, cy, 50, cols[item])
                t_els.append(fig)
                s_els += [fig, text(x + 25, cy + 44, str(int(vals[item])), 15, TEXT, "bold", "middle")]
                x += 70
            elif item in "+×=":
                el = center_label(x + 15, cy, item, 36, LINE, "normal")
                t_els.append(el)
                s_els.append(el)
                x += 50
            elif item == "?":
                t_els += hidden_box(x + 36, cy, 72, 50)
                s_els += [center_label(x + 36, cy, str(int(answer)), 36, GREEN), green_frame(x, cy - 25, 72, 50, 0)]
            else:
                el = text(x, cy + 13, item, 36, LINE, "bold")
                t_els.append(el)
                s_els.append(el)
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: 45. ★ = 10, ● = 5, ▲ = 4; умножение выполняется первым: "
                      "5 + 10 × 4 = 45 (а не 60).")
    save(19, task, sol)
    return str(int(answer))


# =============================================================================
# Задача 20. Числа в треугольниках
# =============================================================================
def task20():
    data = [(3, 4, 2, 10), (5, 2, 1, 9), (6, 3, 4, 14), (7, 2, 5, None)]
    rule = lambda a, b, c: a * b - c
    for a, b, c, v in data[:3]:
        assert rule(a, b, c) == v
    answer = rule(*data[3][:3])
    assert answer == 9

    card = Card(20, "Какое число в центре последнего треугольника?")
    side, gap = 160, 26
    hgt = side * math.sqrt(3) / 2
    x0 = (W - (4 * side + 3 * gap)) / 2
    yt = card.body_top + 130
    t_els, s_els = [], []
    for i, (a, b, c, v) in enumerate(data):
        xl = x0 + i * (side + gap)
        vs = [(xl + side / 2, yt), (xl, yt + hgt), (xl + side, yt + hgt)]
        g = (sum(p[0] for p in vs) / 3, sum(p[1] for p in vs) / 3)
        els = [polygon(vs, "none", RED, 4)]
        for (vx, vy), num in zip(vs, (a, b, c)):
            els.append(center_label(g[0] + 0.6 * (vx - g[0]), g[1] + 0.6 * (vy - g[1]), str(num), 22, LINE))
        t_els += els
        s_els += els
        if v is None:
            t_els += hidden_box(g[0], g[1], 44, 38)
            s_els += [center_label(g[0], g[1], str(answer), 30, GREEN), green_frame(g[0] - 22, g[1] - 19, 44, 38, 0)]
        else:
            el = center_label(g[0], g[1], str(v), 30, RED)
            t_els.append(el)
            s_els.append(el)
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: 9. Центр = верх × левый − правый: 3·4−2 = 10, 5·2−1 = 9, 6·3−4 = 14, 7·2−5 = 9.")
    save(20, task, sol)
    return str(answer)


# =============================================================================
# Задача 21. Сколько квадратов
# =============================================================================
def grid_lines(x, y, n, c, sw):
    return [line(x + i * c, y, x + i * c, y + n * c, LINE, sw) for i in range(n + 1)] + \
           [line(x, y + i * c, x + n * c, y + i * c, LINE, sw) for i in range(n + 1)]


def task21():
    by_size = {k: (5 - k) ** 2 for k in range(1, 5)}
    answer = sum(by_size.values())
    opts = [16, 20, 25, 30, 32]
    ans = "ABCDE"[opts.index(answer)]
    assert answer == 30 and ans == "D"

    card = Card(21, "Сколько всего квадратов на рисунке?")
    c = 72
    x0, y0 = (W - 4 * c) / 2, card.body_top + 8
    main = grid_lines(x0, y0, 4, c, 4)
    s_els = list(main)
    hl = [RED, ORANGE, BLUE, PURPLE]
    spots = [(80, 112), (80, 262), (624, 112), (624, 262)]
    for k, (mx, my) in zip(range(1, 5), spots):
        mc = 24
        s_els.append(rect(mx, my, k * mc, k * mc, hl[k - 1], 0, extra=' opacity="0.3"'))
        s_els += grid_lines(mx, my, 4, mc, 2)
        s_els.append(rect(mx, my, k * mc, k * mc, "none", 0, hl[k - 1], 4))
        s_els.append(text(mx + 48, my + 120, f"{k}×{k}: {by_size[k]}", 16, TITLE, "bold", "middle"))
    card.add_options([lambda x, y, s, o=o: [center_label(x, y, str(o), 40, LINE)] for o in opts])
    card.body = main
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: D — 30. Квадратов 1×1 — 16, 2×2 — 9, 3×3 — 4, 4×4 — 1: 16 + 9 + 4 + 1 = 30.", ans)
    save(21, task, sol)
    return f"{ans} (30)"


# =============================================================================
# Задача 22. Симметричные буквы
# =============================================================================
def task22():
    sym = "AHIMOTUVWXY"  # латинские заглавные с вертикальной осью симметрии (рубленый шрифт)
    seq, nxt = sym[:6], sym[6]
    assert seq == "AHIMOT"
    opts = ["U", "P", "S", "N"]
    ans = "ABCD"[opts.index(nxt)]
    assert ans == "A"

    card = Card(22, "Какая буква следующая?")
    tw, th, gap = 94, 120, 7
    x0, y0 = (W - (7 * tw + 6 * gap)) / 2, card.body_top + 70
    t_els, s_els = [], []
    for i in range(7):
        x = x0 + i * (tw + gap)
        cx, cy = x + tw / 2, y0 + th / 2
        axis = line(cx, y0 + 8, cx, y0 + th - 8, RED, 2.5, ' stroke-dasharray="6 5"')
        if i == 6:
            t_els += [rect(x, y0, tw, th, HIDDEN, 10), center_label(cx, cy, "?", 72)]
            s_els += [rect(x, y0, tw, th, WHITE, 10, HIDDEN, 2), center_label(cx, cy, nxt, 80, LINE), axis,
                      green_frame(x, y0, tw, th, 5)]
            continue
        els = [rect(x, y0, tw, th, WHITE, 10, HIDDEN, 2), center_label(cx, cy, seq[i], 80, LINE)]
        t_els += els
        s_els += els + [axis]
    card.add_options([lambda x, y, s, o=o: [center_label(x, y, o, 64, LINE)] for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: U. Это латинские заглавные буквы с вертикальной осью симметрии по алфавиту: "
                      "A, H, I, M, O, T, U…", ans)
    save(22, task, sol)
    return ans


# =============================================================================
# Задача 23. КОТ = 48
# =============================================================================
ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def task23():
    assert len(ALPHABET) == 33
    num = lambda w: sum(ALPHABET.index(ch) + 1 for ch in w)
    data = [("КОТ", 48), ("ДОМ", 35), ("СОК", 47), ("МИР", None)]
    for w_, v in data[:3]:
        assert num(w_) == v, w_
    answer = num("МИР")
    assert answer == 42

    card = Card(23, "Чему равен МИР?")
    tw, th = 300, 100
    spots = [(70, 150), (430, 150), (70, 320), (430, 320)]
    t_els, s_els = [], []
    for (x, y), (word, v) in zip(spots, data):
        tag = [f'<path d="M{x + 28} {y + th / 2} C{x + 6} {y + 20} {x + 14} {y - 24} {x + 52} {y - 30}" '
               f'fill="none" stroke="#8B6B3D" stroke-width="2"/>',
               f'<path d="M{x + 36} {y} H{x + tw - 10} Q{x + tw} {y} {x + tw} {y + 10} V{y + th - 10} '
               f'Q{x + tw} {y + th} {x + tw - 10} {y + th} H{x + 36} L{x} {y + th / 2} Z" '
               f'fill="#FFE08A" stroke="#D9B44A" stroke-width="2"/>',
               f'<circle cx="{x + 28}" cy="{y + th / 2}" r="7" fill="{WHITE}" stroke="#C9A23C" stroke-width="2"/>']
        t_els += tag
        s_els += tag
        cx = x + 60
        base = y + 72
        for ch in word:
            wch = text_width(ch, 40, True)
            el = text(cx, base, ch, 40, LINE, "bold")
            t_els.append(el)
            s_els += [el, text(cx + wch / 2, y + 26, str(ALPHABET.index(ch) + 1), 15, GREEN, "bold", "middle")]
            cx += wch
        cx += 14
        eq = text(cx, base, "=", 40, LINE, "bold")
        cx += text_width("=", 40, True) + 14
        t_els.append(eq)
        s_els.append(eq)
        if v is None:
            t_els += hidden_box(cx + 32, y + th / 2 + 8, 64, 48, size=30)
            s_els += hidden_box(cx + 32, y + th / 2 + 8, 64, 48, str(answer), GREEN, 30)
        else:
            el = text(cx, base, str(v), 40, LINE, "bold")
            t_els.append(el)
            s_els.append(el)
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: 42. Складываются номера букв в алфавите (с Ё): М14 + И10 + Р18 = 42; "
                      "КОТ = 12 + 16 + 20 = 48.")
    save(23, task, sol)
    return str(answer)


# =============================================================================
# Задача 24. Лишнее слово
# =============================================================================
def task24():
    words = ["ШАЛАШ", "КАЗАК", "ДОХОД", "РАДАР", "ЛИМОН", "КОМОК"]
    odd = [w_ for w_ in words if w_ != w_[::-1]]
    assert odd == ["ЛИМОН"]
    card = Card(24, "Какое слово лишнее?")
    t, gap = 50, 6
    ww = 5 * t + 4 * gap
    xs = [(W - (2 * ww + 90)) / 2, (W - (2 * ww + 90)) / 2 + ww + 90]
    t_els, s_els = [], []
    for i, word in enumerate(words):
        x, y = xs[i % 2], card.body_top + 66 + (i // 2) * 120
        els = []
        for k, ch in enumerate(word):
            tx = x + k * (t + gap)
            els += [rect(tx, y, t, t, TEAL, 6), center_label(tx + t / 2, y + t / 2, ch, 28)]
        t_els += els
        s_els += els
        if word in odd:
            s_els.append(rect(x - 7, y - 7, ww + 14, t + 14, "none", 8, RED, 5))
        else:
            s_els.append(f'<path d="M{f(x + 20)} {f(y - 8)} Q{f(x + ww / 2)} {f(y - 52)} {f(x + ww - 20)} {f(y - 8)}" '
                         f'fill="none" stroke="{LINE}" stroke-width="2" marker-start="url(#arr-k)" marker-end="url(#arr-k)"/>')
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: ЛИМОН. Все остальные слова — палиндромы: читаются одинаково в обе стороны.")
    save(24, task, sol)
    return odd[0]


# =============================================================================
# index.html
# =============================================================================
INDEX_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
<meta name="description" content="Визуальные головоломки на поиск закономерности с ответами и объяснениями.">
<title>Головоломки на закономерность</title>
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head>
<body>
<header class="top">
  <h1>Головоломки на закономерность</h1>
  <p>{count} задач. Нажмите на карточку, чтобы открыть её крупно, подумайте — и только потом смотрите ответ.</p>
</header>
<main class="grid">
{cards}
</main>
<dialog class="viewer" id="viewer" aria-labelledby="v-title">
  <div class="viewer-inner">
    <div class="viewer-bar">
      <h2 id="v-title">Задача</h2>
      <button type="button" class="btn btn-icon" id="v-close" aria-label="Закрыть">✕</button>
    </div>
    <div class="viewer-img"><img id="v-img" alt="" width="800" height="600"></div>
    <div class="viewer-controls">
      <button type="button" class="btn btn-icon" id="v-prev" aria-label="Предыдущая задача">←</button>
      <button type="button" class="btn btn-main" id="v-toggle" aria-expanded="false">Показать ответ</button>
      <button type="button" class="btn btn-icon" id="v-next" aria-label="Следующая задача">→</button>
    </div>
    <p class="answer" id="v-answer" aria-live="polite" hidden></p>
  </div>
</dialog>
<footer class="foot">Стрелки ← → листают задачи, Esc закрывает окно.</footer>
</body>
</html>
"""


def build_index(answers):
    from html import escape as h
    cards = []
    for n in sorted(answers):
        expl = CARDS[n].solution_text
        rest = expl.split(". ", 1)[1] if ". " in expl else ""
        cards.append(
            f'  <a class="card" href="img/{n:02d}_task.svg" data-n="{n}" data-answer="{h(answers[n])}" '
            f'data-expl="{h(rest)}">\n'
            f'    <img src="img/{n:02d}_task.svg" alt="Задача {n}" width="800" height="600" loading="lazy">\n'
            f'    <span class="card-title">Задача {n}</span>\n  </a>')
    (OUT / "index.html").write_text(
        INDEX_TEMPLATE.replace("{count}", str(len(cards))).replace("{cards}", "\n".join(cards)),
        encoding="utf-8")


TASKS = {n: globals()[f"task{n:02d}"] for n in range(1, 25)}

if __name__ == "__main__":
    nums = [int(a) for a in sys.argv[1:]] or sorted(TASKS)
    answers = {}
    for n in nums:
        answers[n] = TASKS[n]()
    if len(answers) == len(TASKS):
        build_index(answers)
    print("\nКонтрольный список:")
    for n, a in answers.items():
        print(f"  {n:2d} → {a}")
