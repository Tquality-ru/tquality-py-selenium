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

## CI/CD

### На каждом MR и на master

- **`mypy`** - строгий режим проверки типов.
- **`tests:linux`** - юнит-тесты pytest без настоящих браузеров
  (default uv+python image, фильтр `-m "not macos"`).
- **`tests:linux-browsers-healthcheck`** - chrome, firefox, edge,
  undetected-chrome на linux-runner'е. Использует образ
  `selenium/standalone-all-browsers:latest` с запечёнными браузерами
  и драйверами. `allow_failure: true`.
- **`tests:macos-browsers-healthcheck`** - все 5 браузеров (chrome,
  firefox, edge, safari, undetected-chrome) на macos-runner'е.
  `allow_failure: true`.
- **`tests:windows-browsers-healthcheck`** - chrome, firefox, edge,
  undetected-chrome на windows-runner'е. `allow_failure: true`.

`allow_failure: true` на browsers-healthcheck значит, что временная
недоступность runner'а не валит весь pipeline.

### Windows-runner

Установить gitlab-runner под реальным локальным пользователем (не
`LocalSystem`) - headless Edge требует desktop-сессию, а сервис под
`LocalSystem` запускается в Session 0 и Edge падает с
`DevToolsActivePort file doesn't exist`. Установка через `services.msc`
→ gitlab-runner → Properties → Log On → "This account".

Включить long-path support для глубоких build-путей uv:

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
git config --system core.longpaths true
Restart-Service gitlab-runner
```

### macOS-runner

При зависании Selenium Manager / Chrome `--version` (симптом - тесты
упираются в `pytest-timeout`/2h, sample-стек показывает `_dyld_start`
или `poll()` без прогресса) обычно помогает рестарт code-signing
демонов:

```bash
sudo killall amfid syspolicyd
```

Daemons стартуют заново, dyld перестаёт зависать на signature-
верификации, Chrome `--version` отрабатывает за <1s.

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
│   ├── page_source_plugin.py  # pytest-плагин: page_source -> allure при падении
│   ├── schema.py              # генератор JSON-схемы для SeleniumConfig
│   ├── screencast_provider.py # webm-видеозапись шага (BiDi -> CDP -> screenshot)
│   ├── screenshot_provider.py # снимок экрана для CRITICAL-шагов
│   ├── elements/
│   │   ├── base_element.py    # BaseElement (DI-резолверы, локатор как By, element.wait)
│   │   ├── button.py
│   │   ├── by.py              # By NamedTuple + ByKind str-Enum + By.to_xpath()
│   │   ├── checkbox.py
│   │   ├── input.py
│   │   └── label.py
│   ├── pages/                 # BaseForm (с element_factory из контейнера)
│   ├── services/
│   │   ├── collection_factory.py # фабрика коллекций Pydantic-моделей из DOM
│   │   ├── element_factory.py    # фабрика типизированных элементов + get_child_*
│   │   ├── element_waiter.py     # ElementWaiter[E]: per-element waits (element.wait)
│   │   ├── js_actions.py         # JsActions + ElementJsActions
│   │   └── waiter.py             # обертка над WebDriverWait
│   └── utils/
│       ├── locator_utils.py   # LocatorUtils: normalize_xpath, join_xpath
│       └── os_utils.py        # OSUtils: карта поддержки браузеров ОС
├── tests/
├── README.md                  # английский (по умолчанию для PyPI)
├── README.ru.md               # русский
└── CHANGELOG.md
```
