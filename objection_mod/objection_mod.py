#!/usr/bin/env python3
"""
Мод для Phoenix Wright: Ace Attorney Trilogy (PC/Steam).
Заменяет все темы "Objection!" (AA2 "Objection! 2002", AA3 "Objection! 2004")
на "Objection! 2001" из первой игры.

Использование:
  python objection_mod.py list    [путь_к_игре]   - показать все аудиофайлы игры
  python objection_mod.py install [путь_к_игре]   - установить мод (с бэкапом)
  python objection_mod.py restore [путь_к_игре]   - вернуть оригиналы

Имена файлов задаются в config.json (SOURCE и TARGETS).
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
BACKUP_SUFFIX = ".orig"
AUDIO_EXT = {".ogg", ".wav", ".acb", ".awb", ".bin", ".bytes", ".unity3d", ".bank"}
DEFAULT_GAME_DIRS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Phoenix Wright Ace Attorney Trilogy",
    "~/.steam/steam/steamapps/common/Phoenix Wright Ace Attorney Trilogy",
    "~/.local/share/Steam/steamapps/common/Phoenix Wright Ace Attorney Trilogy",
]


def find_game(arg):
    candidates = [arg] if arg else DEFAULT_GAME_DIRS
    for c in candidates:
        p = Path(c).expanduser()
        if p.is_dir():
            return p
    sys.exit("Папка игры не найдена. Укажите путь: python objection_mod.py install \"<путь>\"")


def load_config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    return cfg["SOURCE"], cfg["TARGETS"]


def locate(game, rel):
    """Ищет файл по относительному пути или, если не найден, по имени во всей папке игры."""
    p = game / rel
    if p.is_file():
        return p
    hits = [h for h in game.rglob(Path(rel).name) if not h.name.endswith(BACKUP_SUFFIX)]
    return hits[0] if hits else None


def cmd_list(game):
    files = sorted(f for f in game.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXT)
    for f in files:
        print(f"{f.stat().st_size:>12,}  {f.relative_to(game)}")
    print(f"\nВсего: {len(files)}")


def cmd_install(game):
    source_rel, targets = load_config()
    src = locate(game, source_rel)
    if not src:
        sys.exit(f"Не найден исходный файл Objection 2001: {source_rel}")
    # Берём оригинал источника, если он сам вдруг был заменён ранее
    src_backup = src.with_name(src.name + BACKUP_SUFFIX)
    data_src = src_backup if src_backup.exists() else src
    for rel in targets:
        dst = locate(game, rel)
        if not dst:
            print(f"[пропуск] не найден: {rel}")
            continue
        if dst.resolve() == src.resolve():
            continue
        backup = dst.with_name(dst.name + BACKUP_SUFFIX)
        if not backup.exists():
            shutil.copy2(dst, backup)
        shutil.copy2(data_src, dst)
        print(f"[ok] {dst.relative_to(game)}  <-  {src.name}")
    print("Готово. OBJECTION!")


def cmd_restore(game):
    n = 0
    for backup in game.rglob("*" + BACKUP_SUFFIX):
        orig = backup.with_name(backup.name[: -len(BACKUP_SUFFIX)])
        shutil.move(str(backup), orig)
        print(f"[восстановлен] {orig.relative_to(game)}")
        n += 1
    print(f"Восстановлено файлов: {n}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("list", "install", "restore"):
        sys.exit(__doc__)
    game = find_game(sys.argv[2] if len(sys.argv) > 2 else None)
    {"list": cmd_list, "install": cmd_install, "restore": cmd_restore}[sys.argv[1]](game)


if __name__ == "__main__":
    main()
