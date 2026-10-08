"""
Проверка пределов Lenovo Legion K500 — нужна перед ranni_live.py.

1. Память: сохраняет ли клавиатура цвет после переподключения USB.
   Если да — скорее всего, каждая команда пишется во flash, и частые
   команды её изнашивают. Тогда быстрый режим запрещён.
2. Скорость: сколько команд в секунду клавиатура принимает и сливает ли
   глаз быстрое чередование двух кадров в одну картинку без мерцания.

Результат — k500_limits.json рядом со скриптом.
    python k500_limits.py
"""
import json
import os
import time

import k500

HERE = os.path.dirname(os.path.abspath(__file__))
LEFT = [k[0] for k in k500.KEYS if k[4] <= 9]
RIGHT = [k[0] for k in k500.KEYS if k[4] > 9]
VIOLET = (0x8C, 0x00, 0xFF)
CYAN = (0x00, 0xC8, 0xFF)


def ask(q):
    while True:
        a = input(f"{q} [y/n]: ").strip().lower()
        if a in ("y", "n", "д", "н"):
            return a in ("y", "д")


def persistence():
    print("\n=== 1. Память ===")
    with k500.K500() as kb:
        kb.static((0x00, 0xFF, 0x40))
    print("Клавиатура стала зелёной (такого цвета у Lenovo по умолчанию нет).")
    input("Выньте USB клавиатуры, подождите 5 секунд, вставьте обратно и нажмите Enter...")
    time.sleep(2)
    return ask("После переподключения клавиатура снова ЗЕЛЁНАЯ?")


def rate_test():
    print("\n=== 2. Скорость ===")
    print("Левая половина — фиолетовая, правая — голубая. Кадры чередуются.")
    print("Нужно понять, при какой частоте обе половины видны одновременно и ровно.\n")
    best, measured = None, {}
    with k500.K500() as kb:
        for hz in (20, 40, 60, 90, 120):
            period, sent, t0 = 1.0 / hz, 0, time.perf_counter()
            while time.perf_counter() - t0 < 4:
                start = time.perf_counter()
                kb.custom(VIOLET if sent % 2 == 0 else CYAN, LEFT if sent % 2 == 0 else RIGHT)
                sent += 1
                time.sleep(max(0.0, period - (time.perf_counter() - start)))
            real = sent / (time.perf_counter() - t0)
            measured[hz] = round(real, 1)
            kb.static((0x00, 0x00, 0x00))
            print(f"  цель {hz}/с, получилось {real:.0f}/с")
            if ask("  Обе половины светились одновременно, без заметного мерцания?"):
                best = hz
        kb.static((0x00, 0x28, 0xFF))
    return best, measured


def main():
    persistent = persistence()
    if persistent:
        print("\nКлавиатура запоминает цвет. Быстрый режим опасен для её памяти —")
        print("тест скорости пропущен, ranni_live.py будет работать в медленном режиме.")
        best, measured = None, {}
    else:
        best, measured = rate_test()
    res = {"persistent": persistent, "smooth_hz": best, "measured": measured}
    path = os.path.join(HERE, "k500_limits.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"\nСохранено: {path}\n{res}")


if __name__ == "__main__":
    main()
