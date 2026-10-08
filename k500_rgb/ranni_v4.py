"""
Ranni v4 — «Ночь Ранни». Подсветку рисует сама прошивка клавиатуры: плавно,
с разными цветами на разных клавишах. Скрипт лишь выбирает сцены и
перекрашивает их в цвета Ранни. Команда отправляется только при смене сцены,
поэтому нет ни мерцания «гирлянды», ни потока записей в клавиатуру.

Сцены:
  Звёздное небо    — Starlight dual: холодные звёзды двух оттенков (основная сцена)
  Лунный прилив / Каррийский водоворот / Дыхание луны
                   — Drifting, Spiral или Breathing rainbow в сине-фиолетовом
                     градиенте (разведка подтвердила, что они берут палитру)
  Тёмная Луна      — изредка: фиолетовая спираль раскручивается из центра
  --typing         — вместо неба: каждое нажатие оставляет гаснущий
                     каррийский след (Fading trace)

Сначала один раз запустите k500_explore.py — он запишет explore_results.json.

    python ranni_v4.py
    python ranni_v4.py --typing
    python ranni_v4.py --brightness 1
    python ranni_v4.py --show darkmoon   # одна сцена: stars, tide, whirl, breath, darkmoon, typing
Ctrl+C — выход.
"""
import argparse
import json
import os
import random
import time

import k500

STAR_DEEP = (0x2A, 0x3C, 0xD8)   # далёкие синие звёзды
STAR_COLD = (0x9F, 0xE8, 0xFF)   # холодные голубые звёзды
MOON = (0x39, 0x48, 0xC8)
DARK_MOON = (0x70, 0x40, 0xB8)
CARIAN = (0x5A, 0xB4, 0xFF)
NIGHT = (0x08, 0x0A, 0x30)

# Палитра «лунного прилива»: слоты идут плавным градиентом по кругу
# ночная синева -> каррийский -> звезда -> лунный -> фиолет -> сумерки -> назад.
# Слишком тёмных цветов нет: на клавишах они выглядят как дырки.
TIDE_PALETTE = [
    (0x1E, 0x28, 0x8C),  # ночная синева
    (0x4A, 0x7C, 0xFF),  # каррийский синий
    (0x9F, 0xE8, 0xFF),  # холодная звезда
    (0x39, 0x48, 0xC8),  # лунная волна
    (0x70, 0x40, 0xB8),  # Тёмная Луна
    (0x46, 0x1E, 0x8C),  # сумеречный фиолет
    (0x26, 0x30, 0xA8),  # глубокий синий
    (0x1E, 0x28, 0x8C),
]
# Тёмная Луна: только фиолетовые оттенки — закручивается спиралью из центра.
DARK_MOON_PALETTE = [
    (0x70, 0x40, 0xB8), (0x50, 0x28, 0x98), (0x8C, 0x5A, 0xD8), (0x3C, 0x14, 0x78),
    (0x70, 0x40, 0xB8), (0x5A, 0x30, 0xA8), (0x96, 0x6E, 0xE6), (0x50, 0x28, 0x98),
]

HERE = os.path.dirname(os.path.abspath(__file__))
# Многоцветные режимы, у которых разведка подтвердила подмену палитры
# (у Surfing — нет, он рисует своими цветами).
TIDE_MODES = [k500.MODE_DRIFTING, k500.MODE_SPIRAL, k500.MODE_BREATHING_RAINBOW]


def palette_modes():
    try:
        with open(os.path.join(HERE, "explore_results.json"), encoding="utf-8") as f:
            res = json.load(f)
    except (OSError, ValueError):
        return None
    return {int(k, 16) for k, v in res.items() if v.get("palette")}


def scenes(rnd, ok, typing):
    tides = [m for m in TIDE_MODES if ok and m in ok]
    spiral_ok = bool(ok) and k500.MODE_SPIRAL in ok
    while True:
        if typing:
            yield "Каррийский след под пальцами", rnd.uniform(240, 420), dict(
                mode=k500.MODE_FADING_TRACE, color1=CARIAN, speed=1)
        else:
            yield "Звёздное небо", rnd.uniform(180, 300), dict(
                mode=k500.MODE_STARLIGHT_DUAL, color1=STAR_DEEP, color2=STAR_COLD, speed=0)
        if tides:
            mode = rnd.choice(tides)
            name = {k500.MODE_DRIFTING: "Лунный прилив",
                    k500.MODE_SPIRAL: "Каррийский водоворот",
                    k500.MODE_BREATHING_RAINBOW: "Дыхание луны"}[mode]
            yield name, rnd.uniform(60, 100), dict(mode=mode, palette=TIDE_PALETTE, speed=0)
        else:
            yield "Лунное дыхание", rnd.uniform(40, 60), dict(
                mode=k500.MODE_BREATHING, color1=MOON, speed=0)
        if rnd.random() < 0.4:
            if spiral_ok:
                yield "Тёмная Луна", rnd.uniform(20, 30), dict(
                    mode=k500.MODE_SPIRAL, palette=DARK_MOON_PALETTE, speed=0)
            else:
                yield "Тёмная Луна", 14, dict(mode=k500.MODE_BREATHING, color1=DARK_MOON, speed=1)


SHOW = {
    "stars": dict(mode=k500.MODE_STARLIGHT_DUAL, color1=STAR_DEEP, color2=STAR_COLD, speed=0),
    "tide": dict(mode=k500.MODE_DRIFTING, palette=TIDE_PALETTE, speed=0),
    "whirl": dict(mode=k500.MODE_SPIRAL, palette=TIDE_PALETTE, speed=0),
    "breath": dict(mode=k500.MODE_BREATHING_RAINBOW, palette=TIDE_PALETTE, speed=0),
    "darkmoon": dict(mode=k500.MODE_SPIRAL, palette=DARK_MOON_PALETTE, speed=0),
    "typing": dict(mode=k500.MODE_FADING_TRACE, color1=CARIAN, speed=1),
}


def main():
    ap = argparse.ArgumentParser(description="Ranni v4 — Ночь Ранни")
    ap.add_argument("--typing", action="store_true", help="след от нажатий вместо звёздного неба")
    ap.add_argument("--brightness", type=int, default=2, choices=[0, 1, 2], help="яркость прошивки 0–2")
    ap.add_argument("--show", choices=sorted(SHOW), help="включить одну сцену и выйти")
    a = ap.parse_args()

    if a.show:
        cmd = dict(SHOW[a.show])
        with k500.K500() as kb:
            kb.send(cmd.pop("mode"), brightness=a.brightness, **cmd)
        print(f"Включена сцена {a.show}. Она останется на клавиатуре.")
        return

    ok = palette_modes()
    if ok is None:
        print("explore_results.json не найден — запустите сначала k500_explore.py.")
        print("Пока работаю без «Лунного прилива» (только подтверждённые цвета).\n")

    rnd = random.Random()
    with k500.K500() as kb:
        print("Ranni v4 — Ночь Ранни. Ctrl+C — выход.")
        try:
            for name, seconds, cmd in scenes(rnd, ok, a.typing):
                cmd = dict(cmd)
                kb.send(cmd.pop("mode"), brightness=a.brightness, **cmd)
                print(f"  {time.strftime('%H:%M:%S')}  {name} ({int(seconds)} с)")
                time.sleep(seconds)
        except KeyboardInterrupt:
            kb.send(k500.MODE_STARLIGHT_DUAL, STAR_DEEP, STAR_COLD, speed=0, brightness=a.brightness)
            print("\nОстановлено. Звёздное небо остаётся на клавиатуре.")


if __name__ == "__main__":
    main()
