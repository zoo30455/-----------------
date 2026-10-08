import re, sys
sys.path.insert(0, sys.argv[3])
from usbdump import packets
# порядок клавиш из README захвата
order = """ESC F1 F2 F3 F4 F5 F6 F7 F8 F9 F10 F11 F12 PrtSc ScrollLock Pause
Grave 1 2 3 4 5 6 7 8 9 0 Minus Equal Backspace Insert Home PgUp NumLock NumSlash NumAsterisk NumMinus
Tab Q W E R T Y U I O P LBracket RBracket Backslash Delete End PgDn Num7 Num8 Num9 NumPlus
CapsLock A S D F G H J K L Semicolon Quote Enter Num4 Num5 Num6
LShift Z X C V B N M Comma Period Slash RShift Up Num1 Num2 Num3 NumEnter
LCtrl LWin LAlt Space RAlt RWin Menu RCtrl Left Down Right Num0 NumDecimal""".split()
# таблица OpenRGB
src = open(sys.argv[2]).read()
tbl = re.findall(r'\{(\d+), (\d+)\}, // (\S+)', src)
openrgb = {name: (int(b), int(i)) for b, i, name in tbl}
masks = []
for ts, resp, ep, tt, p in packets(sys.argv[1]):
    if not resp and tt == 1 and ep == 4 and p[1] == 6:
        masks.append(int.from_bytes(p[0x30:0x40], 'little'))
seen, new_bits = 0, []
for m in masks:
    added = m & ~seen
    if added:
        bits = [b for b in range(128) if added >> b & 1]
        new_bits.append(bits)
    seen |= m
print('пакетов customize:', len(masks), ' нажатий с новым битом:', len(new_bits), ' клавиш в README:', len(order))
bad = 0
for name, bits in zip(order, new_bits):
    exp = openrgb.get(name)
    got = [(b // 8, b % 8) for b in bits]
    if [exp] != got:
        bad += 1
        print('НЕ СОВПАЛО', name, 'openrgb', exp, 'capture', got)
print('расхождений:', bad)
print('все биты в итоговой маске:', bin(seen).count('1'))
