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

- `[{module}]` - название затронутого модуля: `[Config]`, `[Browser]`,
  `[Elements]`, `[Services]`, `[Container]`, `[Reporting]`, `[CI]`
- `[Docs]` - изменения документации
- `[Fix]` - исправление бага без привязки к issue
- `[Fix #{issueId}]` - исправление бага по конкретному issue
- `[Style]` - только форматирование
- `[Feature]` - новая функциональность

### Примеры

```
[Browser] Поддержка запуска Firefox в headless-режиме
[Elements][Feature] Добавлен класс Select для выпадающих списков
[Services][Feature] CollectionFactory: поддержка XPath-полей
[Reporting][Feature] page_source прикрепляется к allure при падении теста
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

Job `tests:macos-browsers-healthcheck` запускает smoke-тесты всех 5 браузеров
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

Push тега `vX.Y.Z` триггерит три CI-джоба в stage `release`:

- **`publish-pypi`** - сборка (`uv build` получает версию из тега через
  `hatch-vcs`) и публикация пакета в публичный
  [PyPI](https://pypi.org/project/tquality-py-selenium/). Это основной канал
  установки для всех потребителей.
- **`publish`** - дублирующая публикация в GitLab Package Registry
  (`https://git.tquality.ru/frameworks/python/tquality-py-selenium/-/packages`)
  как внутреннее зеркало.
- **`mirror-to-github`** - пушит `master` и сам тег в
  https://github.com/Tquality-ru/tquality-py-selenium (feature-ветки и
  служебные refs не зеркалируются).

### Настройка публикации в PyPI (однократно)

1. На https://pypi.org/manage/account/token/ создать API-токен со
   scope, ограниченным проектом `tquality-py-selenium` (после первой
   ручной публикации). Для самой первой публикации нужен токен с
   глобальным scope.
2. В GitLab: **Settings → CI/CD → Variables** добавить переменную:
   - Key: `PYPI_TOKEN`
   - Value: токен с PyPI (включая префикс `pypi-`)
   - Protected: yes (только для protected refs, включая теги `v*`)
   - Masked: yes

### Установка пакета из GitLab Package Registry (внутренний канал)

```bash
uv pip install tquality-py-selenium \
  --index-url "https://gitlab-ci-token:${GITLAB_TOKEN}@git.tquality.ru/api/v4/projects/43/packages/pypi/simple"
```

Либо добавьте в `pyproject.toml` консьюмера:

```toml
[[tool.uv.index]]
name = "tquality"
url = "https://git.tquality.ru/api/v4/projects/43/packages/pypi/simple"
explicit = true

[tool.uv.sources]
tquality-py-selenium = { index = "tquality" }
```

### Настройка зеркалирования в GitHub (однократно)

1. Создать GitHub Personal Access Token с правами `public_repo` (или `repo`
   для приватных).
2. В GitLab: **Settings → CI/CD → Variables** добавить переменную:
   - Key: `GITHUB_MIRROR_TOKEN`
   - Value: токен с GitHub
   - Protected: yes (только для protected refs, включая теги `v*`)
   - Masked: yes

Для публикации в Package Registry дополнительная настройка не нужна: джоб
использует встроенный `CI_JOB_TOKEN`.

## Структура репозитория

```
tquality-py-selenium/
├── .gitlab-ci.yml             # CI: mypy + pytest, на тег - publish-pypi/publish/mirror-to-github
├── pyproject.toml             # конфиг проекта, mypy, зависимости (core - с PyPI)
├── schema/
│   └── config.schema.json     # JSON-схема SeleniumConfig (публикуется через jsDelivr)
├── scripts/
│   └── install-hooks.sh
├── src/tquality_selenium/
│   ├── browser.py             # BrowserService, is_browser_started
│   ├── cli.py                 # CLI: tquality-selenium-config init / schema
│   ├── config.py              # SeleniumConfig, BrowserType
│   ├── container.py           # SeleniumServices (composition root, setup())
│   ├── os_utils.py            # OSUtils: карта поддержки браузеров ОС
│   ├── page_source_plugin.py  # pytest-плагин: page_source -> allure при падении
│   ├── schema.py              # генератор JSON-схемы для SeleniumConfig
│   ├── screencast_provider.py # webm-видеозапись шага (BiDi -> CDP -> screenshot)
│   ├── screenshot_provider.py # снимок экрана для CRITICAL-шагов
│   ├── elements/
│   │   ├── base_element.py    # BaseElement (DI-резолверы, локатор как By)
│   │   ├── button.py
│   │   ├── by.py              # By NamedTuple + ByKind str-Enum (own типы локаторов)
│   │   ├── checkbox.py
│   │   ├── input.py
│   │   └── label.py
│   ├── pages/                 # BaseForm (с element_factory из контейнера)
│   └── services/
│       ├── collection_factory.py # фабрика коллекций Pydantic-моделей из DOM
│       ├── element_factory.py    # фабрика типизированных элементов
│       ├── element_waiter.py     # explicit waits по локатору
│       ├── js_actions.py         # JsActions + ElementJsActions
│       └── waiter.py             # обертка над WebDriverWait
├── tests/
├── README.md                  # английский (по умолчанию для PyPI)
├── README.ru.md               # русский
└── CHANGELOG.md
```
