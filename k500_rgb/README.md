# K500 RGB из Python

**Главное — `ranni_signs.py`: знаки Ранни** (Тёмная Луна, Меч Тёмной Луны, шляпа
Снежной ведьмы, Кольцо, Эра Звёзд и живые эффекты). Каждый знак — одна команда,
клавиатура его запоминает. Рисунки — `ranni_signs.png`.

```
python ranni_signs.py --preview
python ranni_signs.py --tour
python ranni_signs.py moon
```

```
pip install hidapi
python k500_test.py      # пошаговый тест
python ranni.py          # эффект Ranni (программная анимация)
python ranni.py --hw     # аппаратный Starlight Dual, одна команда
python k500_explore.py   # разведка: какие режимы прошивки берут свою палитру
python ranni_v4.py       # «Ночь Ранни»: эффекты прошивки в цветах Ранни
```

python ranni_v6.py       # яркие эффекты прошивки в цветах Ранни, клавиатура горит постоянно
python k500_limits.py    # проверка памяти и скорости клавиатуры
python ranni_live.py     # свои узоры: фон, волна, круги, звёзды, вихрь Тёмной Луны
python ranni_live.py --preview   # то же в консоли, без клавиатуры
```

`ranni_live.py` раскладывает каждый кадр на 2–3 цветовые группы и быстро их
чередует — глаз видит разные цвета на клавишах одновременно. Включается, только
если `k500_limits.py` показал, что клавиатура не запоминает цвет (иначе частые
команды изнашивали бы её память) и не мерцает.

```
 анимацию рисует сама клавиатура (плавно и с разными
цветами на клавишах), скрипт только переключает сцены. Подмена палитры в
многоцветных режимах не подтверждена захватами — её проверяет `k500_explore.py`.

Перед запуском закройте Lenovo Legion Accessory Central.
Протокол и источники — в `PROTOCOL.md`.

## Разбор legion_hid.exe (на вашем ПК)

```
dotnet tool install -g ilspycmd
ilspycmd -p -o legion_src "C:\Program Files (x86)\Lenovo\Legion Accessory Central\legion_hid.exe"
findstr /s /i /m "K500Extra KeyMatrix SyncPacket Switch_Effect" legion_src\*.cs
```

Пришлите найденные .cs-файлы с этими классами — по ним можно проверить, есть ли команды кроме описанных в `PROTOCOL.md`.
