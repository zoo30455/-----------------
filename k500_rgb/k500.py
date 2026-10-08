"""
Lenovo Legion K500 (VID 0x17EF, PID 0x60D5) — управление подсветкой через hidapi.

Протокол подтверждён двумя независимыми USB-захватами официального приложения
(OpenRGB issue #1553 и MR !3472) и драйвером OpenRGB
Controllers/LenovoControllers/LenovoLegionK500Controller/LenovoK500Controller.cpp.

Каждая команда = 2 передачи на интерфейс 3:
  1) Feature report (SET_REPORT, report ID 0): 14 00 5A 00 00 00 00 00
  2) Output report 64 байта (без report ID) в interrupt-endpoint 0x04:
       [0x00] 0x01            константа
       [0x01] режим           0x01 static ... 0x06 customize ... 0x0B surfing
       [0x02] яркость         0..2
       [0x03] скорость        0..3
       [0x10..0x12] цвет 1 RGB
       [0x14..0x16] цвет 2 RGB  (Starlight Dual)
       [0x18..0x1A] цвет 3 RGB
       [0x10..0x2F] палитра: 8 слотов по 4 байта (R,G,B,0)
       [0x30..0x3F] маска клавиш для customize: 1 бит = 1 клавиша
  Контрольной суммы нет.

ОГРАНИЧЕНИЕ: в режиме customize один пакет несёт ОДИН цвет и маску клавиш.
Разных цветов на разных клавишах одновременно протокол не задаёт.
"""
import hid

VID, PID, INTERFACE = 0x17EF, 0x60D5, 3

MODE_STATIC = 0x01
MODE_SPIRAL = 0x02
MODE_LASER = 0x03
MODE_DRIFTING = 0x04
MODE_FADING_TRACE = 0x05
MODE_CUSTOMIZE = 0x06
MODE_BREATHING = 0x07
MODE_BREATHING_RAINBOW = 0x08
MODE_STARLIGHT = 0x09
MODE_STARLIGHT_DUAL = 0x0A
MODE_SURFING = 0x0B

FEATURE = bytes([0x14, 0x00, 0x5A, 0x00, 0x00, 0x00, 0x00, 0x00])

# Палитра по умолчанию, байты 0x10..0x2F, ровно как шлёт приложение Lenovo
# (захват k500-customize.pcapng). 8 слотов по 4 байта: R, G, B, 0.
# Примечание: у OpenRGB в default_palette ошибка в слотах 5-6
# (ff 00 ff ff | 00 00 00 ff вместо ff ff 00 00 | 00 ff ff 00).
DEFAULT_PALETTE = bytes([
    0xff, 0x00, 0x00, 0x00,  # слот 0 = цвет 1
    0xff, 0xff, 0xff, 0x00,  # слот 1 = цвет 2
    0x00, 0xff, 0x00, 0x00,  # слот 2 = цвет 3
    0x00, 0x00, 0xff, 0x00,
    0xff, 0x00, 0xff, 0x00,
    0xff, 0xff, 0x00, 0x00,
    0x00, 0xff, 0xff, 0x00,
    0x00, 0x00, 0x00, 0x00,
])

# (имя, байт маски, бит, ряд, колонка) — 104 клавиши.
# Байт/бит проверены по захвату k500-all.pcapng: все 104 совпали.
# Ряд/колонка — из matrix_map OpenRGB (сетка 6x23), нужны для эффектов.
KEYS = [
    ("ESC", 0, 0, 0, 0),
    ("F1", 0, 1, 0, 2),
    ("F2", 0, 2, 0, 3),
    ("F3", 0, 3, 0, 4),
    ("F4", 0, 4, 0, 5),
    ("F5", 0, 5, 0, 7),
    ("F6", 0, 6, 0, 8),
    ("F7", 0, 7, 0, 9),
    ("F8", 1, 0, 0, 10),
    ("F9", 1, 1, 0, 12),
    ("F10", 1, 2, 0, 13),
    ("F11", 1, 3, 0, 14),
    ("F12", 1, 4, 0, 15),
    ("PrtSc", 1, 5, 0, 17),
    ("ScrollLock", 1, 6, 0, 18),
    ("Pause", 1, 7, 0, 19),
    ("Grave", 2, 0, 1, 0),
    ("1", 2, 1, 1, 1),
    ("2", 2, 2, 1, 2),
    ("3", 2, 3, 1, 3),
    ("4", 2, 4, 1, 4),
    ("5", 2, 5, 1, 5),
    ("6", 2, 6, 1, 6),
    ("7", 2, 7, 1, 7),
    ("8", 3, 0, 1, 8),
    ("9", 3, 1, 1, 9),
    ("0", 3, 2, 1, 10),
    ("Minus", 3, 3, 1, 11),
    ("Equal", 3, 4, 1, 12),
    ("Backspace", 3, 5, 1, 13),
    ("Insert", 3, 6, 1, 15),
    ("Home", 3, 7, 1, 16),
    ("PgUp", 7, 6, 1, 17),
    ("NumLock", 12, 0, 1, 19),
    ("NumSlash", 12, 5, 1, 20),
    ("NumAsterisk", 13, 1, 1, 21),
    ("NumMinus", 14, 0, 1, 22),
    ("Tab", 4, 0, 2, 0),
    ("Q", 4, 1, 2, 2),
    ("W", 4, 2, 2, 3),
    ("E", 4, 3, 2, 4),
    ("R", 4, 4, 2, 5),
    ("T", 4, 5, 2, 6),
    ("Y", 4, 6, 2, 7),
    ("U", 4, 7, 2, 8),
    ("I", 5, 0, 2, 9),
    ("O", 5, 1, 2, 10),
    ("P", 5, 2, 2, 11),
    ("LBracket", 5, 3, 2, 12),
    ("RBracket", 5, 4, 2, 13),
    ("Backslash", 5, 5, 2, 14),
    ("Delete", 5, 6, 2, 15),
    ("End", 5, 7, 2, 16),
    ("PgDn", 7, 7, 2, 17),
    ("Num7", 12, 1, 2, 19),
    ("Num8", 12, 6, 2, 20),
    ("Num9", 13, 2, 2, 21),
    ("NumPlus", 14, 1, 2, 22),
    ("CapsLock", 6, 0, 3, 0),
    ("A", 6, 1, 3, 2),
    ("S", 6, 2, 3, 3),
    ("D", 6, 3, 3, 4),
    ("F", 6, 4, 3, 5),
    ("G", 6, 5, 3, 6),
    ("H", 6, 6, 3, 7),
    ("J", 6, 7, 3, 8),
    ("K", 7, 0, 3, 9),
    ("L", 7, 1, 3, 10),
    ("Semicolon", 7, 2, 3, 11),
    ("Quote", 7, 3, 3, 12),
    ("Enter", 7, 4, 3, 13),
    ("Num4", 12, 2, 3, 19),
    ("Num5", 12, 7, 3, 20),
    ("Num6", 13, 3, 3, 21),
    ("LShift", 8, 0, 4, 0),
    ("Z", 8, 1, 4, 2),
    ("X", 8, 2, 4, 3),
    ("C", 8, 3, 4, 4),
    ("V", 8, 4, 4, 5),
    ("B", 8, 5, 4, 6),
    ("N", 8, 6, 4, 7),
    ("M", 8, 7, 4, 8),
    ("Comma", 9, 0, 4, 9),
    ("Period", 9, 1, 4, 10),
    ("Slash", 9, 2, 4, 11),
    ("RShift", 9, 3, 4, 12),
    ("Up", 9, 6, 4, 16),
    ("Num1", 12, 3, 4, 19),
    ("Num2", 13, 0, 4, 20),
    ("Num3", 13, 4, 4, 21),
    ("NumEnter", 14, 3, 4, 22),
    ("LCtrl", 10, 0, 5, 0),
    ("LWin", 10, 1, 5, 1),
    ("LAlt", 10, 2, 5, 2),
    ("Space", 10, 5, 5, 6),
    ("RAlt", 11, 0, 5, 11),
    ("RWin", 11, 1, 5, 12),
    ("Menu", 11, 2, 5, 13),
    ("RCtrl", 11, 3, 5, 14),
    ("Left", 11, 6, 5, 15),
    ("Down", 11, 7, 5, 16),
    ("Right", 9, 7, 5, 17),
    ("Num0", 12, 4, 5, 19),
    ("NumDecimal", 13, 5, 5, 21),
]
KEY_INDEX = {k[0]: i for i, k in enumerate(KEYS)}


def find_path():
    """Путь к RGB-интерфейсу: интерфейс 3 (на Windows — коллекция 0xFF01/0x01)."""
    devs = [d for d in hid.enumerate(VID, PID) if d["interface_number"] == INTERFACE]
    if not devs:
        raise RuntimeError("K500 (интерфейс 3) не найдена")
    for d in devs:
        if d.get("usage_page") == 0xFF01 and d.get("usage") == 0x01:
            return d["path"]
    return devs[0]["path"]


class K500:
    def __init__(self, path=None):
        self.dev = hid.device()
        self.dev.open_path(path or find_path())

    def close(self):
        self.dev.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def send(self, mode, color1=(0, 0, 0), color2=None, color3=None,
             brightness=2, speed=3, keys=None, palette=None):
        """Отправляет одну команду.
        keys    — имена клавиш для customize;
        palette — до 8 цветов RGB для слотов 0..7 (поверх палитры по умолчанию;
                  color1/color2/color3 затем перезаписывают слоты 0/1/2)."""
        buf = bytearray(64)
        buf[0x00] = 0x01
        buf[0x01] = mode
        buf[0x02] = max(0, min(2, brightness))
        buf[0x03] = max(0, min(3, speed))
        buf[0x10:0x10 + len(DEFAULT_PALETTE)] = DEFAULT_PALETTE
        for i, rgb in enumerate((palette or [])[:8]):
            buf[0x10 + 4 * i:0x13 + 4 * i] = bytes(rgb)
        if palette is None or color1 != (0, 0, 0):
            buf[0x10:0x13] = bytes(color1)
        if color2 is not None:
            buf[0x14:0x17] = bytes(color2)
        if color3 is not None:
            buf[0x18:0x1B] = bytes(color3)
        if keys:
            for name in keys:
                _, byte, bit, _, _ = KEYS[KEY_INDEX[name]]
                buf[0x30 + byte] |= 1 << bit
        # report ID 0 первым байтом, как в OpenRGB
        self.dev.send_feature_report(b"\x00" + FEATURE)
        n = self.dev.write(b"\x00" + bytes(buf))
        if n < 0:
            raise IOError("hid write failed")

    def static(self, rgb, brightness=2):
        self.send(MODE_STATIC, rgb, brightness=brightness)

    def custom(self, rgb, keys, brightness=2):
        """Горят только клавиши keys, все одним цветом rgb; остальные выключены."""
        self.send(MODE_CUSTOMIZE, rgb, brightness=brightness, keys=keys)

    def starlight_dual(self, rgb1, rgb2, speed=0, brightness=2):
        self.send(MODE_STARLIGHT_DUAL, rgb1, rgb2, speed=speed, brightness=brightness)
