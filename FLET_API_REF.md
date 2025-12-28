# Flet 1.0 (Beta) API Reference

Generated from local environment: 3.13.9 (tags/v3.13.9:8183fa5, Oct 14 2025, 14:09:13) [MSC v.1944 64 bit (AMD64)]
Flet Version: <module 'flet.version' from 'C:\\Users\\gary\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\LocalCache\\local-packages\\Python313\\site-packages\\flet\\version.py'>

## Page
**Module:** `flet.controls.page`

### Constructor Parameters
```python
Page(
    sess: dataclasses.InitVar['Session'] = <class 'inspect._empty'>,
    multi_views: list[flet.controls.multi_view.MultiView] = <factory>,
    window: <class 'flet.controls.core.window.Window'> = <factory>,
    route: <class 'str'> = /,
    web: <class 'bool'> = False,
    pwa: <class 'bool'> = False,
    debug: <class 'bool'> = False,
    wasm: <class 'bool'> = False,
    test: <class 'bool'> = False,
    multi_view: <class 'bool'> = False,
    pyodide: <class 'bool'> = False,
    platform_brightness: typing.Optional[flet.controls.types.Brightness] = None,
    client_ip: typing.Optional[str] = None,
    client_user_agent: typing.Optional[str] = None,
    platform: typing.Optional[flet.controls.types.PagePlatform] = None,
    fonts: typing.Optional[dict[str, str]] = None,
    on_platform_brightness_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.PlatformBrightnessChangeEvent], typing.Any], NoneType] = None,
    on_app_lifecycle_state_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.AppLifecycleStateChangeEvent], typing.Any], NoneType] = None,
    on_route_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.RouteChangeEvent], typing.Any], NoneType] = None,
    on_view_pop: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.ViewPopEvent], typing.Any], NoneType] = None,
    on_keyboard_event: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.KeyboardEvent], typing.Any], NoneType] = None,
    on_connect: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Page')]], typing.Any], NoneType] = None,
    on_disconnect: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Page')]], typing.Any], NoneType] = None,
    on_close: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Page')]], typing.Any], NoneType] = None,
    on_login: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.LoginEvent], typing.Any], NoneType] = None,
    on_logout: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Page')]], typing.Any], NoneType] = None,
    on_error: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Page')]], typing.Any], NoneType] = None,
    on_multi_view_add: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.MultiViewAddEvent], typing.Any], NoneType] = None,
    on_multi_view_remove: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.page.MultiViewRemoveEvent], typing.Any], NoneType] = None,
    _services: <class 'flet.controls.page.ServiceRegistry'> = <factory>,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    views: list[flet.controls.core.view.View] = <factory>,
    theme_mode: typing.Optional[flet.controls.types.ThemeMode] = ThemeMode.SYSTEM,
    theme: typing.Optional[flet.controls.theme.Theme] = None,
    dark_theme: typing.Optional[flet.controls.theme.Theme] = None,
    locale_configuration: typing.Optional[flet.controls.types.LocaleConfiguration] = None,
    show_semantics_debugger: typing.Optional[bool] = None,
    title: typing.Optional[str] = None,
    enable_screenshots: <class 'bool'> = False,
    on_resize: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[ForwardRef('PageResizeEvent')], typing.Any], NoneType] = None,
    on_media_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.base_page.PageMediaData], typing.Any], NoneType] = None,
    media: <class 'flet.controls.base_page.PageMediaData'> = <factory>,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    _overlay: Overlay = <factory>,
    _dialogs: Dialogs = <factory>,
)
```

### Public Attributes
`appbar`, `auth`, `auto_scroll`, `bgcolor`, `bottom_appbar`, `browser_context_menu`, `clipboard`, `controls`, `decoration`, `drawer`, `end_drawer`, `executor`, `floating_action_button`, `floating_action_button_location`, `foreground_decoration`, `horizontal_alignment`, `loop`, `name`, `navigation_bar`, `overlay`, `padding`, `page`, `parent`, `pubsub`, `query`, `scroll`, `services`, `session`, `shared_preferences`, `spacing`, `storage_paths`, `url`, `url_launcher`, `vertical_alignment`

### Events
* `on_platform_brightness_change` -> flet.controls.page.PlatformBrightnessChangeEvent
* `on_app_lifecycle_state_change` -> flet.controls.page.AppLifecycleStateChangeEvent
* `on_route_change` -> flet.controls.page.RouteChangeEvent
* `on_view_pop` -> flet.controls.page.ViewPopEvent
* `on_keyboard_event` -> flet.controls.page.KeyboardEvent
* `on_connect` -> flet.controls.control_event.Event
* `on_disconnect` -> flet.controls.control_event.Event
* `on_close` -> flet.controls.control_event.Event
* `on_login` -> flet.controls.page.LoginEvent
* `on_logout` -> flet.controls.control_event.Event
* `on_error` -> flet.controls.control_event.Event
* `on_multi_view_add` -> flet.controls.page.MultiViewAddEvent
* `on_multi_view_remove` -> flet.controls.page.MultiViewRemoveEvent
* `on_resize` -> PageResizeEvent
* `on_media_change`

### Key Methods
`add`, `before_event`, `before_update`, `can_launch_url`, `close_drawer`, `close_end_drawer`, `close_in_app_web_view`, `error`, `go`, `init`, `insert`, `is_isolated`, `launch_url`, `login`, `logout`, `pop_dialog`, `push_route`, `remove`, `remove_at`, `render`, `render_views`, `run_task`, `run_thread`, `schedule_update`, `scroll_to`, `show_dialog`, `show_drawer`, `show_end_drawer`, `take_screenshot`

---

## Container
**Module:** `flet.controls.material.container`

### Constructor Parameters
```python
Container(
    content: typing.Optional[flet.controls.control.Control] = None,
    padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    alignment: typing.Optional[flet.controls.alignment.Alignment] = None,
    bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    gradient: typing.Optional[flet.controls.gradients.Gradient] = None,
    blend_mode: typing.Optional[flet.controls.types.BlendMode] = None,
    border: typing.Optional[flet.controls.border.Border] = None,
    border_radius: typing.Union[int, float, flet.controls.border_radius.BorderRadius, NoneType] = None,
    shape: <enum 'BoxShape'> = BoxShape.RECTANGLE,
    clip_behavior: typing.Optional[flet.controls.types.ClipBehavior] = None,
    ink: <class 'bool'> = False,
    image: typing.Optional[flet.controls.box.DecorationImage] = None,
    ink_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    animate: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    blur: typing.Union[int, float, tuple[typing.Union[int, float], typing.Union[int, float]], flet.controls.blur.Blur, NoneType] = None,
    shadow: typing.Union[flet.controls.box.BoxShadow, list[flet.controls.box.BoxShadow], NoneType] = None,
    url: typing.Union[str, flet.controls.types.Url, NoneType] = None,
    theme: typing.Optional[flet.controls.theme.Theme] = None,
    dark_theme: typing.Optional[flet.controls.theme.Theme] = None,
    theme_mode: typing.Optional[flet.controls.types.ThemeMode] = None,
    color_filter: typing.Optional[flet.controls.box.ColorFilter] = None,
    ignore_interactions: <class 'bool'> = False,
    foreground_decoration: typing.Optional[flet.controls.box.BoxDecoration] = None,
    on_click: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Container')]], typing.Any], NoneType] = None,
    on_tap_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('Container')]], typing.Any], NoneType] = None,
    on_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Container')]], typing.Any], NoneType] = None,
    on_hover: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Container')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_click` -> flet.controls.control_event.Event
* `on_tap_down` -> flet.controls.events.TapEvent
* `on_long_press` -> flet.controls.control_event.Event
* `on_hover` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`

---

## Column
**Module:** `flet.controls.core.column`

### Constructor Parameters
```python
Column(
    controls: list[flet.controls.control.Control] = <factory>,
    alignment: <enum 'MainAxisAlignment'> = MainAxisAlignment.START,
    horizontal_alignment: <enum 'CrossAxisAlignment'> = CrossAxisAlignment.START,
    spacing: typing.Union[int, float] = 10,
    tight: <class 'bool'> = False,
    wrap: <class 'bool'> = False,
    run_spacing: typing.Union[int, float] = 10,
    run_alignment: <enum 'MainAxisAlignment'> = MainAxisAlignment.START,
    intrinsic_width: <class 'bool'> = False,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    scroll: typing.Optional[flet.controls.types.ScrollMode] = None,
    auto_scroll: <class 'bool'> = False,
    scroll_interval: typing.Union[int, float] = 10,
    on_scroll: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.scrollable_control.OnScrollEvent], typing.Any], NoneType] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_scroll` -> flet.controls.scrollable_control.OnScrollEvent
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`, `scroll_to`

---

## Row
**Module:** `flet.controls.core.row`

### Constructor Parameters
```python
Row(
    controls: list[flet.controls.control.Control] = <factory>,
    alignment: <enum 'MainAxisAlignment'> = MainAxisAlignment.START,
    vertical_alignment: <enum 'CrossAxisAlignment'> = CrossAxisAlignment.CENTER,
    spacing: typing.Union[int, float] = 10,
    tight: <class 'bool'> = False,
    wrap: <class 'bool'> = False,
    run_spacing: typing.Union[int, float] = 10,
    run_alignment: <enum 'MainAxisAlignment'> = MainAxisAlignment.START,
    intrinsic_height: <class 'bool'> = False,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    scroll: typing.Optional[flet.controls.types.ScrollMode] = None,
    auto_scroll: <class 'bool'> = False,
    scroll_interval: typing.Union[int, float] = 10,
    on_scroll: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.scrollable_control.OnScrollEvent], typing.Any], NoneType] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_scroll` -> flet.controls.scrollable_control.OnScrollEvent
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`, `scroll_to`

---

## ListView
**Module:** `flet.controls.core.list_view`

### Constructor Parameters
```python
ListView(
    controls: list[flet.controls.control.Control] = <factory>,
    horizontal: <class 'bool'> = False,
    reverse: <class 'bool'> = False,
    spacing: typing.Union[int, float] = 0,
    item_extent: typing.Union[int, float, NoneType] = None,
    first_item_prototype: <class 'bool'> = False,
    prototype_item: typing.Optional[flet.controls.control.Control] = None,
    divider_thickness: typing.Union[int, float] = 0,
    padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    clip_behavior: <enum 'ClipBehavior'> = ClipBehavior.HARD_EDGE,
    semantic_child_count: typing.Optional[int] = None,
    cache_extent: typing.Union[int, float, NoneType] = None,
    build_controls_on_demand: <class 'bool'> = True,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    scroll: typing.Optional[flet.controls.types.ScrollMode] = None,
    auto_scroll: <class 'bool'> = False,
    scroll_interval: typing.Union[int, float] = 10,
    on_scroll: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.scrollable_control.OnScrollEvent], typing.Any], NoneType] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_scroll` -> flet.controls.scrollable_control.OnScrollEvent
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`, `scroll_to`

---

## Stack
**Module:** `flet.controls.core.stack`

### Constructor Parameters
```python
Stack(
    controls: list[flet.controls.control.Control] = <factory>,
    clip_behavior: <enum 'ClipBehavior'> = ClipBehavior.HARD_EDGE,
    alignment: typing.Optional[flet.controls.alignment.Alignment] = None,
    fit: <enum 'StackFit'> = StackFit.LOOSE,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`

---

## Text
**Module:** `flet.controls.core.text`

### Constructor Parameters
```python
Text(
    value: <class 'str'> = ,
    spans: typing.Optional[list[flet.controls.core.text_span.TextSpan]] = None,
    text_align: <enum 'TextAlign'> = TextAlign.START,
    font_family: typing.Optional[str] = None,
    size: typing.Union[int, float, NoneType] = None,
    weight: typing.Optional[flet.controls.types.FontWeight] = None,
    italic: <class 'bool'> = False,
    style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    theme_style: typing.Optional[flet.controls.text_style.TextThemeStyle] = None,
    max_lines: typing.Optional[int] = None,
    overflow: <enum 'TextOverflow'> = TextOverflow.CLIP,
    selectable: typing.Optional[bool] = None,
    no_wrap: typing.Optional[bool] = None,
    color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    semantics_label: typing.Optional[str] = None,
    show_selection_cursor: <class 'bool'> = False,
    enable_interactive_selection: <class 'bool'> = True,
    selection_cursor_width: typing.Union[int, float] = 2.0,
    selection_cursor_height: typing.Union[int, float, NoneType] = None,
    selection_cursor_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    on_tap: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Text')]], typing.Any], NoneType] = None,
    on_selection_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.core.text.TextSelectionChangeEvent[ForwardRef('Text')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_tap` -> flet.controls.control_event.Event
* `on_selection_change` -> flet.controls.core.text.TextSelectionChangeEvent
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`

---

## TextField
**Module:** `flet.controls.material.textfield`

### Constructor Parameters
```python
TextField(
    value: <class 'str'> = ,
    selection: typing.Optional[flet.controls.core.text.TextSelection] = None,
    keyboard_type: <enum 'KeyboardType'> = KeyboardType.TEXT,
    multiline: <class 'bool'> = False,
    min_lines: typing.Optional[int] = None,
    max_lines: typing.Optional[int] = None,
    max_length: typing.Optional[int] = None,
    password: <class 'bool'> = False,
    can_reveal_password: <class 'bool'> = False,
    read_only: <class 'bool'> = False,
    shift_enter: <class 'bool'> = False,
    text_align: typing.Optional[flet.controls.types.TextAlign] = None,
    autofocus: <class 'bool'> = False,
    capitalization: typing.Optional[flet.controls.material.textfield.TextCapitalization] = None,
    autocorrect: <class 'bool'> = True,
    enable_suggestions: <class 'bool'> = True,
    smart_dashes_type: <class 'bool'> = True,
    smart_quotes_type: <class 'bool'> = True,
    show_cursor: <class 'bool'> = True,
    cursor_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    cursor_error_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    cursor_width: typing.Union[int, float] = 2.0,
    cursor_height: typing.Union[int, float, NoneType] = None,
    cursor_radius: typing.Union[int, float, NoneType] = None,
    selection_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    input_filter: typing.Optional[flet.controls.material.textfield.InputFilter] = None,
    obscuring_character: <class 'str'> = •,
    enable_interactive_selection: <class 'bool'> = True,
    enable_ime_personalized_learning: <class 'bool'> = True,
    can_request_focus: <class 'bool'> = True,
    ignore_pointers: <class 'bool'> = False,
    enable_stylus_handwriting: <class 'bool'> = True,
    animate_cursor_opacity: typing.Optional[bool] = None,
    always_call_on_tap: <class 'bool'> = False,
    scroll_padding: typing.Union[int, float, flet.controls.padding.Padding] = 20,
    clip_behavior: <enum 'ClipBehavior'> = ClipBehavior.HARD_EDGE,
    keyboard_brightness: typing.Optional[flet.controls.types.Brightness] = None,
    mouse_cursor: typing.Optional[flet.controls.types.MouseCursor] = None,
    strut_style: typing.Optional[flet.controls.text_style.StrutStyle] = None,
    autofill_hints: typing.Union[flet.controls.core.autofill_group.AutofillHint, list[flet.controls.core.autofill_group.AutofillHint], NoneType] = None,
    on_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextField')]], typing.Any], NoneType] = None,
    on_selection_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.core.text.TextSelectionChangeEvent[ForwardRef('TextField')]], typing.Any], NoneType] = None,
    on_click: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextField')]], typing.Any], NoneType] = None,
    on_submit: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextField')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextField')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextField')]], typing.Any], NoneType] = None,
    on_tap_outside: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextField')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
    text_size: typing.Union[int, float, NoneType] = None,
    text_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    text_vertical_align: typing.Union[flet.controls.types.VerticalAlignment, int, float, NoneType] = None,
    label: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    label_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    border: <enum 'InputBorder'> = InputBorder.OUTLINE,
    color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    border_radius: typing.Union[int, float, flet.controls.border_radius.BorderRadius, NoneType] = None,
    border_width: typing.Union[int, float, NoneType] = None,
    border_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    focused_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    focused_bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    focused_border_width: typing.Union[int, float, NoneType] = None,
    focused_border_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    content_padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    dense: typing.Optional[bool] = None,
    filled: typing.Optional[bool] = None,
    fill_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    focus_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    align_label_with_hint: typing.Optional[bool] = None,
    hover_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    hint_text: typing.Optional[str] = None,
    hint_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    hint_fade_duration: typing.Union[flet.controls.duration.Duration, int, NoneType] = None,
    hint_max_lines: typing.Optional[int] = None,
    helper: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    helper_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    helper_max_lines: typing.Optional[int] = None,
    counter: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    counter_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    error: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    error_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    error_max_lines: typing.Optional[int] = None,
    prefix: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    prefix_icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    prefix_icon_size_constraints: typing.Optional[flet.controls.box.BoxConstraints] = None,
    prefix_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    suffix: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    suffix_icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    suffix_icon_size_constraints: typing.Optional[flet.controls.box.BoxConstraints] = None,
    size_constraints: typing.Optional[flet.controls.box.BoxConstraints] = None,
    collapsed: typing.Optional[bool] = None,
    fit_parent_size: typing.Optional[bool] = None,
    suffix_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_change` -> flet.controls.control_event.Event
* `on_selection_change` -> flet.controls.core.text.TextSelectionChangeEvent
* `on_click` -> flet.controls.control_event.Event
* `on_submit` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_tap_outside` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `focus`, `init`, `is_isolated`

---

## Checkbox
**Module:** `flet.controls.material.checkbox`

### Constructor Parameters
```python
Checkbox(
    label: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    value: typing.Optional[bool] = False,
    label_position: <enum 'LabelPosition'> = LabelPosition.RIGHT,
    label_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    tristate: <class 'bool'> = False,
    autofocus: <class 'bool'> = False,
    fill_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, dict[flet.controls.control_state.ControlState, typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors]], NoneType] = None,
    overlay_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, dict[flet.controls.control_state.ControlState, typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors]], NoneType] = None,
    check_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    active_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    hover_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    focus_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    semantics_label: typing.Optional[str] = None,
    shape: typing.Optional[flet.controls.buttons.OutlinedBorder] = None,
    splash_radius: typing.Union[int, float, NoneType] = None,
    border_side: typing.Union[flet.controls.border.BorderSide, dict[flet.controls.control_state.ControlState, flet.controls.border.BorderSide], NoneType] = None,
    error: <class 'bool'> = False,
    visual_density: typing.Optional[flet.controls.types.VisualDensity] = None,
    mouse_cursor: typing.Optional[flet.controls.types.MouseCursor] = None,
    on_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Checkbox')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Checkbox')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Checkbox')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_change` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`

---

## Slider
**Module:** `flet.controls.material.slider`

### Constructor Parameters
```python
Slider(
    value: typing.Union[int, float, NoneType] = None,
    label: typing.Optional[str] = None,
    min: typing.Union[int, float] = 0.0,
    max: typing.Union[int, float] = 1.0,
    divisions: typing.Optional[int] = None,
    round: <class 'int'> = 0,
    autofocus: <class 'bool'> = False,
    active_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    inactive_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    thumb_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    interaction: typing.Optional[flet.controls.material.slider.SliderInteraction] = None,
    secondary_active_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    overlay_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, dict[flet.controls.control_state.ControlState, typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors]], NoneType] = None,
    secondary_track_value: typing.Union[int, float, NoneType] = None,
    mouse_cursor: typing.Optional[flet.controls.types.MouseCursor] = None,
    padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    year_2023: typing.Optional[bool] = None,
    on_change: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Slider')]], typing.Any], NoneType] = None,
    on_change_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Slider')]], typing.Any], NoneType] = None,
    on_change_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Slider')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Slider')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Slider')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_change` -> flet.controls.control_event.Event
* `on_change_start` -> flet.controls.control_event.Event
* `on_change_end` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`

---

## Button
**Module:** `flet.controls.material.button`

### Constructor Parameters
```python
Button(
    content: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    icon_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    elevation: typing.Union[int, float] = 1,
    style: typing.Optional[flet.controls.buttons.ButtonStyle] = None,
    autofocus: typing.Optional[bool] = None,
    clip_behavior: typing.Optional[flet.controls.types.ClipBehavior] = None,
    url: typing.Union[str, flet.controls.types.Url, NoneType] = None,
    on_click: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_hover: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_click` -> flet.controls.control_event.Event
* `on_long_press` -> flet.controls.control_event.Event
* `on_hover` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `focus`, `init`, `is_isolated`

---

## IconButton
**Module:** `flet.controls.material.icon_button`

### Constructor Parameters
```python
IconButton(
    icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    icon_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    icon_size: typing.Union[int, float, NoneType] = None,
    selected: typing.Optional[bool] = None,
    selected_icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    selected_icon_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    highlight_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    style: typing.Optional[flet.controls.buttons.ButtonStyle] = None,
    autofocus: <class 'bool'> = False,
    disabled_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    hover_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    focus_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    splash_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    splash_radius: typing.Union[int, float, NoneType] = None,
    alignment: typing.Optional[flet.controls.alignment.Alignment] = None,
    padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    enable_feedback: typing.Optional[bool] = None,
    url: typing.Union[str, flet.controls.types.Url, NoneType] = None,
    mouse_cursor: typing.Optional[flet.controls.types.MouseCursor] = None,
    visual_density: typing.Optional[flet.controls.types.VisualDensity] = None,
    size_constraints: typing.Optional[flet.controls.box.BoxConstraints] = None,
    on_click: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('IconButton')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('IconButton')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('IconButton')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_click` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `focus`, `init`, `is_isolated`

---

## AlertDialog
**Module:** `flet.controls.material.alert_dialog`

### Constructor Parameters
```python
AlertDialog(
    content: typing.Optional[flet.controls.control.Control] = None,
    modal: <class 'bool'> = False,
    title: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    actions: list[flet.controls.control.Control] = <factory>,
    bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    elevation: typing.Union[int, float, NoneType] = None,
    icon: typing.Optional[flet.controls.control.Control] = None,
    title_padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    content_padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    actions_padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    actions_alignment: typing.Optional[flet.controls.types.MainAxisAlignment] = None,
    shape: typing.Optional[flet.controls.buttons.OutlinedBorder] = None,
    inset_padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    icon_padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    action_button_padding: typing.Union[int, float, flet.controls.padding.Padding, NoneType] = None,
    shadow_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    icon_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    scrollable: <class 'bool'> = False,
    actions_overflow_button_spacing: typing.Union[int, float, NoneType] = None,
    alignment: typing.Optional[flet.controls.alignment.Alignment] = None,
    content_text_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    title_text_style: typing.Optional[flet.controls.text_style.TextStyle] = None,
    clip_behavior: <enum 'ClipBehavior'> = ClipBehavior.NONE,
    semantics_label: typing.Optional[str] = None,
    barrier_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    open: <class 'bool'> = False,
    on_dismiss: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('DialogControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_dismiss` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`

---

## GestureDetector
**Module:** `flet.controls.core.gesture_detector`

### Constructor Parameters
```python
GestureDetector(
    content: typing.Optional[flet.controls.control.Control] = None,
    mouse_cursor: typing.Optional[flet.controls.types.MouseCursor] = None,
    drag_interval: <class 'int'> = 0,
    hover_interval: <class 'int'> = 0,
    multi_tap_touches: <class 'int'> = 0,
    exclude_from_semantics: <class 'bool'> = False,
    on_force_press_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ForcePressEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_force_press_peak: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ForcePressEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_force_press_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ForcePressEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_force_press_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ForcePressEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    trackpad_scroll_causes_scale: <class 'bool'> = False,
    allowed_devices: typing.Optional[list[flet.controls.types.PointerDeviceType]] = None,
    on_tap: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tap_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tap_up: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tap_move: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapMoveEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tap_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_multi_tap: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_multi_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_tap: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_tap_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_tap_up: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_tap_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_tap_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_tap_up: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_tap_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_long_press_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressDownEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_long_press_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_long_press_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressStartEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_long_press_move_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressMoveUpdateEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_long_press_up: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_long_press_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_long_press_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressDownEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_long_press_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_long_press_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressStartEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_long_press_move_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressMoveUpdateEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_long_press_up: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_secondary_long_press_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_long_press_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressDownEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_long_press_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_long_press_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressStartEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_long_press_move_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressMoveUpdateEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_long_press_up: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_tertiary_long_press_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.LongPressEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_double_tap: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_double_tap_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.TapEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_double_tap_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_horizontal_drag_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragDownEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_horizontal_drag_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragStartEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_horizontal_drag_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragUpdateEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_horizontal_drag_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_horizontal_drag_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_vertical_drag_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragDownEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_vertical_drag_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragStartEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_vertical_drag_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragUpdateEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_vertical_drag_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_vertical_drag_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_pan_down: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragDownEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_pan_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragStartEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_pan_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragUpdateEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_pan_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.DragEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_pan_cancel: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_right_pan_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.PointerEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_right_pan_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.PointerEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_right_pan_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.PointerEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_scale_start: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ScaleStartEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_scale_update: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ScaleUpdateEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_scale_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ScaleEndEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_hover: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.PointerEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_enter: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.PointerEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_exit: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.PointerEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    on_scroll: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.events.ScrollEvent[ForwardRef('GestureDetector')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_force_press_start` -> flet.controls.events.ForcePressEvent
* `on_force_press_peak` -> flet.controls.events.ForcePressEvent
* `on_force_press_update` -> flet.controls.events.ForcePressEvent
* `on_force_press_end` -> flet.controls.events.ForcePressEvent
* `on_tap` -> flet.controls.control_event.Event
* `on_tap_down` -> flet.controls.events.TapEvent
* `on_tap_up` -> flet.controls.events.TapEvent
* `on_tap_move` -> flet.controls.events.TapMoveEvent
* `on_tap_cancel` -> flet.controls.control_event.Event
* `on_multi_tap` -> flet.controls.events.TapEvent
* `on_multi_long_press` -> flet.controls.events.LongPressEndEvent
* `on_secondary_tap` -> flet.controls.control_event.Event
* `on_secondary_tap_down` -> flet.controls.events.TapEvent
* `on_secondary_tap_up` -> flet.controls.events.TapEvent
* `on_secondary_tap_cancel` -> flet.controls.control_event.Event
* `on_tertiary_tap_down` -> flet.controls.events.TapEvent
* `on_tertiary_tap_up` -> flet.controls.events.TapEvent
* `on_tertiary_tap_cancel` -> flet.controls.control_event.Event
* `on_long_press_down` -> flet.controls.events.LongPressDownEvent
* `on_long_press_cancel` -> flet.controls.control_event.Event
* `on_long_press` -> flet.controls.control_event.Event
* `on_long_press_start` -> flet.controls.events.LongPressStartEvent
* `on_long_press_move_update` -> flet.controls.events.LongPressMoveUpdateEvent
* `on_long_press_up` -> flet.controls.control_event.Event
* `on_long_press_end` -> flet.controls.events.LongPressEndEvent
* `on_secondary_long_press_down` -> flet.controls.events.LongPressDownEvent
* `on_secondary_long_press_cancel` -> flet.controls.control_event.Event
* `on_secondary_long_press` -> flet.controls.control_event.Event
* `on_secondary_long_press_start` -> flet.controls.events.LongPressStartEvent
* `on_secondary_long_press_move_update` -> flet.controls.events.LongPressMoveUpdateEvent
* `on_secondary_long_press_up` -> flet.controls.control_event.Event
* `on_secondary_long_press_end` -> flet.controls.events.LongPressEndEvent
* `on_tertiary_long_press_down` -> flet.controls.events.LongPressDownEvent
* `on_tertiary_long_press_cancel` -> flet.controls.control_event.Event
* `on_tertiary_long_press` -> flet.controls.control_event.Event
* `on_tertiary_long_press_start` -> flet.controls.events.LongPressStartEvent
* `on_tertiary_long_press_move_update` -> flet.controls.events.LongPressMoveUpdateEvent
* `on_tertiary_long_press_up` -> flet.controls.control_event.Event
* `on_tertiary_long_press_end` -> flet.controls.events.LongPressEndEvent
* `on_double_tap` -> flet.controls.control_event.Event
* `on_double_tap_down` -> flet.controls.events.TapEvent
* `on_double_tap_cancel` -> flet.controls.control_event.Event
* `on_horizontal_drag_down` -> flet.controls.events.DragDownEvent
* `on_horizontal_drag_start` -> flet.controls.events.DragStartEvent
* `on_horizontal_drag_update` -> flet.controls.events.DragUpdateEvent
* `on_horizontal_drag_end` -> flet.controls.events.DragEndEvent
* `on_horizontal_drag_cancel` -> flet.controls.control_event.Event
* `on_vertical_drag_down` -> flet.controls.events.DragDownEvent
* `on_vertical_drag_start` -> flet.controls.events.DragStartEvent
* `on_vertical_drag_update` -> flet.controls.events.DragUpdateEvent
* `on_vertical_drag_end` -> flet.controls.events.DragEndEvent
* `on_vertical_drag_cancel` -> flet.controls.control_event.Event
* `on_pan_down` -> flet.controls.events.DragDownEvent
* `on_pan_start` -> flet.controls.events.DragStartEvent
* `on_pan_update` -> flet.controls.events.DragUpdateEvent
* `on_pan_end` -> flet.controls.events.DragEndEvent
* `on_pan_cancel` -> flet.controls.control_event.Event
* `on_right_pan_start` -> flet.controls.events.PointerEvent
* `on_right_pan_update` -> flet.controls.events.PointerEvent
* `on_right_pan_end` -> flet.controls.events.PointerEvent
* `on_scale_start` -> flet.controls.events.ScaleStartEvent
* `on_scale_update` -> flet.controls.events.ScaleUpdateEvent
* `on_scale_end` -> flet.controls.events.ScaleEndEvent
* `on_hover` -> flet.controls.events.PointerEvent
* `on_enter` -> flet.controls.events.PointerEvent
* `on_exit` -> flet.controls.events.PointerEvent
* `on_scroll` -> flet.controls.events.ScrollEvent
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`

---

## Clipboard
**Module:** `flet.controls.services.clipboard`

### Constructor Parameters
```python
Clipboard(
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
None

### Key Methods
`before_event`, `before_update`, `get`, `init`, `is_isolated`, `set`

---

## FilePicker
**Module:** `flet.controls.services.file_picker`

### Constructor Parameters
```python
FilePicker(
    on_upload: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.services.file_picker.FilePickerUploadEvent], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_upload` -> flet.controls.services.file_picker.FilePickerUploadEvent

### Key Methods
`before_event`, `before_update`, `init`, `is_isolated`, `pick_files`, `save_file`, `upload`

---

## Alignment
**Module:** `flet.controls.alignment`

### Constructor Parameters
```python
Alignment(
    x: typing.Union[int, float] = <class 'inspect._empty'>,
    y: typing.Union[int, float] = <class 'inspect._empty'>,
)
```

### Public Attributes
`BOTTOM_CENTER`, `BOTTOM_LEFT`, `BOTTOM_RIGHT`, `CENTER`, `CENTER_LEFT`, `CENTER_RIGHT`, `TOP_CENTER`, `TOP_LEFT`, `TOP_RIGHT`

### Events
None

### Key Methods
`copy`

---

## ElevatedButton
**Module:** `flet.controls.material.elevated_button`

### Constructor Parameters
```python
ElevatedButton(
    content: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    icon_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    bgcolor: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    elevation: typing.Union[int, float] = 1,
    style: typing.Optional[flet.controls.buttons.ButtonStyle] = None,
    autofocus: typing.Optional[bool] = None,
    clip_behavior: typing.Optional[flet.controls.types.ClipBehavior] = None,
    url: typing.Union[str, flet.controls.types.Url, NoneType] = None,
    on_click: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_hover: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('Button')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_click` -> flet.controls.control_event.Event
* `on_long_press` -> flet.controls.control_event.Event
* `on_hover` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `focus`, `init`, `is_isolated`

---

## OutlinedButton
**Module:** `flet.controls.material.outlined_button`

### Constructor Parameters
```python
OutlinedButton(
    content: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    icon_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    style: typing.Optional[flet.controls.buttons.ButtonStyle] = None,
    autofocus: <class 'bool'> = False,
    clip_behavior: <enum 'ClipBehavior'> = ClipBehavior.NONE,
    url: typing.Union[str, flet.controls.types.Url, NoneType] = None,
    on_click: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('OutlinedButton')]], typing.Any], NoneType] = None,
    on_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('OutlinedButton')]], typing.Any], NoneType] = None,
    on_hover: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('OutlinedButton')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('OutlinedButton')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('OutlinedButton')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_click` -> flet.controls.control_event.Event
* `on_long_press` -> flet.controls.control_event.Event
* `on_hover` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `focus`, `init`, `is_isolated`

---

## TextButton
**Module:** `flet.controls.material.text_button`

### Constructor Parameters
```python
TextButton(
    content: typing.Union[str, ForwardRef('Control'), NoneType] = None,
    icon: typing.Union[flet.controls.icon_data.IconData, ForwardRef('Control'), NoneType] = None,
    icon_color: typing.Union[str, flet.controls.colors.Colors, flet.controls.cupertino.cupertino_colors.CupertinoColors, NoneType] = None,
    style: typing.Optional[flet.controls.buttons.ButtonStyle] = None,
    autofocus: <class 'bool'> = False,
    url: typing.Union[str, flet.controls.types.Url, NoneType] = None,
    clip_behavior: <enum 'ClipBehavior'> = ClipBehavior.NONE,
    on_click: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextButton')]], typing.Any], NoneType] = None,
    on_long_press: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextButton')]], typing.Any], NoneType] = None,
    on_hover: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextButton')]], typing.Any], NoneType] = None,
    on_focus: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextButton')]], typing.Any], NoneType] = None,
    on_blur: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('TextButton')]], typing.Any], NoneType] = None,
    data: typing.Any = None,
    key: typing.Union[flet.controls.keys.ValueKey, flet.controls.keys.ScrollKey, str, int, float, bool, NoneType] = None,
    ref: dataclasses.InitVar[typing.Optional[flet.controls.ref.Ref[ForwardRef('BaseControl')]]] = None,
    expand: typing.Union[bool, int, NoneType] = None,
    expand_loose: <class 'bool'> = False,
    col: typing.Union[dict[typing.Union[str, flet.controls.types.ResponsiveRowBreakpoint], typing.Union[int, float]], int, float] = 12,
    opacity: typing.Union[int, float] = 1.0,
    tooltip: typing.Union[str, flet.controls.material.tooltip.Tooltip, NoneType] = None,
    badge: typing.Union[str, flet.controls.material.badge.Badge, NoneType] = None,
    visible: <class 'bool'> = True,
    disabled: <class 'bool'> = False,
    rtl: <class 'bool'> = False,
    adaptive: typing.Optional[bool] = None,
    width: typing.Union[int, float, NoneType] = None,
    height: typing.Union[int, float, NoneType] = None,
    left: typing.Union[int, float, NoneType] = None,
    top: typing.Union[int, float, NoneType] = None,
    right: typing.Union[int, float, NoneType] = None,
    bottom: typing.Union[int, float, NoneType] = None,
    align: typing.Optional[flet.controls.alignment.Alignment] = None,
    margin: typing.Union[int, float, flet.controls.margin.Margin, NoneType] = None,
    rotate: typing.Union[int, float, flet.controls.transform.Rotate, NoneType] = None,
    scale: typing.Union[int, float, flet.controls.transform.Scale, NoneType] = None,
    offset: typing.Union[flet.controls.transform.Offset, tuple[typing.Union[int, float], typing.Union[int, float]], NoneType] = None,
    aspect_ratio: typing.Union[int, float, NoneType] = None,
    animate_opacity: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_size: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_position: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_align: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_margin: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_rotation: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_scale: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    animate_offset: typing.Union[bool, int, flet.controls.animation.Animation, NoneType] = None,
    on_animation_end: typing.Union[typing.Callable[[], typing.Any], typing.Callable[[flet.controls.control_event.Event[ForwardRef('LayoutControl')]], typing.Any], NoneType] = None,
)
```

### Public Attributes
`page`, `parent`

### Events
* `on_click` -> flet.controls.control_event.Event
* `on_long_press` -> flet.controls.control_event.Event
* `on_hover` -> flet.controls.control_event.Event
* `on_focus` -> flet.controls.control_event.Event
* `on_blur` -> flet.controls.control_event.Event
* `on_animation_end` -> flet.controls.control_event.Event

### Key Methods
`before_event`, `before_update`, `focus`, `init`, `is_isolated`

---

# Event Object Details

## AppLifecycleStateChangeEvent
* `state`: <enum 'AppLifecycleState'>
* `data`
* `page` (property)
* `target` (property)

## DragDownEvent
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `data`
* `page` (property)
* `target` (property)

## DragEndEvent
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `velocity`: <class 'flet.controls.transform.Offset'>
* `primary_velocity`: typing.Optional[float]
* `data`
* `page` (property)
* `primary_velocity`
* `target` (property)

## DragStartEvent
* `kind`: <enum 'PointerDeviceType'>
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `timestamp`: typing.Optional[flet.controls.duration.Duration]
* `data`
* `page` (property)
* `target` (property)
* `timestamp`

## DragUpdateEvent
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `local_delta`: typing.Optional[flet.controls.transform.Offset]
* `global_delta`: typing.Optional[flet.controls.transform.Offset]
* `primary_delta`: typing.Optional[float]
* `timestamp`: typing.Optional[flet.controls.duration.Duration]
* `data`
* `global_delta`
* `local_delta`
* `page` (property)
* `primary_delta`
* `target` (property)
* `timestamp`

## Event
* `name`: <class 'str'>
* `data`: typing.Optional[typing.Any]
* `control`: ~EventControlType
* `data`
* `page` (property)
* `target` (property)

## FilePickerUploadEvent
* `file_name`: <class 'str'>
* `progress`: typing.Optional[float]
* `error`: typing.Optional[str]
* `data`
* `error`
* `page` (property)
* `progress`
* `target` (property)

## ForcePressEvent
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `pressure`: <class 'float'>
* `data`
* `page` (property)
* `target` (property)

## KeyboardEvent
* `key`: <class 'str'>
* `shift`: <class 'bool'>
* `ctrl`: <class 'bool'>
* `alt`: <class 'bool'>
* `meta`: <class 'bool'>
* `data`
* `page` (property)
* `target` (property)

## LoginEvent
* `error`: typing.Optional[str]
* `error_description`: typing.Optional[str]
* `data`
* `page` (property)
* `target` (property)

## LongPressDownEvent
* `kind`: typing.Optional[flet.controls.types.PointerDeviceType]
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `data`
* `kind`
* `page` (property)
* `target` (property)

## LongPressEndEvent
* `local_position`: typing.Optional[flet.controls.transform.Offset]
* `global_position`: typing.Optional[flet.controls.transform.Offset]
* `velocity`: <class 'flet.controls.transform.Offset'>
* `data`
* `global_position`
* `local_position`
* `page` (property)
* `target` (property)

## LongPressMoveUpdateEvent
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `offset_from_origin`: <class 'flet.controls.transform.Offset'>
* `local_offset_from_origin`: <class 'flet.controls.transform.Offset'>
* `data`
* `page` (property)
* `target` (property)

## LongPressStartEvent
* `local_position`: typing.Optional[flet.controls.transform.Offset]
* `global_position`: typing.Optional[flet.controls.transform.Offset]
* `data`
* `global_position`
* `local_position`
* `page` (property)
* `target` (property)

## MultiViewAddEvent
* `view_id`: <class 'int'>
* `initial_data`: typing.Any
* `data`
* `page` (property)
* `target` (property)

## MultiViewRemoveEvent
* `view_id`: <class 'int'>
* `data`
* `page` (property)
* `target` (property)

## OnScrollEvent
* `event_type`: <enum 'ScrollType'>
* `pixels`: <class 'float'>
* `min_scroll_extent`: <class 'float'>
* `max_scroll_extent`: <class 'float'>
* `viewport_dimension`: <class 'float'>
* `scroll_delta`: typing.Optional[float]
* `direction`: typing.Optional[flet.controls.scrollable_control.ScrollDirection]
* `overscroll`: typing.Optional[float]
* `velocity`: typing.Optional[float]
* `data`
* `direction`
* `overscroll`
* `page` (property)
* `scroll_delta`
* `target` (property)
* `velocity`

## PageResizeEvent
* `width`: <class 'float'>
* `height`: <class 'float'>
* `data`
* `page` (property)
* `target` (property)

## PlatformBrightnessChangeEvent
* `brightness`: <enum 'Brightness'>
* `data`
* `page` (property)
* `target` (property)

## PointerEvent
* `kind`: <enum 'PointerDeviceType'>
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `timestamp`: <class 'flet.controls.duration.Duration'>
* `device`: <class 'float'>
* `pressure`: <class 'float'>
* `pressure_min`: <class 'float'>
* `pressure_max`: <class 'float'>
* `distance`: <class 'float'>
* `distance_max`: <class 'float'>
* `size`: <class 'float'>
* `radius_major`: <class 'float'>
* `radius_minor`: <class 'float'>
* `radius_min`: <class 'float'>
* `radius_max`: <class 'float'>
* `orientation`: <class 'float'>
* `tilt`: <class 'float'>
* `local_delta`: typing.Optional[flet.controls.transform.Offset]
* `global_delta`: typing.Optional[flet.controls.transform.Offset]
* `data`
* `global_delta`
* `local_delta`
* `page` (property)
* `target` (property)

## RouteChangeEvent
* `route`: <class 'str'>
* `data`
* `page` (property)
* `target` (property)

## ScaleEndEvent
* `pointer_count`: <class 'int'>
* `velocity`: <class 'flet.controls.transform.Offset'>
* `data`
* `page` (property)
* `target` (property)

## ScaleStartEvent
* `local_focal_point`: <class 'flet.controls.transform.Offset'>
* `global_focal_point`: <class 'flet.controls.transform.Offset'>
* `pointer_count`: <class 'int'>
* `timestamp`: typing.Optional[flet.controls.duration.Duration]
* `data`
* `page` (property)
* `target` (property)
* `timestamp`

## ScaleUpdateEvent
* `local_focal_point`: <class 'flet.controls.transform.Offset'>
* `global_focal_point`: <class 'flet.controls.transform.Offset'>
* `focal_point_delta`: <class 'flet.controls.transform.Offset'>
* `pointer_count`: <class 'int'>
* `horizontal_scale`: <class 'float'>
* `vertical_scale`: <class 'float'>
* `scale`: <class 'float'>
* `rotation`: <class 'float'>
* `timestamp`: typing.Optional[flet.controls.duration.Duration]
* `data`
* `page` (property)
* `target` (property)
* `timestamp`

## ScrollEvent
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `scroll_delta`: <class 'flet.controls.transform.Offset'>
* `data`
* `page` (property)
* `target` (property)

## TapEvent
* `kind`: typing.Optional[flet.controls.types.PointerDeviceType]
* `local_position`: typing.Optional[flet.controls.transform.Offset]
* `global_position`: typing.Optional[flet.controls.transform.Offset]
* `data`
* `global_position`
* `kind`
* `local_position`
* `page` (property)
* `target` (property)

## TapMoveEvent
* `kind`: <enum 'PointerDeviceType'>
* `local_position`: <class 'flet.controls.transform.Offset'>
* `global_position`: <class 'flet.controls.transform.Offset'>
* `delta`: <class 'flet.controls.transform.Offset'>
* `data`
* `page` (property)
* `target` (property)

## TextSelectionChangeEvent
* `selected_text`: <class 'str'>
* `selection`: <class 'flet.controls.core.text.TextSelection'>
* `cause`: typing.Optional[flet.controls.core.text.TextSelectionChangeCause]
* `cause`
* `data`
* `page` (property)
* `target` (property)

## ViewPopEvent
* `route`: <class 'str'>
* `view`: typing.Optional[flet.controls.core.view.View]
* `data`
* `page` (property)
* `target` (property)
* `view`

