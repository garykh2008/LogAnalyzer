import subprocess
import threading
import os

class NotificationManager:
    """A portable notification manager using Windows PowerShell."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationManager, cls).__new__(cls)
            cls._instance.default_app_id = "LogAnalyzer"
        return cls._instance

    def send_toast(self, title, message, app_id=None):
        def _run():
            target_id = app_id or self.default_app_id
            safe_title = title.replace("'", "''")
            safe_message = message.replace("'", "''")
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $xml = [Windows.Data.Xml.Dom.XmlDocument]::new()
            $xml.LoadXml($template.GetXml())
            $textNodes = $xml.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($xml.CreateTextNode('{safe_title}')) | Out-Null
            $textNodes.Item(1).AppendChild($xml.CreateTextNode('{safe_message}')) | Out-Null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{target_id}').Show($toast)
            """
            try:
                # Use STARTUPINFO to hide the console window completely
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script], 
                    capture_output=True, 
                    startupinfo=si,
                    check=False
                )
            except: pass
        threading.Thread(target=_run, daemon=True).start()

notification_manager = NotificationManager()
