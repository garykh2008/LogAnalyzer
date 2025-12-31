import flet as ft
from log_analyzer.core.filter import Filter
from log_analyzer.utils.helpers import adjust_color_for_theme

class Dialogs:
    def __init__(self, app):
        self.app = app
        self.dialog = None

    def show_unsaved_changes_dialog(self, on_save, on_dont_save, on_cancel):
        self.dialog = ft.AlertDialog(
            title=ft.Text("Unsaved Changes"),
            content=ft.Text("Filters have been modified. Do you want to save changes?"),
            actions=[
                ft.TextButton("Save", on_click=on_save),
                ft.TextButton("Don't Save", on_click=on_dont_save),
                ft.TextButton("Cancel", on_click=on_cancel),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.show_dialog(self.dialog)

    def show_keyboard_shortcuts_dialog(self):
        shortcuts_data = [
            ("General & View", ""),
            ("Ctrl + B", "Toggle Sidebar (Left/Right/Bottom)"),
            ("Ctrl + F", "Show Find Bar"),
            ("Ctrl + H", "Toggle 'Show Filtered Only'"),
            ("Ctrl + C", "Copy selected lines"),
            ("Esc", "Hide Find Bar"),
            ("", ""),
            ("Navigation", ""),
            ("Arrow Up/Down", "Move selection up/down (1 line)"),
            ("Page Up/Down", "Move selection up/down (page)"),
            ("Home/End", "Jump to first/last line"),
            ("Ctrl + Arrow Up/Down", "Move selection faster"),
            ("F2", "Find previous occurrence"),
            ("F3", "Find next occurrence"),
            ("Shift + F3", "Find previous occurrence"), # Flet doesn't distinguish F3/Shift+F3
            ("Enter (in Find)", "Find next occurrence"),
            ("Shift + Enter (in Find)", "Find previous occurrence"),
            ("", ""),
            ("Filter List", ""),
            ("Double-Click (filter)", "Edit filter"),
            ("Right-Click (filter)", "Open filter context menu"),
            ("", ""),
            ("Log View", ""),
            ("Double-Click (log line)", "Add Filter from selected line"),
            ("Right-Click (log line)", "Open log line context menu"),
            ("", ""),
            ("Dialogs", ""),
            ("Escape", "Close dialog"),
        ]

        items = []
        for key, desc in shortcuts_data:
            if not key and not desc:
                items.append(ft.Divider())
                continue

            items.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(key, weight=ft.FontWeight.BOLD),
                        width=150, # Fixed width for keys
                        alignment=ft.Alignment(-1, 0), # Align left center
                    ),
                    ft.Text(desc, expand=True)
                ])
            )

        self.dialog = ft.AlertDialog(
            title=ft.Text("Keyboard Shortcuts"),
            content=ft.Column(
                items,
                scroll=ft.ScrollMode.ADAPTIVE,
                tight=True,
                height=400, # Max height for scrollable content
                width=500, # Fixed width for content
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda _: [setattr(self.dialog, 'open', False), self.app.page.update()]),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.show_dialog(self.dialog)

    def show_about_dialog(self):
        self.dialog = ft.AlertDialog(
            title=ft.Text(f"About {self.app.APP_NAME}"),
            content=ft.Column(
                [
                    ft.Text(f"Version: {self.app.VERSION}"),
                    ft.Text("A high-performance log analysis tool."),
                    ft.Text("Developed with Flet & Rust"),
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda _: [setattr(self.dialog, 'open', False), self.app.page.update()]),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.show_dialog(self.dialog)

    def show_filter_dialog(self, filter_obj=None, initial_text=None, on_save_callback=None):
        is_new = filter_obj is None
        d_text = (initial_text if initial_text else "") if is_new else filter_obj.text
        d_fore = filter_obj.fore_color if not is_new else "#FFFFFF"
        d_back = filter_obj.back_color if not is_new else "#000000"
        d_regex = filter_obj.is_regex if not is_new else False
        d_exclude = filter_obj.is_exclude if not is_new else False

        # Dialog controls
        txt_pattern = ft.TextField(label="Pattern", value=d_text, autofocus=True, expand=True)
        sw_regex = ft.Switch(label="Regex", value=d_regex)
        sw_exclude = ft.Switch(label="Exclude", value=d_exclude)

        # Simple color presets (Matching loganalyzer.py common colors)
        colors = ["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
                  "#800000", "#008000", "#000080", "#808000", "#808000", "#008080", "#C0C0C0", "#808080"]

        selected_fg = d_fore
        selected_bg = d_back

        def update_preview():
            is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK
            adj_bg = adjust_color_for_theme(selected_bg, True, is_dark)
            adj_fg = adjust_color_for_theme(selected_fg, False, is_dark)
            preview.bgcolor = adj_bg
            preview.content.color = adj_fg
            preview.update()

        def set_fg(color):
            nonlocal selected_fg
            selected_fg = color
            update_preview()

        def set_bg(color):
            nonlocal selected_bg
            selected_bg = color
            update_preview()

        preview = ft.Container(
            content=ft.Text("Preview Text", color=adjust_color_for_theme(selected_fg, False, self.app.page.theme_mode == ft.ThemeMode.DARK), weight=ft.FontWeight.BOLD),
            bgcolor=adjust_color_for_theme(selected_bg, True, self.app.page.theme_mode == ft.ThemeMode.DARK),
            padding=10,
            border_radius=5,
            alignment=ft.Alignment(0, 0)
        )

        def build_color_grid(on_click_func, is_bg_selection):
            is_dark = self.app.page.theme_mode == ft.ThemeMode.DARK
            return ft.Row([
                ft.Container(
                    width=24, height=24,
                    # Show the adjusted color in the palette so it matches preview
                    bgcolor=adjust_color_for_theme(c, is_bg_selection, is_dark),
                    border_radius=3,
                    border=ft.Border.all(1, ft.Colors.GREY_400),
                    tooltip=f"Original: {c}",
                    on_click=lambda e, col=c: on_click_func(col)
                ) for c in colors
            ], wrap=True, width=300)

        async def save_filter(e):
            nonlocal filter_obj
            self.app.filters_dirty = True # Mark as modified
            if is_new:
                filter_obj = Filter(txt_pattern.value, selected_fg, selected_bg, True, sw_regex.value, sw_exclude.value)
                self.app.filters.append(filter_obj)
            else:
                filter_obj.text = txt_pattern.value
                filter_obj.fore_color = selected_fg
                filter_obj.back_color = selected_bg
                filter_obj.is_regex = sw_regex.value
                filter_obj.is_exclude = sw_exclude.value

            self.dialog.open = False
            if on_save_callback:
                await on_save_callback()
            self.app.page.update()

        self.dialog = ft.AlertDialog(
            title=ft.Text("Edit Filter" if not is_new else "Add Filter"),
            content=ft.Column([
                txt_pattern,
                ft.Row([sw_regex, sw_exclude]),
                ft.Text("Foreground Color:"),
                build_color_grid(set_fg, False),
                ft.Text("Background Color:"),
                build_color_grid(set_bg, True),
                ft.Text("(Colors automatically adjusted for readability)", size=10, italic=True, color=ft.Colors.GREY_500),
                ft.Divider(),
                ft.Text("Preview:"),
                preview
            ], tight=True, scroll=ft.ScrollMode.AUTO, width=400),
            actions=[
                ft.TextButton("Save", on_click=save_filter),
                ft.TextButton("Cancel", on_click=lambda _: [setattr(self.dialog, 'open', False), self.app.page.update()])
            ]
        )
        self.app.page.show_dialog(self.dialog)

    def show_filter_context_menu(self, filter_obj):
        def close_dlg(ev):
            self.dialog.open = False
            self.app.page.update()

        async def menu_edit(ev):
            await self.app.open_filter_dialog(filter_obj)
            close_dlg(None)

        async def menu_top(ev):
            await self.app.move_filter_to_top(filter_obj)
            close_dlg(None)

        async def menu_bottom(ev):
            await self.app.move_filter_to_bottom(filter_obj)
            close_dlg(None)

        async def menu_delete(ev):
            await self.app.delete_filter(filter_obj)
            close_dlg(None)

        self.dialog = ft.AlertDialog(
            title=ft.Text("Filter Actions"),
            content=ft.Column([
                ft.ListTile(leading=ft.Icon(ft.Icons.EDIT), title=ft.Text("Edit Filter"), on_click=menu_edit),
                ft.ListTile(leading=ft.Icon(ft.Icons.ARROW_UPWARD), title=ft.Text("Move to Top"), on_click=menu_top),
                ft.ListTile(leading=ft.Icon(ft.Icons.ARROW_DOWNWARD), title=ft.Text("Move to Bottom"), on_click=menu_bottom),
                ft.ListTile(leading=ft.Icon(ft.Icons.DELETE), title=ft.Text("Delete"), on_click=menu_delete),
            ], height=240, width=200),
            actions=[ft.TextButton("Close", on_click=close_dlg)]
        )
        self.app.page.show_dialog(self.dialog)

    def show_log_context_menu(self, real_idx, on_copy, on_add_filter):
        def close_dlg(e):
            self.dialog.open = False
            self.app.page.update()

        copy_label = f"Copy Line" if len(self.app.selected_indices) <= 1 else f"Copy {len(self.app.selected_indices)} Lines"

        self.dialog = ft.AlertDialog(
            title=ft.Text(f"Line {real_idx + 1} Actions"),
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.COPY),
                    title=ft.Text(copy_label),
                    on_click=lambda _: [on_copy(), close_dlg(None)]
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ADD),
                    title=ft.Text("Add Filter from Line"),
                    on_click=lambda _: [on_add_filter(), close_dlg(None)]
                ),
            ], height=140, width=300),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.dialog.open = True
        self.app.page.show_dialog(self.dialog)
        self.app.page.update()
