# DennyWindowsAutoTools

一个基于PySide6开发的Windows桌面应用程序合辑，目前包含文件夹检索工具。

## 功能特性

### 文件夹检索工具
- 🔍 扫描指定文件夹下的所有子文件夹
- 📊 显示每个子文件夹的大小统计
- 🎯 支持文件夹浏览器选择路径
- ⚡ 多线程扫描，界面不卡顿
- 🛡️ 权限错误处理和异常捕获

## 安装要求

- Python 3.7 或更高版本
- Windows 操作系统

## 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd DennyWindowsAutoTools
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行应用程序**
   ```bash
   python main.py
   ```

## 打包成EXE文件

如果你想将应用程序打包成独立的exe文件，可以使用以下方法：

### 方法一：简单打包
1. **双击运行** `build_exe.bat`
2. 等待打包完成
3. 在 `dist/` 文件夹中找到 `DennyAutoTools.exe`

### 方法二：高级打包（推荐）
1. **双击运行** `build_exe_advanced.bat`
2. 使用优化的配置进行打包
3. 生成更小、更优化的exe文件

### 手动打包命令
```bash
# 安装PyInstaller
pip install pyinstaller

# 简单打包
pyinstaller --onefile --windowed --name="DennyAutoTools" main.py

# 或使用配置文件
pyinstaller main.spec
```

### 打包后的优势
- ✅ **独立运行**：无需安装Python环境
- ✅ **单文件**：所有依赖打包在一个exe中
- ✅ **便于分享**：可以直接发送给其他人使用
- ✅ **无控制台**：运行时不显示命令行窗口

## 使用说明

### 启动应用程序
1. 运行 `python main.py`
2. 主窗口将显示 "Denny自动程序合辑" 标题
3. 点击 "文件夹检索工具" 按钮

### 使用文件夹检索工具
1. 在新打开的窗口中，输入要检索的文件夹路径
   - 可以直接输入路径，如：`C:\Users`
   - 或点击 "浏览" 按钮选择文件夹
2. 点击 "确认" 按钮开始扫描
3. 扫描结果将显示在下方文本框中，包括：
   - 子文件夹名称
   - 每个文件夹的大小（自动格式化为 B/KB/MB/GB/TB）

## 项目结构

```
DennyWindowsAutoTools/
├── main.py                 # 主应用程序文件
├── main.spec              # PyInstaller配置文件
├── requirements.txt       # Python依赖包列表
├── install.bat           # 安装脚本
├── run.bat              # 运行脚本
├── build_exe.bat        # 简单打包脚本
├── build_exe_advanced.bat # 高级打包脚本
├── dist/                # 打包输出目录（生成后）
│   └── DennyAutoTools.exe # 生成的可执行文件
└── README.md           # 项目说明文档
```

## 技术实现

- **GUI框架**: PySide6 (Qt6 for Python)
- **多线程**: QThread 用于文件夹扫描，避免界面冻结
- **文件系统**: os 模块进行文件夹遍历和大小计算
- **异常处理**: 完善的权限和错误处理机制

## 注意事项

- 扫描大型文件夹可能需要较长时间，请耐心等待
- 某些系统文件夹可能因权限限制无法访问
- 建议在扫描前确保有足够的系统资源

## 后续功能规划

- [ ] 文件搜索工具
- [ ] 重复文件查找器
- [ ] 文件批量重命名工具
- [ ] 系统清理工具

### mainly use to simply my daily work