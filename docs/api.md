# Python API

## `KnowledgeGraphBuilder`

主入口类。完整构建流程：

```python
from kg_core import KnowledgeGraphBuilder

builder = KnowledgeGraphBuilder(file_path, model_name="qwen2.5:3b")
```

### 构造参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `file_path` | `str` | 必填 | 电子文件路径（自动识别格式） |
| `model_name` | `str` | `"qwen2.5:3b"` | Ollama 模型名（仅 `summary=True` 时使用） |

### 方法

#### `load_book()`
加载并解析电子文件。自动识别格式：

- PDF（文本型）→ PyMuPDF
- PDF（图像型）→ EasyOCR 自动回退
- EPUB → ebooklib
- DOCX → python-docx
- PPTX → python-pptx
- XLSX → openpyxl
- HTML → beautifulsoup4
- Markdown / TXT → 内置解析（自动检测编码）

#### `extract_entities()`
提取实体：

- 章节标题（一级、二级标题）
- 参考文献编号（`[1] Singhal` 等）

返回 `List[Entity]`，每个 Entity 包含 `name`、`is_reference`、`chapter` 等字段。

#### `extract_definitions_and_paragraphs()`
为每个实体提取：

- `definition`：核心定义
- `paragraphs`：相关上下文段落

#### `build_relations()`
构建实体间的语义关系（共现、引用、衍生等）。

#### `build()`
返回完整的 dict，可直接 `json.dump`：

```python
{
    "book_name": "...",
    "entities": [...],
    "relations": [...],
    "chapters": [...],
    "stats": {...}
}
```

#### `save_json(path)`
保存为 JSON 文件。

#### `save_js(path)`
保存为 JS 文件（前端可直接 `loadKnowledgeGraph()`）。

#### `save_md(path, book_name="")`
保存原文为 Markdown，按章节组织，自动格式化参考文献小节。

---

## 工具函数

### `clean_text(text)`
清洗文本：去除多余空白、不可见字符、合并换行等。

### `split_chapters(text)`
按章节切分文本，返回 `Dict[chapter_num, chapter_text]`。

---

## `SummaryGenerator`

LLM 摘要生成器（基于 Ollama）：

```python
from kg_core import SummaryGenerator

gen = SummaryGenerator(model_name="qwen2.5:3b")
summary = gen.generate("一段文本...")
```

---

## 命令行接口

```bash
kg-build <input> [--output JSON] [--js JS] [--model NAME] [--summary]
```

详见 [命令行工具](cli.md)。
