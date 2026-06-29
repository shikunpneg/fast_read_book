# 支持的输入格式

| 格式 | 扩展名 | 解析器 | 备注 |
|------|--------|--------|------|
| PDF（文本型） | `.pdf` | PyMuPDF | 优先 |
| PDF（图像型） | `.pdf` | EasyOCR | 自动回退 |
| EPUB | `.epub` | ebooklib | |
| Word | `.docx` | python-docx | |
| PowerPoint | `.pptx` | python-pptx | |
| Excel | `.xlsx` | openpyxl | |
| HTML | `.html` `.htm` | beautifulsoup4 | |
| Markdown | `.md` `.markdown` | 内置 | |
| 纯文本 | `.txt` | 内置 | 自动检测编码 |
| 图片 | `.png` `.jpg` `.jpeg` `.bmp` `.tiff` | EasyOCR | |

## 编码支持

自动检测以下编码：

- UTF-8 / UTF-8 with BOM
- GBK / GB2312 / GB18030
- Big5
- Latin-1 / ISO-8859-1
- Windows-1252
- ASCII

依赖：`chardet` + `charset_normalizer`。

## OCR 行为

当 PDF 文本提取后字符数 < 阈值（默认 100 / 页）时，自动判定为图像型 PDF，调用 EasyOCR（首次使用会下载模型）。

如果想强制使用 OCR：

```python
from kg_core.converters import ocr_pdf
text = ocr_pdf("image_only.pdf", lang="ch_sim+en")
```

## 参考文献识别

自动检测参考文献小节起点：

- `参考文献` / `References` / `Bibliography`

将编号条目合并为 Markdown 列表：

```text
# 输入
参考文献
[1] Singhal A. Modern IR. 2010.
[2] Robertson S. BM25. 2009.

# 输出
参考文献

- [1] Singhal A. Modern IR. 2010.
- [2] Robertson S. BM25. 2009.
```
