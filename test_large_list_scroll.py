import flet as ft
import time
import os

def main(page: ft.Page):
    page.title = "Large File Scroll Test"
    page.theme_mode = ft.ThemeMode.DARK

    # Status and metrics
    status_text = ft.Text("Ready to load file.")
    load_time_text = ft.Text("")

    # The list view that will hold the file content
    # spacing=0 helps compact the view like a log viewer
    # item_extent helps with performance if rows have fixed height,
    # but strictly speaking text wrap might vary height.
    # For a log viewer test, usually lines are single height.
    log_list = ft.ListView(
        expand=True,
        spacing=0,
        padding=10,
        auto_scroll=False,
    )

    # Loading indicator
    progress_bar = ft.ProgressBar(visible=False)

    def on_file_picked(e: ft.FilePickerResultEvent):
        if not e.files:
            return

        file_path = e.files[0].path
        status_text.value = f"Loading: {file_path}..."
        progress_bar.visible = True
        page.update()

        start_time = time.time()

        try:
            # Read all lines
            # For extremely large files, one might want to use a generator
            # or read in chunks, but to test ListView's capability to handle
            # a large list of controls, we'll load them all.
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            # Create controls
            # We use ft.Text for each line.
            # Using a list comprehension is faster than a loop with append.
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

    # File Picker setup
    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # Layout
    header = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.ElevatedButton(
                        "Pick File",
                        icon=ft.icons.FOLDER_OPEN,
                        on_click=lambda _: file_picker.pick_files(
                            allow_multiple=False,
                            dialog_title="Select a log file"
                        )
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
    ft.app(target=main)
