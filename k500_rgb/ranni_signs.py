"""
Знаки Ранни — подсветка Lenovo Legion K500 по образу Ранни Ведьмы (Elden Ring).

Кто она: холодная и властная Каррийская принцесса, отказавшаяся от судьбы
божества. Её тело — кукла по образу Снежной ведьмы: голубая кожа, одежда цвета
снега, огромная заиндевевшая шляпа. Её знак — Тёмная Луна, «холодная и
свинцовая»; Меч Тёмной Луны — «лишь луч её света». Её цель — Эра Звёзд.
Поэтому цвета: лёд, снег, лунное серебро и глубокая ночная синева.

Клавиатура запоминает каждую команду (проверено k500_limits.py), поэтому
каждый знак — ОДНА команда: либо неподвижный рисунок, либо эффект, который
прошивка анимирует сама. Поставили — и он остаётся даже после перезагрузки.

Знаки-рисунки:
  moon      Тёмная Луна   — ледяной ореол вокруг тёмного диска
  blade     Меч Тёмной Луны — клинок с гардой, луч лунного света
  hat       Шляпа Снежной ведьмы
  ring      Кольцо Тёмной Луны — вокруг клавиши R (Ранни)
  stars     Эра Звёзд     — редкие неподвижные звёзды
Живые знаки (анимирует прошивка):
  night     Ночь Эры Звёзд — снежные звёзды мерцают на глубокой синеве
  frost     Дыхание Снежной ведьмы — вся клавиатура медленно дышит льдом
  moonlight Лунный свет   — по клавишам плывут оттенки от ночи до снега
  rise      Восход Тёмной Луны — свинцово-серебряная спираль из центра
  sorcery   Холодное колдовство — каждое нажатие оставляет ледяной след

    python ranni_signs.py --preview          # все рисунки в консоли, без клавиатуры
    python ranni_signs.py moon               # поставить знак
    python ranni_signs.py --tour             # показать все знаки по 15 с (≈10 команд)
    python ranni_signs.py --test-mask        # проверить «живые рисунки» (2 команды)
"""
import argparse
import json
import os
import sys
import time

import k500

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = {(k[3], k[4]): k[0] for k in k500.KEYS}


def cells(*rc):
    return [GRID[c] for c in rc if c in GRID]


def halo(cx, cy, rx, ry, lo, hi):
    """Клавиши в кольце эллипса: lo..hi в долях радиуса."""
    return [k[0] for k in k500.KEYS
            if lo <= (((k[4] - cx) / rx) ** 2 + ((k[3] - cy) / ry) ** 2) ** 0.5 <= hi]


# --- цвета Ранни ---
NIGHT = (0x00, 0x1E, 0xFF)       # глубокая ночная синева
SNOW = (0xB4, 0xF0, 0xFF)        # снег / звёздный свет
MOON_ICE = (0x8C, 0xDC, 0xFF)    # лунный лёд
FROST = (0x50, 0xC8, 0xFF)       # иней
BLADE = (0x78, 0xD2, 0xFF)       # луч Тёмной Луны

# лестница «ночь -> снег -> ночь», без фиолета
MOONLIGHT = [
    (0x00, 0x1E, 0xFF), (0x00, 0x50, 0xFF), (0x00, 0x8C, 0xFF), (0x3C, 0xC8, 0xFF),
    (0x9C, 0xF0, 0xFF), (0x3C, 0xC8, 0xFF), (0x00, 0x8C, 0xFF), (0x00, 0x50, 0xFF),
]
# свинцовая луна: серо-синие тона с серебряным пиком
LEADEN = [
    (0x28, 0x3C, 0xC8), (0x46, 0x5A, 0xDC), (0x6E, 0x8C, 0xFF), (0xA0, 0xC8, 0xFF),
    (0x6E, 0x8C, 0xFF), (0x46, 0x5A, 0xDC), (0x28, 0x3C, 0xC8), (0x1E, 0x28, 0xA0),
]

ARTS = {
    "moon": ("Тёмная Луна", MOON_ICE, halo(6.5, 2.0, 3.3, 2.0, 0.72, 1.18)),
    "blade": ("Меч Тёмной Луны", BLADE, cells((0, 7), (0, 8), (1, 8), (1, 9), (2, 9), (2, 10),
                                               (3, 10), (3, 11), (4, 12), (3, 13), (5, 11), (5, 13))),
    "hat": ("Шляпа Снежной ведьмы", SNOW, cells((0, 9), (0, 10), (1, 8), (1, 9), (2, 7), (2, 8),
                                                (3, 6), (3, 7), (3, 8), (3, 9), *[(4, c) for c in range(2, 13)])),
    "ring": ("Кольцо Тёмной Луны", MOON_ICE, cells((1, 4), (1, 5), (1, 6), (2, 4), (2, 6),
                                                   (3, 4), (3, 5), (3, 6))),
    "stars": ("Эра Звёзд", SNOW, cells((0, 3), (1, 8), (2, 12), (3, 6), (0, 13), (4, 10),
                                       (2, 2), (1, 15), (3, 20), (0, 18), (4, 4), (2, 21))),
}

LIVING = {
    "night": ("Ночь Эры Звёзд", dict(mode=k500.MODE_STARLIGHT_DUAL, color1=NIGHT, color2=SNOW, speed=0)),
    "frost": ("Дыхание Снежной ведьмы", dict(mode=k500.MODE_BREATHING, color1=FROST, speed=0)),
    "moonlight": ("Лунный свет", dict(mode=k500.MODE_DRIFTING, palette=MOONLIGHT, speed=0)),
    "rise": ("Восход Тёмной Луны", dict(mode=k500.MODE_SPIRAL, palette=LEADEN, speed=0)),
    "sorcery": ("Холодное колдовство", dict(mode=k500.MODE_FADING_TRACE, color1=FROST, speed=1)),
}

ORDER = ["moon", "night", "blade", "frost", "hat", "moonlight", "ring", "rise", "stars", "sorcery"]
MASK_RESULT = os.path.join(HERE, "ranni_mask.json")


def mask_works():
    try:
        with open(MASK_RESULT, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def put(kb, key, brightness=2):
    if key in ARTS:
        name, color, keys = ARTS[key]
        alive = mask_works()
        # если прошивка учитывает маску в «дыхании» — рисунок оживает
        mode = k500.MODE_BREATHING if alive.get("breathing") else k500.MODE_CUSTOMIZE
        kb.send(mode, color, keys=keys, speed=0, brightness=brightness)
        return name + (" (дышит)" if mode == k500.MODE_BREATHING else "")
    name, cmd = LIVING[key]
    cmd = dict(cmd)
    kb.send(cmd.pop("mode"), brightness=brightness, **cmd)
    return name


def preview():
    if sys.platform == "win32":
        os.system("")
    for key in ARTS:
        name, color, keys = ARTS[key]
        lit = set(keys)
        print(f"\n  {name}")
        for r in range(6):
            line = "  "
            for c in range(23):
                k = GRID.get((r, c))
                if k is None:
                    line += "  "
                elif k in lit:
                    line += "\x1b[38;2;%d;%d;%dm██\x1b[0m" % color
                else:
                    line += "\x1b[38;2;25;28;40m██\x1b[0m"
            print(line)


def ask(q):
    while True:
        a = input(f"{q} [y/n]: ").strip().lower()
        if a in ("y", "n", "д", "н"):
            return a in ("y", "д")


def test_mask(kb):
    """Проверяет, учитывает ли прошивка маску клавиш в анимированных режимах."""
    _, color, keys = ARTS["moon"]
    res = {}
    kb.send(k500.MODE_BREATHING, color, keys=keys, speed=1)
    res["breathing"] = ask("Дышит ТОЛЬКО кольцо Тёмной Луны (остальные клавиши тёмные)?")
    kb.send(k500.MODE_STARLIGHT, color, keys=keys, speed=1)
    res["starlight"] = ask("Звёзды вспыхивают ТОЛЬКО на кольце?")
    with open(MASK_RESULT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("Сохранено:", res)
    print("Если «дыхание» сработало — рисунки (moon, blade, hat…) теперь будут дышать." if res["breathing"]
          else "Маска в анимации не работает — рисунки остаются неподвижными.")


def main():
    ap = argparse.ArgumentParser(description="Знаки Ранни для Lenovo Legion K500")
    ap.add_argument("sign", nargs="?", choices=ORDER, help="какой знак поставить")
    ap.add_argument("--preview", action="store_true", help="рисунки в консоли")
    ap.add_argument("--tour", action="store_true", help="все знаки по 15 с")
    ap.add_argument("--test-mask", action="store_true", help="проверить живые рисунки")
    ap.add_argument("--dim", action="store_true", help="аппаратная яркость 1")
    a = ap.parse_args()

    if a.preview:
        preview()
        return
    if not (a.sign or a.tour or a.test_mask):
        ap.print_help()
        return

    b = 1 if a.dim else 2
    with k500.K500() as kb:
        if a.test_mask:
            test_mask(kb)
        elif a.tour:
            try:
                for key in ORDER:
                    print(f"  {put(kb, key, b)}")
                    time.sleep(15)
            except KeyboardInterrupt:
                pass
            print("Тур окончен. Выберите знак: python ranni_signs.py moon")
        else:
            print("Поставлено:", put(kb, a.sign, b))


if __name__ == "__main__":
    main()
