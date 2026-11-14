# Отдельные изображения Лизы

Подготовлены встроенным imagegen по пользовательскому листу references/redesign/liza.png. Каждый PNG в public/redesign/liza-*.png содержит одного персонажа на прозрачном фоне; исходный лист больше не кадрируется при воспроизведении.

Общий запрос: один изолированный персонаж Лиза в полный рост; сохранить узнаваемую внешность и стиль рисунка с листа — тёмные волнистые волосы, фиолетовый ободок, жёлтая заколка-звёздочка, большие карие глаза, фиолетовая толстовка и рюкзак, синие джинсы, фиолетово-белые кроссовки. Вся фигура и поля вокруг неё, прозрачный фон, без соседних персонажей, посторонних частей тела, текста, рамок и карточек Лиг.

Отдельные варианты запроса:

- greeting — friendly greeting, smiling, both hands holding backpack straps;
- explaining — thoughtfully explaining, one finger gently near chin;
- waiting — calm neutral smile, relaxed hands holding backpack straps;
- speaking — speaking gently, mouth slightly open, one open hand making an explanatory gesture;
- support — gentle encouraging smile, one hand waving softly;
- completed — happy completion, eyes closed smiling, one small raised fist in celebration.

Переключение осуществляется через src изображения по состоянию помощника. CSS не подменяет старый общий лист. Скрипт tools/redesign-assets.py теперь обновляет только иконки и не перезаписывает эти PNG.
