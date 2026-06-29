# fast-read-book

> 将电子书（PDF / EPUB / DOCX / PPTX / XLSX / HTML / Markdown / 图片）自动转换为**交互式知识图谱**。

[![PyPI version](https://img.shields.io/pypi/v/kg-book-tool.svg)](https://pypi.org/project/kg-book-tool/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)


## ✨ 特性

- 📚 **多格式支持** — PDF / EPUB / DOCX / PPTX / XLSX / HTML / Markdown / TXT
- **可以一键生成各个章节的实体思维导图，便于快速了解全书内容和结构**
- **交互性体现在可点击的思维导图实体和原文档定位，方便了用户快速导航**
- **支持 LLM 摘要，为每个实体生成摘要，方便用户快速了解**
- **除了思维导图功能还有论证分析和叙事分析的发展线可视化，可以添加笔记**
- 🖼️ **OCR 回退** — 自动检测图像型 PDF 并调用 EasyOCR（中文支持）
- 🔤 **编码自动检测** — UTF-8 / GBK / GB2312 / GB18030 / Big5 / Latin-1
- 📖 **参考文献识别** — 自动将"参考文献"小节的编号条目（如 `[1] Singhal`）提取为实体
- 🌐 **桌面应用** — Tkinter 原生 GUI（双击启动）
- 🎯 **三视图阅读器** — 实体列表、思维导图、原文对照
![alt text](ltp\scripts\image\主页.png)
![alt text](ltp\scripts\image\思维导图生成.png)
![alt text](ltp\scripts\image\文本定位.png)

## 📦 安装

```bash
pip install kg-book-tool
```

> 默认已包含 PDF / EPUB / DOCX / PPTX / XLSX / HTML / OCR 全套依赖，**无需手动安装**额外组件。

## 🚀 快速开始

### 命令行

```bash
# 从电子书中构建知识图谱
kg-build book.pdf --output data.json --js data.js

# 启用 LLM 摘要
kg-build book.epub --summary --model qwen2.5:7b

# 支持的格式：pdf / epub / docx / pptx / xlsx / html / md / txt / 图片
kg-build book.docx --output data.json
```

### Python API

```python
from kg_core import KnowledgeGraphBuilder

builder = KnowledgeGraphBuilder("book.pdf", model_name="qwen2.5:3b")
builder.load_book()                                # 自动识别格式
builder.extract_entities()                         # 章节标题 + 参考文献
builder.extract_definitions_and_paragraphs()        # 实体定义与上下文
builder.build_relations()                          # 实体关系
data = builder.build()                             # 返回完整字典

builder.save_json("data.json")
builder.save_js("data.js")                         # 前端可用
builder.save_md("data.md", book_name="我的书")      # 原文按章节保存
```

### 桌面应用

```bash
# 命令行启动
kg-desktop
# 或
python -m kg_app.desktop
```

Tkinter 原生窗口，包含：
- 选择电子文件
- 一键构建
- 实时查看知识图谱
- 实体浏览 / 关系网络 / 原文对照

## 🛠️ 支持的输入格式

| 格式 | 扩展名 | 解析器 |
|------|--------|--------|
| PDF（文本型） | `.pdf` | PyMuPDF |
| PDF（图像型） | `.pdf` | EasyOCR（自动回退） |
| EPUB | `.epub` | ebooklib |
| Word | `.docx` | python-docx |
| PowerPoint | `.pptx` | python-pptx |
| Excel | `.xlsx` | openpyxl |
| HTML | `.html` / `.htm` | beautifulsoup4 |
| Markdown | `.md` | 内置 |
| 纯文本 | `.txt` | 内置（自动检测编码） |
| 图片 | `.png` / `.jpg` / ... | EasyOCR |

## 📊 输出示例

```bash
$ kg-build book.pdf --output data.json --js data.js
[kg-build] 开始构建知识图谱...
  书籍: book.pdf
  模型: qwen2.5:3b
  摘要: 否
  JSON: data.json
  JS:   data.js

构建完成!
  实体: 304
  关系: 26832
  有摘要: 0
  有定义: 220
  有段落: 295
```

## 📂 项目结构

```
kg-book-tool/
├── kg_core/                  # 核心库（pip 入口）
│   ├── __init__.py
│   ├── builder.py            # KnowledgeGraphBuilder：构建流程
│   ├── converters.py         # 多格式转换 + OCR 回退
│   ├── text_cleaner.py       # 编码检测与文本清洗
│   ├── summarizer.py         # LLM 摘要（Ollama）
│   └── cli.py                # kg-build 命令行
├── kg_app/                   # Web + 桌面应用
│   ├── desktop.py            # Tkinter 桌面入口
│   ├── main.py               # Flask 后端
│   ├── gui.py                # 旧版 GUI
│   ├── templates/            # 渲染模板
│   │   ├── index.html
│   │   └── reader.html
│   └── static/
│       ├── data/             # 生成的知识图谱数据
│       └── uploads/          # 用户上传的电子文件
├── scripts/                  # 辅助脚本
├── setup.py                  # pip 打包配置
├── requirements.txt
├── prompt.json               # LLM prompt 配置
├── deploy.ps1                # 一键部署脚本
└── DEPLOY.md                 # 部署指南
```

## 🧪 验证安装

```python
import kg_core
print(kg_core.__version__)               # '1.0.0'

from kg_core import (
    KnowledgeGraphBuilder,
    SummaryGenerator,
    clean_text,
    split_chapters,
)
print("All imports OK")
```

## 🐛 故障排查

| 问题 | 解决 |
|------|------|
| `ModuleNotFoundError: No module named 'fitz'` | `pip install pymupdf` |
| `easyocr` 首次运行慢 | 首次会下载模型（约 100MB） |
| 中文乱码 | 项目已内置 `chardet` + `charset_normalizer` 自动检测 |
| 图像型 PDF 提取为空 | 项目已内置 EasyOCR 回退 |
| 参考文献未识别 | 实体识别优先用后端 `is_reference` 字段，详见 `kg_core/builder.py` |

## 📜 许可

MIT License — 详见 [LICENSE](LICENSE)

## 🔗 链接

- 📦 PyPI: <https://pypi.org/project/kg-book-tool/>
- 🐙 GitHub: <https://github.com/shikunpneg/fast_read_book>
- 📖 文档: <https://shikunpneg.github.io/fast_read_book/>
- 🐛 Issues: <https://github.com/shikunpneg/fast_read_book/issues>
- 📜 更新日志: [CHANGELOG.md](CHANGELOG.md)
- 🚀 部署: [DEPLOY.md](DEPLOY.md)
