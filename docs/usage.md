# 快速开始

## 1. 命令行

```bash
# 从 PDF 构建知识图谱
kg-build book.pdf --output data.json --js data.js

# 启用 LLM 摘要
kg-build book.epub --summary --model qwen2.5:7b

# 支持的格式：pdf / epub / docx / pptx / xlsx / html / md / txt / 图片
kg-build book.docx --output data.json
kg-build book.txt  --output data.json
```

输出示例：

```text
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

## 2. Python API

```python
from kg_core import KnowledgeGraphBuilder

# 初始化
builder = KnowledgeGraphBuilder("book.pdf", model_name="qwen2.5:3b")

# 1. 加载书籍（自动识别格式）
builder.load_book()

# 2. 提取实体（章节标题 + 参考文献编号）
builder.extract_entities()

# 3. 提取定义与上下文段落
builder.extract_definitions_and_paragraphs()

# 4. 建立实体关系
builder.build_relations()

# 5. 拿到完整数据
data = builder.build()

# 6. 保存
builder.save_json("data.json")   # 完整 JSON
builder.save_js("data.js")        # 前端可加载
builder.save_md("data.md", book_name="我的书")  # 原文按章节保存
```

## 3. 桌面应用

```bash
# 命令行启动
kg-desktop
# 或
python -m kg_app.desktop
```

打开后：

1. 点击「选择电子文件」选择 PDF/EPUB/DOCX/...
2. 选择 LLM 模型（默认 `qwen2.5:3b`）
3. 点击「开始构建」
4. 在窗口中浏览知识图谱
