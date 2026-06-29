# 命令行工具

`kg-build` 是项目提供的命令行工具。

## 用法

```bash
kg-build <input> [options]
```

## 位置参数

| 参数 | 说明 |
|------|------|
| `input` | 电子文件路径（PDF/EPUB/DOCX/PPTX/XLSX/HTML/MD/TXT/图片） |

## 可选参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--output PATH` | 自动生成 | 输出 JSON 文件路径 |
| `--js PATH` | 自动生成 | 输出 JS 文件路径 |
| `--model NAME` | `qwen2.5:3b` | Ollama 模型名 |
| `--summary` | `False` | 是否启用 LLM 摘要 |
| `--stats` | `False` | 仅统计已有 JSON |

## 示例

```bash
# 基础用法
kg-build book.pdf

# 指定输出
kg-build book.pdf --output data/kg.json --js data/kg.js

# 启用摘要
kg-build book.epub --summary --model qwen2.5:7b

# 统计
kg-build data/kg.json --stats
```

## 输出示例

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
