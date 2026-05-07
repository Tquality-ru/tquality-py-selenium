# Changelog

Формат по [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии по
[семантическому версионированию](https://semver.org/lang/ru/).

## [0.1.6] - 2026-05-07

### Добавлено

- `ElementFactory.elements(element_cls, by, name_prefix="")` -
  лениво-резолвимая коллекция типизированных элементов
  (`LazyElements[E]` в `tquality_selenium.services.lazy_elements`,
  наследник `Sequence[E]`). Длина и элементы вычисляются по обращению,
  что позволяет объявлять коллекцию в `__init__` page-object'а до
  загрузки страницы. Каждый элемент получает имя
  `f"{name_prefix} #{i+1}"` (1-based; пустой префикс заменяется именем
  класса). В рамках одной итерации (`for el in coll`,
  `[... for el in coll]`, `to_list()`, `coll[a:b]`) `find_elements`
  вызывается один раз и элементы привязываются к этому snapshot'у -
  это срезает `O(N)` лишних походов в DOM при действиях в цикле.
  Между итерациями кэш не переиспользуется. Индексный доступ `coll[i]`
  всегда live-резолв (берёт N-й узел на момент действия). Метод
  `to_list() -> list[E]` отдаёт полностью резолвленный список с тем же
  кэшированием, что и итерация.
- `SeleniumServices.override_active()` - classmethod-context manager
  для per-context override активного композиционного корня. Реализован
  через `contextvars.ContextVar`, изолирован между тредами и
  asyncio-tasks, не мешает process-wide default'у, выставленному
  `setup()`. Дочерние треды НЕ наследуют override автоматически -
  пробрасывайте через `contextvars.copy_context().run(...)` при
  необходимости.
- Параметр `platform: str | None = None` в
  `OSUtils.is_browser_supported_on_current_os` - явное значение в
  духе `sys.platform` (по умолчанию читается `sys.platform`). Введён
  для тред-безопасности тестов: модуль `sys` шарится между тредами,
  поэтому `monkeypatch.setattr("sys.platform", ...)` не годится.
- `ElementWaiter.until(condition, by, name="", timeout=None, message="")` -
  ожидание произвольного `expected_conditions`-совместимого условия с
  человекочитаемым сообщением (имя/локатор элемента и хвост `message`
  включаются в текст ожидания). Дополняет существующие
  `until_visible/clickable/present/invisible/not_present`: например,
  `EC.text_to_be_present_in_element(by, "Готово")` теперь можно
  передать через единый API, не дублируя `Waiter.until` напрямую.
- `ElementJsActions.get_computed_style(style_property: str | StyleProperty) -> str`
  и `get_computed_styles() -> dict[str, str]` - чтение
  `window.getComputedStyle(...)` через JS. Первая берёт одно свойство
  по имени (или enum-значению), вторая - все computed-свойства одним
  JS-запросом (выгоднее, чем `get_computed_style` в цикле).
- `StyleProperty` (StrEnum) в `tquality_selenium.services.style_property` -
  имена часто запрашиваемых CSS-свойств для удобного автокомплита
  (`DISPLAY`, `OPACITY`, `BACKGROUND_COLOR`, `Z_INDEX`, ...). Передача
  произвольной строки тоже работает - enum опционален.
- `tests/test_container.py` - 13 тестов на DI-контейнер: резолв по
  типу/по супер-классу, расширение и override в подклассах, изоляция
  `override_active` между тредами через `copy_context`, propagation
  через `BaseElement` и `LazyElements`, subprocess-проверки
  process-wide default'а от `setup()`.

### Изменено

- **Внутреннее.** Активный композиционный корень теперь хранится в
  двух уровнях: `_default_services` (process-wide, выставляется
  `setup()`) и `_active_services_ctx: ContextVar` (per-context,
  выставляется `override_active()`). Старая module-level переменная
  `_active_services` заменена. Внешний API без изменений: существующий
  паттерн `ProjectServices.setup()` в `conftest.py` продолжает
  работать как раньше и виден из всех тредов.
- CI: тестовые job'ы (`tests:linux`, `tests:macos-browsers-healthcheck`,
  `tests:linux-browsers-healthcheck`, `tests:windows-browsers-healthcheck`)
  используют `pytest -n auto` для параллелизма по процессам.
- Тесты приведены к thread-safe виду: убрана мутация `sys.platform`
  через `monkeypatch` (используется новый параметр `platform=`),
  env-переменные `TEST_*` устанавливаются только в подпроцессе,
  subprocess-тесты переехали с `pytester.runpytest_subprocess` на
  прямой `subprocess.run([sys.executable, ...], cwd=tmp_path, ...)`
  с явным `cwd=` (pytester полагается на process-global
  `monkeypatch.chdir`, что ломает `pytest-threadpool`-параллелизм).

## [0.1.5] - 2026-05-05

**Первая публикация в публичный [PyPI](https://pypi.org/project/tquality-py-selenium/).**

### Добавлено

- `By` (`NamedTuple`) и `ByKind` (`str`-Enum) в
  `tquality_selenium.elements.by` - собственные типы локаторов с
  классовыми методами `By.id(...)`, `By.xpath(...)`, `By.css_selector(...)`,
  `By.name(...)`, `By.class_name(...)`, `By.tag_name(...)`,
  `By.link_text(...)`, `By.partial_link_text(...)`. `By` прозрачно
  распаковывается в `(str, str)` для selenium благодаря `ByKind` от `str`.
- Английский `README.md` (по умолчанию для PyPI), русский переведен в
  `README.ru.md`. В шапке обоих файлов - переключатель языков.
- Edge помечен поддерживаемым на Linux: Microsoft публикует Edge для
  Linux наравне с macOS/Windows. `OSUtils._BROWSER_OS_SUPPORT[EDGE]`
  расширен до `{linux, darwin, win32}`, `test_edge_smoke` получил
  mark `linux`.
- CI: добавлены job'ы `publish-pypi` (загрузка в PyPI на git-теге
  `vX.Y.Z`, требует `PYPI_TOKEN`), `tests:linux-browsers-healthcheck`
  и `tests:windows-browsers-healthcheck`. Linux-job использует
  `selenium/standalone-all-browsers:latest` - chrome, firefox, edge
  и matching-драйверы запечены в образ, нет зависимости от
  github.com при запуске.
- Dev-зависимость `pytest-timeout>=2.3` + `timeout = 120` в
  `[tool.pytest.ini_options]` - бьёт зависшие тесты thread-таймаутом
  с traceback'ом всех потоков, job не упирается в 2h-timeout
  GitLab.

### Изменено

- **Breaking.** Сигнатура `BaseElement.__init__(by: str, value: str, name="")`
  заменена на `BaseElement(by: By, name="")`. То же для всех подклассов
  (`Button`, `CheckBox`, `Input`, `Label`) и методов `ElementFactory`:
  `element/button/checkbox/label/input(by: By, name="")`.
  Миграция: `Button(By.ID, "submit", "Войти")` →
  `Button(By.id("submit"), "Войти")`.
- **Breaking.** `ElementWaiter.until_visible/clickable/present/invisible/`
  `not_present` теперь принимают единый `By`-локатор вместо
  пары `(by: str, value: str)`.
- Зависимость `tquality-py-core` переехала с git-URL (`@v0.1.3`) на
  публичный PyPI: `tquality-py-core>=0.1.5`. У потребителей `tquality-py-selenium`
  больше нет необходимости в `[tool.hatch.metadata] allow-direct-references`.
- `pyproject.toml` обогащен PyPI-метаданными: английский `description`,
  `readme = "README.md"`, `keywords`, `classifiers`
  (включая `Framework :: Pytest`, `Typing :: Typed`), `[project.urls]`.
- sdist дополнительно включает `README.ru.md` и `CHANGELOG.md`.
- `CollectionFactory` / `DomField` внутри используют свой `ByKind`
  вместо `selenium.By` (внешний API не изменился).
- Windows-CI `tests:windows-browsers-healthcheck`: PowerShell
  before_script ставит `uv` через `irm https://astral.sh/uv/install.ps1`
  (вместо `throw "uv не установлен"`), а `PYTHONUTF8=1` в `variables`
  заставляет Python читать UTF-8 файлы независимо от системной
  кодовой страницы (на Russian Windows дефолт - cp1251, и
  `tquality-py-core` падал на чтении нашего pyproject.toml с
  кириллическими комментариями).

### Исправлено

- `BrowserType.UNDETECTED_CHROME` на Apple Silicon: UC хардкодит
  платформу `mac-x64` в патчере (`patcher.py:113`), из-за чего на
  arm64-runner'ах скачивался x86_64 chromedriver, несовместимый
  с arm64 Chrome. Теперь chromedriver резолвится через Selenium
  Manager (правильная архитектура), копируется в собственный кэш
  `~/.cache/tquality-py-selenium/chromedriver/<platform>/<version>/`
  и патчится там; на macOS дополнительно ad-hoc-подписывается через
  `codesign --force --sign -`, иначе Gatekeeper убивает изменённый
  патчем бинарник сигналом SIGKILL.
- `uc.Chrome(use_subprocess=True)`: без флага UC закрывает Chrome
  сразу после старта, сессия не успевает подняться. См. UC
  discussion #2282 / issue #2186.
- `--no-sandbox` и `--disable-dev-shm-usage` применяются только на
  Linux (helper `_apply_linux_docker_chromium_flags`). Это workaround
  под root-юзера в Docker и маленький `/dev/shm`; на Windows/macOS
  они либо не нужны, либо ломают браузер.

### Удалено

- Реэкспорт `By` из `tquality_selenium.browser`: используйте
  `from tquality_selenium import By` (свой NamedTuple) или
  `from selenium.webdriver.common.by import By` (если действительно
  нужен селениумовский enum, что больше не требуется в API фреймворка).
- `[tool.hatch.metadata] allow-direct-references = true` из
  `pyproject.toml` - исчез вместе с git-зависимостью на ядро.

## [0.1.4] - 2026-04-25

### Добавлено

- `BaseElement.dismiss_if_visible(close_with=None, timeout=None)` -
  кликнуть и дождаться исчезновения, если элемент виден (иначе no-op).
  Удобно для cookie-баннеров и опциональных попапов.
- `Input.submit_text(text)` - ввести текст и нажать Enter (для форм
  с отправкой по Enter; оборачивает `type_text(text + Keys.RETURN)`).
- Pytest-плагин `tquality_selenium.page_source_plugin`, автоматически
  регистрируется через `entry-points.pytest11`. На падении теста (любая
  фаза) прикрепляет `driver.page_source` к allure как HTML-вложение
  `Page source`. Единственный run-time guard - запущен ли браузер; для
  api/db-only тестов плагин - no-op.
- Если `driver.page_source` сам бросает (мёртвая сессия), вместо HTML
  прикрепляется короткий TEXT-диагностик, чтобы не маскировать исходное
  падение.
- Поле `SeleniumConfig.attach_page_source_on_failure: bool = True` для
  опт-аута. Управляется через `config.json5` или env
  `TEST_ATTACH_PAGE_SOURCE_ON_FAILURE=false`.

## [0.1.3] - 2026-04-24

**Требует tquality-py-core >= 0.1.3** (ядро с `WITH_SCREENCAST`,
DI-провайдерами Logger и `config.json5`).

### Добавлено

- **SeleniumScreencastProvider** - реализация
  `tquality_core.ScreencastProvider`: фоновый поток собирает кадры
  (BiDi → CDP → классический `get_screenshot_as_png` как fallback с
  warning), кодирует в webm (VP9) через imageio-ffmpeg. Обслуживает
  шаги уровня `LogLevel.WITH_SCREENCAST`.
- Под-блок `screencast` в `SeleniumConfig` с параметрами `fps`,
  `frame_interval`, `max_width`, `max_duration`.
- Поле-выбор `browser` + * pid=19647 revision=9ffb4aa0 version=18.8.0                                                                                                         
  report.xml: found 1 matching artifact files and directories                                                                                                                                                                 
  Uploading artifacts as "junit" to coordinator... 201 Created  correlation_id=01KQW5A3BTKZQ6PJ294QFWPM76 id=7042 responseStatus=201 Created token=64_Vx_xfZ         *отдельные под-блоки для каждого браузера**
  (`chrome`, `firefox`, `edge`, `safari`, `undetected_chrome`) со
  структурой `BrowserConfig` (`headless`, `window_width/height`,
  `page_load_timeout`). Все блоки живут одновременно - переключение
  между браузерами делается одной строкой `browser: ...`.
- `SeleniumConfig.active_browser` - конфиг выбранного браузера.
- **Апстрим project-agnostic сервисов из grohe-проекта**: `Waiter`,
  `ElementWaiter`, `ElementFactory`, `JsActions` + `ElementJsActions`,
  `CollectionFactory` (фабрика коллекций Pydantic-моделей из DOM)
  + `DomField.css/xpath`.
- Обогащённые элементы: `BaseElement` получил `text`, `is_displayed`,
  `is_present`, `is_enabled`, `get_attribute`, `wait_until_*` (visible/
  clickable/invisible/not_present) и `js_actions` (лениво резолвится
  к элементу). `Input`, `CheckBox`, `Button` расширены в том же духе.
- `BaseForm` с `title`, `current_url`, `element_factory`.
- **Динамический `SELENIUM_SCHEMA_URL`**: релизная установка - `@vX.Y.Z`,
  dev/editable - `@master`. `tquality-selenium-config init` запекает
  в `config.json5` пин на тег - схема стабильна между релизами.
- Описания и диапазоны валидации у полей `SeleniumConfig`
  (`page_load_timeout >= 1`, `window_width` в 320..7680, и т.д.).

### Изменено

- **`Container` → `SeleniumServices`** (composition root). Вместо
  `wire_core_integrations()` - classmethod `SeleniumServices.setup()`,
  принимает опционально `config_dir` (по умолчанию определяется по
  файлу вызывающего, обычно `conftest.py`, для правильной резолюции
  `config.json5` независимо от CWD pytest).
- **`SeleniumServices.get_service(ServiceType)`** - типобезопасный
  сервис-локатор через DI-контейнер (используется элементами и формами
  для лениво-резолвленных зависимостей).
- **`is_browser_started()` → `SeleniumServices.is_browser_started()`**
  (classmethod вместо module-level функции).
- `BrowserService._create_driver` теперь читает параметры из
  `config.active_browser`, а не из общих полей верхнего уровня.
- Все интерактивные `ElementJsActions` и `Input.type_text/append_text`
  теперь оборачиваются в `maybe_highlight()` - красная рамка на время
  взаимодействия, если `highlight_elements=true`.
- `SeleniumScreenshotProvider` и `SeleniumScreencastProvider` -
  DI-сервисы `SeleniumServices`, инжектятся в `Logger` через
  `ContextLocalSingleton` (вместо ручной регистрации).

### Удалено

- `Container.wire_core_integrations()` (заменено на
  `SeleniumServices.setup()`).
- Общие поля `headless` / `page_load_timeout` / `window_*` на уровне
  `SeleniumConfig` - переехали в per-browser под-блоки.

## [0.1.2] - 2026-04-24

### Добавлено

- Описания и диапазоны валидации у полей `SeleniumConfig`.
- `SeleniumServices.setup(config_dir=...)` - явная директория для
  резолюции `config.json` (предшественник auto-detect через inspect
  в 0.1.3).

## [0.1.1] - 2026-04-23

### Добавлено

- Первый релиз: `SeleniumConfig` (extends core BaseConfig),
  `BrowserService`, `BrowserType` enum со всеми 5 браузерами,
  `OSUtils` с картой поддержки браузеров по ОС.
- Элементы: `BaseElement`, `Button`, `Input`, `CheckBox`, `Label`
  (Locator-based, минимальный API).
- `SeleniumScreenshotProvider` для CRITICAL-шагов ядра.
- Healthcheck-тесты всех 5 браузеров на macos-runner.
- CLI `tquality-selenium-config` + JSON-схема SeleniumConfig.
- Публикация в GitLab Package Registry и зеркалирование на GitHub
  по git-тегу `vX.Y.Z`.
