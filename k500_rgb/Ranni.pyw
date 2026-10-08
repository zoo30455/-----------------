"""
Ranni — знаки Ранни Ведьмы на клавиатуре Lenovo Legion K500.

Один файл. Запуск: двойной щелчок (откроется окно) или из консоли:
    python Ranni.pyw            — окно
    python Ranni.pyw moon       — сразу поставить знак без окна

Знаки: moon, blade, hat, ring, stars, night, frost, moonlight, rise, sorcery.
Перед запуском закройте Lenovo Legion Accessory Central.

Протокол подтверждён драйвером OpenRGB (LenovoK500Controller) и USB-захватами
официального приложения. Клавиатура запоминает каждую команду, поэтому каждый
знак — ровно одна команда: поставили и забыли, он сохранится и после перезагрузки.
"""
import json
import os
import subprocess
import sys

# ============================ протокол K500 ============================

VID, PID, INTERFACE = 0x17EF, 0x60D5, 3
FEATURE = bytes([0x14, 0x00, 0x5A, 0x00, 0x00, 0x00, 0x00, 0x00])
DEFAULT_PALETTE = bytes([
    0xff, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0x00,
    0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00,
    0xff, 0x00, 0xff, 0x00, 0xff, 0xff, 0x00, 0x00,
    0x00, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00,
])
STATIC, SPIRAL, DRIFTING, FADING_TRACE, CUSTOMIZE, BREATHING, STARLIGHT, STARLIGHT_DUAL = \
    0x01, 0x02, 0x04, 0x05, 0x06, 0x07, 0x09, 0x0A

# (имя, байт маски, бит, ряд, колонка) — проверено по захвату, 104 из 104
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
KEY = {k[0]: k for k in KEYS}
GRID = {(k[3], k[4]): k[0] for k in KEYS}


def packet(mode, color=(0, 0, 0), color2=None, palette=None, keys=(), brightness=2, speed=0):
    buf = bytearray(64)
    buf[0], buf[1], buf[2], buf[3] = 0x01, mode, brightness, speed
    buf[0x10:0x30] = DEFAULT_PALETTE
    for i, rgb in enumerate(palette or []):
        buf[0x10 + 4 * i:0x13 + 4 * i] = bytes(rgb)
    if palette is None:
        buf[0x10:0x13] = bytes(color)
    if color2 is not None:
        buf[0x14:0x17] = bytes(color2)
    for name in keys:
        _, byte, bit, _, _ = KEY[name]
        buf[0x30 + byte] |= 1 << bit
    return bytes(buf)


def send(payload):
    """Открывает клавиатуру, отправляет одну команду, закрывает."""
    import hid
    devs = [d for d in hid.enumerate(VID, PID) if d["interface_number"] == INTERFACE]
    if not devs:
        raise RuntimeError("Клавиатура Lenovo Legion K500 не найдена")
    path = next((d["path"] for d in devs if d.get("usage_page") == 0xFF01 and d.get("usage") == 1),
                devs[0]["path"])
    dev = hid.device()
    dev.open_path(path)
    try:
        dev.send_feature_report(b"\x00" + FEATURE)
        if dev.write(b"\x00" + payload) < 0:
            raise IOError("не удалось отправить команду")
    finally:
        dev.close()

# ============================ знаки Ранни ============================

NIGHT = (0x00, 0x1E, 0xFF)
SNOW = (0xB4, 0xF0, 0xFF)
MOON_ICE = (0x8C, 0xDC, 0xFF)
FROST = (0x50, 0xC8, 0xFF)
BLADE = (0x78, 0xD2, 0xFF)
MOONLIGHT = [(0x00, 0x1E, 0xFF), (0x00, 0x50, 0xFF), (0x00, 0x8C, 0xFF), (0x3C, 0xC8, 0xFF),
             (0x9C, 0xF0, 0xFF), (0x3C, 0xC8, 0xFF), (0x00, 0x8C, 0xFF), (0x00, 0x50, 0xFF)]
LEADEN = [(0x28, 0x3C, 0xC8), (0x46, 0x5A, 0xDC), (0x6E, 0x8C, 0xFF), (0xA0, 0xC8, 0xFF),
          (0x6E, 0x8C, 0xFF), (0x46, 0x5A, 0xDC), (0x28, 0x3C, 0xC8), (0x1E, 0x28, 0xA0)]


def cells(*rc):
    return [GRID[c] for c in rc if c in GRID]


def halo(cx, cy, rx, ry, lo, hi):
    return [k[0] for k in KEYS if lo <= (((k[4] - cx) / rx) ** 2 + ((k[3] - cy) / ry) ** 2) ** 0.5 <= hi]


# ключ: (название, описание, цвет для схемы, клавиши рисунка или None, параметры команды)
SIGNS = {
    "moon": ("Тёмная Луна", "Её знак — холодная, свинцовая луна. Ледяной ореол вокруг тёмного диска.",
             MOON_ICE, halo(6.5, 2.0, 3.3, 2.0, 0.72, 1.18), dict(mode=CUSTOMIZE, color=MOON_ICE)),
    "blade": ("Меч Тёмной Луны", "«Лишь луч её света» — клинок с гардой и рукоятью.",
              BLADE, cells((0, 7), (0, 8), (1, 8), (1, 9), (2, 9), (2, 10), (3, 10), (3, 11),
                           (4, 12), (3, 13), (5, 11), (5, 13)), dict(mode=CUSTOMIZE, color=BLADE)),
    "hat": ("Шляпа Снежной ведьмы", "Огромная заиндевевшая шляпа куклы, в которой живёт Ранни.",
            SNOW, cells((0, 9), (0, 10), (1, 8), (1, 9), (2, 7), (2, 8), (3, 6), (3, 7), (3, 8), (3, 9),
                        *[(4, c) for c in range(2, 13)]), dict(mode=CUSTOMIZE, color=SNOW)),
    "ring": ("Кольцо Тёмной Луны", "Кольцо, которое она примет от Погасшего. Вокруг клавиши R.",
             MOON_ICE, cells((1, 4), (1, 5), (1, 6), (2, 4), (2, 6), (3, 4), (3, 5), (3, 6)),
             dict(mode=CUSTOMIZE, color=MOON_ICE)),
    "stars": ("Эра Звёзд", "Её цель — холодная, далёкая эпоха под светом луны и звёзд.",
              SNOW, cells((0, 3), (1, 8), (2, 12), (3, 6), (0, 13), (4, 10), (2, 2), (1, 15), (3, 20),
                          (0, 18), (4, 4), (2, 21)), dict(mode=CUSTOMIZE, color=SNOW)),
    "night": ("Ночь Эры Звёзд", "Живой: снежные звёзды мерцают на глубокой синеве.",
              SNOW, None, dict(mode=STARLIGHT_DUAL, color=NIGHT, color2=SNOW)),
    "frost": ("Дыхание Снежной ведьмы", "Живой: вся клавиатура медленно дышит льдом.",
              FROST, None, dict(mode=BREATHING, color=FROST)),
    "moonlight": ("Лунный свет", "Живой: оттенки плывут от ночной синевы к снегу и обратно.",
                  (0x3C, 0xC8, 0xFF), None, dict(mode=DRIFTING, palette=MOONLIGHT)),
    "rise": ("Восход Тёмной Луны", "Живой: свинцово-серебряная спираль раскручивается из центра.",
             (0x6E, 0x8C, 0xFF), None, dict(mode=SPIRAL, palette=LEADEN)),
    "sorcery": ("Холодное колдовство", "Живой: каждое нажатие оставляет ледяной след.",
                FROST, None, dict(mode=FADING_TRACE, color=FROST, speed=1)),
}

SETTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ranni_settings.json")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(s):
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def apply_sign(key, brightness=2, alive=False):
    name, _, _, keys, cmd = SIGNS[key]
    cmd = dict(cmd)
    mode = cmd.pop("mode")
    if keys is not None and alive:
        mode = BREATHING          # прошивка учитывает маску — рисунок дышит
    send(packet(mode, keys=keys or (), brightness=brightness, **cmd))
    return name


def ensure_hidapi(ask):
    try:
        import hid  # noqa: F401
        return True
    except ImportError:
        pass
    if not ask("Нужна библиотека hidapi. Установить её сейчас (pip install hidapi)?"):
        return False
    exe = sys.executable.replace("pythonw.exe", "python.exe")
    r = subprocess.run([exe, "-m", "pip", "install", "hidapi"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("Не удалось установить hidapi:\n" + (r.stderr or r.stdout)[-800:])
    import importlib
    importlib.invalidate_caches()
    import hid  # noqa: F401
    return True

# ============================ окно ============================


def run_gui():
    import tkinter as tk
    from tkinter import messagebox

    BG, PANEL, TEXT, MUTED, ACCENT = "#07080f", "#10131f", "#dce8ff", "#7d8aa8", "#8cdcff"
    settings = load_settings()

    root = tk.Tk()
    root.title("Ранни — знаки на клавиатуре")
    root.configure(bg=BG)
    root.resizable(False, False)

    tk.Label(root, text="Знаки Ранни", bg=BG, fg=ACCENT, font=("Georgia", 20, "italic")).pack(pady=(14, 0))
    tk.Label(root, text="Нажмите на знак — он появится на клавиатуре и останется на ней",
             bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(pady=(2, 10))

    cell, pad = 26, 3
    canvas = tk.Canvas(root, width=23 * cell + 16, height=6 * cell + 16, bg=PANEL, highlightthickness=0)
    canvas.pack(padx=16)
    caption = tk.Label(root, text="", bg=BG, fg=TEXT, font=("Segoe UI", 11), wraplength=620, justify="center")
    caption.pack(pady=(8, 6))

    def hexc(rgb):
        return "#%02x%02x%02x" % rgb

    def draw(key):
        name, desc, color, keys, cmd = SIGNS[key]
        canvas.delete("all")
        lit = set(keys) if keys is not None else None
        for k in KEYS:
            r, c = k[3], k[4]
            x, y = 8 + c * cell, 8 + r * cell
            if lit is None:
                fill = hexc(color) if (r * 7 + c * 3) % 5 == 0 else "#1b2340"   # живой: намёк на эффект
            else:
                fill = hexc(color) if k[0] in lit else "#161a28"
            canvas.create_rectangle(x, y, x + cell - pad, y + cell - pad, fill=fill, outline="")
        caption.config(text=f"{name}\n{desc}")

    grid = tk.Frame(root, bg=BG)
    grid.pack(padx=16, pady=4)
    status = tk.Label(root, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10))

    bright = tk.IntVar(value=settings.get("brightness", 2))

    def ask(q):
        return messagebox.askyesno("Ранни", q, parent=root)

    def choose(key):
        draw(key)
        try:
            if not ensure_hidapi(ask):
                return
            name = apply_sign(key, bright.get(), settings.get("alive", False))
            settings["last"] = key
            settings["brightness"] = bright.get()
            save_settings(settings)
            status.config(text=f"Поставлено: {name}", fg=ACCENT)
        except Exception as e:  # noqa: BLE001
            status.config(text="Ошибка", fg="#ff8c8c")
            messagebox.showerror("Ранни", f"{e}\n\nЗакройте Lenovo Legion Accessory Central и проверьте USB.",
                                 parent=root)

    for i, key in enumerate(SIGNS):
        name, _, color, keys, _ = SIGNS[key]
        b = tk.Button(grid, text=("✦ " if keys is None else "◆ ") + name, width=24, anchor="w",
                      bg=PANEL, fg=TEXT, activebackground="#1d2440", activeforeground=ACCENT,
                      relief="flat", font=("Segoe UI", 10), padx=10, pady=6,
                      command=lambda k=key: choose(k))
        b.grid(row=i % 5, column=i // 5, padx=4, pady=3)
        b.bind("<Enter>", lambda e, k=key: draw(k))

    bottom = tk.Frame(root, bg=BG)
    bottom.pack(pady=(8, 4))
    tk.Label(bottom, text="◆ рисунок   ✦ живой эффект      Яркость:", bg=BG, fg=MUTED,
             font=("Segoe UI", 9)).pack(side="left")
    for v, t in ((1, "тише"), (2, "ярче")):
        tk.Radiobutton(bottom, text=t, variable=bright, value=v, bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, font=("Segoe UI", 9)).pack(side="left", padx=4)

    def test_mask():
        if not ask("Проверка «живых рисунков»: клавиатура получит 1 команду — ореол Тёмной Луны "
                   "в режиме дыхания. Продолжить?"):
            return
        try:
            if not ensure_hidapi(ask):
                return
            _, _, color, keys, _ = SIGNS["moon"]
            send(packet(BREATHING, color, keys=keys, brightness=bright.get(), speed=1))
            settings["alive"] = ask("Дышит ТОЛЬКО кольцо Тёмной Луны, а остальные клавиши тёмные?")
            save_settings(settings)
            status.config(text="Рисунки будут дышать" if settings["alive"] else "Рисунки остаются неподвижными",
                          fg=ACCENT)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Ранни", str(e), parent=root)

    tk.Button(bottom, text="Проверить живые рисунки", command=test_mask, bg=PANEL, fg=MUTED,
              relief="flat", font=("Segoe UI", 9), padx=8).pack(side="left", padx=(16, 0))
    status.pack(pady=(4, 14))

    draw(settings.get("last", "moon"))
    root.mainloop()


def main():
    if len(sys.argv) > 1:
        key = sys.argv[1].lower()
        if key not in SIGNS:
            print("Знаки:", ", ".join(SIGNS))
            sys.exit(1)
        s = load_settings()
        ensure_hidapi(lambda q: input(q + " [y/n]: ").strip().lower() in ("y", "д"))
        print("Поставлено:", apply_sign(key, s.get("brightness", 2), s.get("alive", False)))
        return
    run_gui()


if __name__ == "__main__":
    main()
