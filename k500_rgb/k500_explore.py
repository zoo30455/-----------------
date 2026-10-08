"""
Разведка возможностей Lenovo Legion K500.

Показывает по очереди все 11 режимов прошивки и проверяет главный вопрос:
перекрашивает ли клавиатура свои многоцветные эффекты, если подменить палитру
(слоты 1–6, которые приложение Lenovo всегда заполняет радугой).

Результаты сохраняются в explore_results.json — ranni_v4.py их использует.

    python k500_explore.py
Закройте Lenovo Legion Accessory Central перед запуском.
"""
import json
import os
import time

import k500

RANNI_PALETTE = [
    (0x08, 0x0A, 0x30),  # 0 глубокая ночь
    (0x9F, 0xE8, 0xFF),  # 1 звезда
    (0x39, 0x48, 0xC8),  # 2 лунная волна
    (0x70, 0x40, 0xB8),  # 3 Тёмная Луна
    (0x1E, 0x28, 0x8C),  # 4 ночная синева
    (0x5A, 0x8C, 0xFF),  # 5 каррийский синий
    (0x3C, 0x14, 0x78),  # 6 сумеречный фиолетовый
    (0x00, 0x00, 0x00),  # 7
]

MODES = [
    (k500.MODE_STATIC, "Static"),
    (k500.MODE_SPIRAL, "Spiral"),
    (k500.MODE_LASER, "Laser"),
    (k500.MODE_DRIFTING, "Drifting"),
    (k500.MODE_FADING_TRACE, "Fading trace (нажимайте клавиши)"),
    (k500.MODE_BREATHING, "Breathing"),
    (k500.MODE_BREATHING_RAINBOW, "Breathing rainbow"),
    (k500.MODE_STARLIGHT, "Starlight"),
    (k500.MODE_STARLIGHT_DUAL, "Starlight dual"),
    (k500.MODE_SURFING, "Surfing"),
]

HERE = os.path.dirname(os.path.abspath(__file__))


def ask(q):
    while True:
        a = input(f"{q} [y/n]: ").strip().lower()
        if a in ("y", "n", "д", "н"):
            return a in ("y", "д")


def main():
    results = {}
    with k500.K500() as kb:
        print("Для каждого режима: сначала обычная радуга, потом палитра Ранни.\n")
        for mode, name in MODES:
            print(f"=== {name} (0x{mode:02X}) ===")
            kb.send(mode, (0xFF, 0x00, 0x00), speed=1)
            input("  Обычные цвета Lenovo. Посмотрите и нажмите Enter...")
            kb.send(mode, palette=RANNI_PALETTE, speed=1)
            time.sleep(0.3)
            changed = ask("  Палитра Ранни: эффект стал сине-фиолетовым (без жёлтого, зелёного, красного)?")
            note = input("  Коротко, как выглядит (Enter — пропустить): ").strip()
            results[f"0x{mode:02X}"] = {"name": name, "palette": changed, "note": note}
            print()

        print("=== Скорость (Surfing, 0 = медленно … 3 = быстро) ===")
        for s in range(4):
            kb.send(k500.MODE_SURFING, palette=RANNI_PALETTE, speed=s)
            input(f"  speed={s}. Enter...")
        print("=== Яркость (Static, 0 … 2) ===")
        for b in range(3):
            kb.send(k500.MODE_STATIC, (0x39, 0x48, 0xC8), brightness=b)
            input(f"  brightness={b}. Enter...")

        kb.static((0x08, 0x0A, 0x30))

    path = os.path.join(HERE, "explore_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nГотово. Результаты: {path}")
    print("Режимы, которые берут палитру:",
          ", ".join(v["name"] for v in results.values() if v["palette"]) or "нет")


if __name__ == "__main__":
    main()
