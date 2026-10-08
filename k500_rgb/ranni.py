"""
Эффект в стиле Ranni (Elden Ring) для Lenovo Legion K500.

Протокол K500 в режиме customize даёт ОДИН цвет на кадр + маску клавиш,
поэтому эффект построен из этого:
  - звёзды: отдельные клавиши появляются и гаснут (маска);
  - лунная волна: полоса клавиш медленно идёт слева направо;
  - мерцание: общая яркость кадра плавно «дышит» (через RGB);
  - Dark Moon: изредка вся клавиатура мягко вспыхивает фиолетовым.
Постоянный фиолетовый фон ОДНОВРЕМЕННО с голубыми звёздами протокол
не позволяет — у кадра только один цвет.

    python ranni.py            # программная анимация
    python ranni.py --hw       # аппаратный Starlight Dual (фиолетовый + циан), одна команда
    python ranni.py --fps 3    # реже кадры

ВНИМАНИЕ: неизвестно, пишет ли клавиатура каждую команду во flash-память.
Если после переподключения USB цвет сохраняется — скорее всего пишет,
и долгая анимация может изнашивать память. Используйте низкий --fps
или режим --hw.
"""
import argparse
import math
import random
import time

import k500

CYAN = (0x40, 0xC8, 0xFF)       # холодные звёзды и волна
VIOLET = (0x50, 0x10, 0xA0)     # Dark Moon
DEEP_BLUE = (0x12, 0x10, 0x60)  # для аппаратного режима

COLS = 23


def scale(rgb, k):
    return tuple(max(0, min(255, int(c * k))) for c in rgb)


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def run(fps):
    stars = {}            # имя клавиши -> момент, когда звезда погаснет
    next_dark_moon = time.time() + random.uniform(30, 60)
    names = [k[0] for k in k500.KEYS]
    col = {k[0]: k[4] for k in k500.KEYS}
    t0 = time.time()

    with k500.K500() as kb:
        print("Ranni: Ctrl+C для выхода")
        try:
            while True:
                now = time.time()
                t = now - t0

                # Dark Moon: плавный фиолетовый импульс 4 сек на всю клавиатуру
                if now >= next_dark_moon:
                    if now < next_dark_moon + 4:
                        p = (now - next_dark_moon) / 4
                        k = math.sin(math.pi * p)
                        kb.custom(scale(VIOLET, 0.25 + 0.75 * k), names)
                        time.sleep(1 / fps)
                        continue
                    next_dark_moon = now + random.uniform(40, 90)

                # звёзды: рождаются и живут 2–5 сек
                for name in [n for n, end in stars.items() if end <= now]:
                    del stars[name]
                if len(stars) < 7 and random.random() < 0.5:
                    stars[random.choice(names)] = now + random.uniform(2, 5)

                # лунная волна: полоса ~3 колонки, полный проход за ~20 сек
                x = (t / 20 % 1) * (COLS + 6) - 3
                wave = [n for n in names if abs(col[n] - x) < 1.5]

                # мерцание: медленное «дыхание» яркости, цвет чуть уходит в синий
                k = 0.55 + 0.45 * math.sin(t * 2 * math.pi / 6)
                color = scale(mix(CYAN, DEEP_BLUE, 0.3 * (1 - k)), 0.35 + 0.65 * k)

                kb.custom(color, list(stars) + wave)
                time.sleep(1 / fps)
        except KeyboardInterrupt:
            kb.static(DEEP_BLUE)
            print("\nОстановлено, оставлен тёмно-синий фон.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hw", action="store_true", help="аппаратный Starlight Dual")
    ap.add_argument("--fps", type=float, default=5, help="кадров в секунду (по умолчанию 5)")
    a = ap.parse_args()
    if a.hw:
        with k500.K500() as kb:
            kb.starlight_dual(DEEP_BLUE, CYAN, speed=0)
        print("Включён аппаратный Starlight Dual: тёмно-синий + циан, медленно.")
    else:
        run(max(0.5, min(a.fps, 20)))


if __name__ == "__main__":
    main()
