"""
Ranni v5 — «Ночь Ранни», дизайн-версия.

Анимацию рисует прошивка клавиатуры (плавно, разные цвета на разных клавишах),
скрипт только меняет сцены — одна команда на сцену.

Дизайн-принципы (почему так выглядит лучше, чем v4):
  1. Ровная яркость внутри сцены. Пока прошивка перетекает по цветам палитры,
     яркость слотов отличается не больше чем в ~1.8 раза (в v4 — в 4.8).
     Иначе светлый слот «вспыхивает» среди тёмных — получается гирлянда.
  2. Насыщенные «светодиодные» цвета: один канал около нуля, главный — у максимума.
     Когда горят все три канала, под колпачком выходит белёсый, дешёвый оттенок.
  3. Узкий диапазон оттенков Ранни: лёд-лазурь 215° -> синий 235° -> фиолет 270°.
     Без розового, зелёного и белого.
  4. Контраст — только намеренный: яркие ледяные звёзды на глубоком синем.
  5. Тише/громче — аппаратной яркостью (--dim), а не тёмными RGB: на малых
     значениях светодиоды теряют точность и уводят оттенок.
  6. Всё медленно (speed 0). Ранни — это тишина, а не дискотека.

    python ranni_v5.py                  # полный цикл
    python ranni_v5.py --dim            # тише (аппаратная яркость 1)
    python ranni_v5.py --show darkmoon  # одна сцена: stars, tide, whirl, breath, darkmoon, typing
    python ranni_v5.py --swatches       # образцы цветов по очереди — проверить, как их рисуют светодиоды
Ctrl+C — выход.
"""
import argparse
import random
import time

import k500

# --- палитры (R, G, B), яркость рассчитана: Y = 0.21R + 0.72G + 0.07B ---

# Звёзды — намеренный контраст: глубокий синий и ледяная искра
STAR_DEEP = (0x00, 0x14, 0xFF)   # 235°, Y≈33
STAR_ICE = (0x3C, 0xC8, 0xFF)    # 197°, Y≈174

# Лунный прилив: лазурь -> синий -> фиолет и обратно, Y 39..69
TIDE = [
    (0x10, 0x28, 0xFF),  # синяя лазурь
    (0x00, 0x40, 0xFF),  # каррийский синий
    (0x00, 0x48, 0xF0),  # ледяная лазурь — самый светлый
    (0x00, 0x40, 0xFF),  # каррийский синий
    (0x30, 0x18, 0xFF),  # лунный сине-фиолетовый
    (0x60, 0x00, 0xFF),  # фиолет Тёмной Луны
    (0x48, 0x08, 0xFF),  # сумеречный фиолет
    (0x18, 0x20, 0xFF),  # ночная синева
]

# Тёмная Луна: только фиолет 258..271°, Y 34..56
DARK_MOON = [
    (0x6E, 0x00, 0xFF), (0x58, 0x00, 0xF0), (0x80, 0x08, 0xFF), (0x50, 0x00, 0xE6),
    (0x6E, 0x00, 0xFF), (0x60, 0x00, 0xF5), (0x88, 0x0C, 0xFF), (0x58, 0x00, 0xF0),
]

CARIAN_TRACE = (0x00, 0x60, 0xFF)  # след от нажатий

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
    """Сценарий: долгое небо, затем одна из «лунных» сцен, иногда Тёмная Луна."""
    base = "typing" if typing else "stars"
    last = None
    while True:
        yield base, rnd.uniform(180, 300)
        tide = rnd.choice([s for s in ("tide", "whirl", "breath") if s != last])
        last = tide
        yield tide, rnd.uniform(70, 110)
        if rnd.random() < 0.35:
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
    ap = argparse.ArgumentParser(description="Ranni v5 — Ночь Ранни")
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
            print("Образцы цветов (по 2.5 с). Соседние цвета прилива должны")
            print("казаться почти одинаково яркими; если какой-то выбивается — скажите.")
            swatches(kb, brightness)
            apply(kb, "stars", brightness)
            return

        print("Ranni v5 — Ночь Ранни. Ctrl+C — выход.")
        try:
            for key, seconds in cycle(random.Random(), a.typing):
                name = apply(kb, key, brightness)
                print(f"  {time.strftime('%H:%M:%S')}  {name} ({int(seconds)} с)")
                time.sleep(seconds)
        except KeyboardInterrupt:
            apply(kb, "stars", brightness)
            print("\nОстановлено. Звёздное небо остаётся.")


if __name__ == "__main__":
    main()
