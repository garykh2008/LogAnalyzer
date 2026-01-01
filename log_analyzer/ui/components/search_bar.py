import flet as ft
import asyncio

class SearchBar:
    def __init__(self, app):
        self.app = app
        self.search_input = None
        self.search_results_count = None
        self.search_bar_container = None
        self.history_button = None

    def build(self):
        colors = self.app._get_colors()

        self.search_input = ft.TextField(
            label="Find",
            height=30,
            text_size=12,
            content_padding=5,
            width=200,
            on_submit=self.app.on_find_next,
            border_color=ft.Colors.BLUE
        )
        self.search_results_count = ft.Text(value="0/0", size=12, color=colors["text"])

        self.history_button = ft.PopupMenuButton(
            icon=ft.Icons.HISTORY,
            tooltip="Search History",
            icon_size=16,
            items=[]
        )
        self.update_history_menu(update=False)

        async def toggle_case(e):
            self.app.search_case_sensitive = not self.app.search_case_sensitive
            e.control.style = ft.ButtonStyle(color=ft.Colors.BLUE if self.app.search_case_sensitive else ft.Colors.GREY)
            e.control.update()
            self.app.search_query = "" # Force re-search
            await self.app.perform_search()

        async def toggle_wrap(e):
            self.app.search_wrap = not self.app.search_wrap
            e.control.style = ft.ButtonStyle(color=ft.Colors.BLUE if self.app.search_wrap else ft.Colors.GREY)
            e.control.update()

        is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK

        self.search_bar_container = ft.Container(
            content=ft.Row([
                self.search_input,
                self.history_button,
                ft.IconButton(ft.Icons.ABC, tooltip="Match Case", icon_size=16, on_click=toggle_case,
                              style=ft.ButtonStyle(color=ft.Colors.GREY)),
                ft.IconButton(ft.Icons.KEYBOARD_RETURN, tooltip="Wrap Around", icon_size=16, on_click=toggle_wrap,
                              style=ft.ButtonStyle(color=ft.Colors.BLUE)),
                ft.IconButton(ft.Icons.ARROW_UPWARD, icon_size=16, tooltip="Previous", on_click=self.app.on_find_prev),
                ft.IconButton(ft.Icons.ARROW_DOWNWARD, icon_size=16, tooltip="Next", on_click=self.app.on_find_next),
                self.search_results_count,
                ft.IconButton(ft.Icons.CLOSE, icon_size=16, on_click=self.app.hide_search_bar),
            ], spacing=5),
            bgcolor=colors["search_bg"],
            padding=5,
            border_radius=8,
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK if is_dark else ft.Colors.GREY_400)),
            visible=False,
        )
        return self.search_bar_container

    def update_colors(self):
        colors = self.app._get_colors()
        is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK

        if self.search_bar_container:
            self.search_bar_container.bgcolor = colors["search_bg"]
            self.search_bar_container.shadow = ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK if is_dark else ft.Colors.GREY_400)
            )
        if self.search_results_count:
            self.search_results_count.color = colors["text"]

    def update_history_menu(self, update=True):
        if not self.history_button: return

        history_items = []
        if not self.app.search_history:
            history_items.append(ft.PopupMenuItem(content=ft.Text("No history"), disabled=True))
        else:
            for query in self.app.search_history:
                # Capture query in closure
                def on_history_click(e, q=query):
                    self.search_input.value = q
                    # Trigger search logic
                    self.search_input.focus()
                    asyncio.create_task(self.app.perform_search(backward=False))

                history_items.append(
                    ft.PopupMenuItem(
                        content=ft.Text(query),
                        on_click=on_history_click
                    )
                )

        self.history_button.items = history_items
        if update:
            self.history_button.update()
