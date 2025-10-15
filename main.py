import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QLabel, QLineEdit, QTextEdit, 
                               QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


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
        
        # 添加到布局
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(folder_scan_button, alignment=Qt.AlignCenter)
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


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
