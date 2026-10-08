"""
Минимальный тест K500: весь цвет -> одна клавиша -> все кроме одной.
Перед запуском закройте Lenovo Legion Accessory Central (иначе она может
перезаписать подсветку).

    pip install hidapi
    python k500_test.py
"""
import time

import k500


def step(text):
    input(f"\n{text}\nНажмите Enter...")


with k500.K500() as kb:
    step("1) Вся клавиатура: тусклый синий (static)")
    kb.static((0x10, 0x10, 0x60))

    step("2) Только ESC: циан (customize, остальные клавиши погаснут)")
    kb.custom((0x00, 0xC0, 0xFF), ["ESC"])

    step("3) Все клавиши, кроме ESC: синий (ESC должна погаснуть)")
    kb.custom((0x10, 0x10, 0x60), [k[0] for k in k500.KEYS if k[0] != "ESC"])

    step("4) Бегущий огонёк по первому ряду (проверка порядка клавиш)")
    for name in ["ESC", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8",
                 "F9", "F10", "F11", "F12", "PrtSc", "ScrollLock", "Pause"]:
        kb.custom((0x00, 0xC0, 0xFF), [name])
        time.sleep(0.4)

    kb.static((0x10, 0x10, 0x60))
    print("\nГотово: возвращён статичный синий.")
