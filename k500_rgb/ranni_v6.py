"""
Ranni v6 — «Ночь Ранни», яркая версия на эффектах прошивки.

Ранни спокойная, но сияющая: яркая каррийская лазурь, ледяной лунный свет,
электрический фиолет. Палитры выстроены лестницей: от глубокого синего
к ослепительному льду и обратно через фиолет. Соседние цвета отличаются по
яркости не больше чем в ~1.8 раза, поэтому пики нарастают как свечение, а не
мигают. Клавиатура горит постоянно: основа — Drifting, звёзды — короткие паузы.

    python ranni_v6.py
    python ranni_v6.py --show tide       # stars, tide, whirl, breath, darkmoon, typing
    python ranni_v6.py --swatches
Ctrl+C — выход.
"""
import argparse
import random
import time

import k500

# --- палитры (R, G, B); яркость Y = 0.21R + 0.72G + 0.07B ---

STAR_DEEP = (0x00, 0x1E, 0xFF)   # глубокий синий
STAR_ICE = (0x78, 0xF0, 0xFF)    # ослепительный лёд

# лестница: 233° Y40 -> 224° Y68 -> 212° Y104 -> 200° Y140 -> 189° Y202 (пик)
#           -> 230° Y114 -> 262° Y73 -> 273° Y48 -> снова синий
TIDE = [
    (0x00, 0x1E, 0xFF),  # глубокий каррийский синий
    (0x00, 0x46, 0xFF),  # лазурь
    (0x00, 0x78, 0xFF),  # яркая лазурь
    (0x00, 0xAA, 0xFF),  # циан
    (0x5A, 0xE6, 0xFF),  # лунный лёд — пик сияния
    (0x50, 0x6E, 0xFF),  # холодный лавандовый синий
    (0x78, 0x28, 0xFF),  # электрический фиолет
    (0x8C, 0x00, 0xFF),  # фиолет Тёмной Луны
]

# Тёмная Луна: фиолет с сияющим лавандовым пиком, Y 31..123
DARK_MOON = [
    (0x5A, 0x00, 0xFF), (0x82, 0x0A, 0xFF), (0xA0, 0x32, 0xFF), (0xBE, 0x5A, 0xFF),
    (0xA0, 0x32, 0xFF), (0x82, 0x0A, 0xFF), (0x5A, 0x00, 0xFF), (0x46, 0x00, 0xE6),
]

CARIAN_TRACE = (0x00, 0xC8, 0xFF)  # след от нажатий

SCENES = {
    "stars":    ("Звёздное небо", dict(mode=k500.MODE_STARLIGHT_DUAL, color1=STAR_DEEP, color2=STAR_ICE, speed=0)),
    "tide":     ("Лунный прилив", dict(mode=k500.MODE_DRIFTING, palette=TIDE, speed=0)),
    "whirl":    ("Каррийский водоворот", dict(mode=k500.MODE_SPIRAL, palette=TIDE, speed=0)),
    "breath":   ("Дыхание луны", dict(mode=k500.MODE_BREATHING_RAINBOW, palette=TIDE, speed=0)),
    "darkmoon": ("Тёмная Луна", dict(mode=k500.MODE_SPIRAL, palette=DARK_MOON, speed=0)),
    "typing":   ("Каррийский след", dict(mode=k500.MODE_FADING_TRACE, color1=CARIAN_TRACE, speed=1)),
}


def apply(kb, key, brightness):
    name, cmd = SCENES[key]
    cmd = dict(cmd)
    kb.send(cmd.pop("mode"), brightness=brightness, **cmd)
    return name


def cycle(rnd, typing):
    """Сценарий: долгий лунный прилив, затем акцент, иногда Тёмная Луна."""
    last = None
    while True:
        yield ("typing" if typing else "tide"), rnd.uniform(150, 240)
        accent = rnd.choice([s for s in ("whirl", "breath", "stars") if s != last])
        last = accent
        yield accent, rnd.uniform(40, 70)
        if rnd.random() < 0.4:
            yield "darkmoon", rnd.uniform(25, 35)


def swatches(kb, brightness):
    colors = [("звезда: глубокий", STAR_DEEP), ("звезда: лёд", STAR_ICE)]
    colors += [(f"прилив {i}", c) for i, c in enumerate(TIDE)]
    colors += [(f"Тёмная Луна {i}", c) for i, c in enumerate(DARK_MOON)]
    colors += [("след нажатий", CARIAN_TRACE)]
    for name, c in colors:
        kb.static(c, brightness=brightness)
        print(f"  {name:18s} #{c[0]:02X}{c[1]:02X}{c[2]:02X}")
        time.sleep(2.5)


def main():
    ap = argparse.ArgumentParser(description="Ranni v6 — Ночь Ранни, яркая версия")
    ap.add_argument("--dim", action="store_true", help="тише: аппаратная яркость 1 вместо 2")
    ap.add_argument("--typing", action="store_true", help="вместо неба — след от нажатий")
    ap.add_argument("--show", choices=sorted(SCENES), help="включить одну сцену и выйти")
    ap.add_argument("--swatches", action="store_true", help="показать все цвета по очереди")
    a = ap.parse_args()
    brightness = 1 if a.dim else 2

    with k500.K500() as kb:
        if a.show:
            print("Включено:", apply(kb, a.show, brightness))
            return
        if a.swatches:
            print("Образцы цветов (по 2.5 с). Прилив должен идти плавной лестницей")
            print("от синего к сияющему льду и через фиолет назад.")
            swatches(kb, brightness)
            apply(kb, "tide", brightness)
            return

        print("Ranni v6 — Ночь Ранни. Ctrl+C — выход.")
        try:
            for key, seconds in cycle(random.Random(), a.typing):
                name = apply(kb, key, brightness)
                print(f"  {time.strftime('%H:%M:%S')}  {name} ({int(seconds)} с)")
                time.sleep(seconds)
        except KeyboardInterrupt:
            apply(kb, "tide", brightness)
            print("\nОстановлено. Лунный прилив остаётся.")


if __name__ == "__main__":
    main()
