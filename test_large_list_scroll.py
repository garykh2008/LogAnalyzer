import flet as ft
import time

def main(page: ft.Page):
    page.title = "Large File Scroll Test"
    page.theme_mode = ft.ThemeMode.DARK

    # Status and metrics
    status_text = ft.Text("Ready to load file.")
    load_time_text = ft.Text("")

    # The list view that will hold the file content
    # spacing=0 helps compact the view like a log viewer
    log_list = ft.ListView(
        expand=True,
        spacing=0,
        padding=10,
        auto_scroll=False,
    )

    # Loading indicator
    progress_bar = ft.ProgressBar(visible=False)

    async def pick_file_click(e):
        try:
            # In Flet 0.80.1+, we instantiate FilePicker on demand and await pick_files
            results = await ft.FilePicker().pick_files(
                allow_multiple=False,
                dialog_title="Select a log file"
            )
        except Exception as ex:
            status_text.value = f"Error picking file: {str(ex)}"
            page.update()
            return

        if not results:
            return

        file_path = results[0].path
        status_text.value = f"Loading: {file_path}..."
        progress_bar.visible = True
        page.update()

        start_time = time.time()

        try:
            # Read all lines
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            # Create controls
            log_list.controls = [ft.Text(line.rstrip(), font_family="Consolas") for line in lines]

            end_time = time.time()
            duration = end_time - start_time

            status_text.value = f"Loaded {len(lines)} lines."
            load_time_text.value = f"Load time: {duration:.4f} seconds"

        except Exception as ex:
            status_text.value = f"Error: {str(ex)}"
            log_list.controls = []

        finally:
            progress_bar.visible = False
            page.update()

    # Layout
    header = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.ElevatedButton(
                        content="Pick File",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=pick_file_click
                    ),
                    status_text,
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            load_time_text,
            progress_bar,
        ]
    )

    page.add(
        header,
        ft.Divider(),
        log_list
    )

if __name__ == "__main__":
    ft.run(main)
