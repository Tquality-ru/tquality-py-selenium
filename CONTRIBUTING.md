# Руководство для контрибьюторов

## Требования

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) для управления окружением и зависимостями

## Настройка окружения

```bash
uv sync
```

Команда создаст `.venv/` и установит зависимости проекта плюс dev-группу
(mypy, pytest).

## Установка git-хуков

Для автоматической проверки типов mypy перед каждым коммитом выполните:

```bash
./scripts/install-hooks.sh
```

## Стиль кода

- Все комментарии, docstring, сообщения логов - на русском языке.
- Не используйте m-тире (длинное тире). Используйте обычное тире или
  переформулируйте.
- Не добавляйте строку `Co-Authored-By` в commit-сообщения.

## Формат commit-сообщений

Каждый коммит начинается с одного или нескольких тегов в квадратных скобках
(на английском), затем краткое описание на русском языке.

### Доступные теги

- `[{module}]` - название затронутого модуля: `[Config]`, `[Browser]`, `[Elements]`, `[Container]`, `[CI]`
- `[Docs]` - изменения документации
- `[Fix]` - исправление бага без привязки к issue
- `[Fix #{issueId}]` - исправление бага по конкретному issue
- `[Style]` - только форматирование
- `[Feature]` - новая функциональность

### Примеры

```
[Browser] Поддержка запуска Firefox в headless-режиме
[Elements][Feature] Добавлен класс Select для выпадающих списков
[Fix #7] Исправлен stale element в type_text
[CI] Добавлен job проверки pylint
```

## Проверка типов

```bash
uv run mypy
```

Ошибки типов блокируют merge в master.

## Запуск тестов

```bash
uv run pytest -v
```

Тесты запускаются автоматически в CI на каждый MR.

## Сборка пакета

```bash
uv build
```

## Релиз

Релиз триггерится git-тегом вида `vX.Y.Z`:

```bash
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0
```

CI-джоб `mirror-to-github` зеркалирует репозиторий в
https://github.com/Tquality-ru/tquality-py-selenium.

### Настройка зеркалирования (однократно)

1. Создать GitHub Personal Access Token с правами `public_repo`.
2. В GitLab: **Settings → CI/CD → Variables** добавить переменную:
   - Key: `GITHUB_MIRROR_TOKEN`
   - Value: токен с GitHub
   - Protected: yes
   - Masked: yes

## Структура репозитория

```
tquality-py-selenium/
├── .gitlab-ci.yml          # CI: mypy + pytest на MR и master, зеркалирование на тег
├── pyproject.toml          # конфиг проекта, mypy, зависимости (core - git-зависимость)
├── scripts/
│   └── install-hooks.sh
├── src/tquality_selenium/
│   ├── browser.py          # BrowserService, is_browser_started
│   ├── config.py           # SeleniumConfig, BrowserType
│   ├── container.py        # DI-контейнер, wire_core_integrations()
│   ├── screenshot_provider.py
│   ├── elements/
│   │   ├── base_element.py # концретный BaseElement поверх core.BaseElement
│   │   ├── button.py
│   │   ├── checkbox.py
│   │   ├── input.py
│   │   └── label.py
│   └── pages/              # реэкспорт BaseForm из ядра
├── tests/
└── README.md
```
