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
    for name, c in (("k", LINE), ("g", GREEN), ("h", "#9AA0A6"), ("r", RED), ("n", "#39FF6A"), ("b", BLUE))) + "</defs>")


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
# Набор 2: задачи 25–44
# =============================================================================
def cipher_grid(cipher, rows, cell, step, x0, y0, opened=(), q=None, letter_size=None):
    """rows: [(слово, номер_строки, первый_столбец)]. Возвращает (task, solution, позиция «?»)."""
    ls = letter_size or round(cell * 0.5)
    t_els, s_els = [], []
    for word, r, c0 in rows:
        for i, ch in enumerate(word):
            cx = x0 + (c0 + i) * step + cell / 2
            cy = y0 + r * step + cell / 2
            color, kind = cipher[ch]
            full = [shape(kind, cx, cy, cell, color), center_label(cx, cy, ch, ls)]
            if (r, c0 + i) == q:
                t_els += qmark(kind, cx, cy, cell)
                s_els += full + [green_frame(cx - cell / 2, cy - cell / 2, cell, cell, 4)]
                continue
            t_els += full if (r, c0 + i) in opened else full[:1]
            s_els += full
    return t_els, s_els


CIPHER25 = {
    "Д": (RED, "square"),    "О": (BLUE, "circle"),    "Р": (GREEN, "square"),  "Е": (ORANGE, "circle"),
    "М": (PURPLE, "rsquare"), "И": (TEAL, "circle"),   "Ф": (YELLOW, "rsquare"), "А": (PINK, "square"),
    "С": (BLUE, "square"),   "Л": (RED, "rsquare"),    "Ь": (GREEN, "circle"),  "Я": (PURPLE, "square"),
}


def task25():
    words = ["СИ", "ФА", "ДО", "СОЛЬ", "МИ", "ЛЯ", "РЕ"]
    check_cipher(CIPHER25, words)
    assert CIPHER25[words[5][0]] == CIPHER25[words[3][2]]  # «?» совпадает с 3-й ячейкой СОЛЬ
    card = Card(25, "Каждая буква всегда изображается одной и той же парой «цвет + форма». Семь слов из "
                    "одного известного ряда записаны в перемешанном порядке. Какая буква под знаком «?»?")
    t_els, s_els = cipher_grid(CIPHER25, [(w, r, 0) for r, w in enumerate(words)], 52, 58, 300,
                               card.body_top + 4, opened={(1, 0), (3, 3)}, q=(5, 0))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: Л. Это ноты ДО…СИ; красный скруглённый квадрат = Л, как в СОЛЬ.")
    save(25, task, sol)
    return "Л"


CIPHER26 = {
    "М": (RED, "square"),     "Е": (BLUE, "circle"),    "Р": (GREEN, "rsquare"), "К": (ORANGE, "square"),
    "У": (PURPLE, "circle"),  "И": (TEAL, "rsquare"),   "Й": (PINK, "square"),   "В": (YELLOW, "circle"),
    "Н": (RED, "rsquare"),    "А": (BLUE, "square"),    "З": (GREEN, "circle"),  "Л": (ORANGE, "rsquare"),
    "Я": (PURPLE, "square"),  "С": (TEAL, "circle"),    "Ю": (PINK, "rsquare"),  "П": (YELLOW, "square"),
    "Т": (RED, "circle"),
}


def task26():
    planets = ["МЕРКУРИЙ", "ВЕНЕРА", "ЗЕМЛЯ", "МАРС", "ЮПИТЕР", "САТУРН", "УРАН", "НЕПТУН"]
    check_cipher(CIPHER26, planets)
    secret_codes = [(TEAL, "circle"), (BLUE, "circle"), (ORANGE, "square"),
                    (GREEN, "rsquare"), (BLUE, "circle"), (RED, "circle")]
    inverse = {v: k for k, v in CIPHER26.items()}
    secret = "".join(inverse[c] for c in secret_codes)
    assert secret == "СЕКРЕТ"
    assert [w for w in planets if "К" in w] == ["МЕРКУРИЙ"]

    card = Card(26, "Шифр тот же: пара «цвет + форма» однозначно задаёт букву. Слева восемь слов одного ряда "
                    "в естественном порядке, одна буква открыта. Подсказка выглядывает из-за левого края. "
                    "Расшифруйте слово справа.")
    cell, step = 44, 50
    y0 = card.body_top + 6
    rows = [(w, r, 8 - len(w)) for r, w in enumerate(planets)]
    t_els, s_els = cipher_grid(CIPHER26, rows, cell, step, 60, y0, opened={(2, 3)}, letter_size=22)
    sy = y0 + 4 * step - 3
    sun = [f'<circle cx="0" cy="{f(sy)}" r="40" fill="{YELLOW}"/>']
    for a in (-70, -42, -14, 14, 42, 70):
        ra = math.radians(a)
        sun.append(line(46 * math.cos(ra), sy + 46 * math.sin(ra), 64 * math.cos(ra), sy + 64 * math.sin(ra), YELLOW, 4))
    right = [text(490, y0 + 100, "Расшифруйте:", 18, TEXT)]
    r_sol = list(right)
    for i, (color, kind) in enumerate(secret_codes):
        cx, cy = 490 + i * 50 + cell / 2, y0 + 120 + cell / 2
        right.append(shape(kind, cx, cy, cell, color))
        r_sol += [shape(kind, cx, cy, cell, color), center_label(cx, cy, secret[i], 22),
                  text(cx, cy + cell / 2 + 30, secret[i], 22, GREEN, "bold", "middle")]
    card.body = sun + t_els + right
    task = card.render()
    card.body = sun + s_els + r_sol
    sol = card.render("Ответ: СЕКРЕТ. Восемь планет по порядку от Солнца; справа С-Е-К-Р-Е-Т.")
    save(26, task, sol)
    return secret


# --- 27. Морзе --------------------------------------------------------------------
MORSE = {"Е": ".", "Т": "-", "И": "..", "А": ".-", "Н": "-.", "М": "--", "С": "...", "О": "---",
         "Ш": "----", "Р": ".-.", "Х": "....", "У": "..-"}


def morse_marks(code, cx, cy, unit=7, color=LINE):
    widths = [unit * (1 if ch == "." else 3) for ch in code]
    total = sum(widths) + unit * 1.2 * (len(code) - 1)
    x, els = cx - total / 2, []
    for ch, w in zip(code, widths):
        if ch == ".":
            els.append(f'<circle cx="{f(x + w / 2)}" cy="{f(cy)}" r="{f(unit / 2)}" fill="{color}"/>')
        else:
            els.append(rect(x, cy - unit / 2, w, unit, color, unit / 2))
        x += w + unit * 1.2
    return els


def task27():
    seq = ["Е", "Т", "И", "А", "Н", "М"]
    # порядок: по длине, внутри длины — как двоичные числа (· = 0, – = 1)
    order = [''.join(".-"[int(b)] for b in format(k, f"0{n}b")) for n in (1, 2, 3) for k in range(2 ** n)]
    assert [MORSE[ch] for ch in seq] == order[:6]
    nxt = order[6]
    opts = ["С", "О", "Ш", "Р", "Х", "У"]
    ans = "ABCDEF"[[MORSE[o] for o in opts].index(nxt)]
    assert ans == "A" and [MORSE[o] for o in opts].count(nxt) == 1

    card = Card(27, "Карточки идут в строгом порядке. Какая карточка следующая?")
    t_els, s_els = [], []
    for i in range(7):
        x, y = 40 + i * 105, card.body_top + 40
        if i == 6:
            t_els += [rect(x, y, 90, 120, HIDDEN, 10), center_label(x + 45, y + 60, "?", 54)]
            s_els += [rect(x, y, 90, 120, WHITE, 10, LINE, 2), center_label(x + 45, y + 40, "С", 40, LINE),
                      *morse_marks(nxt, x + 45, y + 90), green_frame(x, y, 90, 120, 4)]
            continue
        els = [rect(x, y, 90, 120, WHITE, 10, LINE, 2), center_label(x + 45, y + 40, seq[i], 40, LINE),
               *morse_marks(MORSE[seq[i]], x + 45, y + 90)]
        t_els += els
        s_els += els
    card.add_options([lambda x, y, s, o=o: [center_label(x, y - 16, o, 32, LINE), *morse_marks(MORSE[o], x, y + 26, 6)]
                      for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A — С (···). Коды идут по длине, а внутри длины — как двоичные числа "
                      "(· = 0, – = 1): 0, 1, 00, 01, 10, 11, 000.", ans)
    save(27, task, sol)
    return "A (С ···)"


# --- 28. T9 -------------------------------------------------------------------------
T9 = {c: str(d) for d, letters in {2: "ABC", 3: "DEF", 4: "GHI", 5: "JKL", 6: "MNO",
                                    7: "PQRS", 8: "TUV", 9: "WXYZ"}.items() for c in letters}
t9 = lambda w: "".join(T9[c] for c in w)
MONO = "Menlo, Consolas, 'Courier New', monospace"


def task28():
    pairs = [("KISS", "LIPS"), ("BOOK", "COOL"), ("HOME", "GOOD")]
    for a, b in pairs:
        assert t9(a) == t9(b), (a, b)
    opts = ["CAR", "ART", "BAT", "ACE", "TAB", "BUT"]
    matches = [o for o in opts if t9(o) == t9("ACT")]
    assert matches == ["BAT"]
    ans = "ABCDEF"[opts.index("BAT")]

    card = Card(28, "Все равенства верны. Какое слово подходит вместо «?»?")
    cw = 18.06  # ширина символа моноширинного шрифта 30px
    t_els, s_els = [], []
    rows = pairs + [("ACT", None)]
    for k, (a, b) in enumerate(rows):
        y = card.body_top + 62 + k * 62
        left = f"{a} = " + (b or "")
        mono = lambda s, x, size=30, fill=LINE, weight="normal": (
            f'<text x="{f(x)}" y="{f(y)}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" xml:space="preserve">{escape(s)}</text>')
        el = mono(left, 200)
        t_els.append(el)
        s_els.append(el)
        codes = [(a, 200)] + ([(b, 200 + cw * (len(a) + 3))] if b else [])
        for word, x in codes:
            s_els.append(text(x + cw * len(word) / 2, y + 20, t9(word), 14, GREEN, "bold", "middle"))
        if b is None:
            qx = 200 + cw * (len(a) + 3)
            t_els += [rect(qx, y - 30, 40, 40, HIDDEN, 6), center_label(qx + 20, y - 10, "?", 26)]
            s_els += [mono("BAT", qx, 30, GREEN, "bold"),
                      text(qx + cw * 1.5, y + 20, t9("BAT"), 14, GREEN, "bold", "middle")]
    phone = [rect(690, card.body_top + 6, 60, 110, WHITE, 10, LINE, 2)]
    for r in range(4):
        for c in range(3):
            phone.append(f'<circle cx="{705 + c * 15}" cy="{f(card.body_top + 34 + r * 20)}" r="5" fill="{LINE}"/>')
    t_els += phone
    s_els += phone
    card.add_options([lambda x, y, s, o=o: [center_label(x, y, o, 22, LINE)] for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: C — BAT. На кнопочном телефоне обе части набираются одними и теми же клавишами: "
                      "ACT = BAT = 228.", ans)
    save(28, task, sol)
    return "C (BAT)"


# --- 29. Буквы госномеров ------------------------------------------------------------
def task29():
    plate = "АВЕКМНОРСТУХ"  # кириллица, совпадающая по начертанию с латиницей
    assert list(plate) == sorted(plate, key=ALPHABET.index)
    shown = plate[:10] + "?" + plate[11]
    opts = ["У", "Ф", "Ц", "Ш", "Я", "Ю"]
    ans = "ABCDEF"[opts.index(plate[10])]
    assert ans == "A"

    card = Card(29, "Какая буква пропущена?")
    px, py = 40, card.body_top + 70
    base = [rect(px, py, 720, 90, WHITE, 12, LINE, 4)]
    fx, fy = px + 680, py + 30
    base += [rect(fx, fy, 30, 6, WHITE, 0, LINE, 1), rect(fx, fy + 6, 30, 6, BLUE), rect(fx, fy + 12, 30, 6, RED)]
    t_els, s_els = list(base), list(base)
    for i, ch in enumerate(shown):
        cx = 52 + i * 54 + 27
        if ch == "?":
            t_els += [rect(cx - 24, py + 14, 48, 62, HIDDEN, 6), center_label(cx, py + 45, "?", 40)]
            s_els += [center_label(cx, py + 45, plate[10], 44, GREEN), green_frame(cx - 24, py + 14, 48, 62, 0)]
            continue
        el = center_label(cx, py + 45, ch, 44, LINE)
        t_els.append(el)
        s_els.append(el)
    card.add_options([lambda x, y, s, o=o: [center_label(x, y, o, 44, LINE)] for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A — У. Только эти 12 кириллических букв совпадают по начертанию с латинскими "
                      "и разрешены на российских номерах.", ans)
    save(29, task, sol)
    return "A (У)"


# --- 30. Стихи про π ---------------------------------------------------------------
ITALIC = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"


def italic_width(s, size):
    return ImageFont.truetype(ITALIC, size).getlength(s)


def task30():
    l1 = "Это я знаю и помню прекрасно,"
    l2 = "Пи многие знаки мне лишни,"
    opts = ["ненужны", "напрасны", "смешны", "бесполезны", "вредны", "излишни"]
    letters = lambda w: sum(ch.isalpha() for ch in w)
    digits = [letters(w) for w in (l1 + " " + l2).split()]
    pi = "314159265358"
    assert digits == [int(d) for d in pi[:11]]
    fit = [o for o in opts if len(o) == int(pi[11])]
    assert fit == ["напрасны"]
    ans = "ABCDEF"[opts.index(fit[0])]

    card = Card(30, "Закончите двустишие. Подходит только одно слово.")
    y1, y2 = card.body_top + 82, card.body_top + 142
    it = lambda s, x, y, fill=LINE, weight="normal": (
        f'<text x="{f(x)}" y="{f(y)}" font-family="{FONT}" font-size="30" font-style="italic" '
        f'font-weight="{weight}" fill="{fill}" xml:space="preserve">{escape(s)}</text>')
    base = [it(l1, 60, y1), it(l2, 60, y2),
            f'<circle cx="730" cy="{f(card.body_top + 30)}" r="22" fill="{BLUE}"/>',
            center_label(730, card.body_top + 30, "π", 26)]
    bx = 60 + italic_width(l2 + " ", 30)
    t_els = base + [rect(bx, y2 - 27, 160, 36, HIDDEN, 6), center_label(bx + 80, y2 - 9, "?", 24)]
    s_els = base + [it(fit[0], bx, y2, GREEN, "bold"), green_frame(bx - 4, y2 - 29, 168, 40, 0)]
    for y, ln in ((y1, l1), (y2, l2 + " " + fit[0])):
        x = 60
        for w in ln.split(" "):
            ww = italic_width(w, 30)
            s_els.append(text(x + ww / 2, y + 24, str(letters(w)), 16, GREEN, "bold", "middle"))
            x += ww + italic_width(" ", 30)

    def opt(o):
        size = min(20, 96 / text_width(o, 20) * 20)
        return lambda x, y, s: [center_label(x, y, o, round(size, 1), LINE, "normal")]

    card.add_options([opt(o) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: B — «напрасны». Длины слов — цифры числа π = 3,14159265358…", ans)
    save(30, task, sol)
    return "B (напрасны)"


# --- 31. Цифры по алфавиту ----------------------------------------------------------
DIGIT_NAMES = {0: "ноль", 1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять",
               6: "шесть", 7: "семь", 8: "восемь", 9: "девять", 10: "десять"}


def task31():
    row = [8, 2, 9, 0, 1, 5, 7, 3, 4, 6]
    assert row == sorted(range(10), key=lambda d: DIGIT_NAMES[d])
    pos = sorted(range(11), key=lambda d: DIGIT_NAMES[d]).index(10)  # куда встаёт «десять»
    gaps = {"A": 0, "B": 2, "C": 3, "D": 4, "E": 5, "F": 10}  # индекс вставки
    ans = next(k for k, v in gaps.items() if v == pos)
    assert ans == "C"

    card = Card(31, "Цифры выстроены по одному правилу. Где в этом ряду должно встать число 10?")
    cy = card.body_top + 160
    base = []
    for i, d in enumerate(row):
        cx = 85 + i * 70
        base += [f'<circle cx="{cx}" cy="{f(cy)}" r="28" fill="{WHITE}" stroke="{LINE}" stroke-width="3"/>',
                 center_label(cx, cy, str(d), 30, LINE)]
    t_els, s_els = list(base), list(base)
    for k, gi in gaps.items():
        mx = 85 + gi * 70 - 35
        if k == ans:
            t_els += [polygon([(mx, cy + 44), (mx - 9, cy + 58), (mx + 9, cy + 58)], BLUE),
                      text(mx, cy + 80, k, 18, BLUE, "bold", "middle")]
            s_els += [polygon([(mx, cy + 40), (mx - 14, cy + 62), (mx + 14, cy + 62)], GREEN),
                      text(mx, cy + 88, k, 24, GREEN, "bold", "middle")]
        else:
            els = [polygon([(mx, cy + 44), (mx - 9, cy + 58), (mx + 9, cy + 58)], BLUE),
                   text(mx, cy + 80, k, 18, BLUE, "bold", "middle")]
            t_els += els
            s_els += els
    gx = 85 + gaps[ans] * 70 - 35
    s_els += [f'<circle cx="{gx}" cy="{f(cy - 78)}" r="24" fill="{GREEN}"/>', center_label(gx, cy - 78, "10", 22),
              f'<path d="M{gx} {f(cy - 52)} L{gx} {f(cy - 30)}" stroke="{GREEN}" stroke-width="3" marker-end="url(#arr-g)"/>']
    for i, d in enumerate(row):
        s_els.append(text(85 + i * 70, cy + 116, DIGIT_NAMES[d], 13, TEXT, "normal", "middle"))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: C — между 9 и 0. Цифры стоят по алфавиту названий; «десять» — после «девять» "
                      "(в < с) и перед «ноль».")
    save(31, task, sol)
    return "C (между 9 и 0)"


# --- 32. Римские цифры -----------------------------------------------------------------
def roman(n):
    out = ""
    for v, s in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s
            n -= v
    return out


def task32():
    lens = [len(roman(n)) for n in range(1, 11)]
    shown = [1, 2, 3, 2, 1, 2, 3, 4, 2]
    assert lens[:9] == shown
    opts = [1, 2, 3, 4, 5, 0]
    ans = "ABCDEF"[opts.index(lens[9])]
    assert ans == "A"
    card = Card(32, "Какое число следующее?")
    y = card.body_top + 90
    t_els, s_els = [], []
    for i in range(10):
        x = 40 + i * 72
        if i == 9:
            t_els += [rect(x, y, 60, 60, HIDDEN, 8), center_label(x + 30, y + 30, "?", 36)]
            s_els += [rect(x, y, 60, 60, WHITE, 8, LINE, 2), center_label(x + 30, y + 30, str(lens[9]), 30, GREEN),
                      green_frame(x, y, 60, 60, 4)]
        else:
            els = [rect(x, y, 60, 60, WHITE, 8, LINE, 2), center_label(x + 30, y + 30, str(shown[i]), 30, LINE)]
            t_els += els
            s_els += els
        s_els.append(text(x + 30, y - 14, roman(i + 1), 18, GREEN, "bold", "middle"))
    card.add_options([lambda x, y_, s, o=o: [center_label(x, y_, str(o), 40, LINE)] for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A — 1. Это число символов в римской записи чисел 1–10: I, II, III, IV, V … IX, X.", ans)
    save(32, task, sol)
    return "A (1)"


# --- 33. Код Грея ------------------------------------------------------------------------
def lamps(cx, top, bits, r, step, dashed=False):
    els = []
    for k, b in enumerate(bits):
        cy = top + k * step
        if dashed:
            els.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="none" stroke="{LINE}" stroke-width="2" '
                       f'stroke-dasharray="4 4"/>')
        else:
            els.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="{YELLOW if b == "1" else HIDDEN}"'
                       + (f' stroke="{LINE}" stroke-width="2"' if b == "1" else "") + "/>")
    return els


def task33():
    states = [format(i ^ (i >> 1), "04b") for i in range(8)]
    assert states[:7] == ["0000", "0001", "0011", "0010", "0110", "0111", "0101"]
    for a, b in zip(states, states[1:]):
        assert sum(x != y for x, y in zip(a, b)) == 1
    opts = ["0100", "1101", "0110", "1100", "0000", "1111"]
    ans = "ABCDEF"[opts.index(states[7])]
    assert ans == "A"

    card = Card(33, "В каждом столбце горят лампы. Какой столбец следующий?")
    top = card.body_top + 60
    t_els, s_els = [], []
    for i, st in enumerate(states):
        cx = 70 + i * 90
        if i == 7:
            t_els += lamps(cx, top, st, 16, 45, dashed=True) + [text(cx, top + 4 * 45 + 8, "?", 30, LINE, "bold", "middle")]
            s_els += lamps(cx, top, st, 16, 45) + [green_frame(cx - 24, top - 24, 48, 3 * 45 + 48, 2)]
        else:
            els = lamps(cx, top, st, 16, 45)
            t_els += els
            s_els += els
        if i:
            prev = states[i - 1]
            k = next(j for j in range(4) if prev[j] != st[j])
            y = top + k * 45
            s_els.append(f'<path d="M{cx - 70} {f(y)} L{cx - 22} {f(y)}" stroke="{GREEN}" stroke-width="3" '
                         f'marker-end="url(#arr-g)"/>')
            s_els.append(text(cx - 45, top - 30, str(3 - k), 15, GREEN, "bold", "middle"))
    card.add_options([lambda x, y, s, o=o: lamps(x, y - 36, o, 10, 24) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A — 0100. За шаг меняется ровно одна лампа, номер разряда идёт по «линейке» "
                      "0, 1, 0, 2, 0, 1, 0 — это код Грея.", ans)
    save(33, task, sol)
    return "A (0100)"


# --- 34. Инертные газы ----------------------------------------------------------------------
def task34():
    nums = [2, 10, 18, 36, 54, 86]
    diffs = [b - a for a, b in zip(nums, nums[1:])]
    assert diffs == [2 * n * n for n in (2, 2, 3, 3, 4)]
    nxt = nums[-1] + 2 * 4 * 4
    assert nxt == 118 and nums[-1] + 32 == 118
    opts = [100, 118, 104, 122, 132, 110]
    ans = "ABCDEF"[opts.index(nxt)]
    gases = ["He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og"]
    cols = [BLUE, RED, GREEN, PURPLE, ORANGE, TEAL, HIDDEN]

    card = Card(34, "Какое число на последнем шаре?")
    cy = card.body_top + 110
    t_els, s_els = [], []
    for i in range(7):
        cx = 70 + i * 110
        string = (f'<path d="M{cx} {f(cy + 43)} q-10 20 0 30 t0 30" fill="none" stroke="{LINE}" stroke-width="1.5"/>')
        ball = lambda col: f'<ellipse cx="{cx}" cy="{f(cy)}" rx="35" ry="43" fill="{col}"/>'
        if i == 6:
            t_els += [string, ball(HIDDEN), center_label(cx, cy, "?", 32)]
            s_els += [string, ball(GREEN), center_label(cx, cy, str(nxt), 28)]
        else:
            els = [string, ball(cols[i]), center_label(cx, cy, str(nums[i]), 28)]
            t_els += els
            s_els += els
        s_els.append(text(cx, cy + 128, gases[i], 16, TEXT, "bold", "middle"))
        if i:
            d = (diffs + [32])[i - 1]
            s_els.append(text(cx - 55, cy - 54, str(d), 16, GREEN, "bold", "middle"))
    card.add_options([lambda x, y, s, o=o: [center_label(x, y, str(o), 36, LINE)] for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: B — 118. Разности 8, 8, 18, 18, 32, 32 (2·2², 2·3², 2·4²): это атомные номера "
                      "инертных газов.", ans)
    save(34, task, sol)
    return "B (118)"


# --- 35. Ходы коня ----------------------------------------------------------------------------
def knight_dist(start):
    from collections import deque
    dist = {start: 0}
    dq = deque([start])
    while dq:
        f0, n0 = dq.popleft()
        for df, dn in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)):
            p = (f0 + df, n0 + dn)
            if 0 <= p[0] < 8 and 1 <= p[1] <= 8 and p not in dist:
                dist[p] = dist[(f0, n0)] + 1
                dq.append(p)
    return dist


def task35():
    sq = lambda s: ("abcdefgh".index(s[0]), int(s[1]))
    dist = knight_dist(sq("a1"))
    shown = {"b3": 1, "c2": 1, "d4": 2, "h8": 6}
    for s, v in shown.items():
        assert dist[sq(s)] == v
    answer = dist[sq("b2")]
    path = ["a1", "b3", "c5", "d3", "b2"]
    for a, b in zip(path, path[1:]):
        (fa, na), (fb, nb) = sq(a), sq(b)
        assert sorted((abs(fa - fb), abs(na - nb))) == [1, 2]
    opts = [1, 2, 3, 4, 5, 6]
    ans = "ABCDEF"[opts.index(answer)]
    assert answer == 4

    card = Card(35, "Число в клетке — наименьшее число ходов коня от a1 до этой клетки. Какое число вместо «?»?")
    X0, Y0, C = 60, 530, 48
    cxy = lambda s: (X0 + sq(s)[0] * C + C / 2, Y0 - sq(s)[1] * C + C / 2)
    base = []
    for fi in range(8):
        for n in range(1, 9):
            base.append(rect(X0 + fi * C, Y0 - n * C, C, C, HIDDEN if (fi + n) % 2 == 1 else WHITE))
    base.append(rect(X0, Y0 - 8 * C, 8 * C, 8 * C, "none", 0, LINE, 2))
    for fi in range(8):
        base.append(text(X0 + fi * C + C / 2, Y0 + 18, "abcdefgh"[fi], 14, TEXT, "normal", "middle"))
    for n in range(1, 9):
        base.append(text(X0 - 12, Y0 - n * C + C / 2 + 5, str(n), 14, TEXT, "normal", "middle"))
    x, y = cxy("a1")
    base.append(text(x, y + 14, "♞", 40, LINE, "normal", "middle"))
    for s, v in shown.items():
        base.append(center_label(*cxy(s), str(v), 26, BLUE))
    t_els, s_els = list(base), list(base)
    bx, by = cxy("b2")
    t_els += [f'<circle cx="{f(bx)}" cy="{f(by)}" r="18" fill="{RED}"/>', center_label(bx, by, "?", 22)]
    pts = [cxy(s) for s in path]
    s_els.append(f'<polyline points="{" ".join(f"{f(a)},{f(b)}" for a, b in pts)}" fill="none" stroke="{GREEN}" '
                 f'stroke-width="4" stroke-linejoin="round"/>')
    s_els += [f'<circle cx="{f(a)}" cy="{f(b)}" r="5" fill="{GREEN}"/>' for a, b in pts[1:-1]]
    s_els += [f'<circle cx="{f(bx)}" cy="{f(by)}" r="18" fill="{GREEN}"/>', center_label(bx, by, str(answer), 22)]
    for k, o in enumerate(opts):
        ox, oy = 510 + (k % 2) * 130, 130 + (k // 2) * 120
        els = [rect(ox, oy, 110, 110, WHITE, 8, HIDDEN, 2), text(ox + 12, oy + 26, "ABCDEF"[k], 18, TITLE, "bold"),
               center_label(ox + 55, oy + 58, str(o), 40, LINE)]
        t_els += els
        s_els += els
        if "ABCDEF"[k] == ans:
            s_els.append(green_frame(ox, oy, 110, 110, 3))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: D — 4. За 2 хода b2 недостижима, а ход коня всегда меняет цвет клетки — "
                      "значит, ходов чётное число: a1 → b3 → c5 → d3 → b2.")
    save(35, task, sol)
    return "D (4)"


# --- 36. Развёртка кубика -----------------------------------------------------------------------
def cube_views():
    """Все тройки (верх, перед, право) для кубика, сложенного из развёртки-креста."""
    import itertools
    faces = {(0, 0, 1): YELLOW, (0, 1, 0): RED, (0, -1, 0): ORANGE,
             (-1, 0, 0): BLUE, (1, 0, 0): GREEN, (0, 0, -1): PURPLE}
    views = set()
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            m = [[0] * 3 for _ in range(3)]
            for r, c in enumerate(perm):
                m[r][c] = signs[r]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            if det != 1:
                continue
            rot = {tuple(sum(m[r][c] * v[c] for c in range(3)) for r in range(3)): col for v, col in faces.items()}
            views.add((rot[(0, 1, 0)], rot[(0, 0, 1)], rot[(1, 0, 0)]))
    assert len(views) == 24
    return views


def iso_cube(cx, cy, top, front, right):
    return [polygon([(cx, cy - 40), (cx + 35, cy - 20), (cx, cy), (cx - 35, cy - 20)], top, LINE, 2),
            polygon([(cx - 35, cy - 20), (cx, cy), (cx, cy + 40), (cx - 35, cy + 20)], front, LINE, 2),
            polygon([(cx, cy), (cx + 35, cy - 20), (cx + 35, cy + 20), (cx, cy + 40)], right, LINE, 2)]


def task36():
    views = cube_views()
    opts = [(RED, GREEN, YELLOW), (RED, YELLOW, ORANGE), (BLUE, YELLOW, GREEN),
            (RED, PURPLE, BLUE), (YELLOW, RED, GREEN), (ORANGE, YELLOW, GREEN)]
    valid = [i for i, o in enumerate(opts) if o in views]
    assert valid == [3]
    ans = "ABCDEF"[valid[0]]

    card = Card(36, "Какой кубик можно сложить из этой развёртки?")
    dy = 30
    net = [(RED, 330, 100), (BLUE, 260, 170), (YELLOW, 330, 170), (GREEN, 400, 170), (PURPLE, 470, 170), (ORANGE, 330, 240)]
    base = [rect(x, y + dy, 70, 70, c, 0, LINE, 2) for c, x, y in net]
    t_els, s_els = list(base), list(base)
    pairs = {RED: "1", ORANGE: "1", BLUE: "2", GREEN: "2", YELLOW: "3", PURPLE: "3"}
    for c, x, y in net:
        s_els += [f'<circle cx="{x + 35}" cy="{y + dy + 35}" r="15" fill="{WHITE}" stroke="{LINE}" '
                  f'stroke-width="1.5" stroke-dasharray="3 3"/>', center_label(x + 35, y + dy + 35, pairs[c], 18, LINE)]
    s_els.append(text(570, 220, "1, 2, 3 — пары", 15, TEXT))
    s_els.append(text(570, 240, "противоположных граней", 15, TEXT))
    card.add_options([lambda x, y, s, o=o: iso_cube(x, y, *o) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: D. У кубиков B и C рядом стоят противоположные грани, а A, E, F — зеркальные варианты.", ans)
    save(36, task, sol)
    return "D"


# --- 37. Башня из костей -----------------------------------------------------------------------
PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}


def die(x, y, s, n, r):
    o = s * 0.27
    return [rect(x, y, s, s, WHITE, s / 7, LINE, 2)] + [
        f'<circle cx="{f(x + s / 2 + dx * o)}" cy="{f(y + s / 2 + dy * o)}" r="{f(r)}" fill="{LINE}"/>' for dx, dy in PIPS[n]]


def task37():
    top_face, n_dice = 2, 4
    hidden = (7 - top_face) + 7 * (n_dice - 1)
    assert hidden == 26 == 7 * n_dice - top_face
    opts = [24, 25, 26, 28, 21, 30]
    ans = "ABCDEF"[opts.index(hidden)]

    card = Card(37, "Четыре обычные игральные кости стоят столбиком. Какова сумма точек на 7 невидимых "
                    "горизонтальных гранях — всех соприкасающихся и нижней грани нижней кости?")
    s = 60
    y0 = card.body_top + 8
    base = []
    for k, n in enumerate([3, 1, 4, 5]):
        base += die(200, y0 + k * s, s, n, 5)
    for k in range(1, 4):
        base.append(line(198, y0 + k * s, 262, y0 + k * s, RED, 1.5))
    base += [text(500, y0 + 4, "вид сверху", 16, TEXT)] + die(500, y0 + 20, 90, top_face, 7)
    t_els, s_els = list(base), list(base)
    s_els.append(text(280, y0 + s + 5, "низ = 7 − 2 = 5", 15, GREEN, "bold"))
    for k in range(1, 4):
        s_els.append(text(280, y0 + (k + 1) * s + 5 if k < 3 else y0 + 4 * s - 4, "верх + низ = 7", 15, GREEN, "bold"))
    card.add_options([lambda x, y, s_, o=o: [center_label(x, y, str(o), 40, LINE)] for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: C — 26. Противоположные грани кости дают в сумме 7: 5 + 7 + 7 + 7 = 26.", ans)
    save(37, task, sol)
    return "C (26)"


# --- 38. Сложенный лист ------------------------------------------------------------------------
def tri_cell(x, y, c, d, fill=RED):
    """Треугольник в клетке c×c, остриём вправо (R) или влево (L)."""
    a, b = c * 0.27, c * 0.73
    pts = [(x + a, y + a), (x + b, y + c / 2), (x + a, y + b)] if d == "R" else \
          [(x + b, y + a), (x + a, y + c / 2), (x + b, y + b)]
    return polygon(pts, fill)


def task38():
    holes = {(0, 1, "R")}                                             # в сложенном квадрате
    holes |= {(3 - r, c, d) for r, c, d in holes}                     # разворот 2-го сгиба (горизонтальный)
    holes |= {(r, 3 - c, "L" if d == "R" else "R") for r, c, d in holes}  # разворот 1-го сгиба (вертикальный)
    opts = [{(0, 1, "R"), (0, 2, "R"), (3, 1, "R"), (3, 2, "R")},
            {(0, 1, "R"), (0, 2, "L"), (3, 1, "R"), (3, 2, "L")},
            {(0, 1, "L"), (0, 2, "R"), (3, 1, "L"), (3, 2, "R")},
            {(0, 1, "R"), (0, 2, "L"), (1, 1, "R"), (1, 2, "L")},
            {(0, 1, "R"), (0, 2, "L")},
            {(0, 1, "R"), (0, 2, "L"), (3, 1, "L"), (3, 2, "R")}]
    assert [o == holes for o in opts].count(True) == 1
    ans = "ABCDEF"[opts.index(holes)]
    assert ans == "B"

    card = Card(38, "Квадратный лист сложили дважды и пробили треугольным дыроколом. Как выглядит развёрнутый лист?")
    y = card.body_top + 30
    els = [rect(60, y, 120, 120, WHITE, 0, LINE, 2), line(120, y, 120, y + 120, LINE, 2, ' stroke-dasharray="6 5"'),
           f'<path d="M155 {y + 40} Q120 {y - 6} 85 {y + 40}" fill="none" stroke="{BLUE}" stroke-width="3" marker-end="url(#arr-b)"/>',
           rect(280, y, 60, 120, WHITE, 0, LINE, 2), line(280, y + 60, 340, y + 60, LINE, 2, ' stroke-dasharray="6 5"'),
           f'<path d="M352 {y + 95} Q385 {y + 60} 352 {y + 25}" fill="none" stroke="{BLUE}" stroke-width="3" marker-end="url(#arr-b)"/>',
           rect(480, y, 60, 60, WHITE, 0), line(480, y, 540, y, LINE, 2), line(480, y, 480, y + 60, LINE, 2),
           line(540, y, 540, y + 60, LINE, 4), line(480, y + 60, 540, y + 60, LINE, 4),
           polygon([(517, y + 7), (533, y + 15), (517, y + 23)], RED)]
    for ax in (215, 420):
        els.append(f'<path d="M{ax} {y + 60} h30" stroke="{LINE}" stroke-width="3" marker-end="url(#arr-k)"/>')
    for i, cap in enumerate(["шаг 1", "шаг 2", "шаг 3"]):
        els.append(text([120, 310, 510][i], y + 146, cap, 14, TEXT, "normal", "middle"))

    def sheet(o, axes=False):
        def draw(x, yy, s):
            c, x0, y0 = 22, x - 44, yy - 44
            g = [rect(x0, y0, 88, 88, WHITE, 0, LINE, 1.5)]
            g += [line(x0 + k * c, y0, x0 + k * c, y0 + 88, HIDDEN, 1) for k in (1, 2, 3)]
            g += [line(x0, y0 + k * c, x0 + 88, y0 + k * c, HIDDEN, 1) for k in (1, 2, 3)]
            g += [tri_cell(x0 + cc * c, y0 + r * c, c, d) for r, cc, d in o]
            if axes:
                g += [line(x, y0 - 4, x, y0 + 92, GREEN, 2, ' stroke-dasharray="5 4"'),
                      line(x0 - 4, yy, x0 + 92, yy, GREEN, 2, ' stroke-dasharray="5 4"')]
            return g
        return draw

    card.add_options([sheet(o) for o in opts])
    card.body = els
    task = card.render()
    card.options = []
    card.add_options([sheet(o, axes=(i == opts.index(holes))) for i, o in enumerate(opts)])
    sol = card.render("Ответ: B. Отражение через горизонтальный сгиб не меняет «►», "
                      "через вертикальный — превращает в «◄».", ans)
    save(38, task, sol)
    return "B"


# --- 39. Кольцо шестерёнок -------------------------------------------------------------------
def gear(cx, cy, r, teeth, color):
    pts = []
    for k in range(teeth * 4):
        a = 2 * math.pi * k / (teeth * 4)
        rr = r + 10 if k % 4 in (1, 2) else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return [polygon(pts, color), f'<circle cx="{f(cx)}" cy="{f(cy)}" r="8" fill="{WHITE}"/>']


def spin_arrow(cx, cy, r, cw, color=LINE):
    a0, a1 = (-150, 60) if cw else (60, -150)
    p0 = (cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0)))
    p1 = (cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1)))
    return (f'<path d="M{f(p0[0])} {f(p0[1])} A{r} {r} 0 1 {1 if cw else 0} {f(p1[0])} {f(p1[1])}" fill="none" '
            f'stroke="{color}" stroke-width="3" marker-end="url(#arr-k)"/>')


def task39():
    n = 5
    dirs = [k % 2 == 0 for k in range(n)]  # True = по часовой; соседние вращаются в разные стороны
    jammed = dirs[0] == dirs[-1]           # последняя и первая сцеплены, но крутятся одинаково
    assert jammed and n % 2 == 1
    card = Card(39, "Шестерёнку 1 поворачивают по часовой стрелке. Что произойдёт с шестерёнкой 3?")
    ccx, ccy = 250, card.body_top + 200
    cols = [RED, BLUE, GREEN, ORANGE, PURPLE]
    pos = [(ccx + 118 * math.cos(math.radians(a)), ccy + 118 * math.sin(math.radians(a))) for a in (-90, -18, 54, 126, 198)]
    base = []
    for k, (x, y) in enumerate(pos):
        base += gear(x, y, 58, 12, cols[k]) + [center_label(x, y + 26, str(k + 1), 24)]
    t_els = base + [spin_arrow(*pos[0], 36, True)]
    s_els = list(base) + [spin_arrow(x, y, 36, dirs[k]) for k, (x, y) in enumerate(pos)]
    mx, my = (pos[4][0] + pos[0][0]) / 2, (pos[4][1] + pos[0][1]) / 2
    s_els += [line(mx - 12, my - 12, mx + 12, my + 12, RED, 6), line(mx - 12, my + 12, mx + 12, my - 12, RED, 6)]
    labels = ["A — по часовой", "B — против часовой", "C — не повернётся вообще"]
    for k, lab in enumerate(labels):
        y = card.body_top + 90 + k * 100
        els = [rect(510, y, 260, 70, WHITE, 8, HIDDEN, 2), text(526, y + 41, lab, 18, LINE)]
        t_els += els
        s_els += els
        if k == 2:
            s_els.append(green_frame(510, y, 260, 70, 3))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: C — механизм заклинит. В замкнутом кольце из нечётного числа шестерёнок "
                      "соседние 5 и 1 обязаны крутиться в одну сторону.")
    save(39, task, sol)
    return "C (заклинит)"


# --- 40. Светофор --------------------------------------------------------------------------------
def traffic(x, y, w, h, state, r, blink=False, q=False):
    """state: строка из R/Y/G — какие лампы горят."""
    els = [rect(x, y, w, h, LINE, w / 5)]
    for col, key, off in ((RED, "R", 0.19), (YELLOW, "Y", 0.5), (GREEN, "G", 0.81)):
        cy = y + h * off
        on = key in state
        if on and blink:
            els.append(f'<circle cx="{f(x + w / 2)}" cy="{f(cy)}" r="{f(r * 1.4)}" fill="none" stroke="{col}" '
                       f'stroke-width="2" stroke-dasharray="4 3"/>')
        els.append(f'<circle cx="{f(x + w / 2)}" cy="{f(cy)}" r="{f(r)}" fill="{col if on else HIDDEN}"/>')
    if q:
        els.append(center_label(x + w / 2, y + h / 2, "?", w * 0.6, LINE))
    return els


def task40():
    cycle = [("G", False), ("G", True), ("Y", False), ("R", False), ("RY", False)]
    nxt = cycle[4]
    opts = [("RY", False), ("G", False), ("Y", False), ("Y", True), ("R", True), ("", False)]
    ans = "ABCDEF"[opts.index(nxt)]
    assert ans == "A"
    card = Card(40, "Какой сигнал следующий?")
    y = card.body_top + 40
    t_els, s_els = [], []
    for i in range(5):
        x = 100 + i * 130
        if i == 4:
            t_els += traffic(x, y, 60, 160, "", 20, q=True)
            s_els += traffic(x, y, 60, 160, nxt[0], 20) + [green_frame(x, y, 60, 160, 6)]
            continue
        st, bl = cycle[i]
        els = traffic(x, y, 60, 160, st, 20, bl)
        if bl:
            els.append(text(x + 30, y + 182, "мигает", 14, TEXT, "normal", "middle"))
        t_els += els
        s_els += els
    card.add_options([lambda cx, cy, s, o=o: traffic(cx - 18, cy - 48, 36, 96, o[0], 10, o[1]) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A — красный + жёлтый. По ПДД РФ (п. 6.2) это сочетание запрещает движение "
                      "и предупреждает о скором зелёном.", ans)
    save(40, task, sol)
    return "A (красный + жёлтый)"


# --- 41. Клавиши ------------------------------------------------------------------------------------
SEMI = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def keyboard(x, y, whites, blacks_after, fills, nums, num_color=WHITE):
    """whites: ноты белых клавиш; blacks_after: индексы белых, после которых стоит чёрная."""
    els = []
    for i, nt in enumerate(whites):
        els.append(rect(x + i * 40, y, 40, 160, fills.get(i, WHITE), 0, LINE, 2))
        if i in nums:
            els.append(text(x + i * 40 + 20, y + 146, str(nums[i]), 18, num_color, "bold", "middle"))
    for i in blacks_after:
        els.append(rect(x + (i + 1) * 40 - 12, y, 24, 100, LINE, 2))
    return els


def task41():
    major = [2, 2, 1, 2, 2, 2, 1]
    names = {v: k for k, v in SEMI.items()}
    scale = [7]
    for st in major:
        scale.append(scale[-1] + st)
    notes = [names[s % 12] for s in scale]
    assert notes == ["G", "A", "B", "C", "D", "E", "F#", "G"]
    seventh = notes[6]
    opts = ["F", "F#", "G", "D#"]
    ans = "ABCD"[opts.index(seventh)]

    card = Card(41, "Верхняя клавиатура — образец. Какую клавишу нажать седьмой на нижней?")
    ty, by = card.body_top + 12, card.body_top + 212
    top_w = list("CDEFGABC")
    bot_w = list("GABCDEFG")
    top = keyboard(240, ty, top_w, [0, 1, 3, 4, 5], {i: BLUE for i in range(8)}, {i: i + 1 for i in range(8)})
    bot = keyboard(240, by, bot_w, [0, 1, 3, 4, 6], {i: BLUE for i in range(6)}, {i: i + 1 for i in range(6)})
    spots = {"F": (240 + 6 * 40 + 20, by + 112), "F#": (240 + 7 * 40, by + 30),
             "G": (240 + 7 * 40 + 20, by + 112), "D#": (240 + 5 * 40, by + 30)}

    def marks(highlight=None):
        els = []
        for k, o in enumerate(opts):
            x, y = spots[o]
            col = GREEN if o == highlight else ORANGE
            els += [f'<circle cx="{f(x)}" cy="{f(y)}" r="14" fill="{col}"/>', center_label(x, y, "ABCD"[k], 16)]
        return els

    t_els = top + bot + marks()
    sol_bot = keyboard(240, by, bot_w, [0, 1, 3, 4, 6], {i: BLUE for i in range(6)} | {7: BLUE},
                       {i: i + 1 for i in range(6)} | {7: 8})
    fs = rect(240 + 7 * 40 - 12, by, 24, 100, "#1F5F99", 2, LINE, 2)
    s_els = top + sol_bot + [fs, text(240 + 7 * 40, by + 88, "7", 16, WHITE, "bold", "middle")] + marks(seventh)
    s_els.append(text(400, ty + 188, "тон, тон, полутон, тон, тон, тон, полутон", 15, GREEN, "bold", "middle"))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: B — чёрная клавиша F♯ (фа-диез). Образец — мажорная гамма; в соль мажоре "
                      "седьмая ступень — фа-диез.")
    save(41, task, sol)
    return "B (F♯)"


# --- 42. Пасьянс --------------------------------------------------------------------------------------
def playing_card(x, y, w, h, value, suit, back=False):
    if back:
        return [rect(x, y, w, h, BLUE, w / 9, LINE, 2), center_label(x + w / 2, y + h / 2, "?", w * 0.5)]
    col = RED if suit in "♥♦" else LINE
    return [rect(x, y, w, h, WHITE, w / 9, LINE, 2),
            text(x + w * 0.1, y + h * 0.22, value, f(w * 0.27), col, "bold"),
            text(x + w / 2, y + h * 0.7, suit, f(w * 0.53), col, "normal", "middle")]


def task42():
    suits = "♠♥♣♦"
    vals = [1 + 2 * i for i in range(5)]
    seq = [(vals[i], suits[i % 4]) for i in range(5)]
    show = lambda v: "A" if v == 1 else str(v)
    assert [(show(v), s) for v, s in seq[:4]] == [("A", "♠"), ("3", "♥"), ("5", "♣"), ("7", "♦")]
    opts = [("9", "♠"), ("9", "♥"), ("8", "♠"), ("9", "♦"), ("10", "♠"), ("2", "♠")]
    ans = "ABCDEF"[opts.index((show(seq[4][0]), seq[4][1]))]
    assert ans == "A"
    card = Card(42, "Какая карта следующая?")
    y = card.body_top + 50
    x0 = (W - (5 * 90 + 4 * 30)) / 2
    t_els, s_els = [], []
    for i, (v, s) in enumerate(seq):
        x = x0 + i * 120
        if i == 4:
            t_els += playing_card(x, y, 90, 130, "", "", back=True)
            s_els += playing_card(x, y, 90, 130, show(v), s) + [green_frame(x, y, 90, 130, 4)]
        else:
            els = playing_card(x, y, 90, 130, show(v), s)
            t_els += els
            s_els += els
    card.add_options([lambda cx, cy, sz, o=o: playing_card(cx - 32, cy - 46, 64, 92, *o) for o in opts])
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: A — 9♠. Значения растут на 2 (туз = 1), масти идут по кругу ♠ ♥ ♣ ♦.", ans)
    save(42, task, sol)
    return "A (9♠)"


# --- 43. Задача Бонгарда ---------------------------------------------------------------------------------
def is_convex(pts):
    sgn = set()
    n = len(pts)
    for i in range(n):
        (x1, y1), (x2, y2), (x3, y3) = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        cr = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
        if abs(cr) > 1e-9:
            sgn.add(cr > 0)
    return len(sgn) == 1


def task43():
    sc = 0.75
    star = [((38 if k % 2 == 0 else 16) * math.cos(-math.pi / 2 + k * math.pi / 5),
             (38 if k % 2 == 0 else 16) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
    pent = [(36 * math.cos(-math.pi / 2 + k * 2 * math.pi / 5), 36 * math.sin(-math.pi / 2 + k * 2 * math.pi / 5)) for k in range(5)]
    L = {"tri": [(0, -35), (35, 30), (-35, 30)], "rhomb": [(0, -38), (38, 0), (0, 38), (-38, 0)], "pent": pent,
         "hex": [(-20, -35), (25, -30), (40, 0), (20, 35), (-25, 30), (-40, 5)]}
    P = {"star": star, "L": [(-30, -35), (-10, -35), (-10, 15), (30, 15), (30, 35), (-30, 35)],
         "arrow": [(-35, -10), (5, -10), (5, -30), (38, 0), (5, 30), (5, 10), (-35, 10)],
         "plus": [(-11, -35), (11, -35), (11, -11), (35, -11), (35, 11), (11, 11), (11, 35), (-11, 35),
                  (-11, 11), (-35, 11), (-35, -11), (-11, -11)]}
    tip = [(0, -45), (38, 40), (0, 15), (-38, 40)]
    assert all(is_convex(p) for p in L.values()) and not any(is_convex(p) for p in P.values())
    assert not is_convex(tip)

    def poly_at(pts, cx, cy, col, s=sc):
        return polygon([(cx + s * x, cy + s * y) for x, y in pts], col)

    def pacman(cx, cy, col, s=sc):
        r = 35 * s
        a = math.radians(30)
        return (f'<path d="M{f(cx)} {f(cy)} L{f(cx + r * math.cos(a))} {f(cy - r * math.sin(a))} '
                f'A{f(r)} {f(r)} 0 1 0 {f(cx + r * math.cos(a))} {f(cy + r * math.sin(a))} Z" fill="{col}"/>')

    left = [lambda cx, cy: poly_at(L["tri"], cx, cy, RED),
            lambda cx, cy: f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(35 * sc)}" fill="{BLUE}"/>',
            lambda cx, cy: poly_at(L["rhomb"], cx, cy, GREEN),
            lambda cx, cy: poly_at(pent, cx, cy + 3, PURPLE),
            lambda cx, cy: f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(40 * sc)}" ry="{f(22 * sc)}" fill="{ORANGE}"/>',
            lambda cx, cy: poly_at(L["hex"], cx, cy, PINK)]
    right = [lambda cx, cy: poly_at(star, cx, cy + 3, YELLOW),
             lambda cx, cy: poly_at(P["L"], cx, cy, BLUE),
             lambda cx, cy: (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(35 * sc)}" fill="{GREEN}"/>'
                             f'<circle cx="{f(cx + 18 * sc)}" cy="{f(cy)}" r="{f(30 * sc)}" fill="{WHITE}"/>'),
             lambda cx, cy: poly_at(P["arrow"], cx, cy, RED),
             lambda cx, cy: pacman(cx, cy, ORANGE),
             lambda cx, cy: poly_at(P["plus"], cx, cy, PURPLE)]

    card = Card(43, "Все шесть фигур слева обладают свойством, которого нет ни у одной фигуры справа. "
                    "Куда отнести новую фигуру?")
    top = card.body_top + 28
    base = [line(400, top - 24, 400, top + 262, LINE, 2),
            text(185, top - 8, "Группа Л", 18, TITLE, "bold", "middle"),
            text(615, top - 8, "Группа П", 18, TITLE, "bold", "middle")]
    ps = 80
    for k in range(6):
        for figs, xs in ((left, (100, 190)), (right, (520, 610))):
            x, y = xs[k % 2], top + (k // 2) * 90
            base += [rect(x, y, ps, ps, WHITE, 0, "#444444", 1), figs[k](x + ps / 2, y + ps / 2)]
    fx, fy = 350, top + 272
    base += [rect(fx, fy, 100, 100, WHITE, 0, "#444444", 1),
             polygon([(fx + 50 + 0.9 * x, fy + 52 + 0.9 * y) for x, y in tip], TEAL)]
    btns = [(130, "A — в группу Л"), (520, "B — в группу П")]
    t_els, s_els = list(base), list(base)
    for k, (bx, lab) in enumerate(btns):
        els = [rect(bx, fy + 30, 150, 40, WHITE, 8, HIDDEN, 2), text(bx + 75, fy + 56, lab, 18, LINE, "normal", "middle")]
        t_els += els
        s_els += els
        if k == 1:
            s_els.append(green_frame(bx, fy + 30, 150, 40, 3))
    s_els.append(line(fx + 50 - 34, fy + 52 + 36, fx + 50 + 34, fy + 52 + 36, GREEN, 2.5, ' stroke-dasharray="5 4"'))
    card.body = t_els
    task = card.render()
    card.body = s_els
    sol = card.render("Ответ: B — в группу П. Слева выпуклые фигуры, справа невыпуклые; «наконечник» похож "
                      "на треугольник, но у него есть входящий угол.")
    save(43, task, sol)
    return "B (группа П)"


# --- 44. Химическая орфография ----------------------------------------------------------------------------
ELEMENTS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
            "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb "
            "Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf "
            "Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()


def spellable(word):
    word = word.lower()
    symbols = {e.lower() for e in ELEMENTS}
    ok = [True] + [False] * len(word)
    for i in range(1, len(word) + 1):
        ok[i] = any(ok[i - k] and word[i - k:i] in symbols for k in (1, 2) if i - k >= 0)
    return ok[-1]


def task44():
    assert len(ELEMENTS) == 118
    num = lambda s: ELEMENTS.index(s) + 1
    assert (num("Ne"), num("O"), num("N")) == (10, 8, 7)
    opts = ["BACON", "SPACE", "GENIUS", "HOUSE", "MAGIC", "FUNNY"]
    splits = {"BACON": "Ba·Co·N", "SPACE": "S·Pa·Ce", "GENIUS": "Ge·Ni·U·S", "HOUSE": "Ho·U·Se", "FUNNY": "F·U·N·N·Y"}
    for w, sp in splits.items():
        parts = sp.split("·")
        assert "".join(parts).upper() == w and all(p in ELEMENTS for p in parts)
    bad = [w for w in opts if not spellable(w)]
    assert bad == ["MAGIC"]
    ans = "ABCDEF"[opts.index("MAGIC")]

    card = Card(44, "Пример: NEON = Ne + O + N. Какое слово нельзя целиком составить из символов химических элементов?")
    y = card.body_top + 70
    els = [text(110, y + 36, "NEON", 30, LINE, "bold"), text(220, y + 36, "=", 30, LINE, "bold")]
    x = 260
    for k, sym in enumerate(["Ne", "O", "N"]):
        els += [rect(x, y, 50, 50, TEAL, 0, LINE, 2), text(x + 5, y + 13, str(num(sym)), 11, WHITE, "bold"),
                center_label(x + 25, y + 28, sym, 22)]
        x += 50
        if k < 2:
            els.append(text(x + 20, y + 36, "+", 30, LINE, "bold", "middle"))
            x += 40

    def opt(w, show=False):
        def draw(cx, cy, s):
            g = [center_label(cx, cy - (8 if show else 0), w, 22, LINE)]
            if show:
                g.append(text(cx, cy + 26, splits.get(w, "—"), 13, GREEN if w in splits else RED, "bold", "middle"))
            return g
        return draw

    card.add_options([opt(w) for w in opts])
    card.body = els
    task = card.render()
    card.options = []
    card.add_options([opt(w, True) for w in opts])
    sol = card.render("Ответ: E — MAGIC. Нет ни «M», ни «Ma»: на M начинаются только Mc, Md, Mg, Mn, Mo, Mt.", ans)
    save(44, task, sol)
    return "E (MAGIC)"


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


TASKS = {n: globals()[f"task{n:02d}"] for n in range(1, 45)}

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
