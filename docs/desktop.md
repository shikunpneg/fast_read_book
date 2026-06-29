# 桌面应用

`kg-book-tool` 提供 Tkinter 桌面 GUI。

## 启动

=== "命令行"
    ```bash
    kg-desktop
    # 或
    python -m kg_app.desktop
    ```

=== "Python"
    ```python
    from kg_app.desktop import main
    main()
    ```

## 功能

- **文件选择**：原生文件对话框，选择 PDF/EPUB/DOCX/...
- **模型选择**：下拉框选 Ollama 模型
- **后台构建**：多线程，不卡 UI
- **三视图阅读器**：
  - 实体列表
  - 思维导图
  - 原文对照
- **导出**：JSON / JS / Markdown

## 平台要求

=== "Windows"
    Tkinter 随 Python 自带。

=== "macOS"
    ```bash
    brew install python-tk
    ```

=== "Linux (Ubuntu/Debian)"
    ```bash
    sudo apt install python3-tk
    ```

## 截图

（待补充）
