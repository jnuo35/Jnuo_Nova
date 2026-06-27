import json
import os
import sys
import sqlite3
import hashlib
import secrets
import uuid
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta
from typing import Dict, Optional
from PyQt6 import QtCore
import requests
import threading
from PyQt6.QtWidgets import (
    QApplication, QCompleter, QListWidgetItem, QMainWindow, QTabWidget, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QWidget, QToolBar, QMessageBox, QDialog,
    QLabel, QDialogButtonBox, QListWidget, QFormLayout,
    QMenu, QFileDialog, QInputDialog, QComboBox, QTabWidget as QTabWidget2,
    QCheckBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEnginePage,
    QWebEngineDownloadRequest,
    QWebEngineUrlSchemeHandler,
    QWebEngineUrlScheme,
    QWebEngineUrlRequestInterceptor
)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt6.QtCore import (QStringListModel, QUrl, QSettings, Qt, QStandardPaths, QPoint, QMimeData, QByteArray, QEvent, QThread,
                          pyqtSignal, QBuffer, QIODevice, QTimer, QObject, pyqtSlot)
from PyQt6.QtGui import QIcon, QKeySequence, QDrag, QPixmap, QPainter, QColor, QPen, QAction

# ========== 版本信息 ==========
VERSION = "1.0.0"
DEVELOPER = "jnuo"


def get_icon_path():
    """获取打包后图标的正确路径"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "icon.ico")


# ========== 现代化深色样式表 ==========
DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #1e1e1e;
    color: #d4d4d4;
}
QLineEdit, QTextEdit, QListWidget, QComboBox {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    padding: 4px;
}
QPushButton {
    background-color: transparent;
    color: #d4d4d4;
    border: none;
    padding: 6px 12px;
    border-radius: 6px;
}
QPushButton:hover {
    background-color: #3c3c3c;
}
QPushButton:pressed {
    background-color: #505050;
}
QTabWidget::pane {
    background-color: #1e1e1e;
    border: none;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #d4d4d4;
    padding: 8px 16px;
    margin: 2px 2px 0 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 2px solid #0e639c;
}
QTabBar::tab:hover:!selected {
    background-color: #3c3c3c;
}
QLineEdit {
    border-radius: 20px;
    padding: 8px 16px;
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
}
QLineEdit:focus {
    border: 1px solid #0e639c;
    background-color: #252525;
}
QToolBar {
    background-color: #1e1e1e;
    spacing: 5px;
    border: none;
}
QMenu {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
}
QMenu::item:selected {
    background-color: #0e639c;
    border-radius: 4px;
}
QCheckBox, QRadioButton, QLabel {
    color: #d4d4d4;
}
QListWidget, QComboBox {
    border-radius: 6px;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #3c3c3c;
    background-color: #2d2d2d;
}
QCheckBox::indicator:checked {
    background-color: #0e639c;
    border-color: #0e639c;
}
"""


# ========== 获取用户数据目录 ==========
def get_data_dir():
    data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


DATA_DIR = get_data_dir()

# ========== 跨平台安全存储（使用 keyring）==========
import keyring


class SecureStorage:
    """使用 keyring 安全存储 API Key（跨平台）"""

    SERVICE_NAME = "JnuoNova_AI"

    @classmethod
    def save_api_key(cls, api_key: str) -> bool:
        """保存 API Key"""
        try:
            keyring.set_password(cls.SERVICE_NAME, "api_key", api_key)
            return True
        except Exception as e:
            print(f"保存 API Key 失败: {e}")
            return False

    @classmethod
    def get_api_key(cls) -> str:
        """读取 API Key"""
        try:
            return keyring.get_password(cls.SERVICE_NAME, "api_key") or ""
        except Exception:
            return ""

    @classmethod
    def delete_api_key(cls):
        """删除 API Key"""
        try:
            keyring.delete_password(cls.SERVICE_NAME, "api_key")
        except Exception:
            pass


# ========== 设置管理器 ==========
class SettingsManager:
    def __init__(self):
        self.settings = QSettings('JnuoNova', 'Settings')
        self._salt = "jnuo_nova_salt_2024"
        if self.settings.value('search_engine') is None:
            self.settings.setValue('search_engine', 'bing')
            self.settings.sync()

    def _hash_password(self, password: str) -> str:
        if not password:
            return ""
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            self._salt.encode('utf-8'),
            100000
        )
        return hashed.hex()

    def has_password(self) -> bool:
        return bool(self.settings.value('password', ''))

    def set_password(self, password: str):
        if password and password.strip():
            self.settings.setValue('password', self._hash_password(password.strip()))
        else:
            self.settings.remove('password')
        self.settings.sync()

    def remove_password(self):
        self.settings.remove('password')
        self.settings.sync()

    def verify_password(self, input_password: str) -> bool:
        stored_hash = self.settings.value('password', '')
        if not stored_hash:
            return False
        input_hash = self._hash_password(input_password)
        return secrets.compare_digest(input_hash, stored_hash)

    def get_search_engine(self) -> str:
        value = self.settings.value('search_engine', 'bing')
        return value if isinstance(value, str) else 'bing'

    def set_search_engine(self, engine: str):
        self.settings.setValue('search_engine', engine)
        self.settings.sync()

    def get_search_url(self) -> str:
        engines = {
            'google': 'https://www.google.com/search?q=',
            'bing': 'https://www.bing.com/search?q=',
            'baidu': 'https://www.baidu.com/s?wd=',
            'duckduckgo': 'https://duckduckgo.com/?q='
        }
        current = self.get_search_engine()
        return engines.get(current, engines['bing'])

    # ========== AI 设置相关（使用 keyring 安全存储）==========
    def get_ai_provider(self) -> str:
        return self.settings.value('ai_provider', 'deepseek')

    def set_ai_provider(self, provider: str):
        self.settings.setValue('ai_provider', provider)
        self.settings.sync()

    def get_ai_api_key(self) -> str:
        """从 keyring 读取 API Key"""
        return SecureStorage.get_api_key()

    def set_ai_api_key(self, key: str):
        """保存到 keyring"""
        if key:
            SecureStorage.save_api_key(key)
        else:
            SecureStorage.delete_api_key()

    def has_ai_api_key(self) -> bool:
        return bool(self.get_ai_api_key())

    def get_ai_model(self) -> str:
        models = {
            'deepseek': 'deepseek-v4-flash',
            'openai': 'gpt-4o-mini',
            'qwen': 'qwen-plus',
        }
        provider = self.get_ai_provider()
        return models.get(provider, 'deepseek-chat')

    def get_ai_api_url(self) -> str:
        urls = {
            'deepseek': 'https://api.deepseek.com/v1/chat/completions',
            'openai': 'https://api.openai.com/v1/chat/completions',
            'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        }
        return urls.get(self.get_ai_provider(), urls['deepseek'])


# ========== 密码管理器（保存密码）==========
class PasswordManager:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "jnuo_nova_passwords.db")
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

    def create_tables(self):
        try:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    username TEXT,
                    password TEXT,
                    last_used TIMESTAMP
                )
            """)
            self.conn.commit()
        except Exception as e:
            print(f"创建密码表失败: {e}")

    def save_password(self, url: str, username: str, password: str):
        try:
            self.conn.execute(
                "DELETE FROM saved_passwords WHERE url = ? AND username = ?",
                (url, username)
            )
            self.conn.execute(
                "INSERT INTO saved_passwords (url, username, password, last_used) VALUES (?, ?, ?, ?)",
                (url, username, password, datetime.now())
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"保存密码失败: {e}")
            return False

    def get_password(self, url: str) -> Optional[tuple]:
        try:
            cursor = self.conn.execute(
                "SELECT username, password FROM saved_passwords WHERE url = ? ORDER BY last_used DESC LIMIT 1",
                (url,)
            )
            result = cursor.fetchone()
            return result if result else None
        except Exception:
            return None

    def get_all_passwords(self):
        try:
            cursor = self.conn.execute(
                "SELECT id, url, username, last_used FROM saved_passwords ORDER BY last_used DESC")
            return cursor.fetchall()
        except Exception:
            return []

    def delete_password(self, id: int):
        try:
            self.conn.execute("DELETE FROM saved_passwords WHERE id = ?", (id,))
            self.conn.commit()
            return True
        except Exception:
            return False


# ========== 可拖拽标签页的 TabWidget ==========
class DraggableTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_browser = parent
        self.setAcceptDrops(True)
        self.tabBar().setAcceptDrops(True)
        self.drag_start_pos = None
        self.drag_start_index = -1
        self.is_dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            self.drag_start_index = self.tabBar().tabAt(event.pos())
            self.is_dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() == Qt.MouseButton.LeftButton and
                self.drag_start_pos and
                self.drag_start_index >= 0):
            distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance() and not self.is_dragging:
                self.is_dragging = True
                self.start_tab_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        self.drag_start_index = -1
        self.is_dragging = False
        super().mouseReleaseEvent(event)

    def start_tab_drag(self):
        webview = self.widget(self.drag_start_index)
        if not webview:
            return
        url = webview.url().toString()
        title = self.tabText(self.drag_start_index)

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(url)
        mime_data.setUrls([QUrl(url)])
        drag.setMimeData(mime_data)

        pixmap = QPixmap(200, 30)
        pixmap.fill(QColor(30, 30, 30))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.drawRect(0, 0, 199, 29)
        painter.setPen(QPen(QColor(212, 212, 212)))
        painter.drawText(5, 20, title[:30])
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(10, 15))
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls and self.parent_browser:
                self.parent_browser.add_new_tab(urls[0])
                event.acceptProposedAction()
        elif mime_data.hasText():
            text = mime_data.text()
            if text.startswith('http') and self.parent_browser:
                self.parent_browser.add_new_tab(QUrl(text))
                event.acceptProposedAction()


# ========== 书签管理器（支持锁定书签）==========
class BookmarkManager:
    def __init__(self):
        self.filename = os.path.join(DATA_DIR, "jnuo_nova_bookmarks.json")
        self.bookmarks = self.load()

    def load(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data and "folders" in data:
                        for folder in data["folders"]:
                            for bm in data["folders"][folder]:
                                if "locked" not in bm:
                                    bm["locked"] = False
                        return data
        except Exception as e:
            print(f"加载书签失败: {e}")
        return {"folders": {"默认": []}}

    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存书签失败: {e}")

    def get_folders(self):
        return list(self.bookmarks.get("folders", {}).keys())

    def add_bookmark(self, title, url, folder="默认", locked=False):
        if "folders" not in self.bookmarks:
            self.bookmarks["folders"] = {}
        if folder not in self.bookmarks["folders"]:
            self.bookmarks["folders"][folder] = []
        self.bookmarks["folders"][folder].append({
            "title": title,
            "url": url,
            "locked": locked
        })
        self.save()

    def remove_bookmark(self, folder, index):
        if folder in self.bookmarks["folders"] and index < len(self.bookmarks["folders"][folder]):
            self.bookmarks["folders"][folder].pop(index)
            self.save()

    def get_bookmarks(self, folder):
        return self.bookmarks["folders"].get(folder, [])

    def add_folder(self, folder_name):
        if folder_name not in self.bookmarks["folders"]:
            self.bookmarks["folders"][folder_name] = []
            self.save()
            return True
        return False

    def toggle_lock(self, folder, index):
        if folder in self.bookmarks["folders"] and index < len(self.bookmarks["folders"][folder]):
            self.bookmarks["folders"][folder][index]["locked"] = not self.bookmarks["folders"][folder][index]["locked"]
            self.save()
            return True
        return False


# ========== 历史记录管理器 ==========
class HistoryManager:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "jnuo_nova_history.db")
        self._last_url = None
        self._last_time = None
        self._init_database()

    def _init_database(self):
        """初始化数据库，如果损坏则重建"""
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=5)
            self.create_tables()
        except Exception as e:
            print(f"数据库连接失败: {e}")
            # 尝试重建数据库
            try:
                if os.path.exists(self.db_path):
                    # 备份损坏的数据库
                    backup_path = self.db_path + ".backup"
                    import shutil
                    shutil.copy2(self.db_path, backup_path)
                    print(f"已备份损坏的数据库到: {backup_path}")
                    os.remove(self.db_path)
                self.conn = sqlite3.connect(self.db_path, timeout=5)
                self.create_tables()
                print("数据库已重建")
            except Exception as e2:
                print(f"重建数据库失败: {e2}")
                # 使用内存数据库作为后备
                self.conn = sqlite3.connect(":memory:")
                self.create_tables()

    def update_icon(self, url: str, icon_data: bytes):
        """更新历史记录中的图标"""
        try:
            # 先找到最近一条记录的 id
            cursor = self.conn.execute(
                "SELECT id FROM history WHERE url = ? ORDER BY visit_time DESC LIMIT 1",
                (url,)
            )
            row = cursor.fetchone()
            if row:
                self.conn.execute(
                    "UPDATE history SET icon = ? WHERE id = ?",
                    (icon_data, row[0])
                )
                self.conn.commit()
                print(f"✅ 图标已更新: {url}")
            else:
                print(f"⚠️ 未找到 URL: {url}")
        except Exception as e:
            print(f"更新图标失败: {e}")

    def create_tables(self):
        try:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    title TEXT,
                    visit_time TEXT,
                    icon BLOB  -- 新增：存储图标数据
                )
            """)
            self.conn.commit()
            
            # 检查并添加 icon 列（兼容旧数据库）
            try:
                self.conn.execute("ALTER TABLE history ADD COLUMN icon BLOB")
                self.conn.commit()
            except sqlite3.OperationalError:
                # 列已存在，忽略
                pass
        except Exception as e:
            print(f"创建历史表失败: {e}")

    def add_history(self, url: str, title: str, icon_data: bytes = None):
        if not url or url.startswith("about:blank") or url.startswith("jnuo://"):
            return
        now = datetime.now()
        if self._last_url == url and self._last_time:
            if (now - self._last_time).total_seconds() < 5:
                return
        try:
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            self.conn.execute(
                "INSERT INTO history (url, title, visit_time, icon) VALUES (?, ?, ?, ?)",
                (url, title[:200] if title else url, now_str, icon_data)
            )
            self.conn.commit()
            self._last_url = url
            self._last_time = now
        except Exception as e:
            print(f"添加历史记录失败: {e}")

    def get_history(self, limit=100):
        try:
            cursor = self.conn.execute(
                "SELECT url, title, visit_time, icon FROM history ORDER BY visit_time DESC LIMIT ?",
                (limit,)
            )
            results = cursor.fetchall()
            return results if results else []
        except Exception as e:
            print(f"获取历史记录失败: {e}")
            return []
    
    def get_history_by_period(self, days: int):
        """获取指定天数内的历史记录"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
            cursor = self.conn.execute(
                "SELECT url, title, visit_time, icon FROM history WHERE visit_time >= ? ORDER BY visit_time DESC",
                (cutoff_str,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"获取时段历史失败: {e}")
            return []

    def get_history_today(self):
        """获取今天的历史记录"""
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor = self.conn.execute(
                "SELECT url, title, visit_time, icon FROM history WHERE visit_time >= ? ORDER BY visit_time DESC",
                (cutoff_str,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"获取今天历史失败: {e}")
            return []

    def get_history_yesterday(self):
        """获取昨天的历史记录"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today - timedelta(days=1)
        yesterday_end = today
        start_str = yesterday_start.strftime("%Y-%m-%d %H:%M:%S")
        end_str = yesterday_end.strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor = self.conn.execute(
                "SELECT url, title, visit_time, icon FROM history WHERE visit_time >= ? AND visit_time < ? ORDER BY visit_time DESC",
                (start_str, end_str)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"获取昨天历史失败: {e}")
            return []

    def get_history_last_7_days(self):
        """获取过去7天的历史记录（不含今天）"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today - timedelta(days=7)
        start_str = seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")
        end_str = today.strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor = self.conn.execute(
                "SELECT url, title, visit_time, icon FROM history WHERE visit_time >= ? AND visit_time < ? ORDER BY visit_time DESC",
                (start_str, end_str)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"获取7天历史失败: {e}")
            return []

    def get_history_older(self):
        """获取更早的历史记录（7天前）"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today - timedelta(days=7)
        cutoff_str = seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor = self.conn.execute(
                "SELECT url, title, visit_time, icon FROM history WHERE visit_time < ? ORDER BY visit_time DESC",
                (cutoff_str,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"获取更早历史失败: {e}")
            return []

    def clear_history(self, days=None):
        try:
            if days is not None:
                cutoff = datetime.now() - timedelta(days=days)
                cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
                self.conn.execute("DELETE FROM history WHERE visit_time < ?", (cutoff_str,))
            else:
                self.conn.execute("DELETE FROM history")
            self.conn.commit()
        except Exception as e:
            print(f"清理历史记录失败: {e}")

    def close(self):
        """关闭数据库连接"""
        try:
            self.conn.close()
        except:
            pass


# ========== 下载管理器 ==========
class DownloadItem:
    def __init__(self, url: str, path: str, download_id: str):
        self.url = url
        self.path = path
        self.download_id = download_id
        self.completed = False
        self.file_name = os.path.basename(path)


class DownloadManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jnuo Nova - 下载管理")
        self.setModal(False)
        self.resize(600, 400)
        self.downloads: Dict[str, DownloadItem] = {}
        self.list_widget = QListWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清空已完成")
        clear_btn.clicked.connect(self.clear_completed)
        open_folder_btn = QPushButton("打开下载文件夹")
        open_folder_btn.clicked.connect(self.open_download_folder)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(open_folder_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.setStyleSheet(DARK_STYLE)

    def add_download(self, url: str, path: str) -> str:
        download_id = str(uuid.uuid4())
        item = DownloadItem(url, path, download_id)
        self.downloads[download_id] = item
        self.list_widget.addItem(f"📥 {item.file_name} - 下载中...")
        item_widget = self.list_widget.item(self.list_widget.count() - 1)
        item_widget.setData(Qt.ItemDataRole.UserRole, download_id)
        return download_id

    def mark_completed(self, download_id: str, success: bool = True):
        if download_id in self.downloads:
            item = self.downloads[download_id]
            item.completed = success
            for i in range(self.list_widget.count()):
                list_item = self.list_widget.item(i)
                if list_item.data(Qt.UserRole) == download_id:
                    icon = "✅" if success else "❌"
                    status = "已完成" if success else "失败"
                    list_item.setText(f"{icon} {item.file_name} - {status}")
                    break

    def clear_completed(self):
        for i in reversed(range(self.list_widget.count())):
            list_item = self.list_widget.item(i)
            download_id = list_item.data(Qt.UserRole)
            if download_id in self.downloads and self.downloads[download_id].completed:
                self.list_widget.takeItem(i)
                del self.downloads[download_id]

    def open_download_folder(self):
        download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        if sys.platform == 'win32':
            os.startfile(download_dir)


def register_custom_scheme():
    """注册自定义协议"""
    scheme = QWebEngineUrlScheme(b'jnuo')
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
    QWebEngineUrlScheme.registerScheme(scheme)


class AIBridge(QObject):
    response_received = pyqtSignal(str, str)

    def __init__(self, parent_browser):
        super().__init__()
        self.parent_browser = parent_browser
        self.pending_requests = {}
        self.conversation_history = {}
        # 初始化系统消息
        self._init_system_message()

    def _init_system_message(self):
        """初始化系统消息"""
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y%m%d")
        self.system_message = {
            "role": "system",
            "content": f"""【系统时间】今天是 {current_date}。
你的知识截止于2025年5月，关于日期、时间的实时信息必须以系统提供的时间为准。
对于需要最新信息的问题（如比赛、新闻等），你**必须**调用 web_search 工具搜索后再回答。"""
        }

    @pyqtSlot(str, str)
    def send_message(self, request_id, question):
        """接收来自 JavaScript 的消息"""
        print(f"收到 AI 请求 ID: {request_id}")

        # 获取该会话的历史记录（如果没有就创建）
        if request_id not in self.conversation_history:
            # 使用系统消息
            self.conversation_history[request_id] = [self.system_message.copy()]

        # 添加用户消息到历史
        self.conversation_history[request_id].append({
            "role": "user",
            "content": question
        })

        # 限制历史长度（保留系统消息 + 最近20条）
        if len(self.conversation_history[request_id]) > 21:
            self.conversation_history[request_id] = [
                                                        self.conversation_history[request_id][0]  # 系统消息
                                                    ] + self.conversation_history[request_id][-20:]

        def process():
            try:
                api_key = self.parent_browser.settings_mgr.get_ai_api_key()
                if not api_key:
                    self.response_received.emit(request_id, json.dumps({
                        "success": False, "error": "未配置 API Key"
                    }))
                    return

                api_url = self.parent_browser.settings_mgr.get_ai_api_url()
                model = self.parent_browser.settings_mgr.get_ai_model()

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                data = {
                    "model": model,
                    "messages": self.conversation_history[request_id],
                    "stream": False
                }

                # 添加 web_search 支持（如果 API 支持）
                if self.parent_browser.settings_mgr.get_ai_provider() == 'deepseek':
                    data["web_search"] = {
                        "enable": True,
                        "vendor": "tencent_sougo"
                    }

                response = requests.post(api_url, headers=headers, json=data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    answer = result['choices'][0]['message']['content']

                    # 保存助手的回复到历史
                    self.conversation_history[request_id].append({
                        "role": "assistant",
                        "content": answer
                    })

                    self.response_received.emit(request_id, json.dumps({
                        "success": True, "answer": answer
                    }, ensure_ascii=False))
                else:
                    error_msg = f"API 错误: {response.text[:200]}"
                    self.response_received.emit(request_id, json.dumps({
                        "success": False, "error": error_msg
                    }))
            except Exception as e:
                self.response_received.emit(request_id, json.dumps({
                    "success": False, "error": str(e)
                }))

        threading.Thread(target=process, daemon=True).start()


# ========== 自定义 WebView（支持自动填充密码和AI）==========
class CustomWebView(QWebEngineView):
    def __init__(self, parent=None, incognito=False):
        super().__init__(parent)
        self.parent_browser = parent
        self.incognito = incognito
        self._selected_text = ""

        # 全屏相关属性
        self._fullscreen_mode = False
        self._original_parent = None
        self._original_geometry = None
        self._cursor_visible = True

        # 创建 WebChannel（不立即设置，等页面加载后再设置）
        self.channel = QWebChannel(self)
        self.ai_bridge = AIBridge(self.parent_browser)
        self.channel.registerObject("aiBridge", self.ai_bridge)
        self.ai_bridge.response_received.connect(self.on_ai_response)

        # 设置 WebEngine 属性
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)  # 启用全屏支持

        # 设置 User-Agent
        profile = self.page().profile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 设置全屏回调
        self.page().fullScreenRequested.connect(self.on_fullscreen_request)

        # 页面加载完成后自动设置 WebChannel
        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok):
        """页面加载完成后的处理"""
        if ok and self.page():
            self.page().setWebChannel(self.channel)
            print(f"WebChannel 已设置, URL: {self.url().toString()}")

            # 注入全屏优化脚本（针对 B 站等视频网站和云原神）
            js_code = """
            // 监听全屏变化
            document.addEventListener('fullscreenchange', function() {
                if (!document.fullscreenElement) {
                    console.log('全屏已退出');
                    // 退出全屏时可以通过 Qt 信号处理
                }
            });

            // 监听鼠标移动（游戏模式优化）
            document.addEventListener('mousemove', function(e) {
                // 可选：发送鼠标位置给游戏
                if (window.qtMouseMove) {
                    window.qtMouseMove(e.clientX, e.clientY);
                }
            });

            // 防止云原神鼠标锁定失败
            if (document.body.requestPointerLock) {
                console.log('指针锁定 API 可用');
            }

            console.log('全屏优化脚本已注入');
            """
            self.page().runJavaScript(js_code)

    def on_fullscreen_request(self, request):
        """处理全屏请求（用于云原神、B站等）"""
        if request.toggleOn():
            # 进入全屏模式
            print("进入全屏模式")
            self._fullscreen_mode = True
            self._original_parent = self.parent()
            self._original_geometry = self.geometry()

            # 获取主窗口并进入全屏
            main_window = self.window()
            if main_window and isinstance(main_window, QMainWindow):
                # 临时隐藏标签栏和工具栏
                if hasattr(main_window, 'tab_widget'):
                    main_window.tab_widget.tabBar().setVisible(False)
                if hasattr(main_window, 'toolBar'):
                    main_window.toolBar().setVisible(False)

                # 进入全屏
                main_window.showFullScreen()

                # 将 WebView 设置为中央部件并调整大小
                self.setParent(main_window.centralWidget())
                self.setGeometry(main_window.centralWidget().geometry())

                # 隐藏鼠标指针（游戏需要）
                self.setCursor(Qt.CursorStyle.BlankCursor)
                self._cursor_visible = False

            request.accept()
        else:
            # 退出全屏模式
            print("退出全屏模式")
            self._fullscreen_mode = False

            # 获取主窗口并退出全屏
            main_window = self.window()
            if main_window and isinstance(main_window, QMainWindow):
                main_window.showNormal()

                # 恢复标签栏和工具栏
                if hasattr(main_window, 'tab_widget'):
                    main_window.tab_widget.tabBar().setVisible(True)
                if hasattr(main_window, 'toolBar'):
                    main_window.toolBar().setVisible(True)

                # 恢复 WebView 到标签页
                current_index = main_window.tab_widget.currentIndex()
                if current_index >= 0:
                    self.setParent(main_window.tab_widget.widget(current_index))
                    main_window.tab_widget.setCurrentWidget(self)

            # 恢复鼠标指针
            self.setCursor(Qt.CursorStyle.ArrowCursor)
            self._cursor_visible = True
            request.accept()

    def on_ai_response(self, request_id, response_json):
        """将 AI 响应发送回 JavaScript"""
        print(f"收到 AI 响应，request_id: {request_id}")
        print(f"原始响应内容: {response_json[:500]}")

        # 确保 response_json 是字符串
        if isinstance(response_json, dict):
            response_json = json.dumps(response_json)

        # 转义特殊字符
        safe_response = json.dumps(response_json)

        # 使用更安全的 JavaScript 调用方式
        js_code = f"""
        (function() {{
            console.log('Python 回调执行, request_id: {request_id}');

            // 解析响应
            var responseData;
            try {{
                responseData = JSON.parse({safe_response});
                console.log('解析成功:', responseData);
            }} catch(e) {{
                console.error('解析失败:', e);
                responseData = {{success: false, error: '解析响应失败: ' + e.message}};
            }}

            // 调用回调函数
            if (window.aiCallbacks && window.aiCallbacks['{request_id}']) {{
                console.log('找到回调函数，执行中...');
                window.aiCallbacks['{request_id}'](responseData);
                delete window.aiCallbacks['{request_id}'];
            }} else {{
                console.error('找不到回调函数:', request_id);
                console.log('现有的回调:', Object.keys(window.aiCallbacks || {{}}));

                // 尝试模糊匹配（移除时间戳部分）
                var baseId = '{request_id}'.split('_').slice(0, -1).join('_');
                for (var key in window.aiCallbacks) {{
                    if (key.startsWith(baseId)) {{
                        console.log('找到模糊匹配的回调:', key);
                        window.aiCallbacks[key](responseData);
                        delete window.aiCallbacks[key];
                        return;
                    }}
                }}
            }}
        }})();
        """
        self.page().runJavaScript(js_code)

    def createWindow(self, windowType):
        """在新标签页中打开链接"""
        # 创建新的 WebView
        new_webview = CustomWebView(self.parent_browser, incognito=self.incognito)

        # 使用 QTimer 延迟添加
        def add_to_tab():
            index = self.parent_browser.tab_widget.addTab(new_webview, "加载中...")
            self.parent_browser.tab_widget.setCurrentIndex(index)

            def update_title(title):
                if len(title) > 30:
                    title = title[:27] + "..."
                if index < self.parent_browser.tab_widget.count():
                    self.parent_browser.tab_widget.setTabText(index, title)

            new_webview.titleChanged.connect(update_title)

        QTimer.singleShot(0, add_to_tab)
        return new_webview

    def mousePressEvent(self, event):
        """鼠标按下时，如果在全屏游戏模式，确保光标隐藏"""
        if self._fullscreen_mode and not self._cursor_visible:
            # 确保光标保持隐藏
            if self.cursor().shape() != Qt.CursorStyle.BlankCursor:
                self.setCursor(Qt.CursorStyle.BlankCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动时，如果在全屏游戏模式，保持光标隐藏"""
        if self._fullscreen_mode and not self._cursor_visible:
            if self.cursor().shape() != Qt.CursorStyle.BlankCursor:
                self.setCursor(Qt.CursorStyle.BlankCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放时处理"""
        if self._fullscreen_mode and not self._cursor_visible:
            if self.cursor().shape() != Qt.CursorStyle.BlankCursor:
                self.setCursor(Qt.CursorStyle.BlankCursor)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """按键事件，按 ESC 退出全屏"""
        if self._fullscreen_mode and event.key() == Qt.Key.Key_Escape:
            print("ESC 按下，退出全屏")
            # 通知网页退出全屏
            self.page().runJavaScript("""
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                }
            """)
            # Qt 的全屏退出
            self.page().triggerAction(QWebEnginePage.WebAction.ExitFullScreen)
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单 - 全屏游戏模式下禁用"""
        if self._fullscreen_mode:
            # 游戏模式下不显示右键菜单
            return

        # 正常模式下的右键菜单
        menu = QMenu(self)

        # 获取选中的文本
        selected_text = self.get_selected_text()

        # 基本导航
        back_action = QAction("◀ 后退", self)
        back_action.triggered.connect(self.back)
        forward_action = QAction("前进 ▶", self)
        forward_action.triggered.connect(self.forward)
        reload_action = QAction("🔄 刷新", self)
        reload_action.triggered.connect(self.reload)

        menu.addAction(back_action)
        menu.addAction(forward_action)
        menu.addAction(reload_action)
        menu.addSeparator()

        # 复制粘贴
        copy_action = QAction("📋 复制", self)
        copy_action.triggered.connect(lambda: self.triggerPageAction(QWebEnginePage.WebAction.Copy))
        menu.addAction(copy_action)

        paste_action = QAction("📄 粘贴", self)
        paste_action.triggered.connect(lambda: self.triggerPageAction(QWebEnginePage.WebAction.Paste))
        menu.addAction(paste_action)
        menu.addSeparator()

        # 全屏按钮
        fullscreen_action = QAction("🖥️ 全屏模式", self)
        fullscreen_action.triggered.connect(lambda: self.triggerPageAction(QWebEnginePage.WebAction.ToggleFullScreen))
        menu.addAction(fullscreen_action)
        menu.addSeparator()

        # 书签
        if not self.incognito and self.parent_browser and hasattr(self.parent_browser,
                                                                  'bookmark_mgr') and self.parent_browser.bookmark_mgr:
            bookmark_action = QAction("⭐ 添加到书签", self)
            bookmark_action.triggered.connect(lambda: self.parent_browser.add_current_bookmark())
            menu.addAction(bookmark_action)

        # AI 功能
        if not self.incognito:
            menu.addSeparator()

            if selected_text and len(selected_text.strip()) > 0:
                display_text = selected_text[:40] + "..." if len(selected_text) > 40 else selected_text
                ask_selected_action = QAction(f"🤖 问AI: \"{display_text}\"", self)
                text_to_ask = selected_text
                ask_selected_action.triggered.connect(lambda: self.ask_ai_with_text(text_to_ask))
                menu.addAction(ask_selected_action)

                ask_page_action = QAction("🤖 分析当前页面", self)
                ask_page_action.triggered.connect(self.ask_ai)
                menu.addAction(ask_page_action)
            else:
                ask_page_action = QAction("🤖 问AI（分析当前页面）", self)
                ask_page_action.triggered.connect(self.ask_ai)
                menu.addAction(ask_page_action)

        # 新标签页
        menu.addSeparator()
        new_tab_action = QAction("➕ 新标签页", self)
        new_tab_action.triggered.connect(lambda: self.parent_browser.add_new_tab())
        menu.addAction(new_tab_action)

        menu.exec(event.globalPos())

    def ask_ai_with_text(self, text):
        """使用选中的文本调用 AI"""
        if not text or not text.strip():
            QMessageBox.warning(self, "错误", "没有选中的内容")
            return

        if not self.parent_browser or not hasattr(self.parent_browser, 'settings_mgr'):
            QMessageBox.warning(self, "错误", "无法获取设置")
            return

        api_key = self.parent_browser.settings_mgr.get_ai_api_key()
        if not api_key:
            QMessageBox.warning(
                self,
                "未配置AI",
                "请先在「设置 → AI 助手」中配置 API Key"
            )
            return

        question = text.strip()
        if len(question) > 2000:
            question = question[:2000] + "...\n\n(内容已截断)"

        print(f"问AI，选中文本: {question[:100]}...")
        self.parent_browser.add_new_tab_with_ai_question(question)

    def get_selected_text(self):
        """获取当前选中的文本"""
        try:
            return self.selectedText()
        except Exception as e:
            print(f"获取选中文本失败: {e}")
            return ""

    def ask_ai(self):
        """调用AI功能（分析当前页面）"""
        if not self.parent_browser or not hasattr(self.parent_browser, 'settings_mgr'):
            QMessageBox.warning(self, "错误", "无法获取设置")
            return

        api_key = self.parent_browser.settings_mgr.get_ai_api_key()
        if not api_key:
            QMessageBox.warning(
                self,
                "未配置AI",
                "请先在「设置 → AI 助手」中配置 API Key"
            )
            return

        question = self._get_question_content()
        if not question:
            QMessageBox.warning(self, "错误", "无法获取问题内容")
            return

        self.parent_browser.add_new_tab_with_ai_question(question)

    def _get_question_content(self) -> str:
        """获取要问AI的内容"""
        title = self.title()
        url = self.url().toString()
        question = f"""请搜索并帮我分析这个网页的内容：

    标题：{title}
    链接：{url}

    请用中文总结一下这个网页的主要内容。"""
        return question

    def inject_auto_fill_script(self):
        """注入自动填充脚本"""
        if not self.parent_browser or not hasattr(self.parent_browser, 'password_mgr') or self.incognito:
            return

        current_url = self.url().toString()
        password_info = self.parent_browser.password_mgr.get_password(current_url)

        if password_info:
            username, password = password_info
            script = f"""
            (function() {{
                var usernameFields = document.querySelectorAll('input[type="text"], input[type="email"], input[name*="user"], input[name*="email"]');
                var passwordFields = document.querySelectorAll('input[type="password"]');

                if (usernameFields.length > 0 && passwordFields.length > 0) {{
                    usernameFields[0].value = "{username}";
                    passwordFields[0].value = "{password}";

                    var inputEvent = new Event('input', {{ bubbles: true }});
                    usernameFields[0].dispatchEvent(inputEvent);
                    passwordFields[0].dispatchEvent(inputEvent);

                    var hint = document.createElement('div');
                    hint.textContent = '🔐 已自动填充保存的密码';
                    hint.style.cssText = 'position:fixed;bottom:10px;right:10px;background:#0e639c;color:white;padding:8px 12px;border-radius:6px;z-index:9999;font-size:12px;';
                    document.body.appendChild(hint);
                    setTimeout(function() {{ hint.remove(); }}, 3000);
                }}
            }})();
            """
            self.page().runJavaScript(script)

    def close_tab(self):
        """关闭标签页"""
        self.setPage(None)
        self.deleteLater()


# ========== 解锁对话框 ==========
class UnlockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jnuo Nova - 已锁定")
        self.setModal(True)
        self.unlocked = False
        layout = QVBoxLayout()
        info_label = QLabel("Jnuo Nova 浏览器已锁定\n\n需要密码才能访问浏览历史、锁定书签等敏感功能")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("输入密码解锁")
        self.password_input.returnPressed.connect(self.check_password)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.check_password)
        button_box.rejected.connect(self.reject)
        layout.addWidget(info_label)
        layout.addWidget(self.password_input)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def check_password(self):
        try:
            if self.parent() and self.parent().settings_mgr.verify_password(self.password_input.text()):
                self.unlocked = True
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "密码错误")
                self.password_input.clear()
        except Exception as e:
            print(f"密码验证失败: {e}")
            QMessageBox.warning(self, "错误", "密码验证失败")


# ========== 设置对话框（包含关于页面）==========
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jnuo Nova - 设置")
        self.setModal(True)
        self.resize(500, 520)
        self.parent_browser = parent

        layout = QVBoxLayout()
        tabs = QTabWidget2()

        # ========== 1. 常规设置 ==========
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        self.search_engine_combo = QComboBox()
        self.search_engine_combo.addItems(["Google", "Bing", "百度", "DuckDuckGo"])
        engine_map = {"Google": "google", "Bing": "bing", "百度": "baidu", "DuckDuckGo": "duckduckgo"}
        current = parent.settings_mgr.get_search_engine()
        for name, key in engine_map.items():
            if key == current:
                self.search_engine_combo.setCurrentText(name)
        general_layout.addRow("默认搜索引擎:", self.search_engine_combo)
        tabs.addTab(general_tab, "常规")

        # ========== 2. 隐私设置 ==========
        privacy_tab = QWidget()
        privacy_layout = QFormLayout(privacy_tab)
        self.clear_history_btn = QPushButton("清理浏览数据...")
        self.clear_history_btn.clicked.connect(self.show_clear_data_dialog)
        privacy_layout.addRow("浏览数据:", self.clear_history_btn)
        tabs.addTab(privacy_tab, "隐私与安全")

        # ========== 3. 密码设置 ==========
        password_tab = QWidget()
        password_layout = QFormLayout(password_tab)
        self.password_status_label = QLabel()
        self.update_password_status()
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_input.setPlaceholderText("当前密码（如已设置）")
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText("新密码")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("确认新密码")
        password_layout.addRow("当前状态:", self.password_status_label)
        password_layout.addRow("当前密码:", self.current_password_input)
        password_layout.addRow("新密码:", self.new_password_input)
        password_layout.addRow("确认新密码:", self.confirm_password_input)
        tabs.addTab(password_tab, "密码保护")

        # ========== 4. AI 助手设置 ==========
        ai_tab = QWidget()
        ai_layout = QFormLayout(ai_tab)
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["DeepSeek", "OpenAI", "通义千问"])
        provider_map = {"DeepSeek": "deepseek", "OpenAI": "openai", "通义千问": "qwen"}
        current_provider = parent.settings_mgr.get_ai_provider()
        for name, key in provider_map.items():
            if key == current_provider:
                self.ai_provider_combo.setCurrentText(name)
        ai_layout.addRow("AI 服务商:", self.ai_provider_combo)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("请输入 API Key")
        self.api_key_input.setText(parent.settings_mgr.get_ai_api_key())
        ai_layout.addRow("API Key:", self.api_key_input)
        info_label = QLabel("💡 提示：右键菜单中的「问AI」会使用此配置\n\n"
                            "获取 API Key:\n"
                            "• DeepSeek: platform.deepseek.com\n"
                            "• OpenAI: platform.openai.com\n"
                            "• 通义千问: dashscope.aliyun.com")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #808080; font-size: 11px;")
        ai_layout.addRow("", info_label)
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_ai_connection)
        ai_layout.addRow("", self.test_btn)
        tabs.addTab(ai_tab, "AI 助手")

        # ========== 5. 关于页面 ==========
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        title_label = QLabel("Jnuo Nova")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0e639c; margin: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label = QLabel(f"版本 {VERSION}")
        version_label.setStyleSheet("font-size: 14px; color: #d4d4d4;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dev_label = QLabel(f"开发者: {DEVELOPER}\n基于 PyQt6 和 QtWebEngine 构建")
        dev_label.setStyleSheet("font-size: 12px; color: #a0a0a0; margin-top: 20px;")
        dev_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label = QLabel("© 2026-2026 Jnuo Nova. All rights reserved.")
        copyright_label.setStyleSheet("font-size: 10px; color: #606060; margin-top: 30px;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(title_label)
        about_layout.addWidget(version_label)
        about_layout.addWidget(dev_label)
        about_layout.addWidget(copyright_label)
        about_layout.addStretch()
        tabs.addTab(about_tab, "关于")

        layout.addWidget(tabs)

        # 按钮区域
        button_box = QDialogButtonBox()
        save_btn = button_box.addButton("保存设置", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = button_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    # ========== 辅助方法 ==========
    def update_password_status(self):
        if self.parent_browser and self.parent_browser.settings_mgr.has_password():
            self.password_status_label.setText("✅ 已设置密码")
            self.password_status_label.setStyleSheet("color: #4ec9b0;")
        else:
            self.password_status_label.setText("❌ 未设置密码")
            self.password_status_label.setStyleSheet("color: #f48771;")

    def show_clear_data_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("清理浏览数据")
        dialog.resize(300, 200)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("选择要清理的时间范围："))
        combo = QComboBox()
        combo.addItems(["过去1小时", "过去24小时", "过去7天", "全部"])
        layout.addWidget(combo)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.setStyleSheet(DARK_STYLE)

        def do_clear():
            choice = combo.currentText()
            days = None
            if choice == "过去1小时":
                days = 1 / 24
            elif choice == "过去24小时":
                days = 1
            elif choice == "过去7天":
                days = 7
            self.parent_browser.history_mgr.clear_history(days)
            QMessageBox.information(self, "完成", "浏览数据已清理")
            dialog.accept()

        ok_btn.clicked.connect(do_clear)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def save_settings(self):
        if not self.parent_browser:
            return

        # 保存搜索引擎
        engine_map = {"Google": "google", "Bing": "bing", "百度": "baidu", "DuckDuckGo": "duckduckgo"}
        selected = engine_map[self.search_engine_combo.currentText()]
        self.parent_browser.settings_mgr.set_search_engine(selected)

        # 保存密码设置
        current = self.current_password_input.text()
        new_pwd = self.new_password_input.text()
        confirm = self.confirm_password_input.text()

        if not self.parent_browser.settings_mgr.has_password():
            if new_pwd and new_pwd == confirm:
                self.parent_browser.settings_mgr.set_password(new_pwd)
                QMessageBox.information(self, "成功", "密码已设置")
                self.update_password_status()
                self.current_password_input.clear()
                self.new_password_input.clear()
                self.confirm_password_input.clear()
            elif new_pwd:
                QMessageBox.warning(self, "错误", "两次输入的密码不一致")
        else:
            if self.parent_browser.settings_mgr.verify_password(current):
                if new_pwd and new_pwd == confirm:
                    self.parent_browser.settings_mgr.set_password(new_pwd)
                    QMessageBox.information(self, "成功", "密码已修改")
                    self.update_password_status()
                    self.current_password_input.clear()
                    self.new_password_input.clear()
                    self.confirm_password_input.clear()
                elif new_pwd:
                    QMessageBox.warning(self, "错误", "两次输入的密码不一致")
            elif current or new_pwd:
                QMessageBox.warning(self, "错误", "当前密码错误")

        # 保存 AI 设置
        provider_map = {"DeepSeek": "deepseek", "OpenAI": "openai", "通义千问": "qwen"}
        self.parent_browser.settings_mgr.set_ai_provider(provider_map[self.ai_provider_combo.currentText()])
        self.parent_browser.settings_mgr.set_ai_api_key(self.api_key_input.text())

        self.accept()

    def test_ai_connection(self):
        """测试 AI API 连接"""
        if not self.parent_browser:
            return

        api_url = self.parent_browser.settings_mgr.get_ai_api_url()
        api_key = self.api_key_input.text()

        if not api_key:
            QMessageBox.warning(self, "错误", "请先输入 API Key")
            return

        provider_map = {"DeepSeek": "deepseek", "OpenAI": "openai", "通义千问": "qwen"}
        models = {'deepseek': 'deepseek-chat', 'openai': 'gpt-4o-mini', 'qwen': 'qwen-plus'}
        test_provider = provider_map[self.ai_provider_combo.currentText()]
        test_model = models.get(test_provider, 'deepseek-chat')

        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")

        # 将 network_manager 保存为实例变量，防止被垃圾回收
        self.network_manager = QNetworkAccessManager(self)

        request = QNetworkRequest(QUrl(api_url))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", f"Bearer {api_key}".encode())

        data = {
            "model": test_model,
            "messages": [{"role": "user", "content": "说'连接成功'"}],
            "max_tokens": 10
        }

        reply = self.network_manager.post(request, QByteArray(json.dumps(data).encode()))

        # 使用 lambda 传递 reply 参数，避免闭包问题
        reply.finished.connect(lambda: self._on_test_reply_finished(reply))

        # 设置超时（10秒后自动取消）
        timeout_timer = QTimer(self)
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(lambda: self._on_test_timeout(reply, timeout_timer))
        timeout_timer.start(10000)

    def _on_test_reply_finished(self, reply):
        """测试请求完成"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")

        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(reply.readAll().data().decode())
                if 'choices' in data:
                    QMessageBox.information(self, "测试成功", "连接成功！")
                else:
                    error_msg = data.get('error', {}).get('message', '未知错误')
                    QMessageBox.warning(self, "测试失败", f"API 错误: {error_msg}")
            except Exception as e:
                QMessageBox.warning(self, "测试失败", f"解析响应失败: {str(e)}")
        else:
            error_msg = reply.errorString()
            if "timeout" in error_msg.lower():
                QMessageBox.warning(self, "测试失败", "连接超时，请检查网络")
            else:
                QMessageBox.warning(self, "测试失败", f"网络错误: {error_msg}")

        reply.deleteLater()
        # 清理 network_manager
        if hasattr(self, 'network_manager'):
            self.network_manager.deleteLater()

    def _on_test_timeout(self, reply, timer):
        """测试超时处理"""
        if reply and reply.isRunning():
            reply.abort()
        timer.deleteLater()
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        QMessageBox.warning(self, "测试失败", "请求超时，请检查网络或 API Key")


# ========== 快捷键帮助对话框 ==========
class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jnuo Nova - 快捷键")
        self.resize(400, 450)
        layout = QVBoxLayout()
        shortcuts = [
            ("Ctrl+T", "新建标签页"),
            ("Ctrl+Shift+N", "新建无痕窗口"),
            ("Ctrl+W", "关闭当前标签页"),
            ("Ctrl+Tab", "下一个标签页"),
            ("Ctrl+Shift+Tab", "上一个标签页"),
            ("拖拽标签页", "改变顺序 / 拖出为新窗口"),
            ("Ctrl+L", "聚焦地址栏"),
            ("Ctrl+R / F5", "刷新页面"),
            ("Ctrl+H", "历史记录"),
            ("Ctrl+B", "书签管理"),
            ("Ctrl+D", "添加到书签"),
            ("Ctrl+Shift+Delete", "清理浏览数据"),
        ]
        for key, desc in shortcuts:
            label = QLabel(f"{key}  :  {desc}")
            label.setStyleSheet("color: #d4d4d4; padding: 4px;")
            layout.addWidget(label)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.setStyleSheet(DARK_STYLE)


# ========== 主浏览器窗口 ==========
class JnuoNova(QMainWindow):
    def __init__(self, incognito=False):
        super().__init__()

        # 禁用 WebEngine 的某些功能避免卡死
        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = ""  # 禁用远程调试

        self.incognito = incognito
        window_title = "Jnuo Nova 浏览器" + (" (无痕模式)" if incognito else "")
        self.setWindowTitle(window_title)
        self.setWindowIcon(QIcon(get_icon_path()))
        self.setGeometry(100, 100, 1300, 800)

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )

        if not incognito:
            self.settings_mgr = SettingsManager()
            self.bookmark_mgr = BookmarkManager()
            self.history_mgr = HistoryManager()
            self.download_manager = DownloadManager(self)
            self.password_mgr = PasswordManager()
            self.unlocked = False
        else:
            self.settings_mgr = None
            self.bookmark_mgr = None
            self.history_mgr = None
            self.download_manager = None
            self.password_mgr = None
            self.unlocked = True

        self.tab_widget = DraggableTabWidget(self)
        self.tab_widget.parent_browser = self
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        self.create_toolbar()
        self.setup_download_handler()
        self.add_new_tab()
        self.setStyleSheet(DARK_STYLE)

        if not incognito:
            self.check_and_prompt_password()
        self.setup_shortcuts()

    # ========== 窗口管理 ==========
    def open_incognito_window(self):
        try:
            new_window = JnuoNova(incognito=True)
            new_window.show()
        except Exception as e:
            print(f"打开无痕窗口失败: {e}")
            QMessageBox.warning(self, "Jnuo Nova", f"无法打开无痕窗口:\n{str(e)}")

    def close_tab(self, index):
        if self.tab_widget.count() > 1:
            webview = self.tab_widget.widget(index)
            if webview:
                webview.close_tab()
            self.tab_widget.removeTab(index)
        else:
            self.close()

    def next_tab(self):
        count = self.tab_widget.count()
        if count > 0:
            current = self.tab_widget.currentIndex()
            self.tab_widget.setCurrentIndex((current + 1) % count)

    def prev_tab(self):
        count = self.tab_widget.count()
        if count > 0:
            current = self.tab_widget.currentIndex()
            self.tab_widget.setCurrentIndex((current - 1) % count)

    # ========== 快捷键 ==========
    def setup_shortcuts(self):
        new_tab = QAction("新建标签页", self)
        new_tab.setShortcut(QKeySequence("Ctrl+T"))
        new_tab.triggered.connect(lambda: self.add_new_tab())
        self.addAction(new_tab)

        new_incognito = QAction("新建无痕窗口", self)
        new_incognito.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_incognito.triggered.connect(self.open_incognito_window)
        self.addAction(new_incognito)

        close_tab = QAction("关闭标签页", self)
        close_tab.setShortcut(QKeySequence("Ctrl+W"))
        close_tab.triggered.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))
        self.addAction(close_tab)

        focus_url = QAction("聚焦地址栏", self)
        focus_url.setShortcut(QKeySequence("Ctrl+L"))
        focus_url.triggered.connect(lambda: self.url_bar.setFocus())
        self.addAction(focus_url)

        if not self.incognito:
            show_history = QAction("历史记录", self)
            show_history.setShortcut(QKeySequence("Ctrl+H"))
            show_history.triggered.connect(self.show_history_dialog)
            self.addAction(show_history)

        if not self.incognito:
            show_bookmarks = QAction("书签管理", self)
            show_bookmarks.setShortcut(QKeySequence("Ctrl+B"))
            show_bookmarks.triggered.connect(self.show_bookmark_manager)
            self.addAction(show_bookmarks)

        if not self.incognito:
            add_bookmark = QAction("添加书签", self)
            add_bookmark.setShortcut(QKeySequence("Ctrl+D"))
            add_bookmark.triggered.connect(self.add_current_bookmark)
            self.addAction(add_bookmark)

        refresh_page = QAction("刷新", self)
        refresh_page.setShortcut(QKeySequence("F5"))
        refresh_page.triggered.connect(self.refresh)
        self.addAction(refresh_page)

        refresh_page2 = QAction("刷新2", self)
        refresh_page2.setShortcut(QKeySequence("Ctrl+R"))
        refresh_page2.triggered.connect(self.refresh)
        self.addAction(refresh_page2)

        if not self.incognito:
            clear_data = QAction("清理数据", self)
            clear_data.setShortcut(QKeySequence("Ctrl+Shift+Delete"))
            clear_data.triggered.connect(lambda: self.show_settings())
            self.addAction(clear_data)

        next_tab = QAction("下一个标签页", self)
        next_tab.setShortcut(QKeySequence("Ctrl+Tab"))
        next_tab.triggered.connect(self.next_tab)
        self.addAction(next_tab)

        prev_tab = QAction("上一个标签页", self)
        prev_tab.setShortcut(QKeySequence("Ctrl+Shift+Tab"))
        prev_tab.triggered.connect(self.prev_tab)
        self.addAction(prev_tab)

    # ========== 下载处理 ==========
    def setup_download_handler(self):
        if self.incognito:
            return
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.on_download_requested)

    def on_download_requested(self, download_item):
        if self.incognito:
            return
        download_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        suggested_path = os.path.join(download_dir, download_item.suggestedFileName())
        path, _ = QFileDialog.getSaveFileName(self, "保存文件", suggested_path)
        if path:
            download_id = self.download_manager.add_download(download_item.url().toString(), path)
            download_item.setPath(path)
            download_item.accept()
            download_item.downloadProgress.connect(lambda a, b: None)

    # ========== 工具栏 ==========
    def create_toolbar(self):
        toolbar = self.addToolBar("导航")
        toolbar.setMovable(False)

        self.back_btn = QPushButton("◀ 后退")
        self.forward_btn = QPushButton("前进 ▶")
        self.refresh_btn = QPushButton("🔄 刷新")
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("输入网址或搜索内容...")
        self.url_completer = QCompleter(self)
        self.url_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.url_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.url_completer.setMaxVisibleItems(10)
        popup = self.url_completer.popup()
        popup.setStyleSheet("""
            QListView {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 4px;
            }
            QListView::item:selected {
                background-color: #0e639c;
                color: white;
            }
        """)
        # 设置补全数据源
        self.update_url_completer()
        self.url_bar.setCompleter(self.url_completer)
        self.url_completer.activated.connect(self.on_completer_activated)
        self.url_bar.returnPressed.connect(self.navigate_or_search)
        self.url_bar.textChanged.connect(self.update_url_completer)

        bookmark_btn = QPushButton("⭐ 添加书签")
        bookmark_btn.clicked.connect(self.add_current_bookmark)
        show_bookmark_btn = QPushButton("📖 书签管理")
        show_bookmark_btn.clicked.connect(self.show_bookmark_manager)
        history_btn = QPushButton("📜 历史")
        history_btn.clicked.connect(self.show_history_dialog)
        downloads_btn = QPushButton("📥 下载")
        downloads_btn.clicked.connect(lambda: self.download_manager.show() if self.download_manager else None)
        settings_btn = QPushButton("⚙️ 设置")
        settings_btn.clicked.connect(self.show_settings)
        lock_btn = QPushButton("🔒 锁定")
        lock_btn.clicked.connect(self.lock_browser)

        # ========== 新增：AI 助手按钮 ==========
        ai_btn = QPushButton("🤖 AI 助手")
        ai_btn.clicked.connect(self.open_ai_assistant)
        ai_btn.setToolTip("打开 AI 助手对话窗口")

        help_btn = QPushButton("❓ 快捷键")
        help_btn.clicked.connect(self.show_shortcuts)

        if self.incognito:
            for btn in [bookmark_btn, show_bookmark_btn, history_btn, downloads_btn, settings_btn, lock_btn, ai_btn]:
                btn.setEnabled(False)
                btn.setToolTip("无痕模式下不可用")

        # 将 AI 按钮添加到工具栏（放在帮助按钮前面）
        for widget in [self.back_btn, self.forward_btn, self.refresh_btn, self.url_bar,
                       bookmark_btn, show_bookmark_btn, history_btn,
                       downloads_btn, settings_btn, lock_btn, ai_btn, help_btn]:
            toolbar.addWidget(widget)

        self.back_btn.clicked.connect(self.go_back)
        self.forward_btn.clicked.connect(self.go_forward)
        self.refresh_btn.clicked.connect(self.refresh)

        new_tab_btn = QPushButton("+ 新标签页")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab())
        toolbar.addWidget(new_tab_btn)

    def on_completer_activated(self, text):
        """用户选中补全项时，直接导航到该 URL"""
        self.navigate_to_url(text)

    # ========== 导航 ==========
    def go_back(self):
        wv = self.current_webview()
        if wv:
            wv.back()

    def go_forward(self):
        wv = self.current_webview()
        if wv:
            wv.forward()

    def refresh(self):
        wv = self.current_webview()
        if wv:
            wv.reload()

    def navigate_or_search(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        is_url = '.' in text and ' ' not in text and not text.startswith('?')
        if is_url:
            if not text.startswith("http"):
                text = "https://" + text
            self.navigate_to_url(text)
        else:
            if self.settings_mgr:
                search_url = self.settings_mgr.get_search_url()
                self.navigate_to_url(search_url + text)
            else:
                self.navigate_to_url("https://www.google.com/search?q=" + text)

    def navigate_to_url(self, url):
        wv = self.current_webview()
        if wv:
            wv.setUrl(QUrl(url))

    # ========== 标签页管理 ==========
    def add_new_tab(self, url=None):
        """添加新标签页 - 支持图标显示"""
        if url is None:
            url = QUrl("https://www.bing.com")
        elif isinstance(url, str):
            url = QUrl(url)

        # 创建新的 WebView
        webview = CustomWebView(self, incognito=self.incognito)

        # 先添加标签页
        index = self.tab_widget.addTab(webview, "加载中...")
        self.tab_widget.setCurrentIndex(index)

        # 设置标题更新
        def update_title(title):
            if index < self.tab_widget.count():
                short_title = title[:27] + "..." if len(title) > 30 else title
                self.tab_widget.setTabText(index, short_title)

        # 设置 URL 栏更新
        def update_url(qurl):
            if self.tab_widget.currentWidget() == webview:
                self.url_bar.setText(qurl.toString())

        # 更新标签页图标（只用于显示，不保存历史）
        def update_tab_icon(icon):
            if index < self.tab_widget.count() and not icon.isNull():
                self.tab_widget.setTabIcon(index, icon)

        webview.titleChanged.connect(update_title)
        webview.urlChanged.connect(update_url)
        webview.iconChanged.connect(update_tab_icon)

        # 延迟加载 URL
        def load_url():
            try:
                webview.setUrl(url)
            except Exception as e:
                print(f"加载 URL 失败: {e}")

        QTimer.singleShot(10, load_url)

        # 历史记录
        if not self.incognito and self.history_mgr:
            def on_load_finished(ok):
                if ok:
                    url_str = webview.url().toString()
                    title = webview.title()
                    if url_str and not url_str.startswith("about:blank"):
                        # 先保存历史记录（不带图标）
                        self.history_mgr.add_history(url_str, title, None)
                        
                        # 轮询获取图标（不依赖 iconChanged 信号）
                        def try_get_icon(attempt=0):
                            if attempt > 10:  # 最多尝试10次（共5秒）
                                print(f"⏰ 图标获取超时: {url_str}")
                                return
                            
                            try:
                                icon = webview.icon()
                                if not icon.isNull():
                                    pixmap = icon.pixmap(32, 32)
                                    if not pixmap.isNull():
                                        byte_array = QByteArray()
                                        buffer = QBuffer(byte_array)
                                        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                                        pixmap.save(buffer, "PNG")
                                        icon_data = byte_array.data()
                                        self.history_mgr.update_icon(url_str, icon_data)
                                        print(f"✅ 图标已保存: {url_str}")
                                        return
                            except Exception as e:
                                print(f"❌ 获取图标失败: {e}")
                            
                            # 如果图标为空，500ms 后重试
                            QTimer.singleShot(500, lambda: try_get_icon(attempt + 1))
                        
                        # 延迟 500ms 后开始尝试获取图标
                        QTimer.singleShot(500, lambda: try_get_icon(0))
                        
                if ok and not self.incognito:
                    QTimer.singleShot(200, webview.inject_auto_fill_script)

            webview.loadFinished.connect(on_load_finished)

        return webview

    def add_new_tab_with_ai_question(self, question: str):
        """新建标签页打开内置 AI 对话页面，可选自动发送问题"""
        if self.incognito or not self.settings_mgr:
            QMessageBox.warning(self, "错误", "无痕模式下无法使用 AI 功能")
            return

        # 创建 WebView
        webview = CustomWebView(self, incognito=self.incognito)
        index = self.tab_widget.addTab(webview, "AI 助手")
        self.tab_widget.setCurrentIndex(index)

        # 获取 HTML 内容
        from urllib.parse import quote
        encoded_question = quote(question) if question else ""

        html_content = self._get_ai_chat_html(encoded_question)
        webview.setHtml(html_content)

        # 设置 WebChannel
        QTimer.singleShot(500, lambda: self._setup_ai_webchannel(webview))

        # 只有当有问题时才自动发送（空白问题时不发送）
        if question and question.strip():
            def auto_send_after_load():
                js_code = f"""
                (function() {{
                    console.log("尝试自动发送问题...");
                    var checkCount = 0;
                    var maxChecks = 30;
                    var checkInterval = setInterval(function() {{
                        checkCount++;
                        if (typeof webChannelReady !== 'undefined' && webChannelReady && aiBridge) {{
                            console.log("连接就绪，发送问题");
                            clearInterval(checkInterval);
                            var question = decodeURIComponent("{encoded_question}");
                            var msgInput = document.getElementById('messageInput');
                            var sendBtn = document.getElementById('sendBtn');
                            if (msgInput && sendBtn) {{
                                msgInput.value = question;
                                sendBtn.click();
                            }}
                        }} else if (checkCount >= maxChecks) {{
                            console.log("超时，无法发送问题");
                            clearInterval(checkInterval);
                        }}
                    }}, 500);
                }})();
                """
                QTimer.singleShot(1000, lambda: webview.page().runJavaScript(js_code))

            QTimer.singleShot(1500, auto_send_after_load)

    def _get_ai_chat_html(self, question=""):
        """返回 AI 聊天 HTML 内容"""
        from urllib.parse import quote
        encoded_question = quote(question)

        return f'''<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>Jnuo Nova AI 助手</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #1e1e1e;
                color: #d4d4d4;
                height: 100vh;
                display: flex;
                flex-direction: column;
            }}
            .header {{
                background-color: #2d2d2d;
                padding: 12px 20px;
                border-bottom: 1px solid #3c3c3c;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header h1 {{ font-size: 18px; color: #0e639c; }}
            .chat-container {{
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            .message {{
                display: flex;
                max-width: 85%;
                animation: fadeIn 0.3s ease;
            }}
            .message.user {{ align-self: flex-end; }}
            .message.assistant {{ align-self: flex-start; }}
            .message-content {{
                padding: 10px 14px;
                border-radius: 12px;
                line-height: 1.5;
                font-size: 14px;
                white-space: pre-wrap;
                word-break: break-word;
            }}
            .user .message-content {{
                background-color: #0e639c;
                color: white;
            }}
            .assistant .message-content {{
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
            }}
            .input-area {{
                background-color: #2d2d2d;
                padding: 16px;
                border-top: 1px solid #3c3c3c;
                display: flex;
                gap: 10px;
            }}
            textarea {{
                flex: 1;
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                padding: 10px;
                color: #d4d4d4;
                font-family: inherit;
                resize: none;
                font-size: 14px;
            }}
            button {{
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                cursor: pointer;
            }}
            button:disabled {{
                background-color: #3c3c3c;
                cursor: not-allowed;
            }}
            .loading {{
                display: inline-block;
                width: 14px;
                height: 14px;
                border: 2px solid #d4d4d4;
                border-top-color: #0e639c;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .status {{
                position: fixed;
                bottom: 10px;
                right: 10px;
                font-size: 11px;
                background: #2d2d2d;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .connected {{ color: #4ec9b0; }}
            .error {{ color: #f48771; }}
        </style>
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Jnuo Nova AI 助手</h1>
            <button id="newChatBtn">➕ 新对话</button>
        </div>
        <div class="chat-container" id="chatContainer">
            <div class="message assistant">
                <div class="message-content">
                    👋 你好！我是 Jnuo Nova AI 助手。<br><br>
                    🔌 正在连接...
                </div>
            </div>
        </div>
        <div class="input-area">
            <textarea id="messageInput" rows="2" placeholder="等待连接..." disabled></textarea>
            <button id="sendBtn" disabled>发送</button>
        </div>
        <div class="status" id="status">🔌 正在连接 AI 服务...</div>

        <script>
            let sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            let isSending = false;
            let aiBridge = null;
            let webChannelReady = false;

            const chatContainer = document.getElementById('chatContainer');
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');
            const statusDiv = document.getElementById('status');

            function updateStatus(text, isError = false) {{
                statusDiv.innerHTML = text;
                statusDiv.style.color = isError ? '#f48771' : '#4ec9b0';
            }}

            function addMessage(text, role, isHtml = false) {{
                const msgDiv = document.createElement("div");
                msgDiv.className = "message " + role;
                const contentDiv = document.createElement("div");
                contentDiv.className = "message-content";
                if (isHtml) contentDiv.innerHTML = text;
                else contentDiv.textContent = text;
                msgDiv.appendChild(contentDiv);
                chatContainer.appendChild(msgDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }}

            function sendMessage() {{
                const question = messageInput.value.trim();
                if (!question || isSending || !webChannelReady) return;

                isSending = true;
                sendBtn.disabled = true;
                addMessage(question, "user");
                messageInput.value = "";

                // 添加加载提示
                const loadingDiv = document.createElement("div");
                loadingDiv.className = "message assistant";
                loadingDiv.id = "loadingMsg";
                loadingDiv.innerHTML = '<div class="message-content"><span class="loading"></span> 思考中...</div>';
                chatContainer.appendChild(loadingDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;

                const requestId = sessionId + '_' + Date.now();
                window.aiCallbacks = window.aiCallbacks || {{}};

                window.aiCallbacks[requestId] = function(response) {{
                    const loadingMsg = document.getElementById("loadingMsg");
                    if (loadingMsg) loadingMsg.remove();

                    if (response && response.success) {{
                        addMessage(response.answer, "assistant", true);
                    }} else {{
                        const errorMsg = response && response.error ? response.error : "未知错误";
                        addMessage("❌ 错误: " + errorMsg, "assistant");
                    }}
                    isSending = false;
                    sendBtn.disabled = false;
                }};

                try {{
                    aiBridge.send_message(requestId, question);
                }} catch(e) {{
                    document.getElementById("loadingMsg")?.remove();
                    addMessage("❌ 调用失败: " + e.message, "assistant");
                    isSending = false;
                    sendBtn.disabled = false;
                }}
            }}

            // 初始化 WebChannel
            function init() {{
                console.log("初始化 WebChannel...");

                if (typeof QWebChannel === 'undefined') {{
                    setTimeout(init, 200);
                    return;
                }}

                if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {{
                    setTimeout(init, 200);
                    return;
                }}

                updateStatus("🔄 建立连接中...");

                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    aiBridge = channel.objects.aiBridge;
                    if (aiBridge) {{
                        webChannelReady = true;
                        updateStatus("✅ AI 已就绪");
                        messageInput.disabled = false;
                        sendBtn.disabled = false;
                        messageInput.placeholder = "输入你的问题... (Enter 发送)";

                        // 更新欢迎消息
                        const welcomeMsg = chatContainer.querySelector('.message.assistant .message-content');
                        if (welcomeMsg && welcomeMsg.innerHTML.includes("正在连接")) {{
                            welcomeMsg.innerHTML = '👋 你好！我是 Jnuo Nova AI 助手。<br><br>💡 我可以联网搜索最新信息，并记住我们的对话上下文。<br>💡 试试问我："今天是几月几日？" 或 "最近有什么新闻？"';
                        }}

                        // 如果有预设问题，自动发送
                        const urlParams = new URLSearchParams(window.location.search);
                        const presetQuestion = urlParams.get('q');
                        if (presetQuestion) {{
                            setTimeout(() => {{
                                messageInput.value = decodeURIComponent(presetQuestion);
                                sendMessage();
                            }}, 500);
                        }}
                    }} else {{
                        updateStatus("❌ 连接失败", true);
                    }}
                }});
            }}

            // 绑定事件
            sendBtn.onclick = sendMessage;
            document.getElementById('newChatBtn').onclick = function() {{
                sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                while (chatContainer.firstChild) chatContainer.removeChild(chatContainer.firstChild);
                addMessage('👋 你好！我是 Jnuo Nova AI 助手。<br><br>💡 开始新的对话吧！', "assistant", true);
                updateStatus("✅ 新对话已开始");
            }};

            messageInput.onkeydown = function(e) {{
                if (e.key === "Enter" && !e.shiftKey) {{
                    e.preventDefault();
                    sendMessage();
                }}
            }};

            // 启动
            setTimeout(init, 100);
        </script>
    </body>
    </html>'''

    def _setup_ai_webchannel(self, webview):
        """设置 AI 页面的 WebChannel"""
        if webview and webview.page():
            webview.page().setWebChannel(webview.channel)
            print("AI 页面 WebChannel 已设置")

    def on_tab_changed(self, index):
        if index >= 0:
            webview = self.tab_widget.widget(index)
            if webview:
                self.update_url_bar(webview.url(), webview)

    def update_url_bar(self, qurl, webview):
        if self.tab_widget.currentWidget() == webview:
            self.url_bar.setText(qurl.toString())

    def current_webview(self):
        return self.tab_widget.currentWidget()

    # ========== 密码锁定 ==========
    def check_and_prompt_password(self):
        if self.incognito or not self.settings_mgr:
            return
        if not self.settings_mgr.has_password():
            reply = QMessageBox.question(self, "Jnuo Nova - 设置密码",
                                         "您尚未设置浏览器密码。\n\n设置密码后可以保护您的浏览记录、锁定书签等隐私数据。\n\n现在就去设置密码吗？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.show_settings()
            else:
                self.unlocked = True

    def lock_browser(self):
        if self.incognito or not self.settings_mgr:
            return
        if not self.settings_mgr.has_password():
            QMessageBox.information(self, "Jnuo Nova", "您尚未设置密码，无法锁定。")
            return
        self.unlocked = False
        QMessageBox.information(self, "Jnuo Nova", "浏览器已锁定")

    def require_unlock(self):
        try:
            if self.incognito or not self.settings_mgr:
                return True
            if not self.settings_mgr.has_password():
                return True
            if not self.unlocked:
                dialog = UnlockDialog(self)
                if dialog.exec() == QDialog.DialogCode.Accepted and dialog.unlocked:
                    self.unlocked = True
                    return True
                return False
            return True
        except Exception as e:
            print(f"解锁检查失败: {e}")
            return True

    # ========== 设置和帮助 ==========
    def show_settings(self):
        if self.incognito:
            return
        try:
            dialog = SettingsDialog(self)
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                if self.settings_mgr.has_password():
                    self.unlocked = False
                else:
                    self.unlocked = True
        except Exception as e:
            print(f"打开设置对话框失败: {e}")
            QMessageBox.warning(self, "错误", f"无法打开设置: {e}")

    def open_ai_assistant(self):
        """打开 AI 助手（新建标签页）"""
        if self.incognito:
            QMessageBox.warning(self, "提示", "无痕模式下无法使用 AI 助手")
            return

        # 检查是否配置了 API Key
        if not self.settings_mgr.has_ai_api_key():
            reply = QMessageBox.question(
                self,
                "未配置 API Key",
                "AI 助手需要配置 API Key，现在去设置吗？\n\n"
                "支持 DeepSeek（推荐，有免费额度）、OpenAI、通义千问。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.show_settings()
            return

        # 打开 AI 助手新标签页（不自动发送问题，只打开空白对话）
        self.add_new_tab_with_ai_question("")

    def show_shortcuts(self):
        try:
            dialog = ShortcutsDialog(self)
            dialog.exec()
        except Exception as e:
            print(f"打开快捷键对话框失败: {e}")
            QMessageBox.warning(self, "错误", f"无法打开快捷键帮助: {e}")

    # ========== 书签功能 ==========
    def add_current_bookmark(self):
        if self.incognito or not self.bookmark_mgr:
            return
        wv = self.current_webview()
        if wv:
            title = wv.title()
            url = wv.url().toString()
            folders = self.bookmark_mgr.get_folders()

            dialog = QDialog(self)
            dialog.setWindowTitle("添加到书签")
            dialog.resize(400, 250)
            layout = QVBoxLayout()

            layout.addWidget(QLabel("选择文件夹:"))
            folder_combo = QComboBox()
            folder_combo.addItems(folders)
            layout.addWidget(folder_combo)

            new_folder_btn = QPushButton("新建文件夹")
            def create_new_folder():
                name, ok = QInputDialog.getText(dialog, "新建文件夹", "文件夹名称:")
                if ok and name:
                    self.bookmark_mgr.add_folder(name)
                    folder_combo.addItem(name)
                    folder_combo.setCurrentText(name)
            new_folder_btn.clicked.connect(create_new_folder)
            layout.addWidget(new_folder_btn)

            lock_checkbox = QCheckBox("🔒 锁定此书签（需要密码才能打开）")
            layout.addWidget(lock_checkbox)

            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            dialog.setLayout(layout)
            dialog.setStyleSheet(DARK_STYLE)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                folder = folder_combo.currentText()
                locked = lock_checkbox.isChecked()

                if locked and not self.require_unlock():
                    QMessageBox.warning(self, "需要密码", "需要先解锁才能创建锁定的书签")
                    return

                self.bookmark_mgr.add_bookmark(title, url, folder, locked)
                lock_msg = "（已锁定）" if locked else ""
                QMessageBox.information(self, "Jnuo Nova", f"已添加书签：{title} {lock_msg}")

    def show_bookmark_manager(self):
        if self.incognito or not self.bookmark_mgr:
            return
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Jnuo Nova - 书签管理")
            dialog.resize(600, 500)
            layout = QVBoxLayout()
            list_widget = QListWidget()

            bookmarks_list = []

            for folder in self.bookmark_mgr.get_folders():
                for idx, bm in enumerate(self.bookmark_mgr.get_bookmarks(folder)):
                    locked_flag = "🔒 " if bm.get("locked", False) else "📄 "
                    display_text = f"[{folder}] {locked_flag}{bm['title']} - {bm['url']}"
                    list_widget.addItem(display_text)
                    bookmarks_list.append((folder, idx, bm['title'], bm['url'], bm.get("locked", False)))

            def open_selected():
                current = list_widget.currentRow()
                if current >= 0 and current < len(bookmarks_list):
                    folder, idx, title, url, locked = bookmarks_list[current]
                    if locked and not self.require_unlock():
                        QMessageBox.warning(dialog, "需要密码", "此书签已锁定，需要密码才能打开")
                        return
                    if url.startswith('http'):
                        dialog.accept()
                        # 使用 QTimer 确保对话框完全关闭后再打开新标签页
                        QTimer.singleShot(100, lambda u=url: self._open_url_in_new_tab_safe(u))

            def toggle_lock():
                current = list_widget.currentRow()
                if current >= 0 and current < len(bookmarks_list):
                    folder, idx, title, url, locked = bookmarks_list[current]
                    if not locked and not self.require_unlock():
                        QMessageBox.warning(dialog, "需要密码", "需要先解锁才能锁定书签")
                        return
                    self.bookmark_mgr.toggle_lock(folder, idx)
                    dialog.accept()
                    QTimer.singleShot(100, self.show_bookmark_manager)

            def delete_selected():
                current = list_widget.currentRow()
                if current >= 0 and current < len(bookmarks_list):
                    folder, idx, title, url, locked = bookmarks_list[current]
                    if locked and not self.require_unlock():
                        QMessageBox.warning(dialog, "需要密码", "需要先解锁才能删除锁定的书签")
                        return
                    reply = QMessageBox.question(dialog, "确认删除", f"确定要删除书签「{title}」吗？",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        self.bookmark_mgr.remove_bookmark(folder, idx)
                        dialog.accept()
                        QTimer.singleShot(100, self.show_bookmark_manager)

            open_btn = QPushButton("打开选中")
            open_btn.clicked.connect(open_selected)

            lock_btn = QPushButton("🔒 切换锁定状态")
            lock_btn.clicked.connect(toggle_lock)

            delete_btn = QPushButton("删除选中")
            delete_btn.clicked.connect(delete_selected)

            btn_layout = QHBoxLayout()
            btn_layout.addWidget(open_btn)
            btn_layout.addWidget(lock_btn)
            btn_layout.addWidget(delete_btn)

            layout.addWidget(list_widget)
            layout.addLayout(btn_layout)
            dialog.setLayout(layout)
            dialog.setStyleSheet(DARK_STYLE)
            dialog.exec()

        except Exception as e:
            print(f"打开书签管理失败: {e}")
            QMessageBox.warning(self, "错误", f"无法打开书签管理: {e}")

    # ========== 历史记录 ==========
    def show_history_dialog(self):
        """显示历史记录 - 按时段分组"""
        if self.incognito or not self.history_mgr:
            return
        if not self.require_unlock():
            return

        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Jnuo Nova - 浏览历史")
            dialog.resize(700, 500)
            layout = QVBoxLayout()
            
            # 使用 QListWidget 支持图标和分组
            list_widget = QListWidget()
            list_widget.setIconSize(QtCore.QSize(16, 16))
            
            # 获取各时段数据
            today_records = self.history_mgr.get_history_today()
            yesterday_records = self.history_mgr.get_history_yesterday()
            week_records = self.history_mgr.get_history_last_7_days()
            older_records = self.history_mgr.get_history_older()
            
            # 存储所有记录用于打开
            all_records = []
            
            def add_records_with_header(records, header_text):
                """添加带分组标题的记录"""
                if not records:
                    return
                # 添加分组标题（不可选中）
                header_item = QListWidgetItem(f"── {header_text} ──")
                header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                header_item.setForeground(QColor(100, 100, 100))
                list_widget.addItem(header_item)
                
                for record in records:
                    if len(record) >= 3:
                        url = record[0]
                        title = record[1]
                        visit_time = record[2]
                        icon_data = record[3] if len(record) > 3 else None
                        
                        # 格式化时间
                        try:
                            dt = datetime.strptime(visit_time, "%Y-%m-%d %H:%M:%S")
                            time_str = dt.strftime("%H:%M")
                        except:
                            time_str = visit_time[:5] if len(visit_time) >= 5 else visit_time
                        
                        display_text = f"{title or url}  {time_str}"
                        item = QListWidgetItem(display_text)
                        
                        if icon_data:
                            pixmap = QPixmap()
                            if pixmap.loadFromData(icon_data):
                                item.setIcon(QIcon(pixmap))
                            else:
                                item.setIcon(self._get_default_icon())
                        else:
                            item.setIcon(self._get_default_icon())
                        
                        list_widget.addItem(item)
                        all_records.append((url, title, visit_time))
            
            # 按顺序添加各时段
            add_records_with_header(today_records, "今天")
            add_records_with_header(yesterday_records, "昨天")
            add_records_with_header(week_records, "过去7天")
            add_records_with_header(older_records, "更早")
            
            if not all_records:
                QMessageBox.information(dialog, "提示", "暂无浏览记录")
                dialog.accept()
                return

            def open_history():
                current = list_widget.currentRow()
                if current < 0:
                    return
                # 跳过分组标题
                item = list_widget.item(current)
                if not item or not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
                    return
                # 计算对应的记录索引
                record_index = 0
                for i in range(current):
                    if list_widget.item(i).flags() & Qt.ItemFlag.ItemIsSelectable:
                        record_index += 1
                if record_index < len(all_records):
                    try:
                        url = all_records[record_index][0]
                        if url and (url.startswith('http') or url.startswith('https')):
                            dialog.accept()
                            self._open_url_in_new_tab_safe(url)
                        else:
                            QMessageBox.warning(dialog, "错误", "无效的网址")
                    except Exception as e:
                        print(f"打开历史记录失败: {e}")
                        QMessageBox.warning(dialog, "错误", f"无法打开此链接: {str(e)}")

            open_btn = QPushButton("在新标签页打开")
            open_btn.clicked.connect(open_history)
            
            clear_btn = QPushButton("🗑️ 全部清除")
            def clear_all_history():
                reply = QMessageBox.question(
                    dialog, 
                    "确认清除", 
                    "确定要清除所有历史记录吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.history_mgr.clear_history()
                    dialog.accept()
                    QMessageBox.information(self, "完成", "历史记录已清除")
            clear_btn.clicked.connect(clear_all_history)

            btn_layout = QHBoxLayout()
            btn_layout.addWidget(open_btn)
            btn_layout.addWidget(clear_btn)
            
            list_widget.itemDoubleClicked.connect(lambda item: open_history())

            layout.addWidget(list_widget)
            layout.addLayout(btn_layout)
            dialog.setLayout(layout)
            dialog.setStyleSheet(DARK_STYLE)
            dialog.exec()

        except Exception as e:
            print(f"显示历史对话框失败: {e}")
            QMessageBox.warning(self, "错误", f"无法显示历史记录: {str(e)}")
    
    def _get_default_icon(self):
        """生成一个默认的网站图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(60, 60, 60))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.drawRect(0, 0, 15, 15)
        painter.drawText(3, 12, "🌐")
        painter.end()
        return QIcon(pixmap)

    def _open_url_in_new_tab_safe(self, url: str):
        """安全地打开新标签页"""
        # 直接调用，不使用额外延迟
        self.add_new_tab(url)

    def on_tab_changed(self, index):
        if index >= 0:
            webview = self.tab_widget.widget(index)
            if webview:
                self.update_url_bar(webview.url(), webview)

                # 如果其他标签页在全屏模式，强制退出
                for i in range(self.tab_widget.count()):
                    wv = self.tab_widget.widget(i)
                    if wv and wv != webview and hasattr(wv, '_fullscreen_mode') and wv._fullscreen_mode:
                        print(f"强制退出标签页 {i} 的全屏模式")
                        wv.page().runJavaScript("""
                            if (document.exitFullscreen) {
                                document.exitFullscreen();
                            } else if (document.webkitExitFullscreen) {
                                document.webkitExitFullscreen();
                            }
                        """)
                        wv._fullscreen_mode = False
                        wv.setCursor(Qt.CursorStyle.ArrowCursor)

    def closeEvent(self, event):
        """关闭窗口时，确保所有标签页退出全屏"""
        for i in range(self.tab_widget.count()):
            wv = self.tab_widget.widget(i)
            if wv and hasattr(wv, '_fullscreen_mode') and wv._fullscreen_mode:
                wv.page().runJavaScript("""
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                    }
                """)
        event.accept()
        
    # ========== 自动补全 ==========
    def get_url_list(self) -> list:
        """从历史记录和书签中提取所有 URL，用于地址栏自动补全"""
        # 无痕模式或无管理器时返回空列表
        if self.incognito or not self.history_mgr or not self.bookmark_mgr:
            return []

        urls = set()

        # 1. 从历史记录中获取 URL
        try:
            history = self.history_mgr.get_history(limit=100)
            for record in history:
                if len(record) >= 1 and record[0].startswith('http'):
                    urls.add(record[0])
        except Exception as e:
            print(f"获取历史 URL 失败: {e}")

        # 2. 从书签中获取 URL
        try:
            for folder in self.bookmark_mgr.get_folders():
                for bm in self.bookmark_mgr.get_bookmarks(folder):
                    if bm.get('url', '').startswith('http'):
                        urls.add(bm['url'])
        except Exception as e:
            print(f"获取书签 URL 失败: {e}")

        return sorted(list(urls))
    
    def update_url_completer(self):
        """更新地址栏的自动补全数据源"""
        if hasattr(self, 'url_completer'):
            url_list = self.get_url_list()
            # 如果当前有输入，根据输入过滤列表
            current_text = self.url_bar.text().strip().lower()
            if current_text:
                filtered_urls = [url for url in url_list if current_text in url.lower()]
            else:
                filtered_urls = url_list
            self.url_completer.setModel(QStringListModel(filtered_urls))


# ========== 程序入口 ==========
if __name__ == "__main__":
    import ctypes

    # 禁用 WebEngine 沙箱（解决 Windows 卡死问题）
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--no-sandbox "
        "--disable-gpu-sandbox "
        "--disable-software-rasterizer "
        "--enable-features=NetworkService,NetworkServiceInProcess "
        "--disable-features=UseChromeOSDirectVideoDecoder "
        "--ignore-gpu-blocklist"
    )

    # 注册自定义协议（必须在 QApplication 创建之前）
    register_custom_scheme()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_icon_path()))
    app.setStyle("Fusion")

    # 创建浏览器窗口
    browser = JnuoNova(incognito=False)
    browser.show()

    sys.exit(app.exec())

# pyinstaller --onefile --windowed --name="Jnuo Nova" --icon=icon.ico "Jnuo_Nova.py"
