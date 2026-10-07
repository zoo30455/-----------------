# Objection! 2001 everywhere — мод для Ace Attorney Trilogy (PC)

Заменяет «Objection! 2002» (AA2: Justice for All) и «Objection! 2004» (AA3: Trials and Tribulations)
на «Objection! 2001» из первой игры.

## Установка
1. Нужен Python 3.8+.
2. Посмотрите, как называются музыкальные файлы в вашей версии игры:
   `python objection_mod.py list "C:\...\Phoenix Wright Ace Attorney Trilogy"`
3. Впишите в `config.json` путь к Objection из AA1 (`SOURCE`) и к Objection из AA2/AA3 (`TARGETS`).
   Те имена, что там сейчас, — пример: сверьте их с выводом `list`.
4. `python objection_mod.py install "<путь к игре>"`

## Удаление
`python objection_mod.py restore "<путь к игре>"` — вернёт оригиналы из бэкапов `*.orig`.
Ещё можно сделать в Steam «Проверить целостность файлов».

Если трек хранится в общем архиве (`.unity3d`/`.acb`), а не отдельным файлом, сначала
распакуйте его (AssetStudio / UABEA / VGMToolbox), подмените трек и запакуйте обратно.
