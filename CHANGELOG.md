# Changelog

Формат по [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии по
[семантическому версионированию](https://semver.org/lang/ru/).

## [0.1.3] - не выпущено

**Требует tquality-py-core >= 0.1.3** (ядро с WITH_SCREENCAST,
DI-провайдерами Logger и config.json5).

### Добавлено

- **SeleniumScreencastProvider** - реализация
  `tquality_core.ScreencastProvider`: фоновый поток собирает кадры
  (BiDi → CDP → классический get_screenshot_as_png как fallback с
  warning), кодирует в webm (VP9) через imageio-ffmpeg. Обслуживает
  шаги уровня `LogLevel.WITH_SCREENCAST`.
- Блок `screencast` в `SeleniumConfig` с параметрами `fps`,
  `frame_interval`, `max_width`, `max_duration`.
- Поле-выбор `browser` + **отдельные под-блоки для каждого браузера**
  (`chrome`, `firefox`, `edge`, `safari`, `undetected_chrome`) со
  структурой `BrowserConfig` (`headless`, `window_width/height`,
  `page_load_timeout`). Все блоки живут одновременно - переключение
  между браузерами делается одной строкой `browser: ...`.
- `SeleniumConfig.active_browser` - конфиг выбранного браузера.
- Описания и диапазоны валидации у полей `SeleniumConfig`
  (page_load_timeout >= 1, window_width в 320..7680, и т.д.).

### Изменено

- **`Container` → `SeleniumServices`**. `wire_core_integrations()` стало
  `SeleniumServices.setup()` - composition-root classmethod, принимает
  опционально `config_dir` (по умолчанию определяется по файлу
  вызывающего, обычно conftest.py, для правильной резолюции
  config.json5 независимо от CWD pytest).
- **`SeleniumServices.get_service(ServiceType)`** - типобезопасный
  сервис-локатор через DI-контейнер (для элементов и форм).
- **`is_browser_started()` → `SeleniumServices.is_browser_started()`**
  (classmethod вместо module-level функции).
- `BrowserService._create_driver` теперь читает параметры из
  `config.active_browser`, а не из общих полей верхнего уровня.

### Удалено

- `Container.wire_core_integrations()` (заменено на `SeleniumServices.setup()`).
- Общий флажок `headless` / `page_load_timeout` / `window_*` на уровне
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
