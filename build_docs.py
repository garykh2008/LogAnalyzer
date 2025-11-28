import markdown
import os

# 設定輸入與輸出檔案
input_md_file = "Doc\Log_Analyzer_v1.1_Docs_EN.md"  # 您的 Markdown 檔案名稱
output_html_file = "Doc\Log_Analyzer_v1.1_Docs_EN.html"

# 定義 CSS 樣式 (讓 HTML 看起來像 GitHub 風格般漂亮)
css_style = """
<style>
	body {
		font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
		line-height: 1.6;
		color: #24292e;
		max-width: 900px;
		margin: 0 auto;
		padding: 45px;
	}
	h1, h2, h3 { border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
	code { background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: Consolas, "Courier New", monospace; }
	pre { background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 3px; }
	pre code { background-color: transparent; padding: 0; }
	blockquote { border-left: 0.25em solid #dfe2e5; color: #6a737d; padding: 0 1em; margin: 0; }
	table { border-collapse: collapse; width: 100%; margin-bottom: 1rem; }
	th, td { border: 1px solid #dfe2e5; padding: 6px 13px; }
	th { background-color: #f6f8fa; font-weight: 600; }
	tr:nth-child(2n) { background-color: #f6f8fa; }
	a { color: #0366d6; text-decoration: none; }
	a:hover { text-decoration: underline; }
</style>
"""

def convert_md_to_html():
	if not os.path.exists(input_md_file):
		print(f"錯誤: 找不到檔案 {input_md_file}")
		return

	print(f"正在讀取 {input_md_file}...")

	with open(input_md_file, "r", encoding="utf-8") as f:
		text = f.read()

	# 轉換 Markdown 為 HTML
	# extensions=['extra'] 支援表格、程式碼區塊等進階語法
	# 'toc' 擴展會自動處理目錄錨點
	html_body = markdown.markdown(text, extensions=['extra', 'toc', 'fenced_code', 'tables'])

	# 組合完整的 HTML 結構
	full_html = f"""
	<!DOCTYPE html>
	<html lang="en">
	<head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<title>Log Analyzer Documentation</title>
		{css_style}
	</head>
	<body>
		{html_body}
	</body>
	</html>
	"""

	print(f"正在寫入 {output_html_file}...")
	with open(output_html_file, "w", encoding="utf-8") as f:
		f.write(full_html)

	print("轉換完成！")

if __name__ == "__main__":
	convert_md_to_html()