# Changelog

Формат по [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии по
[семантическому версионированию](https://semver.org/lang/ru/).

## [0.1.11] - 2026-05-30

### Добавлено

- **`SeleniumConfig.remote_url: str | None`** - URL Selenium Grid Hub. Если задан, `BrowserService` поднимает `webdriver.Remote(command_executor=remote_url, options=...)` вместо локального драйвера; тип браузера и `headless` берутся из соответствующих секций конфига, BiDi-capability применяется как и для локальных сессий. При remote-сессии `_check_os_support` пропускается - локальная ОС не ограничивает выбор браузера (Safari через Grid можно поднять с Linux-runner'а).
- **`SeleniumConfig.capabilities: Capabilities`** - типизированный контракт W3C-capabilities для Remote-сессии. Известные поля задокументированы (`platformName`, `browserVersion`), произвольные ключи разрешены через `model_config = ConfigDict(extra="allow")` - схема для `config.json5` теперь даёт IDE-автокомплит и подсказки. Применяются через `options.set_capability(...)` перед `webdriver.Remote(...)`; при локальном запуске игнорируются.
- **UC remote через `uc.ChromeOptions()`** - в Remote-режиме для `BrowserType.UNDETECTED_CHROME` собираются опции из `undetected_chromedriver`, а не из чистого `ChromeOptions`. Это даёт UC-специфичные аргументы (`--disable-blink-features=AutomationControlled`, прочие prefs) поверх Grid-сессии; роутинг в UC-слот - ответственность пользовательских capabilities (`browserVersion: undetected`).

### Изменено

- **Top-level export `Capabilities`** - `from tquality_selenium import Capabilities`.
- **Явная зависимость `pydantic>=2.0`** в `[project.dependencies]`. Раньше тянулась транзитивно через `tquality-py-core`; теперь, когда `Capabilities` / `CollectionFactory`-валидаторы / `SeleniumConfig` напрямую используют Pydantic v2 API (`BaseModel`, `ConfigDict`, `field_validator`, `BeforeValidator`), пин закрепляется здесь - чтобы upstream-ядро могло сменить config-движок без поломки нашей валидации.
- **CI pipeline сведен в один job** (`tests:`): юнит-тесты + browser smoke через Selenium Grid в одном прогоне с `TEST_REMOTE_URL`. Smoke `test_browsers_smoke` параметризуется по `(browser, platform_name)` с pytest.param-id'ами вида `chrome-mac` / `undetected-windows` (11 случаев: 3 chrome + 3 firefox + 3 edge + 1 safari + 1 undetected). Заменяет прежние `tests:linux` и `tests:browsers-healthcheck`.

## [0.1.10] - 2026-05-30

### Изменено

- **BiDi включён по умолчанию через новое поле конфига `bidi: bool = true`.** `BrowserService` выставляет capability `webSocketUrl=True` для Chrome / Firefox / Edge / undetected-chrome / Safari, и `driver.input` / `driver.browsing_context` / `driver.script` поднимаются штатно. Без этого BiDi-сервисы падали с `Unable to find url to connect to from capabilities`, а BiDi-путь в `SeleniumScreencastProvider` тихо валился в CDP/PNG-фолбэк. Safari поддерживает BiDi частично с 18.4 (macOS 15.4): доступны `script.*` и базовый `browsingContext.*`, но `input.*` / `network.*` / `browsingContext.captureScreenshot` ещё нет. На macOS <15.4 / Safari <18.4 поставьте `bidi: false`, иначе сессия не поднимется. Полный спектр возможностей: https://www.selenium.dev/documentation/webdriver/bidi/.

## [0.1.9] - 2026-05-30

### Добавлено

- **`CollectionFactory`: computed-style readout.** `DomField.css_style(selector, prop, *, pseudo=...)` и `DomField.xpath_style(selector, prop)` собирают `window.getComputedStyle(el, pseudo).getPropertyValue(prop)`. `pseudo` принимает `PseudoElement` (`BEFORE` / `AFTER` / `MARKER` / `PLACEHOLDER` / `FIRST_LINE` / `FIRST_LETTER` / `SELECTION` / `BACKDROP`); для XPath псевдо-элементы не поддерживаются - в DOM-дереве их нет. Сырое значение - строка (`"none"`, `"rgb(0,0,0)"`, `'url("...")'`); для бизнес-логики оборачивайте поле в `@field_validator(mode="before")` или `Annotated[T, BeforeValidator(...)]`.
- **`CollectionFactory`: type-driven dispatch для полей-элементов.** Аннотация `WebElement` - поле получает сам DOM-узел (без `.textContent`-преобразования); подходит для short-lived моделей, где сразу же кликают/читают, ссылка устаревает при перерисовке DOM. Аннотация-наследник `BaseElement` (`Button`, `Input`, любой кастомный) - фабрика лениво конструирует элемент с row-scoped XPath `(container_xpath)[N]<field_xpath>` и повторно резолвится при каждом обращении (как `LazyElements`). Модель требует `model_config = ConfigDict(arbitrary_types_allowed=True)`.
- **`PseudoElement` расширен** до полного набора стандартных псевдо-элементов: к `BEFORE` / `AFTER` добавлены `MARKER`, `PLACEHOLDER`, `FIRST_LINE`, `FIRST_LETTER`, `SELECTION`, `BACKDROP`. Все варианты используют двойное двоеточие (`::xxx`) - единственная форма, корректно работающая в `getComputedStyle` для CSS3+ псевдо-элементов.

### Изменено

- **`PseudoElement` теперь `StrEnum`** (был `enum.Enum`). `member.value` по-прежнему возвращает строку (`"::before"` и т.д.), но `str(PseudoElement.BEFORE)` теперь даёт `"::before"` вместо `"PseudoElement.BEFORE"` - возможный breaking change, если код полагался на старый `repr`-стиль строкового представления.
- **`PseudoElement` переехал** из `services/js_actions.py` в собственный модуль `services/pseudo_element.py`. Реэкспорт через `tquality_selenium.services.PseudoElement` и `tquality_selenium.PseudoElement` сохранён.

### Тесты

- Новый `tests/test_collection_factory.py` (26 тестов) и `tests/conftest.py` с фикстурой `make_collection_factory`. Покрытие: Pydantic-coercion для `int` / `float` / `bool` / `Decimal`, `@field_validator(mode="before"/"after")` и `Annotated[T, BeforeValidator/AfterValidator]`-валидация, `attr=` + `getAttribute || textContent`-fallback, computed-style readout с `pseudo=` и без, raw `WebElement`-поле, `BaseElement`-subclass-поле с проверкой row-scoped XPath и dot-prefix join (`.//foo` / `./foo` / `//foo`).

## [0.1.8] - 2026-05-29

### Изменено

- **Минимальная версия `tquality-py-core` поднята до `>=0.1.9`** -
  для использования вынесенных в ядро `XPathUtils`, `OSUtils`,
  `build_schema_url`, `build_cli`, параметризуемых
  `generate_schema(..., schema_url=...)` / `write_schema_file(...,
  schema_url=...)`, `ElementState` / `Waiter` / `ResolvedWaiter` /
  `LazyElements` / `WebDriverScreenshotProvider` /
  `WebmScreencastRecorder`, а также нового
  `register_per_test_rebuilder` / `find_upwards` API из
  `tquality_core.per_test_files`. Дополнительно берётся extras-группа
  `[screencast]` (тянет `imageio` / `imageio-ffmpeg` / `numpy` /
  `Pillow`) - эти пакеты больше не объявлены в `[project.dependencies]`
  selenium-пакета напрямую, единственный источник правды - ядро.
- **`LocatorUtils.normalize_xpath` / `LocatorUtils.xpath_literal`** -
  тонкие обёртки над `tquality_core.utils.xpath_utils.XPathUtils.normalize` /
  `.literal`. Логика идентична, публичный API не изменён.
- **`OSUtils.is_macos` / `is_windows` / `is_linux`** - переэкспортированы
  из `tquality_core.utils.os_utils.OSUtils`. Карта `_BROWSER_OS_SUPPORT`
  и `is_browser_supported_on_current_os` остаются в селениум-пакете
  (зависят от `BrowserType`).
- **`tquality_selenium.schema`** - запись схемы и резолв ref-версии
  делегированы в `tquality_core.schema` через `build_schema_url`,
  `generate_schema(SeleniumConfig, schema_url=...)`,
  `write_schema_file(...)`. Публичные `SELENIUM_SCHEMA_URL`,
  `generate_schema()`, `write_schema_file(path)` сохранены.
- **`tquality_selenium.cli.main`** - собирается через
  `tquality_core.cli.build_cli(prog="tquality-selenium-config", ...)`,
  избавляясь от дубля argparse-плиты. Поведение `init` / `schema`
  идентично.
- **`$schema` в `schema/config.schema.json`**: `draft-07` →
  `draft/2020-12` (синхронно с ядром 0.1.6). Pydantic 2 эмитит
  2020-12-features, прежний диалект вводил валидаторы в заблуждение.
  Файл перегенерирован.
- **`Waiter` переехал в `tquality_core`** - локальный
  `tquality_selenium.services.waiter.Waiter` стал тонким реэкспортом
  (`Waiter` + `WaitTimeoutError`). Логика polling'а - в ядре, никакой
  зависимости от selenium больше нет.
- **`SeleniumScreencastProvider` сокращён до тонкого адаптера**
  (с ~230 до ~110 строк): frame-source-лестница BiDi → CDP →
  классический `get_screenshot_as_png` живёт в этом пакете, склейка
  PNG-кадров в webm/VP9 и фоновый цикл - в
  `tquality_core.WebmScreencastRecorder`. Поведение и публичный API
  без изменений; настройки по-прежнему берутся из
  `SeleniumConfig.screencast`.
- **`SeleniumScreenshotProvider` теперь алиас**
  `tquality_core.WebDriverScreenshotProvider`. Класс с обоими
  WebDriver'ами (selenium и appium) идентичен, поэтому реализация
  одна. Импорт `from tquality_selenium import SeleniumScreenshotProvider`
  работает как раньше.
- **`LazyElements` переехал в ядро** - локальный
  `tquality_selenium.services.lazy_elements.LazyElements` стал тонким
  наследником `tquality_core.LazyElements[E]`, прокидывающим
  browser-resolver из `SeleniumServices`. Snapshot-кэширование и
  live-резолв - в ядре; публичный API не изменился.

### Добавлено

- **`ElementState` / `StatePredicate` / `StateSpec`** - переэкспорт
  из ядра (`tquality_core`), доступны и через
  `tquality_selenium.elements` и через top-level
  `tquality_selenium.ElementState`. Каждый элемент теперь принимает
  параметр `state` (`BaseElement(..., state=...)`) - предусловие,
  которое автоматически ожидается перед `click()` / `submit()` /
  `type_text()` / `append_text()`. Дефолты совпадают с appium-пакетом:
  `Button`/`CheckBox` - `CLICKABLE`, `Input`/`Label`/`BaseElement` -
  `DISPLAYED`. `ElementState.EXISTS_IN_ANY_STATE` отключает любые
  ожидания (полезно для «странных» web-компонентов, где
  `EC.element_to_be_clickable` ложно-отрицателен, но реальный клик
  всё равно работает). `state` принимает callable-предикат
  `(element) -> bool` для кастомных условий готовности.
- **`DriverWaiter`** - новый сервис в DI-контейнере
  (`SeleniumServices.driver_waiter`), `ResolvedWaiter[WebDriver]`
  из ядра, тонкая обёртка над `Waiter` с прокинутым
  `driver_resolver`. Используется `ElementWaiter` под капотом и
  доступен напрямую для условий, которым нужен сам драйвер.
- **`ElementFactory` методы принимают `state`** - все
  `element/button/checkbox/label/input` и их `get_child_*`-варианты
  принимают `state: StateSpec`. Дефолт сигнатуры повторяет дефолт
  конструктора целевого класса; передавать вручную нужно только
  когда стандартное условие мешает.
- `ContextLocalSingleton[DriverWaiter]` в `SeleniumServices` -
  собирается из `waiter` + `_resolve_driver_from_active`.
- Реэкспорты в `tquality_selenium`: `ElementWaiter`,
  `WaitTimeoutError`, `DriverWaiter`, `ElementState`,
  `StatePredicate`, `StateSpec`, а также `ContextManager`,
  `ContextWaiter`, `UnknownWindowError`.
- **`ContextManager` (`SeleniumServices.context_manager`)** -
  фасад фокуса сессии в браузере: окна/табы, фреймы, алерты.
  Зеркало `tquality_appium.ContextManager` (минус native/webview-
  переключения, которых в селениуме нет).
  - Окна: `windows`, `current_window`, `switch_to_window(handle |
    index)`, `with context.window(target):`.
  - Фреймы: `switch_to_frame(name | index | element)`,
    `back_to_default_content()`, `with context.frame(target):`.
  - Алерты: `alert()`, `accept_alert()`, `dismiss_alert()`.
  - `wait` - `ContextWaiter`, см. ниже.
- **`ContextWaiter`** - тонкая обёртка над generic
  `tquality_core.Waiter` для ожиданий, привязанных к контексту.
  Доступ - `browser.context.wait`. Текущий API:
  - `for_alert(predicate=None, *, timeout, poll_interval,
    raise_on_timeout=False, message="")` - дождаться появления
    `Alert`. Без `predicate` - вернуть первый же; с `predicate` -
    тот, на котором `predicate(alert)` truthy. Возвращает `Alert`
    либо `None` на таймаут; `raise_on_timeout=True` (или класс) -
    поднимает. `NoAlertPresentException` глотается как «ещё не
    готово».
- **`BrowserService.context -> ContextManager`** - шорткат для
  `SeleniumServices.get_service(ContextManager)`. Типизирован
  через `TYPE_CHECKING`-импорт - IDE/mypy видят `ContextManager`
  в `browser.context.<...>`.
- **Per-test resolve `config.json5` под директорию теста.**
  `SeleniumServices.setup(...)` теперь дополнительно регистрирует
  rebuilder через
  `tquality_core.register_per_test_rebuilder(...)`: перед каждым
  тестом плагин ядра вызывает `cls._rebuild_configs_for_test(test_dir)`,
  который chdir'ит в `test_dir`, пересобирает `SeleniumConfig()`
  (так что `BaseConfig`-цепочка `config.json5` ищет от теста, а
  не от CWD pytest'а) и `.override(...)`-ит DI-провайдер;
  teardown откатывает override назад на baseline, посчитанный в
  `setup(config_dir=...)` на старте сессии.
  Регистрация идемпотентна: повторный `setup()` не плодит дубли.

### Breaking

- **`ElementWaiter.until_*` теперь возвращают `bool`,
  а не сам элемент.** Раньше `button.wait.until_clickable().click()`
  было одним выражением; теперь чейн на возвращаемом значении не
  работает.
  Миграция: разбейте на две строки (`button.wait.until_clickable();
  button.click()`) или просто положитесь на автоматическое
  предусловие из `state` - `button.click()` уже ждёт
  `CLICKABLE` за счёт `Button` дефолта.
  По умолчанию метод НЕ кидает исключение при таймауте, а возвращает
  `False`; для прежнего поведения - `raise_on_timeout=True`
  (или класс исключения).
- **Сигнатура `ElementWaiter.__init__` изменилась:**
  `(waiter: Waiter, element)` → `(driver_waiter: DriverWaiter, element)`.
  Если вы инстанциировали `ElementWaiter` вручную - переключитесь на
  `SeleniumServices.get_service(DriverWaiter)`. `element.wait` уже
  использует новый путь.
- **`BaseElement.click()` / `Button.submit()` / `Input.type_text()` /
  `Input.append_text()` больше не зовут `wait.until_*` напрямую.**
  Теперь они зовут `self._await_state()`, который смотрит на `state`
  элемента. Поведение для дефолтных классов не меняется
  (`Button.click()` всё так же ждёт CLICKABLE), но если вы создавали
  `Button(by, state=ElementState.EXISTS_IN_ANY_STATE)`, ожидание
  пропадает - это и есть смысл фичи.
- **`ElementWaiter.until(...)` и связанные методы перешли на
  keyword-only параметры** (`*` после `condition`/`timeout`):
  `poll_interval`, `raise_on_timeout`, `message`. Позиционная передача
  больше не компилируется.
- **`BaseForm.wait_for_displayed(...)` теперь возвращает `bool`,
  а не сам `BaseForm`**, и не кидает по умолчанию. Сигнатура и
  дефолты выровнены с `element.wait.until_present(...)`:
  `wait_for_displayed(timeout=None, *, poll_interval=None,
  raise_on_timeout=False, message="")`.
  Миграция:
  - Раньше: `HomePage().wait_for_displayed()` падало с
    `TimeoutException`, если экран не появился.
    Теперь: вернётся `False`, тест молча пойдёт дальше.
  - Если нужно прежнее поведение: явно
    `HomePage().wait_for_displayed(raise_on_timeout=True)`
    либо `assert HomePage().wait_for_displayed(), "Home page
    not displayed"`.
  - Если вы чейнили `HomePage().wait_for_displayed().some_button`,
    переделайте в отдельный вызов: `home = HomePage();
    home.wait_for_displayed(raise_on_timeout=True);
    home.some_button.click()`.

### Удалено

- Локальное дублирование `_resolve_ref` и тестов резолва версии
  схемы - теперь это покрытие живёт в `tquality-py-core`.

### Внутреннее

- `container.py`: `_resolve_driver_from_active` теперь падает на
  fallback `SeleniumServices` (вместо `RuntimeError`) - даёт работать
  `SeleniumServices.driver_waiter.override(...)` в тестах без полной
  инициализации composition root'а. Аналогично добавлен
  `_resolve_logger_from_active`.
- `Waiter`-провайдер обогащён kwarg'ами `logger_resolver`,
  `ignored_exceptions=(NoSuchElementException, StaleElementReferenceException)`,
  `default_raise_cls=TimeoutException` - чтобы поведение по умолчанию
  на таймаут (когда `raise_on_timeout=True`) совпадало с прежним
  `WebDriverWait`-стилем.
- Перерасклад тестов `tests/test_elements.py` под новый API: вместо
  моков `LazyElements._browser` через `PropertyMock` - инстансный
  override `collection._driver_resolver = CountingBrowser`; вместо
  `_FakeWaiter(_Waiter)` - `_FakeDriverWaiter(_DriverWaiter)` без
  `super().__init__()` (mypy clean); ассерты `result is btn`
  заменены на `result is True/False`.

## [0.1.7] - 2026-05-15

### Добавлено

- `BaseElement.wait` - per-element `ElementWaiter[Self]`. Все ожидания
  возвращают сам элемент - удобно чейнить:
  `button.wait.until_clickable().click()`. API:
  `wait.until(condition, timeout, message)`,
  `wait.until_visible/clickable/invisible/present/not_present(timeout)`,
  `wait.for_computed_style(prop, expected, timeout)`. Кастомное условие
  получает на вход сам элемент, а не `WebDriver` - доступны
  `is_displayed`, `js_actions`, `text`, `get_attribute` и т.д.
- `BaseElement.by` / `BaseElement.name` - read-only-доступ к локатору и
  имени элемента (раньше было только через `_by` / `_name`).
- `By.to_xpath() -> str` - конвертация любого `By` в xpath. Для XPATH
  значение нормализуется через `LocatorUtils.normalize_xpath`. Для
  `ID/NAME/LINK_TEXT/PARTIAL_LINK_TEXT/CLASS_NAME` значения квотируются
  через `LocatorUtils.xpath_literal` - значения с `'` / `"` (например,
  `By.id("don't")`) больше не ломают результирующий XPath.
- `LocatorUtils` (`tquality_selenium.utils.locator_utils`) - stateless-
  хелперы для xpath:
  - `normalize_xpath(value)` - `./foo` → `/foo`, `.//foo` → `//foo`,
    голый `foo` → `/foo`, абсолютные (`/foo`, `//foo`) без изменений.
    `.` → `""` (join-нейтральный self - standalone не используется).
  - `xpath_literal(value)` - безопасное квотирование XPath-литерала
    (нет `'` → `'…'`; иначе нет `"` → `"…"`; иначе - `concat('a', "'", 'b', …)`).
  - `join_xpath(*bys: By) -> By` - склеивает несколько `By` в один XPATH-
    локатор через `to_xpath()` каждого; используется для дочерних
    локаторов.
- `ElementFactory.buttons/checkboxes/labels/inputs(by, name_prefix="")` -
  типизированные обёртки над `elements()` для соответствующих классов.
- `ElementFactory.element[E](element_cls, by, name="")` - генерик-фабрика
  одиночного элемента (раньше было захардкожено `BaseElement`).
- `ElementFactory.get_child_element/get_child_elements` + per-class
  обёртки (`get_child_button`, `get_child_buttons`, ...) - дочерние
  локаторы как `parent.by + child.by` через `LocatorUtils.join_xpath`.
- Зависимость `cssselect>=1.4.0` (для `By.to_xpath()` от
  `ByKind.CSS_SELECTOR`).

### Изменено

- **Breaking.** Поле `By` переименовано: `by` → `by_kind`. Позиционная
  распаковка `*by` для selenium-API не изменилась.
  Миграция: `By(by=ByKind.ID, value="x")` → `By(by_kind=ByKind.ID, value="x")`,
  `loc.by` → `loc.by_kind`.
- **Breaking.** `BaseElement.wait_until_visible/clickable/invisible/`
  `present/not_present`, `wait_for_displayed`, `wait_until`,
  `wait_for_computed_style` удалены. Используйте `element.wait.<method>`.
  Миграция: `el.wait_until_visible(timeout)` → `el.wait.until_visible(timeout)`,
  `el.wait_until(cond)` → `el.wait.until(cond)`,
  `el.wait_for_computed_style(...)` → `el.wait.for_computed_style(...)`.
- **Breaking.** `ElementWaiter` теперь generic-обёртка
  `ElementWaiter[E: BaseElement]` с конструктором `(waiter, element)`,
  биндится к конкретному элементу. Из DI-контейнера `SeleniumServices`
  удалён - доступ через `element.wait`. Старая API-сигнатура методов
  `(by, name="", timeout=None)` заменена на `(timeout=None)` - by/name
  берутся из бинда.
- **Breaking.** Модуль `tquality_selenium.os_utils` переехал в
  `tquality_selenium.utils.os_utils`. Публичный реэкспорт
  `from tquality_selenium import OSUtils` без изменений; прямые импорты
  обновить: `from tquality_selenium.os_utils import OSUtils` →
  `from tquality_selenium.utils.os_utils import OSUtils`.
- `BaseElement.dismiss_if_visible` и `click` внутри теперь используют
  `self.wait.until_invisible/clickable` (без изменений в API).
- Сообщения ожиданий стали информативнее: для
  `wait.for_computed_style` включают имя свойства и ожидаемое значение
  (`"<element> to have computed style display equal to 'block'"`).

### Внутреннее

- Новый пакет `tquality_selenium.utils` содержит `os_utils` и
  `locator_utils`. `utils/__init__.py` намеренно пустой - чтобы
  импорт `OSUtils` из `browser.py` не подтягивал `LocatorUtils` и не
  создавал цикл `utils → elements → base_element → services →
  element_factory → base_element` на старте.

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
