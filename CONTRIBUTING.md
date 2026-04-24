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

### Healthcheck браузеров на macOS-runner

Job `tests:macos` запускает smoke-тесты всех 5 браузеров
(`tests/test_browser_healthcheck.py`). Чтобы они проходили, на runner'е
нужна разовая настройка:

1. Установить Google Chrome, Firefox, Microsoft Edge - стандартные dmg/pkg.
2. Включить автоматизацию Safari (требует права администратора):
   ```bash
   sudo safaridriver --enable
   ```
   Дополнительно в самом Safari: **Settings → Developer → Allow Remote
   Automation** (опция появляется после включения меню Develop в
   **Settings → Advanced → Show Develop menu in menu bar**).

Без этих шагов `test_safari_smoke` падает с `SessionNotCreatedException`.

## Обновление JSON-схемы

Схема `schema/config.schema.json` описывает все поля `SeleniumConfig`
(включая унаследованные от `BaseConfig`) и публикуется через jsDelivr:

```
https://cdn.jsdelivr.net/gh/Tquality-ru/tquality-py-selenium@master/schema/config.schema.json
```

Если вы изменили поля `SeleniumConfig`, обновите схему:

```bash
uv run tquality-selenium-config schema
```

Коммит без обновленной схемы провалит тест
`test_committed_schema_matches_selenium_config` в CI.

Для инициализации `config.json5` в чужом проекте со значениями по умолчанию:

```bash
uv run tquality-selenium-config init
```

## Сборка пакета

```bash
uv build
```

## Релиз

Версия пакета берется из последнего git-тега вида `vX.Y.Z` через
`hatch-vcs`. В `pyproject.toml` версия не указывается (поле `dynamic`),
поэтому рассинхронизация тега и пакета невозможна.

Ставьте тег **только на master** (после merge соответствующего MR).
`mirror-to-github` публикует на GitHub именно то, что на master, и
проверяет, что коммит тега достижим из master. Тег на feature-ветке
провалит зеркалирование.

```bash
git checkout master
git pull
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0
```

Push тега `vX.Y.Z` триггерит два CI-джоба в stage `release`:

- **`publish`** - сборка (`uv build` получает версию из тега через
  `hatch-vcs`) и публикация в GitLab Package Registry
  (`https://git.tquality.ru/frameworks/python/tquality-py-selenium/-/packages`).
- **`mirror-to-github`** - пушит `master` и сам тег в
  https://github.com/Tquality-ru/tquality-py-selenium (feature-ветки и
  служебные refs не зеркалируются).

### Установка из GitLab Package Registry

```toml
[[tool.uv.index]]
name = "tquality"
url = "https://git.tquality.ru/api/v4/projects/43/packages/pypi/simple"
explicit = true

[tool.uv.sources]
tquality-py-selenium = { index = "tquality" }
```

### Настройка зеркалирования (однократно)

1. Создать GitHub Personal Access Token с правами `public_repo`.
2. В GitLab: **Settings → CI/CD → Variables** добавить переменную:
   - Key: `GITHUB_MIRROR_TOKEN`
   - Value: токен с GitHub
   - Protected: yes
   - Masked: yes

Для публикации в Package Registry дополнительная настройка не нужна: джоб
использует встроенный `CI_JOB_TOKEN`.

## Структура репозитория

```
tquality-py-selenium/
├── .gitlab-ci.yml          # CI: mypy + pytest на MR и master, зеркалирование на тег
├── pyproject.toml          # конфиг проекта, mypy, зависимости (core - git-зависимость)
├── schema/
│   └── config.schema.json  # JSON-схема SeleniumConfig (публикуется через jsDelivr)
├── scripts/
│   └── install-hooks.sh
├── src/tquality_selenium/
│   ├── browser.py          # BrowserService, is_browser_started
│   ├── cli.py              # CLI: tquality-selenium-config init / schema
│   ├── config.py           # SeleniumConfig, BrowserType
│   ├── container.py        # DI-контейнер, wire_core_integrations()
│   ├── os_utils.py         # OSUtils: карта поддержки браузеров ОС
│   ├── schema.py           # генератор JSON-схемы для SeleniumConfig
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
