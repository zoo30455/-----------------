# K500 RGB из Python

```
pip install hidapi
python k500_test.py      # пошаговый тест
python ranni.py          # эффект Ranni (программная анимация)
python ranni.py --hw     # аппаратный Starlight Dual, одна команда
```

Перед запуском закройте Lenovo Legion Accessory Central.
Протокол и источники — в `PROTOCOL.md`.

## Разбор legion_hid.exe (на вашем ПК)

```
dotnet tool install -g ilspycmd
ilspycmd -p -o legion_src "C:\Program Files (x86)\Lenovo\Legion Accessory Central\legion_hid.exe"
findstr /s /i /m "K500Extra KeyMatrix SyncPacket Switch_Effect" legion_src\*.cs
```

Пришлите найденные .cs-файлы с этими классами — по ним можно проверить, есть ли команды кроме описанных в `PROTOCOL.md`.
