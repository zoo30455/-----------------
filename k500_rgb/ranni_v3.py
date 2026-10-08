"""
Ranni v3 — «Эра Звёзд». Маленький фильм про Ранни на клавиатуре Lenovo Legion K500.

Акты (цикл ~70 секунд):
  I.   Эра Звёзд      — холодные звёзды вспыхивают и гаснут по всему небу
  II.  Восход луны    — пиксельный полумесяц плывёт по клавиатуре
  III. RANNI          — имя бежит строкой, как надпись на карте
  IV.  Меч Тёмной Луны — три диагональных взмаха клинка
  V.   Тёмная Луна    — фиолетовый диск растёт из центра и заполняет всё
  VI.  Тишина         — глубокая синяя ночь дышит, пока всё не начнётся снова

Запуск:
    python ranni_v3.py              # на клавиатуре
    python ranni_v3.py --preview    # посмотреть в консоли, клавиатура не нужна
Ctrl+C — выход.
"""
import argparse
import math
import random
import sys
import time

import k500

# --- палитра Ранни ---
NIGHT = (0x06, 0x08, 0x2A)      # глубокая ночь
STAR = (0xA8, 0xEC, 0xFF)       # холодная звезда
MOON = (0xC8, 0xD8, 0xFF)       # бледный лунный свет
CARIAN = (0x4A, 0x7C, 0xFF)     # каррийская синева (надпись)
BLADE = (0x90, 0xF0, 0xFF)      # клинок
DARK_MOON = (0x6A, 0x38, 0xC0)  # Тёмная Луна

KEYS = [k[0] for k in k500.KEYS]
POS = {k[0]: (k[3], k[4]) for k in k500.KEYS}     # имя -> (ряд, колонка)
ROWS, COLS = 6, 23
GAMMA = 2.2


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def env(t, length, fin, fout):
    if t < fin:
        return smooth(t / fin)
    if t > length - fout:
        return smooth((length - t) / fout)
    return 1.0


def shade(rgb, k):
    k = max(0.0, min(1.0, k)) ** GAMMA
    return tuple(int(round(c * k)) for c in rgb)


def keys_where(pred):
    return [n for n in KEYS if pred(*POS[n])]


# --- I. Эра Звёзд ---
def act_stars(rnd, length=16.0):
    groups, t = [], 0.3
    while t < length - 2:
        life = rnd.uniform(1.8, 3.5)
        groups.append((t, life, rnd.sample(KEYS, rnd.randint(4, 9))))
        t += life + rnd.uniform(0.1, 0.5)
    length = t + 0.3

    def frame(t):
        for start, life, keys in groups:
            if start <= t < start + life:
                p = (t - start) / life
                k = smooth(p / 0.25) if p < 0.25 else smooth((1 - p) / 0.5) if p > 0.5 else 1.0
                return STAR, k, keys
        return STAR, 0, []
    return length, frame


# --- II. Восход луны: полумесяц = круг минус смещённый круг ---
def crescent(cx, cy=2.5, r=2.9, cut=2.0, dy=0.4, sx=0.6):
    # колонки сетки ближе друг к другу, чем ряды, поэтому x сжимаем (sx)
    return keys_where(lambda row, col:
                      ((col - cx) * sx) ** 2 + (row - cy) ** 2 <= r * r and
                      ((col - cx - cut) * sx) ** 2 + (row - cy + dy) ** 2 > (r * 0.95) ** 2)


def act_moon(length=13.0):
    def frame(t):
        cx = 13 - 8 * (t / length)          # луна медленно плывёт справа налево
        glow = 0.75 + 0.25 * math.sin(2 * math.pi * t / 4)
        return MOON, glow * env(t, length, 2.5, 2.5), crescent(cx)
    return length, frame


# --- III. RANNI бегущей строкой (шрифт 4 ряда: ряды 1–4 самые плотные) ---
FONT = {
    "R": ["##.", "#.#", "##.", "#.#"],
    "A": [".#.", "#.#", "###", "#.#"],
    "N": ["#..#", "##.#", "#.##", "#..#"],
    "I": ["###", ".#.", ".#.", "###"],
}


def text_pixels(text):
    pix, x = set(), 0
    for ch in text:
        glyph = FONT[ch]
        for r, line in enumerate(glyph):
            for c, v in enumerate(line):
                if v == "#":
                    pix.add((r + 1, x + c))       # ряды 1–4
        x += len(glyph[0]) + 1
    return pix, x - 1


def act_title(length=14.0):
    pix, width = text_pixels("RANNI")
    start, end = COLS, -width

    def frame(t):
        off = round(start + (end - start) * (t / length))
        keys = keys_where(lambda row, col: (row, col - off) in pix)
        return CARIAN, env(t, length, 0.8, 0.8), keys
    return length, frame


# --- IV. Меч Тёмной Луны: три диагональных взмаха ---
def act_blade(rnd):
    slashes, t = [], 0.4
    for _ in range(3):
        tilt = rnd.choice([-1.4, 1.4])
        slashes.append((t, 0.9, tilt))
        t += 0.9 + rnd.uniform(0.6, 1.0)
    length = t + 0.6

    def frame(t):
        for start, dur, tilt in slashes:
            if start <= t < start + dur:
                p = (t - start) / dur
                x = -8 + 38 * smooth(p)          # лезвие проходит всю клавиатуру
                keys = keys_where(lambda row, col: 0 <= x - (col + tilt * (row - 2.5)) < 3.2)
                return BLADE, 1.0 - 0.6 * p, keys
        return BLADE, 0, []
    return length, frame


# --- V. Тёмная Луна: диск растёт из центра ---
def act_dark_moon(length=8.0):
    cx, cy = 11, 2.5

    def frame(t):
        r = 13 * smooth(t / (length * 0.55))
        keys = keys_where(lambda row, col: ((col - cx) * 0.75) ** 2 + (row - cy) ** 2 <= r * r)
        return DARK_MOON, env(t, length, 1.0, 2.5), keys
    return length, frame


# --- VI. Тишина ---
def act_night(length=9.0):
    def frame(t):
        breath = 0.8 + 0.2 * math.sin(2 * math.pi * t / 7)
        return NIGHT, breath * env(t, length, 2.0, 2.0), KEYS
    return length, frame


def film(rnd):
    while True:
        yield act_stars(rnd)
        yield act_moon()
        yield act_title()
        yield act_blade(rnd)
        yield act_dark_moon()
        yield act_night()


# --- вывод: клавиатура или консоль ---
class Preview:
    """Рисует клавиатуру в консоли цветными блоками (ANSI)."""
    def __init__(self):
        self.cells = {}
        for n in KEYS:
            self.cells.setdefault(POS[n], n)
        if sys.platform == "win32":
            import os
            os.system("")          # включает ANSI-цвета в консоли Windows
        sys.stdout.write("\x1b[2J")

    def custom(self, rgb, keys):
        lit = set(keys)
        out = ["\x1b[H  Ranni v3 — превью (Ctrl+C — выход)\n\n"]
        for r in range(ROWS):
            line = "  "
            for c in range(COLS):
                n = self.cells.get((r, c))
                if n is None:
                    line += "  "
                elif n in lit:
                    line += "\x1b[38;2;%d;%d;%dm██\x1b[0m" % tuple(max(v, 25) for v in rgb)
                else:
                    line += "\x1b[38;2;30;30;40m░░\x1b[0m"
            out.append(line + "\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def static(self, rgb):
        self.custom(rgb, KEYS)


def run(out, fps=6, brightness=1.0, seed=None, clock=time.monotonic, sleep=time.sleep, duration=None):
    rnd = random.Random(seed)
    period = 1.0 / fps
    last, t_begin = None, clock()
    for length, frame in film(rnd):
        t0 = clock()
        while True:
            now = clock()
            if duration is not None and now - t_begin >= duration:
                return
            t = now - t0
            if t >= length:
                break
            color, k, keys = frame(t)
            rgb = shade(color, k * brightness)
            if not keys or rgb == (0, 0, 0):
                rgb, keys = (0, 0, 0), []
            mask = frozenset(keys)
            if (last is None or mask != last[1] or (rgb == (0, 0, 0)) != (last[0] == (0, 0, 0))
                    or max(abs(a - b) for a, b in zip(rgb, last[0])) >= max(2, 0.04 * max(rgb))):
                out.custom(rgb, keys)
                last = (rgb, mask)
            sleep(max(0.0, period - (clock() - now)))


def main():
    ap = argparse.ArgumentParser(description="Ranni v3 — Эра Звёзд")
    ap.add_argument("--preview", action="store_true", help="показать в консоли, без клавиатуры")
    ap.add_argument("--fps", type=float, default=6, help="кадров в секунду (по умолчанию 6)")
    ap.add_argument("--brightness", type=float, default=1.0, help="яркость 0.2–1.0")
    a = ap.parse_args()
    fps = max(1.0, min(a.fps, 10.0))
    bright = max(0.2, min(a.brightness, 1.0))

    if a.preview:
        try:
            run(Preview(), fps=fps, brightness=bright)
        except KeyboardInterrupt:
            print("\x1b[0m")
        return

    with k500.K500() as kb:
        print("Ranni v3 — Эра Звёзд. Ctrl+C — выход.")
        try:
            run(kb, fps=fps, brightness=bright)
        except KeyboardInterrupt:
            kb.static(NIGHT)
            print("\nКонец. Осталась ночь.")


if __name__ == "__main__":
    main()
