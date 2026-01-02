import flet as ft

class TopBar:
    def __init__(self, app):
        self.app = app
        self.recent_files_submenu = None
        self.menu_bar = None
        self.app_title_text = None
        self.top_bar_row = None
        self.container = None

    def build(self):
        colors = self.app._get_colors()
        is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK

        # 建立最近檔案子選單
        self.recent_files_submenu = ft.SubmenuButton(
            content=ft.Text("Recent Files"),
            controls=[]
        )
        self.app.update_recent_files_menu() # Calls app logic to populate

        # 建立主選單列 - 背景與父容器保持一致
        self.menu_bar = ft.MenuBar(
            expand=True,
            style=ft.MenuStyle(
                bgcolor=colors["top_bar_bg"],
                alignment=ft.Alignment(-1, -1),
                mouse_cursor=ft.MouseCursor.CLICK,
                shadow_color=ft.Colors.TRANSPARENT,
            ),
            controls=[
                ft.SubmenuButton(
                    content=ft.Text("File", weight=ft.FontWeight.W_500),
                    controls=[
                        ft.MenuItemButton(
                            content=ft.Text("Open File..."),
                            leading=ft.Icon(ft.Icons.FOLDER_OPEN, size=18),
                            on_click=self.app.on_open_file_click
                        ),
                        self.recent_files_submenu,
                        ft.MenuItemButton(
                            content=ft.Text("Load Filters"),
                            leading=ft.Icon(ft.Icons.FILE_OPEN_OUTLINED, size=18),
                            on_click=self.app.import_tat_filters
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Save Filters"),
                            leading=ft.Icon(ft.Icons.SAVE, size=18),
                            on_click=self.app.save_tat_filters
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Save Filters As..."),
                            leading=ft.Icon(ft.Icons.SAVE_AS, size=18),
                            on_click=self.app.save_tat_filters_as
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Exit"),
                            leading=ft.Icon(ft.Icons.EXIT_TO_APP, size=18),
                            on_click=self.app.exit_app
                        )
                    ]
                ),
                ft.SubmenuButton(
                    content=ft.Text("View", weight=ft.FontWeight.W_500),
                    controls=[
                        ft.MenuItemButton(
                            content=ft.Text("Toggle Sidebar"),
                            on_click=lambda _: self.app.toggle_sidebar()
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Toggle Dark/Light Mode"),
                            on_click=self.app.toggle_theme
                        ),
                        ft.SubmenuButton(
                            content=ft.Text("Sidebar Position"),
                            controls=[
                                ft.MenuItemButton(
                                    content=ft.Text("Left"),
                                    on_click=lambda _: self.app.change_sidebar_position("left")
                                ),
                                ft.MenuItemButton(
                                    content=ft.Text("Right"),
                                    on_click=lambda _: self.app.change_sidebar_position("right")
                                ),
                                ft.MenuItemButton(
                                    content=ft.Text("Bottom"),
                                    on_click=lambda _: self.app.change_sidebar_position("bottom")
                                ),
                            ]
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Show Filtered Only"),
                            leading=ft.Icon(ft.Icons.FILTER_ALT, size=18),
                            on_click=self.app.toggle_show_filtered
                        )
                    ]
                ),
                ft.SubmenuButton(
                    content=ft.Text("Help", weight=ft.FontWeight.W_500),
                    controls=[
                        ft.MenuItemButton(
                            content=ft.Text("Keyboard Shortcuts"),
                            leading=ft.Icon(ft.Icons.KEYBOARD, size=18),
                            on_click=self.app.show_keyboard_shortcuts_dialog
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Documentation"),
                            leading=ft.Icon(ft.Icons.DESCRIPTION, size=18),
                            on_click=self.app.open_documentation
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("About"),
                            leading=ft.Icon(ft.Icons.INFO_OUTLINE, size=18),
                            on_click=self.app.show_about_dialog
                        )
                    ]
                )
            ]
        )

        self.app_title_text = ft.Text("LogAnalyzer", weight=ft.FontWeight.BOLD, size=14, color=colors["text"])

        # 組裝頂部橫列
        self.top_bar_row = ft.Row([
            ft.Container(
                content=ft.Icon(ft.Icons.ANALYTICS, color=colors["text"], size=20),
                padding=ft.padding.only(left=15, right=5)
            ),
            self.app_title_text,
            ft.Container(width=15), # 固定的視覺間隔
            self.menu_bar
        ], spacing=0, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # 返回封裝好的頂部容器
        self.container = ft.Container(
            content=self.top_bar_row,
            bgcolor=colors["top_bar_bg"],
            padding=0,
            height=45,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.4 if is_dark else 0.2, ft.Colors.BLACK),
                offset=ft.Offset(0, 2)
            )
        )
        return self.container

    def update_colors(self):
        colors = self.app._get_colors()
        is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK

        if self.container:
            self.container.bgcolor = colors["top_bar_bg"]
            self.container.shadow = ft.BoxShadow(
                spread_radius=1,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.4 if is_dark else 0.2, ft.Colors.BLACK),
                offset=ft.Offset(0, 2)
            )

        if self.menu_bar:
            self.menu_bar.style.bgcolor = colors["top_bar_bg"]

        if self.app_title_text:
            self.app_title_text.color = colors["text"]

        if self.top_bar_row:
            for control in self.top_bar_row.controls:
                if isinstance(control, ft.Container) and isinstance(control.content, ft.Icon):
                    control.content.color = colors["text"]
