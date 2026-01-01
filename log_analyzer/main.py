import flet as ft
from log_analyzer.app import LogAnalyzerApp
import asyncio
import glob

async def main(page: ft.Page):
    # 階段 1 最終優化：main() 僅負責引導啟動
    # 所有初始化邏輯（設定、背景服務、UI）均在類別內部完成
    app = LogAnalyzerApp(page)

    # --- CLI Argument Handling ---
    import argparse

    parser = argparse.ArgumentParser(description="Log Analyzer Flet", fromfile_prefix_chars='@')
    parser.add_argument("logs", nargs="*", help="Log files to open")
    parser.add_argument("-f", "--filter", help="Filter file to load (.tat)")

    # Use parse_known_args to avoid conflict with Flet arguments
    args, _ = parser.parse_known_args()

    if args.filter:
        await app._run_safe_async(app._perform_import_filters_logic(args.filter), "Loading Filters from CLI")

    if args.logs:
        final_logs = []
        for log_arg in args.logs:
            # Handle Wildcards (for CMD where shell doesn't expand)
            if any(c in log_arg for c in '*?['):
                expanded = glob.glob(log_arg)
                if expanded:
                    final_logs.extend(expanded)
                else:
                    final_logs.append(log_arg)
            else:
                final_logs.append(log_arg)

        # Load logs sequentially
        for log_file in final_logs:
            await app.load_file(log_file)

if __name__ == "__main__":
    # 使用隱藏啟動以防閃爍
    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
