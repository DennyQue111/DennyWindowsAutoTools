import sys
import os
import time
import threading
from urllib.parse import urlparse
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QLabel, QLineEdit, QTextEdit, 
                               QMessageBox, QFileDialog, QProgressBar, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class FolderScanWorker(QThread):
    """文件夹扫描工作线程"""
    finished = Signal(str)
    
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
    
    def run(self):
        try:
            result = self.scan_folder(self.folder_path)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"扫描出错: {str(e)}")
    
    def scan_folder(self, folder_path):
        """扫描文件夹并返回子文件夹信息"""
        if not os.path.exists(folder_path):
            return "错误：指定的路径不存在！"
        
        if not os.path.isdir(folder_path):
            return "错误：指定的路径不是文件夹！"
        
        result = f"扫描路径: {folder_path}\n"
        result += "=" * 50 + "\n\n"
        
        try:
            items = os.listdir(folder_path)
            folders = []
            
            for item in items:
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    try:
                        size = self.get_folder_size(item_path)
                        folders.append((item, size))
                    except PermissionError:
                        folders.append((item, "无权限访问"))
                    except Exception as e:
                        folders.append((item, f"错误: {str(e)}"))
            
            if not folders:
                result += "该文件夹下没有子文件夹。"
            else:
                result += f"找到 {len(folders)} 个子文件夹:\n\n"
                for folder_name, size in folders:
                    if isinstance(size, int):
                        size_str = self.format_size(size)
                    else:
                        size_str = size
                    result += f"📁 {folder_name}\n"
                    result += f"   大小: {size_str}\n\n"
        
        except PermissionError:
            result += "错误：没有权限访问该文件夹！"
        except Exception as e:
            result += f"扫描时发生错误: {str(e)}"
        
        return result
    
    def get_folder_size(self, folder_path):
        """计算文件夹大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue
        except PermissionError:
            raise PermissionError("无权限访问")
        return total_size
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"


class DownloadWorker(QThread):
    """下载工作线程"""
    progress_updated = Signal(int, str, str)  # 进度, 速度, 状态
    download_finished = Signal(bool, str)  # 成功/失败, 消息
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.is_paused = False
        self.is_cancelled = False
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.start_time = time.time()
        
    def run(self):
        try:
            self.download_file()
        except Exception as e:
            self.download_finished.emit(False, f"下载失败: {str(e)}")
    
    def download_file(self):
        """执行文件下载"""
        # 创建会话并设置重试策略
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # 检查是否支持断点续传
        resume_pos = 0
        if os.path.exists(self.save_path):
            resume_pos = os.path.getsize(self.save_path)
            headers['Range'] = f'bytes={resume_pos}-'
        
        try:
            response = session.get(self.url, headers=headers, stream=True, timeout=30)
            
            # 获取文件总大小
            if 'content-length' in response.headers:
                self.total_bytes = int(response.headers['content-length'])
                if resume_pos > 0:
                    self.total_bytes += resume_pos
            elif 'content-range' in response.headers:
                # 处理断点续传的情况
                content_range = response.headers['content-range']
                self.total_bytes = int(content_range.split('/')[-1])
            
            self.downloaded_bytes = resume_pos
            
            # 打开文件进行写入
            mode = 'ab' if resume_pos > 0 else 'wb'
            with open(self.save_path, mode) as file:
                chunk_size = 8192  # 8KB chunks
                last_update_time = time.time()
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.is_cancelled:
                        self.download_finished.emit(False, "下载已取消")
                        return
                    
                    while self.is_paused and not self.is_cancelled:
                        time.sleep(0.1)
                    
                    if chunk:
                        file.write(chunk)
                        self.downloaded_bytes += len(chunk)
                        
                        # 更新进度（每0.1秒更新一次）
                        current_time = time.time()
                        if current_time - last_update_time >= 0.1:
                            self.update_progress()
                            last_update_time = current_time
            
            self.download_finished.emit(True, "下载完成！")
            
        except requests.exceptions.RequestException as e:
            self.download_finished.emit(False, f"网络错误: {str(e)}")
        except Exception as e:
            self.download_finished.emit(False, f"下载错误: {str(e)}")
    
    def update_progress(self):
        """更新下载进度"""
        if self.total_bytes > 0:
            progress = int((self.downloaded_bytes / self.total_bytes) * 100)
        else:
            progress = 0
        
        # 计算下载速度
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            speed = self.downloaded_bytes / elapsed_time
            speed_str = self.format_speed(speed)
        else:
            speed_str = "0 B/s"
        
        # 格式化已下载大小
        size_str = f"{self.format_size(self.downloaded_bytes)}"
        if self.total_bytes > 0:
            size_str += f" / {self.format_size(self.total_bytes)}"
        
        self.progress_updated.emit(progress, speed_str, size_str)
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"
    
    def format_speed(self, speed_bytes):
        """格式化下载速度"""
        return f"{self.format_size(speed_bytes)}/s"
    
    def pause(self):
        """暂停下载"""
        self.is_paused = True
    
    def resume(self):
        """恢复下载"""
        self.is_paused = False
    
    def cancel(self):
        """取消下载"""
        self.is_cancelled = True


class DownloadWindow(QWidget):
    """下载工具窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.download_worker = None
        self.is_downloading = False
        
    def init_ui(self):
        self.setWindowTitle("下载工具")
        self.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout()
        
        # URL输入区域
        url_group = QGroupBox("下载链接")
        url_group.setFont(QFont("Microsoft YaHei", 10))
        url_layout = QVBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入要下载的文件链接，例如: https://example.com/file.zip")
        self.url_input.setFont(QFont("Microsoft YaHei", 10))
        
        url_layout.addWidget(self.url_input)
        url_group.setLayout(url_layout)
        
        # 保存路径区域
        path_group = QGroupBox("保存位置")
        path_group.setFont(QFont("Microsoft YaHei", 10))
        path_layout = QHBoxLayout()
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请选择文件保存路径")
        self.path_input.setFont(QFont("Microsoft YaHei", 10))
        
        browse_button = QPushButton("浏览")
        browse_button.setFont(QFont("Microsoft YaHei", 10))
        browse_button.clicked.connect(self.browse_save_path)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_button)
        path_group.setLayout(path_layout)
        
        # 控制按钮区域
        control_layout = QHBoxLayout()
        
        self.download_button = QPushButton("开始下载")
        self.download_button.setFont(QFont("Microsoft YaHei", 11))
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.download_button.clicked.connect(self.start_download)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.setFont(QFont("Microsoft YaHei", 11))
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.pause_button.clicked.connect(self.pause_download)
        self.pause_button.setEnabled(False)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFont(QFont("Microsoft YaHei", 11))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        
        control_layout.addWidget(self.download_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.cancel_button)
        control_layout.addStretch()
        
        # 进度显示区域
        progress_group = QGroupBox("下载进度")
        progress_group.setFont(QFont("Microsoft YaHei", 10))
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 6px;
            }
        """)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setAlignment(Qt.AlignCenter)
        
        self.speed_label = QLabel("下载速度: 0 B/s")
        self.speed_label.setFont(QFont("Microsoft YaHei", 9))
        self.speed_label.setAlignment(Qt.AlignCenter)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.speed_label)
        progress_group.setLayout(progress_layout)
        
        # 添加到主布局
        layout.addWidget(url_group)
        layout.addWidget(path_group)
        layout.addLayout(control_layout)
        layout.addWidget(progress_group)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QWidget {
                background-color: #ecf0f1;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def browse_save_path(self):
        """浏览保存路径"""
        url = self.url_input.text().strip()
        filename = ""
        
        # 尝试从URL中提取文件名
        if url:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = "download_file"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "选择保存位置", 
            filename,
            "所有文件 (*.*)"
        )
        
        if file_path:
            self.path_input.setText(file_path)
    
    def start_download(self):
        """开始下载"""
        url = self.url_input.text().strip()
        save_path = self.path_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "警告", "请输入下载链接！")
            return
        
        if not save_path:
            QMessageBox.warning(self, "警告", "请选择保存路径！")
            return
        
        # 创建保存目录
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建保存目录: {str(e)}")
                return
        
        # 更新UI状态
        self.is_downloading = True
        self.download_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("正在连接...")
        self.progress_bar.setValue(0)
        
        # 创建并启动下载线程
        self.download_worker = DownloadWorker(url, save_path)
        self.download_worker.progress_updated.connect(self.on_progress_updated)
        self.download_worker.download_finished.connect(self.on_download_finished)
        self.download_worker.start()
    
    def pause_download(self):
        """暂停/恢复下载"""
        if self.download_worker and self.is_downloading:
            if self.pause_button.text() == "暂停":
                self.download_worker.pause()
                self.pause_button.setText("恢复")
                self.status_label.setText("下载已暂停")
            else:
                self.download_worker.resume()
                self.pause_button.setText("暂停")
                self.status_label.setText("正在下载...")
    
    def cancel_download(self):
        """取消下载"""
        if self.download_worker and self.is_downloading:
            self.download_worker.cancel()
    
    def on_progress_updated(self, progress, speed, size):
        """更新进度显示"""
        self.progress_bar.setValue(progress)
        self.speed_label.setText(f"下载速度: {speed}")
        self.status_label.setText(f"正在下载... {size}")
    
    def on_download_finished(self, success, message):
        """下载完成回调"""
        self.is_downloading = False
        self.download_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.cancel_button.setEnabled(False)
        
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("下载完成！")
            self.speed_label.setText("下载速度: 0 B/s")
            QMessageBox.information(self, "成功", message)
        else:
            self.status_label.setText("下载失败")
            self.speed_label.setText("下载速度: 0 B/s")
            QMessageBox.critical(self, "错误", message)
        
        if self.download_worker:
            self.download_worker.deleteLater()
            self.download_worker = None


class FolderScanWindow(QWidget):
    """文件夹检索窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.scan_worker = None
    
    def init_ui(self):
        self.setWindowTitle("文件夹检索工具")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # 路径输入区域
        input_layout = QHBoxLayout()
        
        path_label = QLabel("文件夹路径:")
        path_label.setFont(QFont("Microsoft YaHei", 10))
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请输入要检索的文件夹路径，例如: C:\\Users")
        self.path_input.setFont(QFont("Microsoft YaHei", 10))
        
        browse_button = QPushButton("浏览")
        browse_button.setFont(QFont("Microsoft YaHei", 10))
        browse_button.clicked.connect(self.browse_folder)
        
        confirm_button = QPushButton("确认")
        confirm_button.setFont(QFont("Microsoft YaHei", 10))
        confirm_button.clicked.connect(self.scan_folder)
        
        input_layout.addWidget(path_label)
        input_layout.addWidget(self.path_input)
        input_layout.addWidget(browse_button)
        input_layout.addWidget(confirm_button)
        
        # 结果显示区域
        result_label = QLabel("扫描结果:")
        result_label.setFont(QFont("Microsoft YaHei", 10))
        
        self.result_text = QTextEdit()
        self.result_text.setFont(QFont("Consolas", 9))
        self.result_text.setPlaceholderText("点击确认按钮开始扫描...")
        
        layout.addLayout(input_layout)
        layout.addWidget(result_label)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def browse_folder(self):
        """浏览文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self.path_input.setText(folder_path)
    
    def scan_folder(self):
        """开始扫描文件夹"""
        folder_path = self.path_input.text().strip()
        
        if not folder_path:
            QMessageBox.warning(self, "警告", "请输入文件夹路径！")
            return
        
        # 显示扫描中状态
        self.result_text.setText("正在扫描，请稍候...")
        
        # 创建并启动工作线程
        self.scan_worker = FolderScanWorker(folder_path)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()
    
    def on_scan_finished(self, result):
        """扫描完成回调"""
        self.result_text.setText(result)
        if self.scan_worker:
            self.scan_worker.deleteLater()
            self.scan_worker = None


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.folder_scan_window = None
        self.download_window = None
    
    def init_ui(self):
        self.setWindowTitle("Denny自动程序合辑")
        self.setGeometry(100, 100, 400, 300)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("Denny自动程序合辑")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin: 20px;")
        
        # 文件夹检索工具按钮
        folder_scan_button = QPushButton("文件夹检索工具")
        folder_scan_button.setFont(QFont("Microsoft YaHei", 12))
        folder_scan_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        folder_scan_button.clicked.connect(self.open_folder_scan_window)
        
        # 下载工具按钮
        download_button = QPushButton("下载工具")
        download_button.setFont(QFont("Microsoft YaHei", 12))
        download_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        download_button.clicked.connect(self.open_download_window)
        
        # 添加到布局
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(folder_scan_button, alignment=Qt.AlignCenter)
        layout.addWidget(download_button, alignment=Qt.AlignCenter)
        layout.addStretch()
        
        central_widget.setLayout(layout)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
        """)
    
    def open_folder_scan_window(self):
        """打开文件夹检索窗口"""
        if self.folder_scan_window is None:
            self.folder_scan_window = FolderScanWindow()
        
        self.folder_scan_window.show()
        self.folder_scan_window.raise_()
        self.folder_scan_window.activateWindow()
    
    def open_download_window(self):
        """打开下载工具窗口"""
        if self.download_window is None:
            self.download_window = DownloadWindow()
        
        self.download_window.show()
        self.download_window.raise_()
        self.download_window.activateWindow()


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
