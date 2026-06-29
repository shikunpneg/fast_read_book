# 安装

## 系统要求

- Python 3.8+
- 操作系统：Windows / macOS / Linux

## 通过 pip 安装（推荐）

```bash
pip install kg-book-tool
```

默认会安装所有核心依赖，包括 PDF / EPUB / DOCX / PPTX / XLSX / HTML / OCR。

## 验证安装

```bash
kg-build --help
python -c "import kg_core; print(kg_core.__version__)"
```

## 源码安装

```bash
git clone https://github.com/shikunpneg/fast_read_book.git
cd fast_read_book
pip install -e .
```

## 桌面应用额外依赖

桌面 GUI 需要 Tkinter（Python 自带）：

=== "Windows"
    `tkinter` 随 Python 一起安装。

=== "macOS"
    ```bash
    brew install python-tk
    ```

=== "Ubuntu / Debian"
    ```bash
    sudo apt install python3-tk
    ```

## 常见问题

!!! question "ModuleNotFoundError: No module named 'fitz'"
    手动安装：`pip install pymupdf`

!!! question "EasyOCR 首次运行慢"
    首次会下载模型（约 100MB），需要联网。

!!! question "中文乱码"
    项目已内置 `chardet` + `charset_normalizer` 自动检测。如果仍有乱码，请报告 issue。
