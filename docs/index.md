# kg-book-tool

> 将电子书（PDF / EPUB / DOCX / PPTX / XLSX / HTML / Markdown / 图片）自动转换为**交互式知识图谱**。

[![PyPI version](https://img.shields.io/pypi/v/kg-book-tool.svg)](https://pypi.org/project/kg-book-tool/)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/shikunpneg/fast_read_book/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/kg-book-tool)](https://pepy.tech/project/kg-book-tool)
[![CI](https://github.com/shikunpneg/fast_read_book/actions/workflows/ci.yml/badge.svg)](https://github.com/shikunpneg/fast_read_book/actions/workflows/ci.yml)
[![Release](https://github.com/shikunpneg/fast_read_book/actions/workflows/release.yml/badge.svg)](https://github.com/shikunpneg/fast_read_book/actions/workflows/release.yml)
[![Docs](https://github.com/shikunpneg/fast_read_book/actions/workflows/docs.yml/badge.svg)](https://shikunpneg.github.io/fast_read_book/)

## 特性

- 📚 **多格式支持** — PDF / EPUB / DOCX / PPTX / XLSX / HTML / Markdown / TXT
- 🖼️ **OCR 回退** — 自动检测图像型 PDF 并调用 EasyOCR（中文支持）
- 🔤 **编码自动检测** — UTF-8 / GBK / GB2312 / GB18030 / Big5 / Latin-1
- 📖 **参考文献识别** — 自动将"参考文献"小节的编号条目提取为实体
- 🌐 **桌面应用** — Tkinter 原生 GUI
- 🎯 **三视图阅读器** — 实体列表、思维导图、原文对照
- 🪄 **LLM 摘要** — 集成 Ollama，支持 qwen2.5 等模型

## 安装

```bash
pip install kg-book-tool
```

## 快速开始

```bash
# 命令行
kg-build book.pdf --output data.json --js data.js

# 启用 LLM 摘要
kg-build book.epub --summary --model qwen2.5:7b
```

```python
from kg_core import KnowledgeGraphBuilder

builder = KnowledgeGraphBuilder("book.pdf", model_name="qwen2.5:3b")
builder.load_book()
builder.extract_entities()
builder.extract_definitions_and_paragraphs()
builder.build_relations()
data = builder.build()

builder.save_json("data.json")
builder.save_js("data.js")
builder.save_md("data.md", book_name="我的书")
```

## 链接

- 📦 [PyPI 包](https://pypi.org/project/kg-book-tool/)
- 🐙 [GitHub 仓库](https://github.com/shikunpneg/fast_read_book)
- 📖 [完整文档](https://shikunpneg.github.io/fast_read_book/)
- 🐛 [问题反馈](https://github.com/shikunpneg/fast_read_book/issues)
- 📜 [更新日志](changelog.md)

## 许可

MIT License
