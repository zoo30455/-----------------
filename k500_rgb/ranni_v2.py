"""
Ranni v2 — «лунная ночь» для Lenovo Legion K500.

Протокол customize даёт на кадр ОДИН цвет и маску клавиш. Поэтому эффект
собран из спокойных сцен, и внутри сцены меняются только яркость и маска,
а цвет — только на стыке сцен, через затухание в темноту:

  Ночь       — вся клавиатура #080A30, очень медленное «дыхание»
  Звёзды     — группы клавиш #9FE8FF: плавно появляются, светят, гаснут (2–5 с)
  Лунная волна — полоса #3948C8 медленно и чуть по диагонали идёт по клавишам
  Dark Moon  — редкий мягкий импульс #7040B8 на всю клавиатуру

Запуск:
    python ranni_v2.py
    python ranni_v2.py --fps 4 --brightness 0.8
    python ranni_v2.py --no-dark-moon
Выход — Ctrl+C (останется спокойный ночной фон).

Кадры без заметных изменений не отправляются: клавиатура получает команду
только когда картинка реально меняется (бережём возможную flash-память).
"""
import argparse
import math
import random
import time

import k500

NIGHT = (0x08, 0x0A, 0x30)
STAR = (0x9F, 0xE8, 0xFF)
WAVE = (0x39, 0x48, 0xC8)
DARK_MOON = (0x70, 0x40, 0xB8)

ALL_KEYS = [k[0] for k in k500.KEYS]
ROW = {k[0]: k[3] for k in k500.KEYS}
COL = {k[0]: k[4] for k in k500.KEYS}
COLS = 23

FADE = 1.5          # затухание при смене цвета, сек
GAMMA = 2.2         # чтобы затухание выглядело равномерным для глаза


def smooth(x):
    """Плавная кривая 0..1 (smoothstep)."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def envelope(t, length, fade_in, fade_out):
    """Яркость сцены: плавный вход, плато, плавный выход."""
    if t < fade_in:
        return smooth(t / fade_in)
    if t > length - fade_out:
        return smooth((length - t) / fade_out)
    return 1.0


def shade(rgb, k):
    """Цвет с яркостью k (0..1) с гамма-коррекцией."""
    k = max(0.0, min(1.0, k)) ** GAMMA
    return tuple(int(round(c * k)) for c in rgb)


# --- сцены: генераторы кадров (цвет, яркость, клавиши) по времени сцены ---

def scene_night(length):
    def frame(t):
        breath = 0.85 + 0.15 * math.sin(2 * math.pi * t / 9)   # дыхание ~9 с
        return NIGHT, breath * envelope(t, length, FADE, FADE), ALL_KEYS
    return length, frame


def scene_stars(length, rnd):
    """Последовательность «вспышек»: у каждой свои клавиши и свой цикл 2–5 с."""
    groups, t = [], 0.4
    while t < length - 2:
        life = rnd.uniform(2.0, 5.0)
        keys = rnd.sample(ALL_KEYS, rnd.randint(3, 7))
        groups.append((t, life, keys))
        t += life + rnd.uniform(0.2, 0.8)          # короткая тьма между вспышками
    length = t + 0.4

    def frame(t):
        for start, life, keys in groups:
            if start <= t < start + life:
                p = (t - start) / life
                # быстрое появление, плато, медленное угасание
                k = smooth(p / 0.3) if p < 0.3 else smooth((1 - p) / 0.45) if p > 0.55 else 1.0
                return STAR, k, keys
        return STAR, 0.0, []
    return length, frame


def scene_wave(rnd):
    """Полоса шириной ~3 колонки, слегка диагональная, проходит за ~30 с."""
    tilt = rnd.choice([-0.6, 0.6])                   # наклон по рядам
    width = 1.6
    start, end = -4.0, COLS + 4.0
    length = 30.0

    def frame(t):
        x = start + (end - start) * (t / length)
        keys = [n for n in ALL_KEYS if abs(COL[n] + tilt * ROW[n] - x) < width]
        swell = 0.8 + 0.2 * math.sin(math.pi * t / length)
        return WAVE, swell * envelope(t, length, 3.0, 3.0), keys
    return length, frame


def scene_dark_moon():
    length = 6.0

    def frame(t):
        k = math.sin(math.pi * t / length) ** 2      # мягкий подъём и спад
        return DARK_MOON, k, ALL_KEYS
    return length, frame


def playlist(rnd, dark_moon=True):
    """Бесконечная смена сцен. Dark Moon — раз в 2–4 минуты."""
    next_moon = rnd.uniform(120, 240)
    elapsed = 0.0
    while True:
        for scene in (
            scene_night(rnd.uniform(12, 18)),
            scene_stars(rnd.uniform(18, 26), rnd),
            scene_night(rnd.uniform(8, 12)),
            scene_wave(rnd),
        ):
            yield scene
            elapsed += scene[0]
            if dark_moon and elapsed >= next_moon:
                yield scene_dark_moon()
                elapsed, next_moon = 0.0, rnd.uniform(120, 240)


def run(kb, fps=5, brightness=1.0, dark_moon=True, seed=None,
        clock=time.monotonic, sleep=time.sleep, duration=None):
    rnd = random.Random(seed)
    period = 1.0 / fps
    last = None
    t_begin = clock()
    for length, frame in playlist(rnd, dark_moon):
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
                keys, rgb = [], (0, 0, 0)
            mask = frozenset(keys)
            # шлём только заметные изменения: другая маска, погасание
            # или сдвиг цвета больше ~4% (минимум 2 единицы)
            if (last is None or mask != last[1] or (rgb == (0, 0, 0)) != (last[0] == (0, 0, 0))
                    or max(abs(a - b) for a, b in zip(rgb, last[0])) >= max(2, 0.04 * max(rgb))):
                kb.custom(rgb, keys)
                last = (rgb, mask)
            sleep(max(0.0, period - (clock() - now)))


def main():
    ap = argparse.ArgumentParser(description="Ranni v2 для Lenovo Legion K500")
    ap.add_argument("--fps", type=float, default=5, help="кадров в секунду (1–10, по умолчанию 5)")
    ap.add_argument("--brightness", type=float, default=1.0, help="общая яркость 0.2–1.0")
    ap.add_argument("--no-dark-moon", action="store_true", help="без импульса Dark Moon")
    ap.add_argument("--seed", type=int, help="зерно случайности (для повторяемости)")
    a = ap.parse_args()

    with k500.K500() as kb:
        print("Ranni v2: лунная ночь. Ctrl+C — выход.")
        try:
            run(kb, fps=max(1.0, min(a.fps, 10.0)),
                brightness=max(0.2, min(a.brightness, 1.0)),
                dark_moon=not a.no_dark_moon, seed=a.seed)
        except KeyboardInterrupt:
            kb.static(NIGHT)
            print("\nОстановлено, оставлен ночной фон.")


if __name__ == "__main__":
    main()
