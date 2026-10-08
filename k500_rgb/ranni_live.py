"""
Ranni Live — собственный движок узоров для Lenovo Legion K500.

Каждый кадр считается для КАЖДОЙ клавиши отдельно (как на экране):
  Каррийская ночь  — фон всегда горит: медленные диагональные потоки
                     глубокого синего и фиолета
  Лунный прилив    — сияющая лазурно-ледяная волна идёт по клавиатуре
  Каррийские круги — от случайных клавиш расходятся голубые кольца
  Звёзды           — ледяные искры вспыхивают и гаснут поверх фона
  Тёмная Луна      — раз в 1–2 минуты фиолетовый вихрь закручивается вокруг центра

Протокол K500 даёт один цвет на команду, поэтому кадр раскладывается на 2–3
цветовые группы, и они очень быстро чередуются — глаз сливает их в одну
картинку (как светодиодные экраны). Это работает, только если:
  - клавиатура НЕ запоминает цвет после переподключения (иначе износ flash),
  - она принимает достаточно команд в секунду без мерцания.
Оба условия проверяет k500_limits.py — запустите его первым.

    python ranni_live.py --preview   # посмотреть узоры в консоли (клавиатура не нужна)
    python ranni_live.py             # на клавиатуре
Ctrl+C — выход.
"""
import argparse
import json
import math
import os
import random
import sys
import time

import k500

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = [k[0] for k in k500.KEYS]
X = {k[0]: float(k[4]) for k in k500.KEYS}
Y = {k[0]: k[3] * 1.25 for k in k500.KEYS}    # ряды стоят реже колонок
CX, CY = 11.0, 3.1

# цвета в линейном свете 0..1 — насыщенные, «светодиодные»
DEEP = (0.00, 0.10, 1.00)
VIOLET = (0.50, 0.00, 1.00)
AZURE = (0.00, 0.45, 1.00)
ICE = (0.45, 0.95, 1.00)
CYAN = (0.00, 0.80, 1.00)
DARK_MOON = (0.62, 0.08, 1.00)


def add(c, col, k):
    c[0] += col[0] * k
    c[1] += col[1] * k
    c[2] += col[2] * k


def bell(p):
    """0 -> 1 -> 0 на отрезке p 0..1, плавно."""
    return math.sin(math.pi * max(0.0, min(1.0, p))) ** 2


class Scene:
    def __init__(self, rnd):
        self.rnd = rnd
        self.ripples = []    # (x, y, t0)
        self.stars = {}      # key -> (t0, life)
        self.next_ripple = 1.0
        self.next_moon = rnd.uniform(40, 80)

    def frame(self, t):
        rnd = self.rnd
        if t >= self.next_ripple:
            k = rnd.choice(KEYS)
            self.ripples.append((X[k], Y[k], t))
            self.next_ripple = t + rnd.uniform(1.8, 3.5)
        self.ripples = [r for r in self.ripples if t - r[2] < 4.5]
        while len(self.stars) < 6:
            self.stars[rnd.choice(KEYS)] = (t + rnd.uniform(0, 1.5), rnd.uniform(1.5, 3.0))
        self.stars = {k: v for k, v in self.stars.items() if t < v[0] + v[1]}

        moon = 0.0
        if t >= self.next_moon:
            p = (t - self.next_moon) / 9.0
            if p >= 1:
                self.next_moon = t + rnd.uniform(60, 120)
            else:
                moon = bell(p)

        tide_pos = (t / 16.0 % 1) * 40 - 8          # волна проходит за 16 с
        fb = {}
        for k in KEYS:
            x, y = X[k], Y[k]
            c = [0.0, 0.0, 0.0]
            # фон: медленные диагональные потоки синего и фиолета
            s = 0.5 + 0.5 * math.sin(0.28 * x - 0.35 * y + t * 0.25)
            base = 0.72 * (1 - 0.55 * moon)
            add(c, DEEP, base * (1 - s))
            add(c, VIOLET, base * s)
            # лунный прилив: мягкий фронт с ледяным ядром
            d = x + 0.7 * y - tide_pos
            w = math.exp(-(d / 2.4) ** 2)
            add(c, AZURE, 0.9 * w)
            add(c, ICE, 0.35 * math.exp(-(d / 0.9) ** 2))
            # каррийские круги
            for rx, ry, t0 in self.ripples:
                age = t - t0
                dist = math.hypot(x - rx, y - ry)
                ring = math.exp(-((dist - 5.0 * age) / 0.9) ** 2)
                add(c, CYAN, 0.8 * ring * max(0.0, 1 - age / 4.5))
            # звёзды
            if k in self.stars:
                t0, life = self.stars[k]
                add(c, ICE, bell((t - t0) / life))
            # Тёмная Луна: вихрь вокруг центра
            if moon > 0:
                a = math.atan2(y - CY, x - CX)
                r = math.hypot(x - CX, y - CY)
                swirl = 0.5 + 0.5 * math.cos(3 * a - 2.2 * t + 0.5 * r)
                add(c, DARK_MOON, moon * (0.35 + 0.75 * swirl))
            fb[k] = (min(1.0, c[0]), min(1.0, c[1]), min(1.0, c[2]))
        return fb


def quantize(fb, n):
    """Делит клавиши на n цветовых групп (k-means). Возвращает [(цвет, [клавиши])]."""
    keys = sorted(fb, key=lambda k: sum(fb[k]))
    centers = [fb[keys[int((i + 0.5) * len(keys) / n)]] for i in range(n)]
    for _ in range(4):
        groups = [[] for _ in range(n)]
        for k in keys:
            c = fb[k]
            i = min(range(n), key=lambda j: sum((c[m] - centers[j][m]) ** 2 for m in range(3)))
            groups[i].append(k)
        centers = [tuple(sum(fb[k][m] for k in g) / len(g) for m in range(3)) if g else centers[i]
                   for i, g in enumerate(groups)]
    return [(centers[i], g) for i, g in enumerate(groups) if g]


def to_rgb(c, gain):
    peak = max(c) or 1.0
    s = min(gain, 1.0 / peak)          # компенсируем «деление» яркости между группами
    return tuple(int(round(255 * v * s)) for v in c)


class Preview:
    def __init__(self):
        self.cells = {}
        for k in k500.KEYS:
            self.cells.setdefault((k[3], k[4]), k[0])
        if sys.platform == "win32":
            os.system("")
        sys.stdout.write("\x1b[2J")

    def show(self, fb, title):
        out = [f"\x1b[H  {title}  (Ctrl+C — выход)\n\n"]
        for r in range(6):
            line = "  "
            for c in range(23):
                k = self.cells.get((r, c))
                if k is None:
                    line += "  "
                else:
                    rgb = tuple(int(255 * v) for v in fb[k])
                    line += "\x1b[38;2;%d;%d;%dm██\x1b[0m" % rgb
            out.append(line + "\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()


def load_limits():
    try:
        with open(os.path.join(HERE, "k500_limits.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def run_keyboard(scene, groups_n, sub_hz):
    period = 1.0 / sub_hz
    t0 = time.perf_counter()
    with k500.K500() as kb:
        try:
            while True:
                fb = scene.frame(time.perf_counter() - t0)
                for color, keys in quantize(fb, groups_n):
                    start = time.perf_counter()
                    kb.custom(to_rgb(color, groups_n), keys)
                    time.sleep(max(0.0, period - (time.perf_counter() - start)))
        except KeyboardInterrupt:
            kb.send(k500.MODE_STARLIGHT_DUAL, (0x00, 0x1E, 0xFF), (0x5A, 0xE6, 0xFF), speed=0)
            print("\nОстановлено. На клавиатуре оставлено звёздное небо.")


def run_slow(scene):
    """Без быстрого режима: вся клавиатура горит общим цветом кадра (без узора)."""
    t0, last = time.perf_counter(), None
    with k500.K500() as kb:
        try:
            while True:
                fb = scene.frame(time.perf_counter() - t0)
                avg = tuple(sum(fb[k][m] for k in KEYS) / len(KEYS) for m in range(3))
                rgb = to_rgb(avg, 1.6)
                if rgb != last:
                    kb.static(rgb)
                    last = rgb
                time.sleep(0.25)
        except KeyboardInterrupt:
            print("\nОстановлено.")


def main():
    ap = argparse.ArgumentParser(description="Ranni Live — свои узоры для K500")
    ap.add_argument("--preview", action="store_true", help="показать в консоли")
    ap.add_argument("--groups", type=int, choices=[2, 3, 4], help="цветовых групп на кадр")
    a = ap.parse_args()
    scene = Scene(random.Random())

    if a.preview:
        pv, t0 = Preview(), time.perf_counter()
        try:
            while True:
                fb = scene.frame(time.perf_counter() - t0)
                if a.groups:
                    fb = {k: c for c, ks in quantize(fb, a.groups) for k in ks}
                pv.show(fb, "Ranni Live — превью" + (f", {a.groups} группы" if a.groups else ""))
                time.sleep(1 / 20)
        except KeyboardInterrupt:
            print("\x1b[0m")
        return

    lim = load_limits()
    if lim is None:
        sys.exit("Сначала запустите k500_limits.py — нужно проверить память и скорость клавиатуры.")
    if lim.get("persistent") or not lim.get("smooth_hz"):
        print("Быстрый режим недоступен (клавиатура запоминает цвет или мерцает).")
        print("Работаю в медленном режиме: вся клавиатура переливается общим цветом.")
        run_slow(scene)
        return
    hz = lim["smooth_hz"]
    n = a.groups or (3 if hz >= 90 else 2)
    print(f"Ranni Live: {hz} команд/с, {n} цветовые группы. Ctrl+C — выход.")
    run_keyboard(scene, n, hz)


if __name__ == "__main__":
    main()
