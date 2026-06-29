"""
文本清洗工具 - 处理 PDF/EPUB 提取文本中的常见问题
"""
import re


def clean_text(text: str) -> str:
    """清洗文本：合并断行、去除噪声"""
    lines = text.split('\n')
    cleaned = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append('')
            continue

        # 跳过页码、页眉
        if re.match(r'^\d{1,4}$', stripped):
            continue
        if re.match(r'^第[一二三四五六七八九十\d]+章', stripped):
            cleaned.append(stripped)
            cleaned.append('')
            continue

        # 合并断行：如果上一行不以标点结尾，且当前行不是新段落
        if cleaned and cleaned[-1] and not re.search(r'[。！？；：）\)」』"』]$', cleaned[-1]):
            if not re.match(r'^(\d+\.|第|图\d|表\d|[A-Z][a-z])', stripped):
                cleaned[-1] += stripped
                continue

        cleaned.append(stripped)

    # 清理多余空行
    result = '\n'.join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result


def split_chapters(text: str) -> dict:
    """按章节分割文本，返回 {章节号: 文本}"""
    lines = text.split('\n')
    chapters = {}
    current_ch = None
    CH_PAT = re.compile(r'第([一二三四五六七八九十\d]+)章')
    chapter_lines = []

    for line in lines:
        m = CH_PAT.match(line.lstrip('\ufeff').strip())
        if m:
            cn = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}.get(m.group(1))
            if cn is None:
                try:
                    cn = int(m.group(1))
                except ValueError:
                    cn = None
            if cn is not None:
                if current_ch is not None:
                    chapters[current_ch] = '\n'.join(chapter_lines)
                current_ch = cn
                chapter_lines = [line]
        elif current_ch is not None:
            chapter_lines.append(line)

    if current_ch is not None:
        chapters[current_ch] = '\n'.join(chapter_lines)

    return chapters


def extract_chapter_titles(text: str, chapters: dict) -> dict:
    """从文本中提取章节标题，返回 {标题文本: 章节号}"""
    title_pattern = re.compile(r'^(\d+(?:\.\d+)+)\s+(.+)$')
    section_titles = {}

    for line in text.split('\n'):
        line_stripped = line.strip()
        m = title_pattern.match(line_stripped)
        if m:
            title_text = m.group(2).strip()
            if '本章小结' in title_text:
                continue
            top_level = int(m.group(1).split('.')[0])
            if top_level in chapters:
                section_titles[title_text] = top_level

    return section_titles


def clean_paragraph(text: str) -> str:
    """清洗段落文本：合并断行、去除图表噪声"""
    # 合并不以标点结尾的断行
    lines = text.split('\n')
    merged = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            merged.append('')
            continue
        if merged and merged[-1] and not re.search(r'[。！？；：）\)」』"』]$', merged[-1]):
            merged[-1] += stripped
            continue
        merged.append(stripped)

    result = '\n'.join(merged)
    # 去除图表引用
    result = re.sub(r'^(图\d+[-–—]\d+.*?[。；\n])', '', result)
    result = re.sub(r'^(表\d+[-–—]\d+.*?[。；\n])', '', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()