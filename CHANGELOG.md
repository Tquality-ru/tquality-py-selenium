# Changelog

Формат по [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии по
[семантическому версионированию](https://semver.org/lang/ru/).

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
- Поле-выбор `browser` + **отдельные под-блоки для каждого браузера**
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
