import flet as ft

class StatusBar:
    def __init__(self, app):
        self.app = app
        self.status_text = ft.Text("Ready", size=12)

    def build(self):
        colors = self.app._get_colors()
        self.status_text.color = colors["status_text"]

        self.container = ft.Container(
            height=25, # 稍微縮窄一點，更顯精緻
            bgcolor=colors["status_bg"],
            padding=ft.Padding.only(left=15, right=10),
            content=ft.Row([
                self.status_text,
            ], alignment=ft.MainAxisAlignment.START),
            alignment=ft.Alignment(-1, 0)
        )
        return self.container

    def update_colors(self):
        colors = self.app._get_colors()
        if hasattr(self, "container"):
            self.container.bgcolor = colors["status_bg"]
        if hasattr(self, "status_text"):
            self.status_text.color = colors["status_text"]

    def update_status(self, text):
        self.status_text.value = text
        if self.status_text.page:
            self.status_text.update()
