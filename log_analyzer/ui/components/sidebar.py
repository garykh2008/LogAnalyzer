import flet as ft

class Sidebar:
    def __init__(self, app):
        self.app = app
        self.filter_list_view = None
        self.add_filter_btn = None
        self.container = None

    def build(self):
        colors = self.app._get_colors()
        pos = self.app.config.get("sidebar_position", "left")

        # 根據位置決定寬高
        is_bottom = pos == "bottom"
        sidebar_width = 280 if not is_bottom else None
        sidebar_height = None if not is_bottom else 200

        self.filter_list_view = ft.ReorderableListView(
            expand=True,
            spacing=2,
            padding=ft.padding.only(top=10),
            on_reorder=self.app.on_filter_reorder,
        )

        is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK

        # 在底部模式下，Add Filter 按鈕可以跟標題排在同一行
        self.add_filter_btn = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ADD, size=16),
                    ft.Text("Add Filter", size=12),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            height=30,
            on_click=self.app.on_add_filter_click,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: ft.Colors.BLUE_700 if is_dark else ft.Colors.BLUE_50,
                    ft.ControlState.HOVERED: ft.Colors.BLUE_600 if is_dark else ft.Colors.BLUE_100,
                },
                color={
                    ft.ControlState.DEFAULT: ft.Colors.WHITE if is_dark else ft.Colors.BLUE_700,
                },
                padding=ft.padding.symmetric(horizontal=10),
                shape=ft.RoundedRectangleBorder(radius=6)
            )
        )

        title_row = ft.Row([
            ft.Text("Filters", size=16, weight=ft.FontWeight.BOLD, color=colors["text"]),
            ft.VerticalDivider(width=10, color=ft.Colors.TRANSPARENT) if is_bottom else ft.Container(),
            self.add_filter_btn
        ], alignment=ft.MainAxisAlignment.START)

        # Dummy focus target for Sidebar
        self.sidebar_focus_target = ft.Button(
            content=ft.Text(""), width=1, height=1, opacity=0,
            style=ft.ButtonStyle(overlay_color=ft.Colors.TRANSPARENT)
        )

        self.container = ft.Container(
            width=sidebar_width,
            height=sidebar_height,
            visible=False,
            bgcolor=colors["sidebar_bg"],
            padding=ft.padding.all(15),
            content=ft.GestureDetector(
                content=ft.Stack([
                    ft.Column([
                        title_row,
                        self.filter_list_view,
                    ], spacing=10),
                    self.sidebar_focus_target
                ]),
                on_tap_down=lambda _: self.app.set_active_pane("filter")
            )
        )
        return self.container

    def update_colors(self):
        colors = self.app._get_colors()
        is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK

        if self.container:
            self.container.bgcolor = colors["sidebar_bg"]
            if isinstance(self.container.content, ft.Column):
                 for control in self.container.content.controls:
                     if isinstance(control, ft.Text):
                         control.color = colors["text"]
                     elif isinstance(control, ft.Row):
                         for sub_control in control.controls:
                             if isinstance(sub_control, ft.Text):
                                 sub_control.color = colors["text"]
                                 sub_control.update()

            # Update Add Filter Button Style
            if self.add_filter_btn:
                self.add_filter_btn.style = ft.ButtonStyle(
                    bgcolor={
                        ft.ControlState.DEFAULT: ft.Colors.BLUE_700 if is_dark else ft.Colors.BLUE_50,
                        ft.ControlState.HOVERED: ft.Colors.BLUE_600 if is_dark else ft.Colors.BLUE_100,
                    },
                    color={
                        ft.ControlState.DEFAULT: ft.Colors.WHITE if is_dark else ft.Colors.BLUE_700,
                    },
                    padding=ft.padding.symmetric(horizontal=10),
                    shape=ft.RoundedRectangleBorder(radius=6)
                )
                self.add_filter_btn.update()
